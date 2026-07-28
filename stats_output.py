#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集统计脚本
统计 output/captures 和 output/vps 下各平台各行为的 pcap 文件数目
"""

import os
from collections import defaultdict

DIRS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "output/captures"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "output/vps"),
]

# 行为归一化：将不同平台的“分享”类动作合并到同一列
ACTION_ALIAS = {
    "repost": "share",
    "retweet": "share",
    "share": "share",
}


def parse_filename(filename):
    """
    从文件名提取 platform 和 action
    格式: {timestamp}_{platform}_{action}_{num}_{side}.pcap
    例: 20260519_131106_twitter_browse_1_vps.pcap
    """
    name = filename.rsplit(".", 1)[0]  # 去掉扩展名
    parts = name.split("_")
    # parts[0]=日期 parts[1]=时间 parts[2]=platform parts[3]=action ...
    if len(parts) >= 5:
        platform = parts[2]
        action = parts[3]
        action = ACTION_ALIAS.get(action, action)
        return platform, action
    return None, None


def count_pcaps(root_dir):
    """统计目录下各平台各行为的 pcap 数"""
    stats = defaultdict(lambda: defaultdict(int))
    if not os.path.exists(root_dir):
        return stats

    for platform_dir in sorted(os.listdir(root_dir)):
        platform_path = os.path.join(root_dir, platform_dir)
        if not os.path.isdir(platform_path):
            continue
        for fname in os.listdir(platform_path):
            if not fname.endswith(".pcap"):
                continue
            platform, action = parse_filename(fname)
            if platform and action:
                stats[platform][action] += 1
    return stats


def print_table(title, stats):
    """打印统计表格"""
    if not stats:
        print(f"\n{title}: (空)")
        return

    # 收集所有行为类型
    all_actions = sorted({a for acts in stats.values() for a in acts})
    platforms = sorted(stats.keys())

    # 表头
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

    # 合计行
    print(sep)
    totals_row = f"{'合计':<{col_w}}" + "".join(
        f"{sum(stats[p].get(a, 0) for p in platforms):>{col_w}}" for a in all_actions
    ) + f"{grand_total:>{col_w}}"
    print(totals_row)


def main():
    print("=" * 60)
    print("数据集统计")
    print("=" * 60)

    for d in DIRS:
        label = os.path.basename(os.path.dirname(d)) + "/" + os.path.basename(d)
        stats = count_pcaps(d)
        print_table(f"📂 {d}", stats)

    # 汇总两个目录（去重：同一对 pcap 在两端各一份，这里分开统计不去重）
    print("\n")


if __name__ == "__main__":
    main()
