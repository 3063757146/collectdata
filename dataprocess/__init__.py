#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCAP流量特征提取工具
从pcap文件提取(时间戳, 正负包大小)特征用于流量分析
"""

__version__ = '1.0.0'
__author__ = 'Traffic Analysis Tool'

# 导出核心函数和类
from .config import Config
from .pcap_parser import PacketInfo, iter_packets, parse_tcpdump_line
from .feature_extractor import extract_features, extract_multi_flows
from .data_exporter import export, export_csv, export_json, export_numpy, export_pickle
from .utils import (
    epoch_to_datetime_str,
    validate_timestamp,
    validate_packet_size,
    print_statistics
)

__all__ = [
    # 配置
    'Config',

    # 解析器
    'PacketInfo',
    'iter_packets',
    'parse_tcpdump_line',

    # 特征提取
    'extract_features',
    'extract_multi_flows',

    # 导出
    'export',
    'export_csv',
    'export_json',
    'export_numpy',
    'export_pickle',

    # 工具函数
    'epoch_to_datetime_str',
    'validate_timestamp',
    'validate_packet_size',
    'print_statistics',
]
