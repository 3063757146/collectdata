#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCAP流量特征提取工具 - 主程序
从pcap文件提取(时间戳, 正负包大小)特征
"""

import sys
import os
import argparse
import time
from .config import Config
from .feature_extractor import extract_features
from .data_exporter import export
from .utils import print_statistics


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='从pcap文件提取流量特征',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 提取Flow A（macOS <-> VPS）
  %(prog)s -i data/weibo-15.pcapng -o output/flow_a.csv --flow mac_vps

  # 提取Flow B（VPS <-> 网站）
  %(prog)s -i data/all_outbound.pcap -o output/flow_b.csv --flow vps_website --perspective vps

  # NumPy格式输出
  %(prog)s -i data/weibo-15.pcapng -o output/features.npy --format numpy

  # 包含0字节包
  %(prog)s -i data/weibo-15.pcapng -o output/flow_a_full.csv --include-zero
        """
    )

    # 输入输出
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='输入pcap/pcapng文件路径'
    )
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='输出文件路径'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['csv', 'json', 'numpy', 'npy', 'pickle', 'pkl'],
        default='csv',
        help='输出格式（默认: csv）'
    )

    # 流量类型
    parser.add_argument(
        '--flow',
        choices=['mac_vps', 'vps_website', 'all'],
        default='mac_vps',
        help='流量类型（默认: mac_vps）'
    )
    parser.add_argument(
        '--perspective',
        choices=['mac', 'vps'],
        default='mac',
        help='抓包视角（默认: mac）'
    )

    # IP配置
    parser.add_argument(
        '--local-ip',
        default='10.67.227.153',
        help='macOS私有IP（默认: 10.67.227.153）'
    )
    parser.add_argument(
        '--local-public-ip',
        default='124.127.223.133',
        help='macOS公网IP/NAT后（默认: 124.127.223.133）'
    )
    parser.add_argument(
        '--vps-ip',
        default='216.167.34.54',
        help='VPS IP（默认: 216.167.34.54）'
    )
    parser.add_argument(
        '--vps-port',
        type=int,
        default=33979,
        help='VPS隧道端口（默认: 33979）'
    )

    # 处理选项
    parser.add_argument(
        '--include-zero',
        action='store_true',
        help='包含0字节包（默认跳过）'
    )
    parser.add_argument(
        '--epoch-time',
        action='store_true',
        help='使用epoch时间戳而非可读格式（仅CSV/JSON）'
    )
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='不显示进度条'
    )
    parser.add_argument(
        '--no-stats',
        action='store_true',
        help='不显示统计摘要'
    )
    parser.add_argument(
        '--tcpdump-path',
        default='tcpdump',
        help='tcpdump可执行文件路径（默认: tcpdump）'
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 构建配置对象
    config = Config(
        local_ip=args.local_ip,
        local_public_ip=args.local_public_ip,
        vps_ip=args.vps_ip,
        vps_tunnel_port=args.vps_port,
        tcpdump_path=args.tcpdump_path,
        skip_zero_length=not args.include_zero
    )

    # 检查输入文件
    if not os.path.exists(args.input):
        print(f"❌ 错误: 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    # 创建输出目录
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    print("="*60)
    print("PCAP流量特征提取工具")
    print("="*60)
    print(f"输入文件: {args.input}")
    print(f"输出文件: {args.output}")
    print(f"输出格式: {args.format}")
    print(f"流量类型: {args.flow}")
    print(f"抓包视角: {args.perspective}")
    print(f"跳过0字节包: {config.skip_zero_length}")
    print("="*60 + "\n")

    # 记录开始时间
    start_time = time.time()

    try:
        # 提取特征
        features = extract_features(
            pcap_path=args.input,
            config=config,
            flow_type=args.flow,
            perspective=args.perspective,
            skip_zero=config.skip_zero_length,
            show_progress=not args.no_progress
        )

        if not features:
            print("\n⚠️  警告: 未提取到任何数据", file=sys.stderr)
            print("请检查:")
            print("  1. pcap文件是否包含相关流量")
            print("  2. 流量类型和视角配置是否正确")
            print("  3. IP地址和端口配置是否正确")
            sys.exit(1)

        # 导出数据
        export_kwargs = {}
        if args.format in ['csv', 'json']:
            export_kwargs['human_timestamps'] = not args.epoch_time

        export(
            features=features,
            output_path=args.output,
            format_type=args.format,
            **export_kwargs
        )

        # 记录结束时间
        end_time = time.time()

        # 显示统计摘要
        if not args.no_stats:
            print_statistics(features, start_time, end_time)

        print("✅ 处理完成！")

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断", file=sys.stderr)
        sys.exit(130)
    except FileNotFoundError as e:
        print(f"\n❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
