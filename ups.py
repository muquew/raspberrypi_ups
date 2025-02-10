#!/usr/bin/python3

import smbus
import os
import time
import fcntl
import logging
from INA219 import INA219

# 获取当前脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

# 创建 logs 目录（如果不存在）
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 配置日志
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'ups_monitor.log'),  # 日志文件
    level=logging.INFO,  # 设置日志级别为 INFO
    format='%(asctime)s - %(levelname)s - %(message)s',  # 日志格式
)

LOW_PERCENT = 80.0
MONITOR_SCRIPT = os.path.join(SCRIPT_DIR, "monitor_ups_reboot.py")  # 监测脚本路径

def is_monitor_running():
    """检查监测脚本是否在运行"""
    try:
        # 使用ps命令获取所有包含监测脚本名称的进程
        check_process = os.popen("ps aux | grep '[m]onitor_ups_reboot.py'").read().strip()
        if check_process:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"检查监测脚本是否运行时发生错误: {e}")
        return False


if __name__ == '__main__':
    ina219 = INA219(addr=0x41)

    # 初始化状态
    last_percent = 100.0  # 假设开始时电量为100%
    is_waiting_for_recovery = False  # 是否处于等待恢复的状态
    recovery_start_time = 0  # 等待恢复的开始时间

    while True:
        bus_voltage = ina219.getBusVoltage_V()
        p = (bus_voltage - 9) / 3.6 * 100
        p = max(0, min(100, p))  # 保证电量在 0 到 100 之间

        print(f"\rPercent: {p:3.1f}%   ", end="", flush=True)

        if not is_monitor_running():
            # 进入低电量状态（低于80%）
            if p < LOW_PERCENT and last_percent >= LOW_PERCENT:
                is_waiting_for_recovery = True
                recovery_start_time = time.time()  # 记录低电量进入时间
                logging.warning(f"⚠️ 电量低于 {LOW_PERCENT}%，进入低电量状态，开始计时...")

            # 处于低电量状态且电量在5秒内恢复到高电量（> 80%）
            if is_waiting_for_recovery:
                if p > LOW_PERCENT:
                    # 如果在5秒内恢复到高电量
                    if time.time() - recovery_start_time <= 5:
                        logging.info(f"🚀 5s内电量跳动，准备启动监测脚本...")
                        logging.info(f"🚀 启动 `monitor_ups_reboot.py` 进行 20s 监测...")
                        os.system(f"nohup python3 {MONITOR_SCRIPT} > {os.path.join(SCRIPT_DIR, 'ups_monitor.log')} 2>&1 &")
                        is_waiting_for_recovery = False  # 重置等待状态
                    else:
                        # 如果恢复电量时间超过5秒
                        logging.warning(f"⚠️ 电量恢复超过5秒，但未成功启动，重置状态。")
                        is_waiting_for_recovery = False

            # 如果在低电量状态，但5秒内没有恢复，重置状态
            if is_waiting_for_recovery and time.time() - recovery_start_time > 5:
                logging.warning("⚠️ 低电量超过5秒，未恢复，重置状态。")
                is_waiting_for_recovery = False

            last_percent = p  # 更新上次电量状态

        time.sleep(2)
