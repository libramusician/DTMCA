from dc2 import Trace, SpanNode

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
    if span.duration > 500_000:
        return "⚠️ SLOW"
    return "✅ OK"


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

    for orphan in trace.orphans:
        children = orphan.children
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
    node_info = f"{node.service} {node.operation} [{duration_str}] {error_str} "

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