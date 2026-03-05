import time
import requests
import json


def compute_z_score(val, mean, std):
    return (val - mean) / std


while True:
    end = time.time()
    start = end - 300

    metric_list = ["system_cpu_utilization_ratio", "system_network_dropped_packets_total"]
    for m in range(len(metric_list)):
        params = {
            "query": metric_list[m],
            "start": start,
            "end": end,
            "step": "15s"
        }

        response = requests.get("http://192.168.1.28:9090/api/v1/query_range", params=params)
        print(response.status_code)
        res = json.dumps(response.json(), indent=2)
        # print(res)
        res = json.loads(res)

        # anomaly detection here
        with open(f'{metric_list[m]}.json', 'r') as file:
            data_dict = json.load(file)

        for i in range(len(res['data']['result'])):
            count = 0
            metric = metric_list[m]
            value = res['data']['result'][i]['values']
            normal_mean = data_dict[str(res['data']['result'][i]['metric'])][0]
            normal_std = data_dict[str(res['data']['result'][i]['metric'])][1]
            if not normal_std == 0:
                z_score_lst = []
                for j in range(len(value)):
                    z_score_lst.append(compute_z_score(float(value[j][1]), normal_mean, normal_std))
                    if compute_z_score(float(value[j][1]), normal_mean, normal_std) > 3:
                        count += 1

                if count == len(value):
                    print('Anomaly detected')
                    print(value)
                    print(z_score_lst)
                    print(res['data']['result'][i]['metric'])
                    print(data_dict[str(res['data']['result'][i]['metric'])])
                else:
                    print('Normal')
                    print(value)
                    print(z_score_lst)
                    print(res['data']['result'][i]['metric'])
                    print(data_dict[str(res['data']['result'][i]['metric'])])

    time.sleep(15)