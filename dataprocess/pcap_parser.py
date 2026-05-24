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


# tcpdump -v 输出格式的正则表达式
# IP头行示例: 1778750437.909797 IP (tos 0x0, ttl 64, ..., length 1408)
IP_LINE_RE = re.compile(
    r'^(\d+\.\d+)\s+IP\s+\(.+length\s+(\d+)\)\s*$'
)
# TCP详情行示例:     185.199.108.153.443 > 10.67.227.153.55852: Flags [.], ... length 1368
TCP_LINE_RE = re.compile(
    r'^\s+(\d+\.\d+\.\d+\.\d+)\.(\d+)'     # src_ip.src_port
    r'\s+>\s+'                                # separator
    r'(\d+\.\d+\.\d+\.\d+)\.(\d+)'           # dst_ip.dst_port
    r':.*length\s+(\d+)'                      # ... length N (TCP payload)
)


@dataclasses.dataclass
class PacketInfo:
    """数据包信息"""
    timestamp: float    # Unix epoch时间戳（微秒精度）
    src_ip: str         # 源IP地址
    src_port: int       # 源端口
    dst_ip: str         # 目标IP地址
    dst_port: int       # 目标端口
    length: int         # IP包总长度（含IP头+TCP/UDP头+载荷）
    payload_length: int = 0  # TCP/UDP载荷长度（用于过滤控制包）

    def __str__(self):
        return f"{self.timestamp:.6f} {self.src_ip}:{self.src_port} -> {self.dst_ip}:{self.dst_port} [{self.length}B]"


def parse_tcpdump_line(line: str) -> Optional[PacketInfo]:
    """
    解析tcpdump输出的一行（兼容旧的非-v格式，不应再被直接调用）
    """
    return None


def parse_verbose_pair(ip_line: str, tcp_line: str) -> Optional[PacketInfo]:
    """
    解析tcpdump -v输出的两行（IP头行 + TCP详情行）

    Args:
        ip_line: IP头行，含时间戳和IP总长度
        tcp_line: TCP详情行，含src/dst IP和端口

    Returns:
        解析成功返回PacketInfo对象，失败返回None
    """
    ip_match = IP_LINE_RE.match(ip_line)
    if not ip_match:
        return None

    tcp_match = TCP_LINE_RE.match(tcp_line)
    if not tcp_match:
        return None

    try:
        timestamp = float(ip_match.group(1))
        ip_length = int(ip_match.group(2))

        src_ip = tcp_match.group(1)
        src_port = int(tcp_match.group(2))
        dst_ip = tcp_match.group(3)
        dst_port = int(tcp_match.group(4))
        payload_length = int(tcp_match.group(5))

        # 验证数据
        if not validate_timestamp(timestamp):
            return None
        if not validate_packet_size(ip_length):
            return None

        return PacketInfo(
            timestamp=timestamp,
            src_ip=src_ip,
            src_port=src_port,
            dst_ip=dst_ip,
            dst_port=dst_port,
            length=ip_length,
            payload_length=payload_length
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
        '-v',                 # 详细模式（输出IP总长度）
        '-nn',                # 不解析主机名和端口名
        '-tt',                # Unix epoch时间戳
        bpf_filter            # BPF过滤器
    ]

    try:
        # 启动tcpdump子进程
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # 行缓冲
        )

        # 流式读取并解析（-v模式下每个包输出两行）
        pending_ip_line = None
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            # IP头行以时间戳开头（非空白），TCP详情行以空白开头
            if line[0] != ' ' and line[0] != '\t':
                pending_ip_line = line
            else:
                if pending_ip_line is not None:
                    pkt = parse_verbose_pair(pending_ip_line, line)
                    if pkt is not None:
                        yield pkt
                    pending_ip_line = None

        # 等待进程结束
        proc.wait()

        if proc.returncode != 0:
            stderr_msg = proc.stderr.read().strip() if proc.stderr else ''
            raise RuntimeError(f"tcpdump exited with code {proc.returncode}: {stderr_msg}")

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
