import json
import pandas as pd
import time
import requests

PROM_URL = "http://192.168.1.27:9090/api/v1/query_range"
metric_flgd_dict = {"jvm_cpu_recent_utilization_ratio": "adHighCpu", "container_memory_percent_ratio": "emailMemoryLeak",
               "kafka_consumer_commit_rate": "kafkaQueueProblems"}  # multiple metrics

metric_label_dict = {"jvm_cpu_recent_utilization_ratio": "instance", "container_memory_percent_ratio": "container_name",
               "kafka_consumer_commit_rate": "instance"}

end = time.time()
start = end - 600  # last 10 minutes

all_rows = {}

for metric in list(metric_flgd_dict.keys()):
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
        instance = ts['metric'].get(metric_label_dict[metric])
        col_name = metric_flgd_dict[metric] + '_' + name + '_' + str(instance)
        print("Column name:", col_name)
        # convert values into a Series
        times = [float(v[0]) for v in ts['values']]
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
df.to_csv("prometheus_metrics.csv", index=False)
my_csv = pd.read_csv("prometheus_metrics.csv")
print(my_csv.shape)