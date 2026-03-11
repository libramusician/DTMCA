import pandas as pd
import os
import zipfile
import statistics


def compute_z_score(value, mean, std):
    return (value - mean) / std

def get_mean_variance(folder_path):
    time_list = []
    for zip_files in os.listdir(folder_path):
        if zip_files.endswith(".zip"):
            with zipfile.ZipFile(os.path.join(folder_path, zip_files), 'r') as zip_ref:
                for filename in zip_ref.namelist():
                    if filename.endswith("esb.csv"):
                        with zip_ref.open(filename) as csv_file:
                            df = pd.read_csv(csv_file)
                            lst = df["avg_time"].tolist()
                            time_list += lst

    total = sum(time_list)
    length = len(time_list)
    avg_time = total / length
    std = statistics.stdev(time_list)

    return avg_time, std


def detect_anomaly(folder_path):
    mean, std = get_mean_variance("/Users/shifangzhao/Desktop/AIOps/DTMCA/Normal_Data")
    for zip_files in os.listdir(folder_path):
        if zip_files.endswith(".zip"):
            with zipfile.ZipFile(os.path.join(folder_path, zip_files), 'r') as zip_ref:
                # print(zip_ref.namelist())
                for filename in zip_ref.namelist():
                    if filename.endswith("esb.csv"):
                        with zip_ref.open(filename) as csv_file:
                            df = pd.read_csv(csv_file)
                            df["date_time"] = pd.to_datetime(df["startTime"], unit='ms')
                            df["date_time"] = df["date_time"] + pd.Timedelta(hours=8)
                            df['time_cumulative'] = (df['date_time'] - df['date_time'].iloc[0]).dt.total_seconds()
                            pd.set_option("display.max_rows", None)
                            pd.set_option("display.max_columns", None)
                            pd.set_option("display.width", None)
                            print(filename)
                            print(df)
                            time_list = df["avg_time"].tolist()
                            # print(time_list)
                            date_list = df["date_time"].tolist()
                            # print(date_list)
                            # print(compute_z_score(time_list[8], mean, std))
                            time_diff_list = df["time_cumulative"].tolist()
                            left = 0
                            right = 0

                            while right < len(time_diff_list) - 1:
                                time_difference = time_diff_list[right] - time_diff_list[left]
                                while right < len(time_diff_list) - 1 and time_difference < 240:
                                    right += 1
                                    time_difference = time_diff_list[right] - time_diff_list[left]
                                    # print('left: ', left)
                                    # print('right: ', right)


                                count = 0
                                time_clip = time_list[left: right + 1]
                                # print(time_clip)
                                for i in range(len(time_clip)):
                                    if compute_z_score(time_clip[i], mean, std) > 0.2:
                                        count += 1

                                # print(count)
                                # print(len(time_clip))
                                if count == len(time_clip):
                                    start_time = date_list[left]
                                    end_time = date_list[right]
                                    print("Anomaly Detected!")
                                    print(str(start_time) + " --> " + str(end_time))

                                left += 1


detect_anomaly("/Users/shifangzhao/Desktop/AIOps/DTMCA/Normal_Data")