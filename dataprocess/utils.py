#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辅助函数模块
提供时间转换、数据验证、进度显示等工具函数
"""

import sys
import datetime
import time
from typing import Optional


def epoch_to_datetime_str(epoch: float) -> str:
    """
    将Unix时间戳转换为可读的日期时间字符串

    Args:
        epoch: Unix时间戳（秒，可包含微秒小数部分）

    Returns:
        格式化的时间字符串 'YYYY-MM-DD HH:MM:SS.ffffff'
    """
    dt = datetime.datetime.fromtimestamp(epoch)
    return dt.strftime('%Y-%m-%d %H:%M:%S.%f')


def validate_timestamp(timestamp: float) -> bool:
    """
    验证时间戳是否合法

    Args:
        timestamp: Unix时间戳

    Returns:
        True表示合法，False表示非法
    """
    if timestamp <= 0:
        return False

    # 检查是否是未来时间（允许1小时误差）
    now = time.time()
    if timestamp > now + 3600:
        return False

    return True


def validate_packet_size(size: int) -> bool:
    """
    验证包大小是否合法

    Args:
        size: 包大小（字节）

    Returns:
        True表示合法，False表示非法
    """
    # IP包最大65535字节，最小0字节
    return 0 <= size <= 65535


class ProgressBar:
    """简单的文本进度条"""

    def __init__(self, total: int, desc: str = "Processing", width: int = 50):
        """
        Args:
            total: 总数量
            desc: 描述文本
            width: 进度条宽度（字符数）
        """
        self.total = total
        self.desc = desc
        self.width = width
        self.current = 0
        self.start_time = time.time()

    def update(self, n: int = 1):
        """更新进度"""
        self.current += n
        self._display()

    def _display(self):
        """显示进度条"""
        if self.total == 0:
            percent = 100
        else:
            percent = min(100, int(100 * self.current / self.total))

        filled = int(self.width * percent / 100)
        bar = '=' * filled + '-' * (self.width - filled)

        elapsed = time.time() - self.start_time
        if self.current > 0 and elapsed > 0:
            rate = self.current / elapsed
            eta = (self.total - self.current) / rate if rate > 0 else 0
            eta_str = f"{int(eta)}s"
        else:
            eta_str = "?"

        sys.stderr.write(f'\r{self.desc}: [{bar}] {percent}% ({self.current}/{self.total}) ETA: {eta_str}')
        sys.stderr.flush()

        if self.current >= self.total:
            sys.stderr.write('\n')
            sys.stderr.flush()

    def close(self):
        """关闭进度条"""
        self.current = self.total
        self._display()


class PacketCounter:
    """数据包计数器，定期显示进度"""

    def __init__(self, report_interval: int = 10000):
        """
        Args:
            report_interval: 报告间隔（每处理N个包报告一次）
        """
        self.count = 0
        self.report_interval = report_interval
        self.start_time = time.time()

    def increment(self):
        """增加计数"""
        self.count += 1
        if self.count % self.report_interval == 0:
            self._report()

    def _report(self):
        """报告进度"""
        elapsed = time.time() - self.start_time
        rate = self.count / elapsed if elapsed > 0 else 0
        sys.stderr.write(f'已处理: {self.count} 包 ({rate:.0f} 包/秒)\n')
        sys.stderr.flush()

    def finish(self):
        """完成并显示最终统计"""
        elapsed = time.time() - self.start_time
        rate = self.count / elapsed if elapsed > 0 else 0
        sys.stderr.write(f'完成: 共处理 {self.count} 包，耗时 {elapsed:.1f} 秒 ({rate:.0f} 包/秒)\n')
        sys.stderr.flush()


def format_bytes(num_bytes: int) -> str:
    """
    格式化字节数为可读形式

    Args:
        num_bytes: 字节数

    Returns:
        格式化字符串（如 "1.23 MB"）
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


def print_statistics(features: list, start_time: float, end_time: float):
    """
    打印特征统计信息

    Args:
        features: [(timestamp, signed_size), ...] 特征列表
        start_time: 处理开始时间（epoch）
        end_time: 处理结束时间（epoch）
    """
    if not features:
        print("无数据")
        return

    total_count = len(features)
    send_count = sum(1 for _, size in features if size > 0)
    recv_count = sum(1 for _, size in features if size < 0)
    zero_count = sum(1 for _, size in features if size == 0)

    total_send_bytes = sum(size for _, size in features if size > 0)
    total_recv_bytes = sum(-size for _, size in features if size < 0)

    timestamps = [ts for ts, _ in features]
    min_ts = min(timestamps)
    max_ts = max(timestamps)
    duration = max_ts - min_ts

    print("\n" + "="*60)
    print("统计摘要")
    print("="*60)
    print(f"总包数: {total_count}")
    print(f"  - 发送包: {send_count} ({send_count/total_count*100:.1f}%)")
    print(f"  - 接收包: {recv_count} ({recv_count/total_count*100:.1f}%)")
    if zero_count > 0:
        print(f"  - 0字节包: {zero_count} ({zero_count/total_count*100:.1f}%)")
    print(f"\n流量统计:")
    print(f"  - 上传: {format_bytes(total_send_bytes)}")
    print(f"  - 下载: {format_bytes(total_recv_bytes)}")
    print(f"  - 总计: {format_bytes(total_send_bytes + total_recv_bytes)}")
    print(f"\n时间范围:")
    print(f"  - 开始: {epoch_to_datetime_str(min_ts)}")
    print(f"  - 结束: {epoch_to_datetime_str(max_ts)}")
    print(f"  - 持续: {duration:.1f} 秒")
    print(f"\n处理耗时: {end_time - start_time:.1f} 秒")
    print("="*60 + "\n")
