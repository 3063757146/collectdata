#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特征提取模块
从pcap文件中提取流量特征：(时间戳, 有符号包大小)
"""

import sys
from typing import List, Tuple
from .config import Config
from .pcap_parser import iter_packets, PacketInfo
from .utils import PacketCounter


def extract_features(
    pcap_path: str,
    config: Config,
    flow_type: str = "mac_vps",
    perspective: str = "mac",
    skip_zero: bool = True,
    show_progress: bool = True
) -> List[Tuple[float, int, str, int, str, int]]:
    """
    从pcap文件提取流量特征

    Args:
        pcap_path: pcap文件路径
        config: 配置对象
        flow_type: 流量类型（mac_vps/vps_website/all）
        perspective: 抓包视角（mac/vps）
        skip_zero: 是否跳过0字节包
        show_progress: 是否显示进度

    Returns:
        特征列表：[(timestamp, signed_packet_size, src_ip, src_port, dst_ip, dst_port), ...]
        正数表示发送，负数表示接收

    Raises:
        ValueError: 流量类型无效
        FileNotFoundError: pcap文件不存在
        RuntimeError: tcpdump执行失败
    """
    # 根据流量类型和视角生成BPF过滤器
    bpf_filter = config.get_bpf_filter(flow_type, perspective)

    features = []
    counter = PacketCounter(report_interval=10000) if show_progress else None

    if show_progress:
        print(f"正在处理: {pcap_path}", file=sys.stderr)
        print(f"流量类型: {flow_type}, 视角: {perspective}", file=sys.stderr)
        print(f"BPF过滤器: {bpf_filter}", file=sys.stderr)

    try:
        # 流式读取和解析数据包
        for pkt in iter_packets(pcap_path, config, bpf_filter):
            # 跳过TCP载荷为0的控制包（纯ACK/SYN/FIN等）
            if skip_zero and pkt.payload_length == 0:
                continue

            # 判断方向并计算有符号包大小
            signed_size = _compute_signed_size(pkt, config, perspective)

            # 添加到特征列表（含IP和端口信息）
            features.append((pkt.timestamp, signed_size, pkt.src_ip, pkt.src_port, pkt.dst_ip, pkt.dst_port))

            if counter:
                counter.increment()

        if counter:
            counter.finish()

    except KeyboardInterrupt:
        if counter:
            counter.finish()
        print("\n用户中断，已处理的数据将被返回", file=sys.stderr)

    # 按时间戳排序
    features.sort(key=lambda x: x[0])

    return features


def _compute_signed_size(pkt: PacketInfo, config: Config, perspective: str) -> int:
    """
    计算有符号包大小（正数=发送，负数=接收）

    Args:
        pkt: 数据包信息
        config: 配置对象
        perspective: 抓包视角（mac/vps）

    Returns:
        有符号包大小
    """
    is_outgoing = config.is_outgoing(pkt.src_ip, perspective)

    if is_outgoing:
        return pkt.length   # 发送：正数
    else:
        return -pkt.length  # 接收：负数


def classify_flow(pkt: PacketInfo, config: Config) -> str:
    """
    分类数据包属于哪类流量

    Args:
        pkt: 数据包信息
        config: 配置对象

    Returns:
        流量类型（mac_vps/vps_website/other）
    """
    # Flow A: macOS <-> VPS隧道流量
    if pkt.src_port == config.vps_tunnel_port or pkt.dst_port == config.vps_tunnel_port:
        if (pkt.src_ip == config.local_ip or pkt.dst_ip == config.local_ip or
            pkt.src_ip == config.vps_ip or pkt.dst_ip == config.vps_ip):
            return config.FLOW_MAC_VPS

    # Flow B: VPS <-> 网站流量
    if (pkt.src_ip == config.vps_ip or pkt.dst_ip == config.vps_ip):
        if pkt.src_port != config.vps_tunnel_port and pkt.dst_port != config.vps_tunnel_port:
            if pkt.src_port != 22 and pkt.dst_port != 22:  # 排除SSH
                return config.FLOW_VPS_WEBSITE

    return "other"


def extract_multi_flows(
    pcap_path: str,
    config: Config,
    perspective: str = "mac",
    skip_zero: bool = True,
    show_progress: bool = True
) -> dict:
    """
    从pcap文件中同时提取多种流量类型

    Args:
        pcap_path: pcap文件路径
        config: 配置对象
        perspective: 抓包视角（mac/vps）
        skip_zero: 是否跳过0字节包
        show_progress: 是否显示进度

    Returns:
        字典：{flow_type: [(timestamp, signed_size), ...]}
    """
    flows = {
        config.FLOW_MAC_VPS: [],
        config.FLOW_VPS_WEBSITE: [],
        "other": []
    }

    counter = PacketCounter(report_interval=10000) if show_progress else None

    if show_progress:
        print(f"正在处理（多流量模式）: {pcap_path}", file=sys.stderr)

    try:
        # 流式读取所有IP数据包
        for pkt in iter_packets(pcap_path, config, 'ip'):
            if skip_zero and pkt.length == 0:
                continue

            # 分类流量
            flow_type = classify_flow(pkt, config)

            # 计算有符号包大小
            signed_size = _compute_signed_size(pkt, config, perspective)

            # 添加到对应流量列表
            flows[flow_type].append((pkt.timestamp, signed_size))

            if counter:
                counter.increment()

        if counter:
            counter.finish()

    except KeyboardInterrupt:
        if counter:
            counter.finish()
        print("\n用户中断", file=sys.stderr)

    # 排序所有流量
    for flow_type in flows:
        flows[flow_type].sort(key=lambda x: x[0])

    return flows
