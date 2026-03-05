import time
import requests
import json
import statistics


def compute_mean_variance(lst):
    mean = sum(lst) / len(lst)
    std = statistics.stdev(lst)
    return mean, std


end = time.time()
start = end - 600

metric_list = ["system_cpu_utilization_ratio", "system_network_dropped_packets_total"]
for m in range(len(metric_list)):
    params = {
        "query": metric_list[m],
        "start": start,
        "end": end,
        "step": "10s"
    }

    response = requests.get("http://192.168.1.28:9090/api/v1/query_range", params=params)
    print(response.status_code)
    res = json.dumps(response.json(), indent=2)
    print(res)
    res = json.loads(res)
    json_dict = {}
    for i in range(len(res['data']['result'])):
        count = 0
        value_lst = []
        value = res['data']['result'][i]['values']
        for j in range(len(value)):
            value_lst.append(float(value[j][1]))

        mean, std = compute_mean_variance(value_lst)
        json_dict[str(res['data']['result'][i]['metric'])] = [mean, std]

    print(json_dict)
    with open(f'{metric_list[m]}.json', 'w') as f:
        json.dump(json_dict, f, indent=4)
