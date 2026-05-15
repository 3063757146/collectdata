#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCAP解析器模块
使用tcpdump解析pcap文件，提取数据包信息
"""

import re
import subprocess
import dataclasses
from typing import Iterator, Optional
from .config import Config
from .utils import validate_timestamp, validate_packet_size


# tcpdump输出格式的正则表达式
# 示例: 1778750437.909797 IP 185.199.108.153.443 > 10.67.227.153.55852: Flags [.], ... length 1368
PACKET_RE = re.compile(
    r'^(\d+\.\d+)\s+IP\s+'                # timestamp (Unix epoch with microseconds)
    r'(\d+\.\d+\.\d+\.\d+)\.(\d+)'        # src_ip.src_port
    r'\s+>\s+'                            # separator
    r'(\d+\.\d+\.\d+\.\d+)\.(\d+)'        # dst_ip.dst_port
    r':.+length\s+(\d+)$'                 # ... length N (at end of line)
)


@dataclasses.dataclass
class PacketInfo:
    """数据包信息"""
    timestamp: float    # Unix epoch时间戳（微秒精度）
    src_ip: str         # 源IP地址
    src_port: int       # 源端口
    dst_ip: str         # 目标IP地址
    dst_port: int       # 目标端口
    length: int         # TCP/UDP载荷长度

    def __str__(self):
        return f"{self.timestamp:.6f} {self.src_ip}:{self.src_port} -> {self.dst_ip}:{self.dst_port} [{self.length}B]"


def parse_tcpdump_line(line: str) -> Optional[PacketInfo]:
    """
    解析tcpdump输出的一行

    Args:
        line: tcpdump输出的一行文本

    Returns:
        解析成功返回PacketInfo对象，失败返回None
    """
    match = PACKET_RE.match(line)
    if not match:
        return None

    try:
        timestamp_str, src_ip, src_port_str, dst_ip, dst_port_str, length_str = match.groups()

        timestamp = float(timestamp_str)
        src_port = int(src_port_str)
        dst_port = int(dst_port_str)
        length = int(length_str)

        # 验证数据
        if not validate_timestamp(timestamp):
            return None
        if not validate_packet_size(length):
            return None

        return PacketInfo(
            timestamp=timestamp,
            src_ip=src_ip,
            src_port=src_port,
            dst_ip=dst_ip,
            dst_port=dst_port,
            length=length
        )
    except (ValueError, IndexError):
        return None


def iter_packets(
    pcap_path: str,
    config: Config,
    bpf_filter: str = 'ip'
) -> Iterator[PacketInfo]:
    """
    流式读取pcap文件，生成PacketInfo对象

    Args:
        pcap_path: pcap文件路径
        config: 配置对象
        bpf_filter: BPF过滤器表达式

    Yields:
        PacketInfo对象

    Raises:
        RuntimeError: tcpdump执行失败
        FileNotFoundError: pcap文件不存在
    """
    # 构建tcpdump命令
    cmd = [
        config.tcpdump_path,
        '-r', pcap_path,     # 读取文件
        '-nn',                # 不解析主机名和端口名
        '-tt',                # Unix epoch时间戳
        bpf_filter            # BPF过滤器
    ]

    try:
        # 启动tcpdump子进程
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # 忽略stderr（避免"reading from file..."信息）
            text=True,
            bufsize=1  # 行缓冲
        )

        # 流式读取并解析
        for line in proc.stdout:
            pkt = parse_tcpdump_line(line.rstrip())
            if pkt is not None:
                yield pkt

        # 等待进程结束
        proc.wait()

        if proc.returncode != 0:
            raise RuntimeError(f"tcpdump exited with code {proc.returncode}")

    except FileNotFoundError:
        raise FileNotFoundError(f"tcpdump not found at {config.tcpdump_path}")
    except KeyboardInterrupt:
        # 用户中断，终止子进程
        if proc:
            proc.terminate()
            proc.wait()
        raise


def count_packets(pcap_path: str, config: Config, bpf_filter: str = 'ip') -> int:
    """
    快速统计pcap文件中的包数（不解析详细信息）

    Args:
        pcap_path: pcap文件路径
        config: 配置对象
        bpf_filter: BPF过滤器表达式

    Returns:
        包数量
    """
    cmd = [
        config.tcpdump_path,
        '-r', pcap_path,
        '-nn',
        bpf_filter
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True
        )
        # 统计行数
        return len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
    except subprocess.CalledProcessError:
        return 0
    except FileNotFoundError:
        raise FileNotFoundError(f"tcpdump not found at {config.tcpdump_path}")
