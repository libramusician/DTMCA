import pandas as pd
import matplotlib.pyplot as plt

def create_service_dashboard(csv_file_path):
    """
    读取CSV文件并生成服务监控折线图
    CSV格式要求：serviceName, startTime, avg_time, num, succee_num, succee_rate
    """
    # 1. 读取CSV文件（假设使用制表符分隔，如果是逗号分隔请改为 sep=',')
    df = pd.read_csv(csv_file_path)

    # 2. 数据预处理：转换时间戳为可读时间
    df['datetime'] = pd.to_datetime(df['startTime'], unit='ms')

    # 3. 创建图表
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'Service Monitoring Dashboard - {df["serviceName"].iloc[0]}',
                 fontsize=16, fontweight='bold', y=0.98)

    # 3.1 平均响应时间折线图
    ax1 = axes[0, 0]
    ax1.plot(df['datetime'], df['avg_time'], marker='o', linewidth=2,
             markersize=8, color='#FF6B6B', label='Avg Response Time')
    ax1.set_title('Average Response Time Trend', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Response Time (ms)')
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.legend()

    # 3.2 请求数量折线图
    ax2 = axes[0, 1]
    ax2.plot(df['datetime'], df['num'], marker='s', linewidth=2,
             markersize=8, color='#4ECDC4', label='Total Requests')
    ax2.plot(df['datetime'], df['succee_num'], marker='^', linewidth=2,
             markersize=8, color='#45B7D1', label='Success Requests')
    ax2.set_title('Request Volume', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Time')
    ax2.set_ylabel('Request Count')
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.legend()

    # 3.3 成功率折线图
    ax3 = axes[1, 0]
    ax3.plot(df['datetime'], df['succee_rate'], marker='D', linewidth=2,
             markersize=8, color='#96CEB4', label='Success Rate')
    ax3.set_title('Success Rate', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Time')
    ax3.set_ylabel('Success Rate')
    ax3.set_ylim(0, 1.1)
    ax3.grid(True, alpha=0.3, linestyle='--')
    ax3.legend()

    # 3.4 综合对比（双Y轴）
    ax4 = axes[1, 1]
    ax4_twin = ax4.twinx()
    line1 = ax4.plot(df['datetime'], df['avg_time'], marker='o', linewidth=2,
                     markersize=8, color='#FF6B6B', label='Avg Time')
    line2 = ax4_twin.plot(df['datetime'], df['num'], marker='s', linewidth=2,
                          markersize=8, color='#4ECDC4', label='Request Num')
    ax4.set_title('Response Time vs Request Volume', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Time')
    ax4.set_ylabel('Response Time (ms)', color='#FF6B6B')
    ax4_twin.set_ylabel('Request Count', color='#4ECDC4')
    ax4.grid(True, alpha=0.3, linestyle='--')
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax4.legend(lines, labels, loc='best')

    plt.tight_layout()
    plt.savefig('service_monitoring_dashboard.png', dpi=150, bbox_inches='tight')
    plt.show()
    print("图表已保存为: service_monitoring_dashboard.png")


# 使用示例
if __name__ == "__main__":
    create_service_dashboard('2020_05_22/business/esb.csv')