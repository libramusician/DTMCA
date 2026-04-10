from datetime import datetime, timedelta

import pandas as pd
import pytz

from dc import *
from trace_processor import process_trace
from utils.csvprocesser import read_dataframe_from_csv


def process_trace_worker(args):
    trace_id, trace_group = args
    try:
        trace = process_trace(trace_id, trace_group)
        end_time = datetime.fromtimestamp(trace.end_time_ms / 1000)
        min_key = datetime.strftime(end_time, "%Y-%m-%d %H:%M")
        return min_key, trace
    except Exception as e:
        print(f"Error processing trace {trace_id}: {e}")
        return None

def process_traces(csv_pattern: str):
    minute_buckets = {}
    df = read_dataframe_from_csv(csv_pattern)
    df['datetime'] = pd.to_datetime(df['startTime'], unit='ms', utc=True)
    df['minute_key'] = df['datetime'].dt.strftime('%Y-%m-%d %H:%M%z')
    time_buckets: Dict[str, pd.DataFrame] = {}
    for minute_key, group in df.groupby('minute_key'):
        time_buckets[minute_key] = group
    for minute_key in sorted(time_buckets.keys()):
        minute_bucket: MinuteBucket = MinuteBucket(minute_key)
        failed_services_in_this_minute_count = defaultdict(int)
        serviceA_failed_due_to_serviceB_count = defaultdict(int)
        current_dt = datetime.strptime(minute_key, '%Y-%m-%d %H:%M%z')
        next_dt = current_dt + timedelta(minutes=1)
        next_key = next_dt.strftime('%Y-%m-%d %H:%M%z')
        if next_key in time_buckets.keys():
            dfs = [time_buckets[minute_key], time_buckets[next_key]]
            time_buckets[minute_key] = pd.concat(dfs, ignore_index=True)
        for trace_id, trace_group in time_buckets[minute_key].groupby('traceId'):
            trace_group.sort_values(by=['startTime'], inplace=True)
            first_span = trace_group.iloc[0]
            first_span_minute = first_span['minute_key']
            if first_span_minute == minute_key and pd.isna(first_span['pid']):
                trace = process_trace(trace_id, trace_group)
                minute_bucket.traces[trace_id] = trace
        minute_buckets[minute_key] = minute_bucket
        exists_failure_in_this_minute = False
        for trace in minute_bucket.traces.values():
            if trace.failed_services:
                exists_failure_in_this_minute = True
                for failed_service in trace.failed_services:
                    failed_services_in_this_minute_count[failed_service] += 1
                    for root_cause in trace.root_causes:
                        root_cause: SpanNode
                        serviceA_failed_due_to_serviceB_count[f'{failed_service}->{root_cause.service}'] += 1
        if exists_failure_in_this_minute:
            print(f'failed_services_in_this_minute_count: {failed_services_in_this_minute_count}')
            print(f'serviceA_failed_due_to_serviceB_count: {serviceA_failed_due_to_serviceB_count}')
        dt = datetime.strptime(minute_key, '%Y-%m-%d %H:%M%z')
        shanghai_tz = pytz.timezone('Asia/Shanghai')
        dt_shanghai = dt.astimezone(shanghai_tz)
        print(f'processed {dt_shanghai.strftime("%Y-%m-%d %H:%M")}')
    print("done")

    # df_by_trace = df.groupby('traceId')
    # traces_per_min_list = [(trace_id, group) for trace_id, group in df_by_trace]
    # print(f"found {len(traces_per_min_list)} traces.")
    # max_workers = 14
    # with ProcessPoolExecutor(max_workers=max_workers) as executor:
    #     chunksize = max(1, len(traces_per_min_list) // (max_workers * 4))
    #     results = list(executor.map(process_trace_worker, traces_per_min_list, chunksize=chunksize))
    # time_bucket = defaultdict(list)
    # for result in results:
    #     if result is not None:
    #         min_key, trace = result
    #         time_bucket[min_key].append(trace)
    # print("done")


if __name__ == "__main__":
    process_traces("2020_05_23/trace/*.csv")
