#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量 pcap 预处理脚本

用法:
    python3 process_data.py output/vps
    python3 process_data.py output/vps/weibo
    python3 process_data.py output/captures
    python3 process_data.py output/vps --format npy
    python3 process_data.py output/vps --skip-existing
    python3 process_data.py output/vps --dry-run

规则:
    - pcap 的父目录名 = platform
    - xxx_vps.pcap  → perspective=vps,  flow=vps_website
    - xxx_mac.pcap  → perspective=mac,  flow=mac_vps
    - 输出到 data/{platform}/{basename}.{ext}
"""

import os
import sys
import argparse
import time
import traceback
from typing import List, Tuple

# 确保可以导入 dataprocess 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataprocess.config import Config
from dataprocess.feature_extractor import extract_features
from dataprocess.data_exporter import export


# ============================================================
# 常量
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

FORMAT_EXTENSIONS = {
    'csv': '.csv',
    'json': '.json',
    'numpy': '.npy',
    'npy': '.npy',
    'pickle': '.pkl',
    'pkl': '.pkl',
}

# 已知平台列表（用于验证，不在列表内的会打印警告但不阻止处理）
KNOWN_PLATFORMS = {'weibo', 'facebook', 'instagram', 'tiktok', 'twitter', 'zhihu'}


# ============================================================
# 核心逻辑
# ============================================================

def find_pcap_files(root_path: str) -> List[str]:
    """递归查找目录下所有 .pcap 文件"""
    pcap_files = []
    for dirpath, _, filenames in os.walk(root_path):
        for fname in sorted(filenames):
            if fname.endswith('.pcap') or fname.endswith('.pcapng'):
                pcap_files.append(os.path.join(dirpath, fname))
    return sorted(pcap_files)


def get_platform(pcap_path: str) -> str:
    """从 pcap 路径提取平台名（父目录名）"""
    return os.path.basename(os.path.dirname(pcap_path))


def get_side(pcap_path: str) -> str:
    """
    从文件名提取端信息：'mac' 或 'vps'
    文件名格式: {timestamp}_{platform}_{action}_{num}_{side}.pcap
    """
    basename = os.path.basename(pcap_path)
    name_without_ext = basename.rsplit('.', 1)[0]
    parts = name_without_ext.split('_')
    if parts:
        last = parts[-1].lower()
        if last in ('mac', 'vps'):
            return last
    return 'vps'  # 默认当作 vps 端


def get_flow_config(side: str) -> Tuple[str, str]:
    """
    根据端返回 (flow_type, perspective)

    mac 端：macOS 抓取的是 mac <-> vps 的隧道流量
    vps 端：VPS 抓取的是 vps <-> website 的流量
    """
    if side == 'mac':
        return 'mac_vps', 'mac'
    else:
        return 'vps_website', 'vps'


def get_output_path(pcap_path: str, platform: str, side: str, fmt: str) -> str:
    """构建输出文件路径：data/{platform}/{side}/{basename}.{ext}"""
    basename = os.path.basename(pcap_path)
    name_without_ext = basename.rsplit('.', 1)[0]
    ext = FORMAT_EXTENSIONS[fmt]
    output_dir = os.path.join(DATA_DIR, platform, side)
    return os.path.join(output_dir, name_without_ext + ext)


def process_one(
    pcap_path: str,
    fmt: str,
    skip_existing: bool,
    dry_run: bool,
    config: Config,
) -> str:
    """
    处理单个 pcap 文件

    Returns:
        'ok' | 'skipped' | 'empty' | 'error'
    """
    platform = get_platform(pcap_path)
    side = get_side(pcap_path)
    flow_type, perspective = get_flow_config(side)
    output_path = get_output_path(pcap_path, platform, side, fmt)

    if platform not in KNOWN_PLATFORMS:
        print(f"  ⚠️  未知平台目录: {platform}，继续处理")

    if skip_existing and os.path.exists(output_path):
        return 'skipped'

    if dry_run:
        print(f"  [dry-run] {os.path.basename(pcap_path)}")
        print(f"           platform={platform}  side={side}  flow={flow_type}")
        print(f"           → {output_path}")
        return 'ok'

    # 创建输出目录
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        features = extract_features(
            pcap_path=pcap_path,
            config=config,
            flow_type=flow_type,
            perspective=perspective,
            skip_zero=config.skip_zero_length,
            show_progress=False,
        )

        if not features:
            print(f"  ⚠️  空结果（无匹配包）: {os.path.basename(pcap_path)}")
            return 'empty'

        export_kwargs = {}
        if fmt in ('csv', 'json'):
            export_kwargs['human_timestamps'] = False  # 用 epoch 更适合机器学习

        export(features, output_path, format_type=fmt, **export_kwargs)
        return 'ok'

    except Exception as e:
        print(f"  ❌ 处理失败: {os.path.basename(pcap_path)}: {e}")
        traceback.print_exc()
        return 'error'


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='批量 pcap 预处理：提取流量特征并保存到 data/{platform}/',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理所有 VPS 抓包
  %(prog)s output/vps

  # 只处理微博的 VPS 抓包
  %(prog)s output/vps/weibo

  # 处理 macOS 端抓包，NumPy 格式
  %(prog)s output/captures --format npy

  # 跳过已处理的文件（增量处理）
  %(prog)s output/vps --skip-existing

  # 预览（不实际处理）
  %(prog)s output/vps --dry-run

输出目录: data/{platform}/
        """
    )

    parser.add_argument(
        'input_path',
        help='输入路径（output/vps 或 output/vps/weibo 等）'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['csv', 'json', 'numpy', 'npy', 'pickle', 'pkl'],
        default='csv',
        dest='fmt',
        help='输出格式（默认: csv）'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='跳过已存在的输出文件（增量模式）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='只打印计划，不实际处理'
    )
    parser.add_argument(
        '--vps-ip',
        default='216.167.34.54',
    )
    parser.add_argument(
        '--local-ip',
        default='10.6.32.145',
    )

    args = parser.parse_args()

    # 处理输入路径（支持相对路径）
    input_path = args.input_path
    if not os.path.isabs(input_path):
        input_path = os.path.join(BASE_DIR, input_path)
    input_path = os.path.normpath(input_path)

    if not os.path.exists(input_path):
        print(f"❌ 路径不存在: {input_path}", file=sys.stderr)
        sys.exit(1)

    # 构建配置
    config = Config(
        local_ip=args.local_ip,
        vps_ip=args.vps_ip,
        skip_zero_length=True,
    )

    # 扫描 pcap 文件
    print(f"扫描路径: {input_path}")
    pcap_files = find_pcap_files(input_path)

    if not pcap_files:
        print("⚠️  未找到任何 pcap/pcapng 文件")
        sys.exit(0)

    print(f"找到 {len(pcap_files)} 个 pcap 文件\n")

    if args.dry_run:
        print("=" * 60)
        print("[dry-run 模式] 以下文件将被处理：")
        print("=" * 60)

    # 统计
    stats = {'ok': 0, 'skipped': 0, 'empty': 0, 'error': 0}
    start_time = time.time()

    # 按平台分组显示进度
    current_platform = None

    for i, pcap_path in enumerate(pcap_files, 1):
        platform = get_platform(pcap_path)

        # 打印平台分隔
        if platform != current_platform:
            current_platform = platform
            print(f"\n── {platform} ──")

        result = process_one(
            pcap_path=pcap_path,
            fmt=args.fmt,
            skip_existing=args.skip_existing,
            dry_run=args.dry_run,
            config=config,
        )
        stats[result] += 1

        if result == 'skipped':
            print(f"  [{i:4d}/{len(pcap_files)}] ⏭  {os.path.basename(pcap_path)}")
        elif result == 'ok' and not args.dry_run:
            output_path = get_output_path(pcap_path, platform, get_side(pcap_path), args.fmt)
            print(f"  [{i:4d}/{len(pcap_files)}] ✅ {os.path.basename(pcap_path)}")
            print(f"           → {os.path.relpath(output_path, BASE_DIR)}")

    # 打印汇总
    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"处理完成  耗时 {elapsed:.1f}s")
    print(f"  ✅ 成功:     {stats['ok']}")
    print(f"  ⏭  跳过:     {stats['skipped']}")
    print(f"  ⚠️  空结果:   {stats['empty']}")
    print(f"  ❌ 失败:     {stats['error']}")
    print(f"{'=' * 60}")

    if stats['error'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
