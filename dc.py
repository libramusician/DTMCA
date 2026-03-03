from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Set


@dataclass
class SpanNode:
    trace_id: str
    span_id: str
    operation: str
    parent_id: str
    start_time_stamp: int
    duration: float
    # tags
    service: str
    cmdb: str
    success: bool
    caused_by_failed_spans: list
    children: List['SpanNode'] = field(default_factory=list)

    def __gt__(self, other):
        return self.start_time_stamp > other.start_time_stamp

    def __lt__(self, other):
        return self.start_time_stamp < other.start_time_stamp

    def __hash__(self):
        return self.span_id

@dataclass
class Trace:
    """完整的trace，跨文件收集"""
    trace_id: str
    root: SpanNode
    spans: Dict[str, SpanNode]
    failed_services: Set[str]
    start_time_ms: int
    root_causes: list[SpanNode]


@dataclass
class ServiceMetrics:
    """服务级别的指标（被调用方统计）"""
    service: str
    total_calls: int = 0
    failed_calls: int = 0
    total_duration: float = 0.0

    @property
    def error_rate(self) -> float:
        return self.failed_calls / self.total_calls if self.total_calls > 0 else 0.0

    @property
    def avg_latency(self) -> float:
        return self.total_duration / self.total_calls if self.total_calls > 0 else 0.0


@dataclass
class EdgeMetrics:
    """服务间调用边指标（调用方->被调用方）"""
    source: str  # 调用方
    target: str  # 被调用方
    operation: str  # 调用操作名
    total_calls: int = 0
    failed_calls: int = 0
    total_duration: float = 0.0

    @property
    def error_rate(self) -> float:
        return self.failed_calls / self.total_calls if self.total_calls > 0 else 0.0

    @property
    def avg_latency(self) -> float:
        return self.total_duration / self.total_calls if self.total_calls > 0 else 0.0

    @property
    def edge_key(self) -> str:
        """用于去重的边标识"""
        return f"{self.source}|{self.target}|{self.operation}"



class MinuteBucket:
    def __init__(self, minute_key: str):
        self.minute_key = minute_key
        self.traces = {}
