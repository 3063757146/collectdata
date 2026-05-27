#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据导出模块
支持多种格式导出流量特征：CSV、JSON、NumPy、Pickle
"""

import csv
import json
import pickle
from typing import List, Tuple
from .utils import epoch_to_datetime_str


def export_csv(
    features: List[Tuple[float, int]],
    output_path: str,
    human_timestamps: bool = True
):
    """
    导出为CSV格式

    Args:
        features: [(timestamp, signed_size), ...]
        output_path: 输出文件路径
        human_timestamps: True使用可读时间，False使用epoch时间戳
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        # 固定列宽对齐输出
        fmt = "{:<18} {:>7} {:<16} {:>5} {:<16} {:>5}\n"
        f.write(fmt.format('timestamp', 'size', 'src_ip', 'sport', 'dst_ip', 'dport'))

        for row in features:
            timestamp, size = row[0], row[1]
            src_ip = row[2] if len(row) > 2 else ''
            src_port = row[3] if len(row) > 3 else ''
            dst_ip = row[4] if len(row) > 4 else ''
            dst_port = row[5] if len(row) > 5 else ''
            if human_timestamps:
                ts_str = epoch_to_datetime_str(timestamp)
            else:
                ts_str = f"{timestamp:.6f}"
            f.write(fmt.format(ts_str, size, src_ip, src_port, dst_ip, dst_port))

    print(f"✅ CSV已导出: {output_path} ({len(features)} 条)")


def export_json(
    features: List[Tuple[float, int]],
    output_path: str,
    human_timestamps: bool = True,
    indent: int = None
):
    """
    导出为JSON格式

    Args:
        features: [(timestamp, signed_size), ...]
        output_path: 输出文件路径
        human_timestamps: True使用可读时间，False使用epoch时间戳
        indent: JSON缩进（None为紧凑格式）
    """
    data = []
    for row in features:
        timestamp, size = row[0], row[1]
        if human_timestamps:
            ts = epoch_to_datetime_str(timestamp)
        else:
            ts = timestamp

        entry = {"timestamp": ts, "size": size}
        if len(row) > 2:
            entry["src_ip"] = row[2]
            entry["src_port"] = row[3]
            entry["dst_ip"] = row[4]
            entry["dst_port"] = row[5]
        data.append(entry)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)

    print(f"✅ JSON已导出: {output_path} ({len(features)} 条)")


def export_numpy(
    features: List[Tuple[float, int]],
    output_path: str
):
    """
    导出为NumPy .npy格式

    Args:
        features: [(timestamp, signed_size), ...]
        output_path: 输出文件路径（建议 .npy 扩展名）

    Raises:
        ImportError: NumPy未安装
    """
    try:
        import numpy as np
    except ImportError:
        raise ImportError(
            "NumPy未安装。请运行: pip install numpy\n"
            "或使用其他导出格式（csv/json/pickle）"
        )

    # 转换为NumPy数组，shape=(N, 2)
    # 列0=时间戳（epoch），列1=有符号包大小
    arr = np.array(features, dtype=np.float64)

    np.save(output_path, arr)

    print(f"✅ NumPy已导出: {output_path} (shape={arr.shape}, dtype={arr.dtype})")


def export_pickle(
    features: List[Tuple[float, int]],
    output_path: str
):
    """
    导出为Pickle格式（Python原生序列化）

    Args:
        features: [(timestamp, signed_size), ...]
        output_path: 输出文件路径（建议 .pkl 扩展名）
    """
    with open(output_path, 'wb') as f:
        pickle.dump(features, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"✅ Pickle已导出: {output_path} ({len(features)} 条)")


def export(
    features: List[Tuple[float, int]],
    output_path: str,
    format_type: str = 'csv',
    **kwargs
):
    """
    统一导出接口

    Args:
        features: [(timestamp, signed_size), ...]
        output_path: 输出文件路径
        format_type: 格式类型（csv/json/numpy/pickle）
        **kwargs: 传递给具体导出函数的参数

    Raises:
        ValueError: 格式类型无效
    """
    if format_type == 'csv':
        export_csv(features, output_path, **kwargs)
    elif format_type == 'json':
        export_json(features, output_path, **kwargs)
    elif format_type == 'numpy' or format_type == 'npy':
        export_numpy(features, output_path)
    elif format_type == 'pickle' or format_type == 'pkl':
        export_pickle(features, output_path)
    else:
        raise ValueError(f"不支持的格式: {format_type}。支持的格式: csv, json, numpy, pickle")
