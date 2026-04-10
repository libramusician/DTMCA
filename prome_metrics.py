import json
import pandas as pd


metrics = [
    "jvm_cpu_recent_utilization_ratio",
    "container_memory_percent_ratio",
    "kafka_consumer_records_lag",
    "jvm_gc_duration_seconds_bucket"
]

csv_list = ['prometheus_metrics/prometheus_metrics_adHighCpu.csv', 'prometheus_metrics/prometheus_metrics_adManualGc.csv',
            'prometheus_metrics/prometheus_metrics_emailMemoryLeak.csv', 'prometheus_metrics/prometheus_metrics_loadGeneratorFloodHomepage.csv']


with open("observation_period.json", 'r') as file:
    obs_dict = json.load(file)

# The upper and lower bound of different metrics and services
with open(f"ci_results.json", 'r') as file:
    ci_dict = json.load(file)

print('ci_dict', ci_dict)

for csv in csv_list:
    data_df = pd.read_csv(csv)
    col_list = data_df.columns.to_list()
    col_list.remove('time')
    print('col list: ', col_list)

    anomaly = False
    anomaly_metrics = []
    for i in range(len(col_list)):
        count = 0
        obs_start = 0
        obs_period = 0
        for metric in metrics:
            if metric in col_list[i]:
                obs_period = obs_dict[metric]
                break

        obs_end = obs_start + obs_period - 1
        value = data_df[col_list[i]].tolist()
        upper_bound = ci_dict[col_list[i]]['upper']
        lower_bound = ci_dict[col_list[i]]['lower']
        anomaly = False
        while obs_end < len(value):
            for j in range(obs_start, obs_end + 1):
                if 'jvm_cpu_recent_utilization_ratio' in col_list[i] and value[j] > upper_bound + 0.05:
                    count += 1
                elif 'container_memory_percent_ratio' in col_list[i] and (value[j] < lower_bound - 10 or value[j] > upper_bound + 10):
                    count += 1
                elif 'kafka_consumer_records_lag' in col_list[i] and value[j] > upper_bound:
                    count += 1
                elif 'jvm_gc_duration_seconds_bucket' in col_list[i] and value[j] > upper_bound:
                    count += 1

            if count >= obs_period:
                anomaly = True
                break

            obs_start += 1
            obs_end += 1

        if anomaly:
            anomaly_metrics.append(col_list[i])


    if anomaly_metrics:
        print("Anomaly detected")
        print('csv file is', csv)
        print('Metric: ', anomaly_metrics)

    else:
        print('csv file is', csv)
        print("No anomaly detected")