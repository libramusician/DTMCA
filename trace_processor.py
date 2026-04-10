import numpy as np
import pandas as pd

from dc import SpanNode, Trace


def find_root_cause(current_span, root_causes):
    """
    有人背锅就往外甩，否则自己背
    """
    if current_span.caused_by_failed_spans:
        for cause_span in current_span.caused_by_failed_spans:
            find_root_cause(cause_span, root_causes)
    else:
        root_causes.append(current_span)

def process_trace(trace_id: str, trace_df: pd.DataFrame):
    # 将trace的spans按照时间排序，检查第一个是否有parent，有就是root，没有就是trace不完整跳过
    # trace_df = trace_df.sort_values('startTime')
    # first_span = trace_df.iloc[0]
    # if not np.isnan(first_span['pid']):
    #     print(f'drop trace {trace_id} due to no root')
    #     return None

    spans: dict[str, SpanNode] = {}
    failed_services: set[str] = set()
    root_span = None

    # 第一遍：创建所有节点
    for _, row in trace_df.iterrows():
        span_id = str(row['id'])
        parent_id = str(row['pid']) if pd.notna(row['pid']) else ''

        # 处理serviceName可能为nan的情况
        if pd.notna(row['serviceName']) and not row['serviceName'].startswith('local'):
            service_name = row['serviceName']
        else:
            service_name = row['dsName']

        node = SpanNode(
            trace_id=trace_id,
            span_id=span_id,
            parent_id=parent_id,
            service=service_name,
            instance_id=str(row['cmdb_id']),
            operation=str(row['callType']),
            duration=float(row['elapsedTime']),
            success=str(row['success']).lower() == 'true',
            start_time_stamp=int(row['startTime']),
            caused_by_failed_spans=[],
            children=[]
        )

        spans[node.span_id] = node
        if node.parent_id == '':
            root_span = node

    # 第二遍：构建树结构
    for span_id, span in spans.items():
        parent_id = span.parent_id
        if parent_id and parent_id in spans:
            spans[parent_id].children.append(span)
        # 如果该span fail了，它是父span失败的原因之一
        if not span.success:
            if parent_id != '':
                spans[parent_id].caused_by_failed_spans.append(span)
            if span.service != '':
                failed_services.add(span.service)

    root_causes: list[SpanNode] = []
    # 第三遍，如果有失败找根因
    if len(failed_services) > 0:
        find_root_cause(root_span, root_causes)

    # 存储trace
    return Trace(
        trace_id=trace_id,
        spans=spans,
        failed_services=failed_services,
        root=root_span,
        start_time_ms=root_span.start_time_stamp,
        root_causes=root_causes
    )

