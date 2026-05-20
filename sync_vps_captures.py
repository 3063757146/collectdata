#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步 VPS captures 到本地，传输完毕后删除 VPS 上的文件。

文件名格式: YYYYMMDD_HHMMSS_{platform}_{action}_{num}_vps.pcap
本地目标:   output/captures/{platform}/

用法:
    python3 sync_vps_captures.py
    python3 sync_vps_captures.py --dry-run   # 只列出，不下载不删除
"""

import os
import sys
import argparse
import paramiko

# ============================================================
# VPS 配置
# ============================================================
SSH_HOST = "216.167.34.54"
SSH_PORT = 22
SSH_USER = "root"
SSH_PASSWORD = "rXQUHMhMh4AnlgO5"
REMOTE_DIR = "/root/captures"
LOCAL_BASE = os.path.join(os.path.dirname(__file__), "output/vps")

KNOWN_PLATFORMS = {"weibo", "facebook", "tiktok", "twitter", "zhihu"}


def parse_platform(filename: str) -> str | None:
    """从文件名中提取平台名，例如 20260519_182154_weibo_comment_1_vps.pcap → weibo"""
    parts = filename.split("_")
    # 格式: [日期, 时间, platform, action, num, vps.pcap]
    if len(parts) >= 3 and parts[2] in KNOWN_PLATFORMS:
        return parts[2]
    return None


def connect() -> tuple[paramiko.SSHClient, paramiko.SFTPClient]:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER,
                   password=SSH_PASSWORD, timeout=15)
    sftp = client.open_sftp()
    return client, sftp


def list_remote_files(sftp: paramiko.SFTPClient) -> list[str]:
    return [f.filename for f in sftp.listdir_attr(REMOTE_DIR)
            if f.filename.endswith(".pcap")]


def sync(dry_run: bool = False):
    print(f"{'[DRY RUN] ' if dry_run else ''}连接 VPS {SSH_HOST}...")
    client, sftp = connect()
    print("✅ 已连接\n")

    files = sorted(list_remote_files(sftp))
    if not files:
        print("VPS 上没有 pcap 文件，退出。")
        sftp.close()
        client.close()
        return

    print(f"发现 {len(files)} 个文件：")

    # 按 platform 分组，跳过无法解析的
    grouped: dict[str, list[str]] = {}
    skipped = []
    for f in files:
        platform = parse_platform(f)
        if platform:
            grouped.setdefault(platform, []).append(f)
        else:
            skipped.append(f)
            print(f"  ⚠️  无法识别平台，跳过: {f}")

    for platform, pfiles in grouped.items():
        print(f"\n  [{platform}] {len(pfiles)} 个文件")
        for f in pfiles:
            print(f"    {f}")

    if dry_run:
        print("\n[DRY RUN] 不执行下载/删除。")
        sftp.close()
        client.close()
        return

    print("\n开始下载...")
    downloaded = []
    failed = []

    for platform, pfiles in grouped.items():
        local_dir = os.path.join(LOCAL_BASE, platform)
        os.makedirs(local_dir, exist_ok=True)

        for filename in pfiles:
            remote_path = f"{REMOTE_DIR}/{filename}"
            local_path = os.path.join(local_dir, filename)

            # 获取远端文件大小
            remote_stat = sftp.stat(remote_path)
            remote_size = remote_stat.st_size

            print(f"  ↓ {filename} ({remote_size/1024/1024:.1f} MB) → {platform}/", end="", flush=True)

            try:
                sftp.get(remote_path, local_path)

                # 校验：本地文件大小一致
                local_size = os.path.getsize(local_path)
                if local_size == remote_size:
                    print(f" ✅")
                    downloaded.append(remote_path)
                else:
                    print(f" ❌ 大小不符（本地 {local_size} vs 远端 {remote_size}）")
                    failed.append(filename)
                    os.remove(local_path)

            except Exception as e:
                print(f" ❌ {e}")
                failed.append(filename)
                if os.path.exists(local_path):
                    os.remove(local_path)

    # 汇总
    print(f"\n下载完成: ✅ {len(downloaded)} 个  ❌ {len(failed)} 个")

    if failed:
        print(f"失败文件: {failed}")
        print("因为有失败，不删除 VPS 文件，请手动处理。")
        sftp.close()
        client.close()
        return

    # 全部成功 → 删除 VPS 上所有 pcap（包括无法识别平台的）
    all_remote = [f"{REMOTE_DIR}/{f}" for f in files]
    print(f"\n删除 VPS 上 {len(all_remote)} 个文件...")
    _, stdout, stderr = client.exec_command(f"rm -f {REMOTE_DIR}/*.pcap")
    stdout.channel.recv_exit_status()
    err = stderr.read().decode().strip()
    if err:
        print(f"  ⚠️  删除时有警告: {err}")
    else:
        print("  ✅ VPS captures 已清空")

    sftp.close()
    client.close()
    print("\n✅ 同步完成！")


def main():
    parser = argparse.ArgumentParser(description="同步 VPS pcap 文件到本地")
    parser.add_argument("--dry-run", action="store_true", help="只列出文件，不下载不删除")
    args = parser.parse_args()
    sync(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
