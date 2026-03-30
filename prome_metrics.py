import json
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


metrics = [
    "jvm_cpu_recent_utilization_ratio",
    "container_memory_percent_ratio",
    "kafka_consumer_commit_rate"
]

ground_truth = []
anomaly_detection = []

with open('prometheus_metrics.csv', 'r') as f:
    data_dict = json.load(f)


# The upper and lower bound of different metrics and services
for metric in metrics:
    with open(f"ci_results/{metric}.json", 'r') as file:
        ci_dict = json.load(file)

    # The observation period of different metrics and services
    with open(f"observation_period/{metric}.json", 'r') as obs_file:
        obs_dict = json.load(obs_file)

    obs_period = obs_dict[metric]

    for i in range(len(data_dict['data']['result'])):
        obs_start = 0
        obs_end = obs_start + obs_period - 1
        value = data_dict['data']['result'][i]['values']
        upper_bound = data_dict[metric]['upper']
        lower_bound = data_dict[metric]['lower']
        anomaly = False
        while obs_end < len(value):
            count = 0
            for j in range(obs_start, obs_end + 1):
                if value[j] >= upper_bound or value[j] <= lower_bound:
                    count += 1

            if count == obs_period:
                anomaly = True
                anomaly_detection.append(1)
                break

        if not anomaly:
            anomaly_detection.append(0)

    accuracy = accuracy_score(ground_truth, anomaly_detection)
    recall = recall_score(ground_truth, anomaly_detection)
    precision = precision_score(ground_truth, anomaly_detection)
    f1_score = f1_score(ground_truth, anomaly_detection)
