import socket
import time
import urllib.parse
from collections import defaultdict

import requests
import urllib3.util.connection as urllib3_cn

from dc2 import Trace, SpanNode, Process

# ipv4 only
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

def format_duration(duration_us: int) -> str:
    """将微秒格式化为易读的时间"""
    if duration_us < 1000:
        return f"{duration_us}μs"
    elif duration_us < 1_000_000:
        return f"{duration_us / 1000:.2f}ms"
    else:
        return f"{duration_us / 1_000_000:.2f}s"


def get_error_status(span: SpanNode) -> str:
    """获取错误状态标识"""
    if span.error:
        return "❌ ERROR"
    return "✅ OK"

def find_root_cause(current_span, root_causes):
    """
    有人背锅就往外甩，否则自己背
    """
    if current_span.caused_by_failed_spans:
        for cause_span in current_span.caused_by_failed_spans:
            find_root_cause(cause_span, root_causes)
    else:
        root_causes.append(current_span)


def print_trace_tree(trace: Trace) -> None:
    root_span = trace.root
    duration_str = format_duration(root_span.duration)
    error_str = get_error_status(root_span)
    node_info = f"{root_span.operation} [{duration_str}] {error_str}"
    print(f"trace:{trace.trace_id}")
    print(f"failed_services:{trace.failed_services}")
    print(f"root_causes:{trace.root_causes}")

    print(node_info)
    # 准备子节点的前缀
    children = root_span.children
    child_count = len(children)
    for i, child in enumerate(children):
        is_last_child = (i == child_count - 1)
        print_span_tree(child, "    ", is_last_child)

def print_span_tree(node: SpanNode, prefix: str = "", is_last: bool = True) -> None:
    """
    打印 ASCII 树形拓扑图，保持连接线连贯

    Args:
        node: 当前 span 节点
        prefix: 前缀缩进（用于子节点）
        is_last: 是否是父节点的最后一个子节点
        is_root: 是否是根节点
    """
    # 当前节点的连接线（根节点不需要）
    connector = "└── " if is_last else "├── "
    # 非根节点需要显示父节点传来的 prefix（包含垂直线）
    current_prefix = prefix

    duration_str = format_duration(node.duration) if node.duration else ""
    error_str = get_error_status(node)
    node_info = f"{node.operation} [{duration_str}] {error_str}"

    print(f"{current_prefix}{connector}{node_info}")

    # 准备子节点的前缀
    children = node.children
    child_count = len(children)

    for i, child in enumerate(children):
        is_last_child = (i == child_count - 1)

        # 构建子节点的前缀
        # 非根节点：如果当前节点不是最后一个，需要保留垂直线 │
        if is_last:
            child_prefix = prefix + "    "
        else:
            child_prefix = prefix + "│   "

        print_span_tree(child, child_prefix, is_last_child)


def get_traces_by_service_jaeger_url(service_name, minutes_ago=2):
    # 当前时间微秒
    end_ts = int(time.time() * 1_000_000)
    # N分钟前微秒
    start_ts = end_ts - (minutes_ago * 60 * 1_000_000)

    params = {
        "service": service_name,
        "start": start_ts,
        "end": end_ts,
    }

    base_url = "http://localhost:8080/jaeger/ui/api/traces"
    return f"{base_url}?{urllib.parse.urlencode(params)}"

def get_traces_by_service(service_name, minutes_ago=2):
    url = get_traces_by_service_jaeger_url(service_name, minutes_ago)
    response = requests.get(url, timeout=5)
    data = response.json()['data']
    if not data:
        return None
    failed_services_count = defaultdict(int)
    serviceA_failed_due_to_serviceB_count = defaultdict(int)
    for trace in data:
        trace_id = trace['traceID']
        spans = trace['spans']
        processes = {}
        failed_services: set[str] = set()
        root_span = None
        # 解析trace涉及的process
        for process_id, process in trace['processes'].items():
            tag_dict = {tag["key"]: tag["value"] for tag in process['tags']}
            p = Process(id=process_id)
            p.hostname = tag_dict.get('host.name')
            p.container_id = tag_dict.get('container.id')
            p.serviceName = process.get('serviceName')
            processes[process_id] = p
        spans_dict = {}
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
        # 连接span
        for span_id, span in spans_dict.items():
            parent_id = span.parent_id
            if parent_id and parent_id in spans_dict:
                spans_dict[parent_id].children.append(span)
            # 如果该span fail了，它是父span失败的原因之一
            if span.error:
                if parent_id:
                    spans_dict[parent_id].caused_by_failed_spans.append(span)
                if span.service:
                    failed_services.add(span.service)
        root_causes: list[SpanNode] = []
        # 第三遍，如果有失败找根因
        if len(failed_services) > 0:
            find_root_cause(root_span, root_causes)
        trace = Trace(
            trace_id=trace_id,
            root=root_span,
            failed_services=failed_services,
            root_causes=root_causes,
            spans=spans_dict,
            start_time_stamp=root_span.start_time_stamp,
        )
        print_trace_tree(trace)
        for failed_service in trace.failed_services:
            failed_services_count[failed_service] += 1
            for root_cause in trace.root_causes:
                root_cause: SpanNode
                serviceA_failed_due_to_serviceB_count[f'{failed_service}->{root_cause.service}'] += 1
        if failed_services_count:
            print(f'Failed services count: {failed_services_count.items()}')
        if serviceA_failed_due_to_serviceB_count:
            print(f'ServiceA failed due to serviceB: {serviceA_failed_due_to_serviceB_count.items()}')


def get_all_services():
    resp = requests.get("http://localhost:8080/jaeger/ui//api/services", timeout=5)
    return resp.json()["data"]

def get_all_traces():
    traces:dict[str,Trace] = {}
    services = get_all_services()
    for service in services:
        t = get_traces_by_service(service_name=service, minutes_ago=2)

get_all_traces()