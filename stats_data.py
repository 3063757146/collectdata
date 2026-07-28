#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data 目录统计脚本
统计 data/ 下各来源/平台/行为的数据集文件数目
目录结构: data/{source_dir}/{platform}/{side}/{basename}.{ext}
"""

import os
import sys
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 统计的文件扩展名
VALID_EXTENSIONS = {'.csv', '.json', '.npy', '.pkl'}

# 行为归一化
ACTION_ALIAS = {
    "repost": "share",
    "retweet": "share",
    "share": "share",
}


def parse_filename(filename):
    """
    从文件名提取 platform 和 action
    格式: {timestamp}_{platform}_{action}_{num}_{side}.{ext}
    例: 20260728_034546_weibo_like_1_vps.csv
    """
    name = filename.rsplit(".", 1)[0]
    parts = name.split("_")
    if len(parts) >= 5:
        platform = parts[2]
        action = parts[3]
        action = ACTION_ALIAS.get(action, action)
        return platform, action
    return None, None


def count_data(data_dir, target_side='vps'):
    """统计 data 目录下各来源/平台/行为的文件数（只统计指定 side 目录）"""
    stats = {}

    if not os.path.exists(data_dir):
        return stats

    for source_dir in sorted(os.listdir(data_dir)):
        source_path = os.path.join(data_dir, source_dir)
        if not os.path.isdir(source_path):
            continue

        source_stats = defaultdict(lambda: defaultdict(int))
        total_files = 0

        for platform_dir in sorted(os.listdir(source_path)):
            platform_path = os.path.join(source_path, platform_dir)
            if not os.path.isdir(platform_path):
                continue

            # 只统计指定的 side 目录（vps 或 mac）
            side_path = os.path.join(platform_path, target_side)
            if not os.path.isdir(side_path):
                continue

            for fname in os.listdir(side_path):
                ext = os.path.splitext(fname)[1].lower()
                if ext not in VALID_EXTENSIONS:
                    continue
                platform, action = parse_filename(fname)
                if platform and action:
                    source_stats[platform][action] += 1
                    total_files += 1

        if total_files > 0:
            stats[source_dir] = dict(source_stats)

    return stats


def print_table(title, stats):
    """打印统计表格"""
    if not stats:
        print(f"\n{title}: (空)")
        return

    all_actions = sorted({a for acts in stats.values() for a in acts})
    platforms = sorted(stats.keys())

    col_w = 10
    header = f"{'平台':<{col_w}}" + "".join(f"{a:>{col_w}}" for a in all_actions) + f"{'合计':>{col_w}}"
    sep = "-" * len(header)

    print(f"\n{title}")
    print(sep)
    print(header)
    print(sep)

    grand_total = 0
    for p in platforms:
        row_total = sum(stats[p].values())
        grand_total += row_total
        row = f"{p:<{col_w}}" + "".join(f"{stats[p].get(a, 0):>{col_w}}" for a in all_actions) + f"{row_total:>{col_w}}"
        print(row)

    print(sep)
    totals_row = f"{'合计':<{col_w}}" + "".join(
        f"{sum(stats[p].get(a, 0) for p in platforms):>{col_w}}" for a in all_actions
    ) + f"{grand_total:>{col_w}}"
    print(totals_row)


def print_summary(all_stats):
    """打印汇总表（跨来源合并）"""
    merged = defaultdict(lambda: defaultdict(int))
    for source, stats in all_stats.items():
        for platform, actions in stats.items():
            for action, count in actions.items():
                merged[platform][action] += count

    if not merged:
        return

    print_table("📊 汇总（所有来源合计）", dict(merged))


def main():
    import argparse

    parser = argparse.ArgumentParser(description='统计 data 目录下数据集文件数量')
    parser.add_argument('--side', '-s', choices=['vps', 'mac'], default='vps',
                        help='统计指定的 side 目录（默认: vps）')
    args = parser.parse_args()

    print("=" * 60)
    print("data 目录数据集统计")
    print("=" * 60)
    print(f"统计路径: {DATA_DIR}")
    print(f"统计目录: {args.side}/")

    if not os.path.exists(DATA_DIR):
        print(f"❌ data 目录不存在: {DATA_DIR}")
        sys.exit(1)

    all_stats = count_data(DATA_DIR, target_side=args.side)

    if not all_stats:
        print(f"⚠️  data 目录下没有 {args.side} 数据文件")
        sys.exit(0)

    for source_dir in sorted(all_stats.keys()):
        title = f"📂 data/{source_dir}/{args.side}"
        print_table(title, all_stats[source_dir])

    print_summary(all_stats)

    print()


if __name__ == "__main__":
    main()