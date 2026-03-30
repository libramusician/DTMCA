import json
import time
import pandas as pd
from generate_csv import create_csv
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


create_csv()
time.sleep(10)

metrics = [
    "jvm_cpu_recent_utilization_ratio",
    "container_memory_percent_ratio",
    "kafka_consumer_commit_rate"
]

ground_truth = [0]
anomaly_detection = []

data_df = pd.read_csv('prometheus_metrics.csv')

with open("observation_period.json", 'r') as file:
    obs_dict = json.load(file)

# The upper and lower bound of different metrics and services
with open(f"ci_results.json", 'r') as file:
    ci_dict = json.load(file)

print('ci_dict', ci_dict)
col_list = data_df.columns.to_list()
col_list.remove('time')

anomaly = False
for i in range(len(col_list)):
    print('col', col_list[i])
    obs_start = 0
    obs_period = 0
    for metric in metrics:
        if metric in col_list:
            obs_period = obs_dict[metric]
            break

    obs_end = obs_start + obs_period - 1
    value = data_df[col_list[i]].tolist()
    upper_bound = ci_dict[col_list[i]]['upper']
    lower_bound = ci_dict[col_list[i]]['lower']
    anomaly = False
    while obs_end < len(value):
        count = 0
        for j in range(obs_start, obs_end + 1):
            if value[j] >= upper_bound or value[j] <= lower_bound:
                count += 1

        if count == obs_period:
            anomaly = True
            break

        obs_start += 1
        obs_end += 1

    if anomaly:
        anomaly_detection.append(1)
        break

if not anomaly:
    anomaly_detection.append(0)

print(anomaly_detection)
accuracy = accuracy_score(ground_truth, anomaly_detection)
recall = recall_score(ground_truth, anomaly_detection)
precision = precision_score(ground_truth, anomaly_detection)
f1_score = f1_score(ground_truth, anomaly_detection)
print(accuracy)
print(recall)
print(precision)
print(f1_score)

