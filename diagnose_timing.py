#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断脚本抓包时机问题
对比手动启动和脚本启动tcpdump的差异
"""

import subprocess
import time
import os
import sys

print("="*70)
print("🔍 诊断tcpdump启动时机")
print("="*70)

# 测试1：检查tcpdump启动延迟
print("\n【测试1：tcpdump启动延迟】")
print("-"*70)

output_file = f"test_timing_{int(time.time())}.pcap"

print(f"启动tcpdump: {output_file}")
print("记录启动时间...")

start_time = time.time()

# 使用subprocess.Popen启动（和脚本相同）
proc = subprocess.Popen(
    ['sudo', '/usr/sbin/tcpdump', '-i', 'en0', '-s', '0', '-w', output_file, 'host', '216.167.34.54'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

# 检查进程是否启动
time.sleep(0.5)
if proc.poll() is not None:
    print("❌ tcpdump启动失败")
    _, stderr = proc.communicate()
    print(stderr)
    sys.exit(1)

print(f"✅ 进程启动 (PID: {proc.pid})")
after_popen = time.time()
print(f"   Popen耗时: {(after_popen - start_time)*1000:.1f}ms")

# 等待文件创建
print("\n等待pcap文件创建...")
for i in range(20):  # 最多等2秒
    if os.path.exists(output_file):
        file_created = time.time()
        print(f"✅ 文件创建 (耗时: {(file_created - start_time)*1000:.1f}ms)")
        break
    time.sleep(0.1)
else:
    print("❌ 文件未创建（2秒超时）")

# 等待文件可写
print("\n等待tcpdump真正开始抓包...")
initial_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0
print(f"   初始文件大小: {initial_size} bytes")

for i in range(50):  # 最多等5秒
    time.sleep(0.1)
    if os.path.exists(output_file):
        current_size = os.path.getsize(output_file)
        if current_size > initial_size:
            ready_time = time.time()
            print(f"✅ tcpdump开始抓包 (耗时: {(ready_time - start_time)*1000:.1f}ms)")
            print(f"   当前文件大小: {current_size} bytes")
            break
else:
    print("⚠️  5秒内未检测到抓包活动（文件大小未变）")

# 测试2：模拟bot执行
print("\n【测试2：模拟bot执行】")
print("-"*70)

print("当前等待策略：")
print(f"  - Popen后等待: 0.5秒")
print(f"  - manager.start()预热: 3秒")
print(f"  - 总等待: 3.5秒")
print()

total_wait = 3.5
print(f"如果tcpdump在 {total_wait}秒 内没准备好，就会错过流量")
print()

# 继续抓包10秒，模拟bot执行
print("继续抓包10秒，模拟bot执行...")
time.sleep(10)

# 停止tcpdump
print("\n停止tcpdump...")
proc.terminate()
time.sleep(1)

# 分析结果
print("\n【测试3：分析抓包结果】")
print("-"*70)

if not os.path.exists(output_file):
    print("❌ pcap文件不存在")
    sys.exit(1)

file_size = os.path.getsize(output_file)
print(f"文件大小: {file_size} bytes")

# 使用tshark分析
try:
    result = subprocess.run(
        ['tshark', '-r', output_file, '-q', '-z', 'io,phs'],
        capture_output=True,
        text=True,
        timeout=10
    )
    print("\n协议统计:")
    print(result.stdout[:500])

    # 统计包数
    result2 = subprocess.run(
        ['tshark', '-r', output_file],
        capture_output=True,
        text=True,
        timeout=10
    )
    lines = [l for l in result2.stdout.strip().split('\n') if l]
    total = len(lines)

    result3 = subprocess.run(
        ['tshark', '-r', output_file, '-Y', 'tcp'],
        capture_output=True,
        text=True,
        timeout=10
    )
    tcp_lines = [l for l in result3.stdout.strip().split('\n') if l]
    tcp = len(tcp_lines)

    print(f"\n包数量:")
    print(f"  总包数: {total}")
    print(f"  TCP包: {tcp}")

    # 显示前几个包的时间戳
    if lines:
        print(f"\n前5个包的时间戳:")
        for line in lines[:5]:
            print(f"  {line[:80]}")

except Exception as e:
    print(f"⚠️  无法分析: {e}")

# 诊断结论
print("\n" + "="*70)
print("💡 诊断结论")
print("="*70)

print("\n根据测试结果：")
print()
print("如果tcpdump启动耗时 > 3.5秒：")
print("  → 需要增加预热时间（capture/manager.py中的warmup_time）")
print()
print("如果文件创建延迟很大：")
print("  → 可能是磁盘IO问题，考虑更换输出目录")
print()
print("如果抓到的包很少：")
print("  → 说明tcpdump启动太慢，bot流量错过了")
print()

print(f"\n测试文件: {output_file}")
print("建议：根据上面的启动耗时，调整预热时间")
