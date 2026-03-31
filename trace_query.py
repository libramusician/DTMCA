import json
import socket
import time
import urllib.parse
from collections import defaultdict

import prometheus_client
import requests
import pandas as pd
import urllib3.util.connection as urllib3_cn
from prometheus_client import Gauge, CollectorRegistry, Counter, Histogram, start_http_server

from dc2 import Trace, SpanNode, Process
from formatting.format import print_trace_tree

# ipv4 only
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
registry = CollectorRegistry()

# operation_success_gauge = Gauge(name='operation_success',documentation='number of successful operations per min',
#                                     labelnames=['service','operation'], registry=registry)
operation_fail_gauge = Gauge(name='operation_fail',documentation='number of failed operations per min',
                                    labelnames=['service','operation'], registry=registry)
operation_latency_histogram = Histogram(
    'operation_duration_microseconds',
    'Operation duration in microseconds in a minute',
    ['service', 'operation'],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
    registry=registry
)

# -------------------------
# GLOBAL TRACE BUFFER (NEW)
# -------------------------
trace_records = []

def find_root_cause(current_span, root_causes):
    """
    有人背锅就往外甩，否则自己背
    """
    if current_span.caused_by_failed_spans:
        for cause_span in current_span.caused_by_failed_spans:
            find_root_cause(cause_span, root_causes)
    else:
        root_causes.append(current_span)



def get_traces_by_service_jaeger_url(service_name, start, end):
    params = {
        "service": service_name,
        "start": start,
        "end": end,
    }
    base_url = "http://192.168.1.27:8080/jaeger/ui/api/traces"
    return f"{base_url}?{urllib.parse.urlencode(params)}"


def record_operation_metrics(span_node: SpanNode):
    service = span_node.service
    operation = span_node.operation

    if not service or not operation:
        return

    duration = span_node.duration / 1000  # ms
    timestamp = int(span_node.start_time_stamp / 1_000_000)  # seconds

    error = 1 if span_node.error else 0

    # -------------------------
    # NEW: store for CSV
    # -------------------------
    trace_records.append({
        "time": timestamp,
        "service": service,
        "operation": operation,
        "latency": duration,
        "error": error
    })

    # Existing Prometheus logic
    if span_node.error:
        operation_fail_gauge.labels(service=service, operation=operation).inc(1)

    operation_latency_histogram.labels(
        service=service,
        operation=operation,
    ).observe(duration)


def query_container_metrics(container_id, start, end):
    metric_list = []
    for m in range(len(metric_list)):
        params = {
            "query": metric_list[m],
            "start": start,
            "end": end,
            "step": "15s"
        }
        response = requests.get("http://127.0.0.1:9090/api/v1/query_range", params=params)
        res = json.dumps(response.json(), indent=2)
        res = json.loads(res)


def get_traces_by_service(service_name):
    end_ts = int(time.time() * 1_000_000)
    due_ts = end_ts - (1 * 60 * 1_000_000)
    start_ts = end_ts - (30 * 60 * 1_000_000)  # 30 minutes
    url = get_traces_by_service_jaeger_url(service_name, start_ts, end_ts)
    response = requests.get(url, timeout=5)
    data = response.json()['data']

    if not data:
        return None
    failed_services_count = defaultdict(int)
    serviceA_failed_due_to_serviceB_count = defaultdict(int)
    problem_container_ids = set()
    for trace in data:
        trace_id = trace['traceID']
        spans = trace['spans']
        processes = {}
        failed_services: set[str] = set()
        root_span = None
        orphans = []
        # 解析trace涉及的process
        for process_id, process in trace['processes'].items():
            tag_dict = {tag["key"]: tag["value"] for tag in process['tags']}
            p = Process(id=process_id)
            p.hostname = tag_dict.get('host.name')
            p.container_id = tag_dict.get('container.id')
            p.serviceName = process.get('serviceName')
            processes[process_id] = p
        spans_dict:dict[str, SpanNode] = {}
        # 构造span node
        for span in spans:
            trace_id = span['traceID']
            span_id = span['spanID']
            operation = span['operationName']
            parent_span_id = None
            for reference in span['references']:
                if reference['refType'] == "CHILD_OF":
                    parent_span_id = reference['spanID']

            start_time = span['startTime']
            duration = span['duration']
            tag_dict = {tag["key"]: tag["value"] for tag in span['tags']}
            error = tag_dict.get('error')
            process_id = span['processID']
            process = processes[process_id]
            span_node = SpanNode(trace_id=trace_id, span_id=span_id, operation=operation,
                                 parent_id=parent_span_id, start_time_stamp=start_time,
                                 duration=duration, service=processes[process_id].serviceName,error=error, children=[],
                                 process=process,
                                 caused_by_failed_spans=[]
                                 )
            spans_dict[span_id] = span_node
            if not parent_span_id:
                root_span = span_node
        # stop if trace is incomplete
        if not root_span:
            continue
        if root_span.start_time_stamp > due_ts:
            continue
        # 连接span
        for span_id, span in spans_dict.items():
            parent_id = span.parent_id
            if parent_id:
                # span 可以连接父span
                if parent_id in spans_dict:
                    spans_dict[parent_id].children.append(span)
                # 孤儿span
                else:
                    orphans.append(span)

            # 如果该span fail了，它是父span失败的原因之一
            # 假设0.5s以上是慢
            if span.error or span.duration > 500_000:
                if parent_id and parent_id in spans_dict:
                    spans_dict[parent_id].caused_by_failed_spans.append(span)
                if span.service:
                    failed_services.add(span.service)
            # record_operation_metrics(span)
        root_causes: list[SpanNode] = []
        # 第三遍，如果有失败找根因
        if len(failed_services) > 0:
            find_root_cause(root_span, root_causes)
        # fallback, 假设孤儿服务也是根因
        for orphan in orphans:
            root_causes.append(orphan)
        trace = Trace(
            trace_id=trace_id,
            root=root_span,
            failed_services=failed_services,
            root_causes=root_causes,
            spans=spans_dict,
            start_time_stamp=root_span.start_time_stamp,
            orphans=orphans
        )
        print_trace_tree(trace)

        for failed_service in trace.failed_services:
            failed_services_count[failed_service] += 1
            for span in trace.spans.values():
                if span.service:
                    serviceA_failed_due_to_serviceB_count[f'{failed_service}->{span.service}'] += 1

                record_operation_metrics(span)

                if span.process and span.process.container_id:
                    problem_container_ids.add(span.process.container_id)
        if failed_services_count:
            print(f'Failed services count: {failed_services_count.items()}')
        if serviceA_failed_due_to_serviceB_count:
            print(f'ServiceA failed due to serviceB: {serviceA_failed_due_to_serviceB_count.items()}')
    print(f"problem_container_ids: {problem_container_ids}")



def get_all_services():
    resp = requests.get("http://192.168.1.27:8080/jaeger/ui/api/services", timeout=5)
    return resp.json()["data"]

def get_all_traces():
    traces:dict[str,Trace] = {}
    services = get_all_services()
    for service in services:
        t = get_traces_by_service(service_name=service)



import os

def build_csv(filename="trace_metrics.csv", window=15):
    global trace_records

    if not trace_records:
        print("No trace records collected")
        return

    df = pd.DataFrame(trace_records)

    # Aggregate
    df["time"] = (df["time"] // window) * window
    grouped = df.groupby(["time", "service"])

    agg_df = grouped.agg({
        "latency": "mean",
        "error": "mean"
    }).reset_index()

    # Pivot
    latency_df = agg_df.pivot(index="time", columns="service", values="latency")
    error_df = agg_df.pivot(index="time", columns="service", values="error")

    latency_df.columns = [f"{s}_latency" for s in latency_df.columns]
    error_df.columns = [f"{s}_error_rate" for s in error_df.columns]

    df_final = pd.concat([latency_df, error_df], axis=1)
    df_final = df_final.sort_index().ffill().bfill().reset_index()

    # Drop constant columns
    non_time_cols = [c for c in df_final.columns if c != "time"]
    df_final = df_final[["time"] + [c for c in non_time_cols if df_final[c].nunique() > 1]]

    # -------------------------
    # ✅ Append instead of overwrite
    # -------------------------
    if os.path.exists(filename):
        df_final.to_csv(filename, mode='a', header=False, index=False)
    else:
        df_final.to_csv(filename, index=False)

    print(f"Appended to {filename}")

    # Keep only last N minutes (e.g., 1 hour)
    cutoff = int(time.time()) - 3600  # 1 hour

    trace_records = [r for r in trace_records if r["time"] >= cutoff]


if __name__ == '__main__':
    start_http_server(8000, registry=registry)
    # operation_success_gauge.clear()
    operation_fail_gauge.clear()
    operation_latency_histogram.clear()
    get_all_traces()
    # get_traces_by_service(service_name='recommendation')
    build_csv("trace_metrics.csv")
