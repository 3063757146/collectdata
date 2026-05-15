#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
显示实际执行的抓包命令
"""

from capture.config import CaptureConfig
from capture.label import generate_filename
import time

config = CaptureConfig()

print("="*70)
print("📝 实际执行的抓包命令")
print("="*70)

# 生成示例文件名
label = "weibo_repost_1"
timestamp = time.time()
mac_filename = generate_filename(label, "mac", timestamp)
vps_filename = generate_filename(label, "vps", timestamp)

local_pcap = f"{config.local_output_dir}/{mac_filename}"
remote_pcap = f"{config.remote_output_dir}/{vps_filename}"

# 1. macOS端命令
print("\n【1. macOS端（本地）抓包命令】")
print("-"*70)

local_bpf = config.get_local_bpf()
local_cmd = [
    'sudo',
    config.local_tcpdump,
    '-i', config.interface_local,
    '-s', str(config.snaplen),
    '-w', local_pcap,
    local_bpf
]

print("完整命令：")
print(' '.join(local_cmd))
print()
print("参数说明：")
print(f"  -i {config.interface_local}  : 网卡接口")
print(f"  -s {config.snaplen}          : 抓包长度（0=完整包）")
print(f"  -w {local_pcap} : 输出文件")
print(f"  BPF: {local_bpf}")
print()
print("💡 这条命令的意思：")
print(f"   在网卡 {config.interface_local} 上抓取所有与 {config.vps_ip} 通信的流量")
print(f"   保存到 {local_pcap}")

# 2. VPS端命令
print("\n【2. VPS端（远程）抓包命令】")
print("-"*70)

remote_bpf = config.get_remote_bpf(platform='weibo')
remote_cmd = [
    config.remote_tcpdump,
    '-i', config.interface_remote,
    '-s', str(config.snaplen),
    '-w', remote_pcap,
    f"'{remote_bpf}'"
]

print("完整命令（在VPS上执行）：")
print(' '.join(remote_cmd))
print()
print("参数说明：")
print(f"  -i {config.interface_remote}  : 网卡接口")
print(f"  -s {config.snaplen}          : 抓包长度（0=完整包）")
print(f"  -w {remote_pcap} : 输出文件")
print(f"  BPF: {remote_bpf}")
print()
print("💡 这条命令的意思：")
print(f"   在网卡 {config.interface_remote} 上抓取流量，排除：")
print(f"   1. 从 {config.mac_public_ip} 到端口 {config.vps_tunnel_port} 的隧道流量")
print(f"   2. SSH流量（端口22）")
print(f"   保存到 {remote_pcap}")

# 3. 手动测试命令
print("\n" + "="*70)
print("🧪 手动测试命令（推荐）")
print("="*70)

test_file = "manual_test.pcap"
print("\n在本地运行以下命令，同时在浏览器访问微博：")
print()
print(f"sudo tcpdump -i en0 -s 0 -w {test_file} host 216.167.34.54")
print()
print("然后在另一个终端：")
print("1. 打开浏览器")
print("2. 配置代理：socks5://127.0.0.1:10818")
print("3. 访问 https://weibo.com")
print("4. 浏览一些内容")
print("5. 回到第一个终端按 Ctrl+C 停止抓包")
print()
print("检查结果：")
print(f"tshark -r {test_file} -q -z io,phs")
print()
print("💡 如果看到大量TCP流量 → 抓包工作正常，问题在run_capture.py的时序")
print("💡 如果只有ICMP/SSH → 代理配置有问题，或浏览器没用代理")

# 4. 快速测试脚本
print("\n" + "="*70)
print("⚡ 或者用这个一键测试脚本：")
print("="*70)
print()

test_script = f"""#!/bin/bash
# 一键测试本地抓包

echo "启动抓包（60秒）..."
sudo tcpdump -i en0 -s 0 -w test_$(date +%s).pcap host 216.167.34.54 &
PID=$!

echo "tcpdump PID: $PID"
echo "等待5秒让tcpdump初始化..."
sleep 5

echo ""
echo "现在请："
echo "1. 打开浏览器"
echo "2. 设置代理：socks5://127.0.0.1:10818"
echo "3. 访问 https://weibo.com 并浏览"
echo ""
echo "按Enter停止抓包..."
read

echo "停止抓包..."
sudo kill -TERM $PID
wait $PID

echo ""
echo "分析最新的pcap文件..."
LATEST=$(ls -t test_*.pcap | head -1)
echo "文件: $LATEST"
ls -lh "$LATEST"
echo ""
tshark -r "$LATEST" -q -z io,phs | head -30
"""

with open('quick_test_local.sh', 'w') as f:
    f.write(test_script)

print("已生成脚本: quick_test_local.sh")
print("运行方法：")
print("  chmod +x quick_test_local.sh")
print("  ./quick_test_local.sh")
