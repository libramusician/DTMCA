import requests
import pandas as pd
import numpy as np
import json
import time
import os

# -------------------------
# 1. Prometheus settings
# -------------------------
PROM_URL = "http://app.libra.com:9090/api/v1/query_range"

metrics = [
    "jvm_cpu_recent_utilization_ratio",
    "container_memory_percent_ratio",
    "kafka_consumer_records_lag",
    "jvm_gc_duration_seconds_bucket"
]

metric_service_dict = {"jvm_cpu_recent_utilization_ratio": "service_name", "container_memory_percent_ratio": "container_name",
                           "jvm_gc_duration_seconds_bucket": "service_name", "kafka_consumer_records_lag": "service_name"}



hours = 4
step = 15  # seconds

start_time = int(time.time()) - hours * 60 * 60
end_time = int(time.time())

# Create output folder
os.makedirs("ci_results", exist_ok=True)

# -------------------------
# 2. Bootstrap CI function
# -------------------------
def bootstrap_ci(values, n_boot=1000, ci=95):
    boot_means = []

    for _ in range(n_boot):
        sample = np.random.choice(values, size=len(values), replace=True)
        boot_means.append(np.mean(sample))

    lower = np.percentile(boot_means, (100 - ci) / 2)
    upper = np.percentile(boot_means, 100 - (100 - ci) / 2)

    return float(lower), float(upper)

# -------------------------
# 3. Fetch + compute CI per series
# -------------------------
metric_ci = {}
for metric in metrics:
    print(f"\nFetching metric: {metric}")

    response = requests.get(PROM_URL, params={
        "query": metric,
        "start": start_time,
        "end": end_time,
        "step": step
    })

    result = response.json()

    if not result["data"]["result"]:
        print(f"❌ No data found for {metric}")
        continue

    # ---- process each series separately ----
    for series in result["data"]["result"]:
        label = series["metric"]  # Prometheus labels
        times = [float(v[0]) for v in series["values"]]
        values = [float(v[1]) for v in series["values"]]

        df_series = pd.DataFrame({
            "time": times,
            "value": values
        })

        # Clean data
        df_series = df_series.sort_values("time")
        df_series = df_series.ffill().bfill()

        values = df_series["value"].dropna().values

        print(f"{len(values)} points")

        if len(values) < 20:
            print(f"⚠️ Skipping {label} (not enough data)")
            continue

        # ---- compute CI ----
        lower, upper = bootstrap_ci(values)


        metric_ci[str(metric + '_' + label[metric_service_dict[metric]])] = {
            "lower": lower,
            "upper": upper,
            "num_points": len(values)
        }

    # -------------------------
    # 4. Save JSON per metric
    # -------------------------
output_file = f"ci_results.json"

with open(output_file, "w") as f:
    json.dump(metric_ci, f, indent=4)

print(f"✅ Saved CI → {output_file}")
