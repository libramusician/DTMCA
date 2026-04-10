import json
import pandas as pd
import time
import requests
from json_to_csv import create_jaegar_csv


def create_csv():
    PROM_URL = "http://app.libra.com:9090/api/v1/query_range"

    metric_service_dict = {"jvm_cpu_recent_utilization_ratio": "service_name", "container_memory_percent_ratio": "container_name",
                           "jvm_gc_duration_seconds_bucket": "service_name", "kafka_consumer_records_lag": "service_name"}

    end = time.time()
    start = end - 300  # last 5 minutes

    all_rows = {}

    for metric in list(metric_service_dict.keys()):
        params = {
            "query": metric,
            "start": start,
            "end": end,
            "step": "15s"
        }
        response = requests.get(PROM_URL, params=params)
        res = json.dumps(response.json(), indent=2)
        response = response.json()
        print(res)

        for ts in response['data']['result']:
            # pick a label to identify the column (e.g., host_name)
            name = ts['metric'].get('__name__')
            col_name = name + '_' + ts['metric'][metric_service_dict[name]]
            print("Column name:", col_name)
            # convert values into a Series
            times = [float(v[0]) for v in ts['values']]
            times = list(map(lambda x: x - times[0], times))
            values = [float(v[1]) for v in ts['values']]
            s = pd.Series(values, index=times)

            all_rows[col_name] = s

    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', None)
    # Optional: Adjust the console width so columns display side-by-side
    pd.set_option('display.width', None)
    # Combine into DataFrame
    df = pd.DataFrame(all_rows)

    # Reset index to make timestamp a column
    df = df.reset_index().rename(columns={'index': 'time'})
    df = df.sort_index()

    # Drop any extra unnamed columns
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    # Save CSV
    df.to_csv("prometheus_metrics/prometheus_metrics_recommendationCacheFailure.csv", index=False)
    time.sleep(5)
    prome_csv = pd.read_csv("prometheus_metrics/prometheus_metrics_recommendationCacheFailure.csv")
    print(prome_csv.shape)
    jaegar_csv = pd.read_csv("latency_and_error_services.csv")
    merged = pd.merge(prome_csv, jaegar_csv, on='time', how='inner')
    merged.to_csv("merged_metrics/merged_metrics_recommendationCacheFailure.csv", index=False)
    print(merged)

create_jaegar_csv()
time.sleep(5)
create_csv()