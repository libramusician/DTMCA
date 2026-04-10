import glob

import pandas as pd


def read_dataframe_from_csv(csv_pattern: str):
    """主入口：处理CSV文件"""
    files = sorted(glob.glob(csv_pattern))
    print(f"找到 {len(files)} 个文件")
    dfs = []
    for file_path in files:
        try:
            df = pd.read_csv(file_path)
            dfs.append(df)
            print(f"  ✓ 读取 {file_path}: {len(df)} 行")
        except Exception as e:
            print(f"  ✗ 读取 {file_path} 失败: {e}")
    df: pd.DataFrame = pd.concat(dfs, ignore_index=True)
    print(f"\n合并后总行数: {len(df)}")
    return df