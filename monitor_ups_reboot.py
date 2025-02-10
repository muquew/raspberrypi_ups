#!/usr/bin/python3

import os
import time
import logging
from INA219 import INA219

# 获取当前脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

# logs 目录
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')

# 配置日志
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'ups_monitor.log'),  # 日志文件
    level=logging.INFO,  # 设置日志级别为 INFO
    format='%(asctime)s - %(levelname)s - %(message)s',  # 日志格式
)

# INA219 设备地址
ina219 = INA219(addr=0x41)

# 电量阈值
LOW_PERCENT = 80.0   # 电量低于 80% 时表示掉电
REBOOT_SIGNAL_COUNT = 3  # 需要 3 次 "掉电->恢复" 触发重启
DETECTION_WINDOW = 20  # 监测窗口时间 (秒)

# 计数器
reboot_signals = 0
start_time = time.time()
last_state = "high"  # 最后一次的电量状态，高或低
transition_count = 0  # 记录从低到高电量的次数

logging.info("🕵️  进入 UPS 20s 监测模式...")

while time.time() - start_time < DETECTION_WINDOW:
    bus_voltage = ina219.getBusVoltage_V()
    p = (bus_voltage - 9) / 3.6 * 100
    p = max(0, min(100, p))

    # 将电量百分比写入日志
    logging.info(f"⚡ 当前电量: {p:.1f}%")

    # 判断电量是否从低到高（低电量恢复到高电量）
    if p > LOW_PERCENT and last_state == "low":
        transition_count += 1
        logging.info(f"🔄 第 {transition_count} 次电量跳动")

        # 重置状态为“高”
        last_state = "high"

    # 判断电量是否从高到低（电量掉到低电量）
    elif p < LOW_PERCENT and last_state == "high":
        # 重置状态为“低”
        last_state = "low"

    # 达到 3 次电量恢复信号，触发重启
    if transition_count >= REBOOT_SIGNAL_COUNT:
        logging.error("✅ 触发重启信号！系统即将重启...")
        # os.system("sudo reboot")
        break

    time.sleep(2)  # 采样周期

logging.info("🛑 20s 监测结束，未触发重启")
