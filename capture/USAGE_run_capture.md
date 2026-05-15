# run_capture.py 使用指南

## 概述

`run_capture.py` 是顶层抓包控制脚本，提供 **会话级别的抓包**。每次迭代包含完整的流程：

```
启动抓包 → 登录 → 访问 → 执行行为 → 退出 → 停止抓包 → 保存
```

与装饰器模式的区别：
- **装饰器模式**：在每个小动作（like/comment）上抓包，适合细粒度分析
- **会话级模式**：整个会话抓包，包含登录流量，适合完整行为分析

## 快速开始

### 基本用法

```bash
# 执行5次微博点赞（每次都是独立会话）
python3 run_capture.py --platform weibo --action like --num 5

# 执行3次Facebook评论
python3 run_capture.py --platform facebook --action comment --num 3

# 执行10次TikTok浏览
python3 run_capture.py --platform tiktok --action browse --num 10
```

### 完整参数

```bash
python3 run_capture.py \
  --platform weibo \      # 平台: weibo, facebook, tiktok
  --action like \         # 行为: like, comment, repost, share, post, browse
  --num 5 \               # 执行次数
  --timeout 600           # 单次超时（秒），默认300秒
```

## 支持的平台和行为

| 平台 | 支持的行为 |
|------|-----------|
| **weibo** | `like`, `comment`, `repost`, `post`, `browse` |
| **facebook** | `like`, `comment`, `share`, `browse` |
| **tiktok** | `like`, `comment`, `share`, `browse` |

## 工作流程

每次迭代的详细流程：

```
[迭代 i/num]
├─ 1. 生成标签: platform_action_i
│    例如: weibo_like_1, weibo_like_2, ...
│
├─ 2. 启动双端抓包
│    ├─ SSH连接VPS
│    ├─ VPS端启动tcpdump
│    └─ macOS端启动tcpdump
│
├─ 3. 启动浏览器
│    ├─ 打开平台首页
│    ├─ 检查登录状态
│    └─ 如需登录，等待手动登录
│
├─ 4. 执行指定行为
│    ├─ like: 浏览5条微博，点赞1-2次
│    ├─ comment: 浏览5条微博，评论1-2次
│    ├─ repost: 浏览5条微博，转发1-2次
│    ├─ post: 发布1条新微博
│    └─ browse: 浏览10条微博，不互动
│
├─ 5. 关闭浏览器
│
├─ 6. 停止双端抓包
│    ├─ 停止macOS端tcpdump
│    ├─ 停止VPS端tcpdump
│    ├─ 下载VPS端pcap
│    └─ 保存元数据JSON
│
├─ 7. 保存结果
│    ├─ weibo_like_1_mac.pcap
│    ├─ weibo_like_1_vps.pcap
│    └─ weibo_like_1_meta.json
│
└─ 8. 等待间隔（30秒）
     └─ 继续下一次迭代...
```

## 输出示例

执行 `python3 run_capture.py --platform weibo --action like --num 3` 后：

```
output/captures/
├── weibo_like_1_mac.pcap           # 第1次，macOS端
├── weibo_like_1_vps.pcap           # 第1次，VPS端
├── weibo_like_1_meta.json          # 第1次，元数据
├── weibo_like_2_mac.pcap           # 第2次，macOS端
├── weibo_like_2_vps.pcap           # 第2次，VPS端
├── weibo_like_2_meta.json          # 第2次，元数据
├── weibo_like_3_mac.pcap           # 第3次，macOS端
├── weibo_like_3_vps.pcap           # 第3次，VPS端
└── weibo_like_3_meta.json          # 第3次，元数据
```

每个pcap文件包含：
- **登录流量**：从打开首页到登录完成
- **浏览流量**：浏览微博的所有流量
- **行为流量**：执行点赞/评论/转发的流量
- **退出流量**：关闭浏览器前的流量

## 使用场景

### 场景1：采集点赞行为样本

```bash
# 采集10次点赞行为，用于训练模型
python3 run_capture.py --platform weibo --action like --num 10
```

**适合用于**：
- 研究点赞行为的流量特征
- 对比不同微博的点赞流量差异
- 训练点赞行为识别模型

### 场景2：采集评论行为样本

```bash
# 采集5次评论行为
python3 run_capture.py --platform weibo --action comment --num 5
```

**适合用于**：
- 研究评论行为的流量特征
- 对比点赞vs评论的流量差异
- 研究文本输入的流量模式

### 场景3：采集完整浏览会话

```bash
# 采集3次纯浏览会话（不互动）
python3 run_capture.py --platform weibo --action browse --num 3
```

**适合用于**：
- 研究背景流量模式
- 作为对照组（无互动行为）
- 研究浏览行为的流量特征

### 场景4：多平台对比

```bash
# 采集3个平台的点赞行为
python3 run_capture.py --platform weibo --action like --num 5
python3 run_capture.py --platform facebook --action like --num 5
python3 run_capture.py --platform tiktok --action like --num 5
```

**适合用于**：
- 对比不同平台的流量特征
- 研究跨平台的行为模式
- 训练平台识别模型

## Python API调用

除了命令行，也可以在Python代码中调用：

```python
from run_capture import run

# 执行5次微博点赞
success_count = run(
    platform="weibo",
    action="like",
    num=5,
    timeout=300
)

print(f"成功执行了 {success_count} 次")
```

## 日志输出

运行时会输出详细日志：

```
[2026-05-15 16:30:00] INFO: ======================================================================
[2026-05-15 16:30:00] INFO: Starting capture run: platform=weibo, action=like, num=5
[2026-05-15 16:30:00] INFO: ======================================================================

[2026-05-15 16:30:00] INFO: ======================================================================
[2026-05-15 16:30:00] INFO: Iteration 1/5
[2026-05-15 16:30:00] INFO: ======================================================================
[2026-05-15 16:30:00] INFO: [1/5] Starting capture: weibo_like_1
[2026-05-15 16:30:01] INFO: VPS connection established
[2026-05-15 16:30:02] INFO: Remote capture started: /tmp/captures/20260515_163002_weibo_like_1_vps.pcap
[2026-05-15 16:30:02] INFO: Local capture started: output/captures/20260515_163002_weibo_like_1_mac.pcap
[2026-05-15 16:30:02] INFO: [Iteration 1] Starting Weibo bot for action: like
[2026-05-15 16:30:15] INFO: [Iteration 1] Logged in successfully
[2026-05-15 16:30:45] INFO: [Iteration 1] Action completed successfully
[2026-05-15 16:30:45] INFO: [Iteration 1] Browser closed
[2026-05-15 16:30:45] INFO: [1/5] Stopping capture...
[2026-05-15 16:30:46] INFO: Local capture stopped
[2026-05-15 16:30:47] INFO: Remote capture stopped
[2026-05-15 16:30:50] INFO: Remote pcap downloaded: output/captures/20260515_163002_weibo_like_1_vps.pcap
[2026-05-15 16:30:50] INFO: [1/5] ✅ Success!
[2026-05-15 16:30:50] INFO:   Duration: 48.3s
[2026-05-15 16:30:50] INFO:   Local pcap: output/captures/20260515_163002_weibo_like_1_mac.pcap
[2026-05-15 16:30:50] INFO:   VPS pcap: output/captures/20260515_163002_weibo_like_1_vps.pcap

[2026-05-15 16:30:50] INFO: Waiting 30s before next iteration...

[继续下一次迭代...]
```

## 注意事项

### 1. 首次登录

第一次运行时，需要手动登录：
```
[Iteration 1] Not logged in, waiting for manual login...
⚠️  似乎还没有登录，请确认已登录后按回车...
```

在浏览器中登录后，按Enter继续。后续迭代会检查登录状态。

### 2. 权限要求

需要sudo权限运行tcpdump：
```bash
# 方法1：使用sudo
sudo python3 run_capture.py --platform weibo --action like --num 5

# 方法2：配置passwordless sudo（推荐）
sudo visudo -f /etc/sudoers.d/tcpdump
# 添加: your_username ALL=(ALL) NOPASSWD: /usr/sbin/tcpdump
```

### 3. VPS连接

确保VPS在线并可SSH连接。如果VPS不可达：
- 系统会自动降级到local-only模式
- 仍然会保存macOS端的pcap文件
- 日志会显示警告：`VPS unavailable`

### 4. 迭代间隔

每次迭代之间有30秒间隔，避免被检测为机器人。可以在代码中修改：

```python
# 在run_capture.py的run函数中
interval = 30  # 修改这个值（秒）
```

### 5. 超时设置

如果行为执行时间较长，增加超时：
```bash
# 10分钟超时
python3 run_capture.py --platform weibo --action post --num 3 --timeout 600
```

### 6. 磁盘空间

每次会话约生成10-50MB数据（双端合计），确保有足够磁盘空间：
- 10次迭代 ≈ 100-500MB
- 100次迭代 ≈ 1-5GB

## 故障排除

### Q1: 浏览器一直不登录

**问题**：脚本卡在 `waiting for manual login...`

**解决**：
1. 检查浏览器是否正常打开
2. 手动在浏览器中登录
3. 登录成功后，在终端按Enter

### Q2: SSH连接失败

**问题**：日志显示 `VPS unavailable`

**解决**：
1. 检查VPS是否在线：`ping 216.167.34.54`
2. 检查SSH端口：`ssh root@216.167.34.54`
3. 检查防火墙设置
4. 系统会自动降级到local-only模式，仍可继续

### Q3: tcpdump权限错误

**问题**：`Permission denied`

**解决**：
```bash
# 使用sudo运行
sudo python3 run_capture.py --platform weibo --action like --num 5

# 或配置passwordless sudo（推荐）
sudo visudo -f /etc/sudoers.d/tcpdump
# 添加: your_username ALL=(ALL) NOPASSWD: /usr/sbin/tcpdump
```

### Q4: 浏览器启动失败

**问题**：`selenium.common.exceptions.WebDriverException`

**解决**：
1. 检查Chrome浏览器是否安装
2. 检查ChromeDriver版本是否匹配
3. 检查代理设置是否正确
4. 查看bot脚本日志

### Q5: 抓包文件为空

**问题**：生成的pcap文件为0字节

**解决**：
1. 检查BPF过滤器是否正确
2. 检查是否有网络流量（浏览器是否正常访问）
3. 检查tcpdump是否正常运行：`ps aux | grep tcpdump`
4. 查看tcpdump日志

## 高级用法

### 批量采集脚本

创建 `batch_collect.sh`：

```bash
#!/bin/bash

# 采集微博的所有行为类型
python3 run_capture.py --platform weibo --action like --num 10
sleep 60
python3 run_capture.py --platform weibo --action comment --num 10
sleep 60
python3 run_capture.py --platform weibo --action repost --num 10
sleep 60
python3 run_capture.py --platform weibo --action browse --num 10

echo "✅ 批量采集完成！"
```

运行：
```bash
chmod +x batch_collect.sh
sudo ./batch_collect.sh
```

### 自定义bot行为

修改 `run_capture.py` 中的 `run_weibo_action` 函数：

```python
def run_weibo_action(action: str, iteration: int) -> bool:
    # 自定义行为逻辑
    if action == "custom":
        # 你的自定义代码
        ...
```

### 集成到数据流水线

```python
#!/usr/bin/env python3
"""数据采集流水线"""

from run_capture import run
from dataprocess.main import extract_features

# 1. 采集数据
run("weibo", "like", num=10)

# 2. 提取特征
import glob
for pcap in glob.glob("output/captures/weibo_like_*_mac.pcap"):
    csv_path = pcap.replace('.pcap', '_features.csv')
    extract_features(pcap, csv_path, flow_type="mac_vps")

# 3. 训练模型
# ... 你的机器学习代码 ...
```

## 与装饰器模式的对比

| 特性 | run_capture.py（会话级） | @capture_traffic（装饰器） |
|------|------------------------|--------------------------|
| **抓包粒度** | 整个会话（登录+浏览+行为） | 单个动作（like/comment） |
| **包含登录流量** | ✅ 是 | ❌ 否 |
| **文件数量** | 少（每次会话1对） | 多（每个动作1对） |
| **标签格式** | platform_action_N | platform_action_id_xxx |
| **适用场景** | 行为级分析、模型训练 | 细粒度分析、调试 |
| **使用方式** | 命令行 | 代码装饰器 |

## 总结

`run_capture.py` 提供了**会话级抓包**的完整解决方案：
- ✅ 包含完整流程（登录+浏览+行为）
- ✅ 简单的命令行接口
- ✅ 自动化迭代和间隔
- ✅ 双端同步抓包
- ✅ 标签化存储

适合用于：
- 批量采集行为样本
- 训练流量分析模型
- 研究完整行为流程
- 对比不同平台/行为

配合 `dataprocess` 工具，可以构建完整的流量采集和分析流水线。
