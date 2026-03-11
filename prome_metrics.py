import time
import requests
import json


def compute_z_score(val, mean, std):
    return (val - mean) / std


while True:
    end = time.time()
    start = end - 300

    metric_list = ["system_cpu_utilization_ratio"]
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
        print(res)
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
            value_lst = []
            for j in range(len(value)):
                value_lst.append(float(value[j][1]))

            value_mean = sum(value_lst) / len(value_lst)
            if not normal_std == 0:
                if compute_z_score(value_mean, normal_mean, normal_std) > 3:
                    print('Anomaly detected')

                else:
                    print('Normal')

                print('The metric values and the timestamps are', value)
                print('z-scores is: ', compute_z_score(value_mean, normal_mean, normal_std))
                print('The combination is: ', res['data']['result'][i]['metric'])
                print('The normal mean and standard deviation are: ', data_dict[str(res['data']['result'][i]['metric'])])
    time.sleep(15)