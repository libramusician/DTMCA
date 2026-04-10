import time
import urllib
import pandas as pd
import requests
from datetime import datetime


def create_jaegar_csv():
    # Dictionary to store per-service dataframes
    service_dfs = {}
    metric_list = ['latencies', 'errors']

    # Fetch services
    resp = requests.get("http://app.libra.com:8080/jaeger/ui/api/services", timeout=5)
    all_services = resp.json()["data"]

    for metric in metric_list:
        base_url = f"http://app.libra.com:8080/jaeger/ui/api/metrics/{metric}"
        for service in all_services:
            params = {
                "service": service,
                "lookback": 300000,
                "endTs": int(time.time()) * 1000,
                "quantile": 0.5,
                "ratePer": 600000,
                "spanKind": "server",
                "step": 15000
            }
            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            res = requests.get(url)
            res = res.json()
            print(res)

            if res["metrics"]:
                points = res["metrics"][0]["metricPoints"]
                rows = []

                for p in points:
                    ts_str = p["timestamp"]
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    unix_time = dt.timestamp()
                    value = p["gaugeValue"]["doubleValue"]
                    if isinstance(value, str):  # skip NaN
                        continue
                    rows.append((unix_time, float(value)))

                # Create a dataframe with dynamic column name
                col_name = f"{res['name']}_{service}"
                df = pd.DataFrame(rows, columns=["time", col_name])
                df["time"] = df["time"] - df["time"].min()
                df["time"] = df["time"].astype(int)

                # Store in dict for merging
                service_dfs[metric + service] = df
                print(service_dfs)

    # Merge all dataframes on 'time'
    final_df = None
    for df in service_dfs.values():
        if final_df is None:
            final_df = df
        else:
            final_df = pd.merge(final_df, df, on="time", how="outer")

    # Fill missing values with NaN or 0 if you want
    final_df = final_df.sort_values("time").reset_index(drop=True)
    print(final_df)

    # Save to CSV
    final_df.to_csv("latency_and_error_services.csv", index=False)
    print("CSV file saved: combined_latency_services.csv")