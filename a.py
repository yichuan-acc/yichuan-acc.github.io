
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QPushButton, QVBoxLayout)
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
import sys
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import akshare as ak
from flask import Flask, render_template

import io
import base64

import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端


def get_hs300_close_by_date(start_date, end_date=None):
    """
    获取指定日期范围内的沪深300收盘指数

    参数：
    start_date : str 格式为"YYYY-MM-DD"的起始日期
    end_date : str (可选) 格式为"YYYY-MM-DD"的结束日期，默认为起始日期

    返回：
    pandas.DataFrame 包含日期和收盘价的DataFrame
    """
    try:
        # 获取完整历史数据
        df = ak.stock_zh_index_daily(symbol="sh000300")
        df['date'] = pd.to_datetime(df['date'])

        # 处理日期参数
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date) if end_date else start

        # 筛选日期范围
        mask = (df['date'] >= start) & (df['date'] <= end)
        filtered_df = df.loc[mask, ['date', 'close']].rename(
            columns={'close': '收盘价'})

        if filtered_df.empty:
            available_start = df['date'].min().strftime("%Y-%m-%d")
            available_end = df['date'].max().strftime("%Y-%m-%d")
            raise ValueError(
                f"日期范围内无数据，可用数据范围：{available_start} 至 {available_end}")

        return filtered_df.sort_values('date').reset_index(drop=True)

    except Exception as e:
        print(f"发生错误：{str(e)}")
        return pd.DataFrame()


def get_if_close(target_date, contract=None):
    """
    获取指定日期的IF股指期货收盘价

    参数：
    target_date : str 格式为"YYYY-MM-DD"的日期
    contract : str (可选) 合约代码，如"IF2301"。若未指定则自动判断主力合约

    返回：
    float 收盘价（若不存在返回None）
    """
    try:
        # 转换日期格式
        target_dt = pd.to_datetime(target_date)

        # 自动判断合约逻辑（示例：简单按月份判断）
        if not contract:
            year_month = target_dt.strftime("%y%m")
            contract = f"IF{year_month}"
            print(f"自动生成合约代码：{contract}")

        # 获取历史数据
        df = ak.futures_zh_daily_sina(symbol=contract)
        df['date'] = pd.to_datetime(df['date'])

        # 筛选指定日期
        result = df[df['date'] == target_dt]

        if not result.empty:
            return result.iloc[0]['close']
        else:
            # 尝试获取主力合约数据
            main_df = ak.futures_main_sina(symbol="IF0")  # IF0表示IF主力合约
            main_df['date'] = pd.to_datetime(main_df['date'])
            main_result = main_df[main_df['date'] == target_dt]

            if not main_result.empty:
                return main_result.iloc[0]['close']
            else:
                print(f"未找到{target_date}的交易数据")
                return None

    except Exception as e:
        print(f"获取数据失败：{str(e)}")
        return None


# 获取沪深300最近 N 个交易日数据
def get_recent_hs300(tailN=1):

    try:

        # 获取足够长时间范围内的数据
        end_date = datetime.now().strftime("%Y-%m-%d")
        hs300_data = get_hs300_close_by_date(
            start_date='2020-01-01', end_date=end_date)
        if hs300_data.empty:
            print("未获取到沪深300数据")
            return pd.DataFrame()
        # 提取最近 N 个交易日
        recent_hs300 = hs300_data.tail(tailN)
        # print(f"沪深300最近{tailN}个交易日收盘价：")
        # print(recent_hs300)
        return recent_hs300
    except Exception as e:
        print(f"获取沪深300数据失败：{str(e)}")
        return pd.DataFrame()


def get_recent_if(tailN=1):
    try:
        # 获取沪深300的最近5个交易日日期
        hs300_recent = get_recent_hs300(tailN)
        if hs300_recent.empty:
            return pd.DataFrame()
        target_dates = hs300_recent['date'].tolist()

        # 获取IF主力合约数据（检查实际列名）
        if_main = ak.futures_main_sina(symbol="IF0")

        # 调试：打印列名和样例数据
        # print("\nIF主力合约原始列名:", if_main.columns.tolist())
        # print(f"前{tailN}行数据:\n", if_main.tail(tailN))

        # 修正列名（假设日期列实际名为 "trade_date"）
        if_main = if_main.rename(columns={"日期": "date"})  # 根据实际列名调整

        # print("\nIF主力合约修正列名:", if_main.columns.tolist())
        # print(f"前{tailN}行数据:\n", if_main.tail(tailN))

        # 处理日期格式
        if_main['date'] = pd.to_datetime(if_main['date'])

        # 筛选目标日期
        if_filtered = if_main[if_main['date'].isin(target_dates)]
        if if_filtered.empty:
            print(f"警告: 未找到 {target_dates} 的IF主力合约数据")
            return pd.DataFrame()

        # 格式化输出
        if_filtered = if_filtered.sort_values('date').reset_index(drop=True)
        if_filtered = if_filtered[['date', '收盘价']].rename(
            columns={'data': '收盘价'})

        # print("\nIF主力合约收盘价：")
        # print(if_filtered)
        return if_filtered
    except Exception as e:
        print(f"获取IF数据失败：{str(e)}")

        return pd.DataFrame()


# 执行函数
def aa(days=30):

    recent_hs300 = get_recent_hs300(days)
    recent_if = get_recent_if(days)

    print(f"最近{days}个交易日的沪深300收盘价:\n", recent_hs300, type(recent_hs300))
    print(f"最近{days}个交易日的IF主力合约收盘价:\n", recent_if)

    # 步骤1：合并数据
    merged_df = pd.merge(recent_hs300.rename(columns={'收盘价': 'hs300_close'}),
                         recent_if.rename(columns={'收盘价': 'if_close'}),
                         on='date',
                         how='inner')

    # 步骤2：计算基差（假设基差=期货-现货）
    merged_df['basis'] = merged_df['hs300_close'] - merged_df['if_close']

    # 步骤3：可视化
    plt.figure(figsize=(14, 7))

    # 主坐标轴（左轴）
    ax1 = plt.gca()
    ax1.plot(merged_df['date'], merged_df['hs300_close'],
             label='HS300 Close', color='blue', marker='o', markersize=4)
    ax1.plot(merged_df['date'], merged_df['if_close'],
             label='IF Close', color='green', marker='s', markersize=4)
    ax1.set_xlabel('Date', fontsize=14)
    ax1.set_ylabel('Price', fontsize=14)
    ax1.tick_params(axis='x', rotation=45)

    # 次坐标轴（右轴）
    ax2 = ax1.twinx()
    ax2.plot(merged_df['date'], merged_df['basis'],
             label='Basis (IF - HS300)', color='red', linestyle='--', linewidth=2)
    ax2.set_ylabel('Basis', fontsize=14)

    ax2.set_xticks(merged_df['date'])  # 仅使用数据中的日期作为刻度位置

    # 合并图例
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    plt.title('HS300 vs IF with Basis', fontsize=14)
    plt.grid(linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.show()


def get_merged_data(days=30):

    try:

        recent_hs300 = get_recent_hs300(days)
        recent_if = get_recent_if(days)

        # print(f"最近{days}个交易日的沪深300收盘价:\n", recent_hs300, type(recent_hs300))
        # print(f"最近{days}个交易日的IF主力合约收盘价:\n", recent_if)

        # 步骤1：合并数据
        merged_df = pd.merge(recent_hs300.rename(columns={'收盘价': 'hs300_close'}),
                             recent_if.rename(columns={'收盘价': 'if_close'}),
                             on='date',
                             how='inner')

        # 步骤2：计算基差（假设基差=期货-现货）
        merged_df['basis'] = merged_df['hs300_close'] - merged_df['if_close']

        return merged_df
    except Exception as e:
        print(f"获取数据失败：{str(e)}")

        return pd.DataFrame()


app = Flask(__name__)


@app.route('/')
def index():

    try:
        # 获取数据
        days = 30
        merged_df = get_merged_data(days)

        # 步骤3：可视化
        plt.figure(figsize=(14, 7))

        # 主坐标轴（左轴）
        ax1 = plt.gca()
        ax1.plot(merged_df['date'], merged_df['hs300_close'],
                 label='HS300 Close', color='blue', marker='o', markersize=4)
        ax1.plot(merged_df['date'], merged_df['if_close'],
                 label='IF Close', color='green', marker='s', markersize=4)
        ax1.set_xlabel('Date', fontsize=14)
        ax1.set_ylabel('Price', fontsize=14)
        ax1.tick_params(axis='x', rotation=45)

        # 次坐标轴（右轴）
        ax2 = ax1.twinx()
        ax2.plot(merged_df['date'], merged_df['basis'],
                 label='Basis (IF - HS300)', color='red', linestyle='--', linewidth=2)
        ax2.set_ylabel('Basis', fontsize=14)

        ax2.set_xticks(merged_df['date'])  # 仅使用数据中的日期作为刻度位置

        # 合并图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

        plt.title('HS300 vs IF with Basis', fontsize=14)
        plt.grid(linestyle='--', alpha=0.5)
        plt.tight_layout()
        # plt.show()

        # 将图表保存为 base64 编码的图片
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()

        # 渲染 HTML 模板
        return render_template('index_stock.html', tables=[merged_df.to_html(classes='data')], plot_url=plot_url)

    except Exception as e:
        print(f"发生错误：{str(e)}")
        return f"<h1>发生错误：</h1><p>{str(e)}</p>"


if __name__ == '__main__':
    # app = QApplication(sys.argv)
    # ex = FuturesBasisApp()
    # ex.show()
    # sys.exit(app.exec_())
    # pass
    app.run(debug=True)
