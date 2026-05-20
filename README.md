# CollectData — 社交媒体流量采集框架

自动化采集六大社交平台（微博、Facebook、Instagram、Twitter/X、TikTok、知乎）的网络流量，用于流量特征研究与行为分类分析。

---

## 目录

- [架构概览](#架构概览)
- [支持平台与行为](#支持平台与行为)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [核心模块说明](#核心模块说明)
- [采集流程](#采集流程)
- [批量采集](#批量采集)
- [数据同步与处理](#数据同步与处理)
- [输出格式](#输出格式)
- [配置说明](#配置说明)

---

## 架构概览

```
本地 macOS                              VPS（境外节点）
──────────────────────                  ──────────────────────
Selenium Bot
    │
    ▼
tcpdump (en0)  ←── SOCKS5/VLESS 代理 ───►  tcpdump (eth0)
    │                                              │
    ▼                                              ▼
*_mac.pcap                               *_vps.pcap（SSH 下载到本地）
（加密代理流量）                            （明文社交平台流量）
```

每次行为采集生成**成对的两个 pcap 文件**：
- `*_mac.pcap`：本地端，抓取经代理的加密流量
- `*_vps.pcap`：VPS 端，抓取目标平台的明文流量

两端文件名完全对应，便于关联分析。

---

## 支持平台与行为

| 平台      | like | comment | repost / share     | post | browse |
|-----------| :--: | :-----: | :----------------: | :--: | :----: |
| 微博      | ✅   | ✅      | ✅ (repost)        | ✅   | ✅     |
| Facebook  | ✅   | ✅      | ✅ (share)         | ✅   | ✅     |
| Instagram | ✅   | ✅      | ✅ (share/repost)  | —    | ✅     |
| Twitter/X | ✅   | ✅      | ✅ (retweet)       | ✅   | ✅     |
| TikTok    | ✅   | ✅      | —                  | —    | ✅     |
| 知乎      | ✅   | ✅      | ✅ (share)         | ✅   | ✅     |

---

## 项目结构

```
collcetdata/
│
├── capture/                     # 核心抓包模块
│   ├── __init__.py              # 公共 API 导出
│   ├── config.py                # 配置（BPF 过滤、路径、SSH、超时等）
│   ├── manager.py               # CaptureManager：双端采集协调器
│   ├── local_capture.py         # macOS 端 tcpdump 控制
│   ├── remote_capture.py        # VPS 端 tcpdump 控制（含下载/删除）
│   ├── ssh_client.py            # SSH 客户端（自动重连、SFTP）
│   ├── label.py                 # 标签与文件名生成
│   ├── decorator.py             # @capture_traffic 装饰器
│   └── exceptions.py            # 自定义异常层级
│
├── dataprocess/                 # 数据后处理模块
│   ├── config.py                # 特征提取配置
│   ├── pcap_parser.py           # tcpdump 解析包字段
│   ├── feature_extractor.py     # 提取 (timestamp, signed_size) 特征
│   ├── data_exporter.py         # 导出 CSV / JSON / NumPy / Pickle
│   └── main.py                  # 单文件处理入口
│
├── weibo_bot_smart.py           # 微博自动化 Bot
├── facebook_bot_smart.py        # Facebook 自动化 Bot
├── instagram_bot_smart.py       # Instagram 自动化 Bot
├── twitter_bot_smart.py         # Twitter/X 自动化 Bot
├── tiktok_bot.py                # TikTok 自动化 Bot
├── zhihu_bot_smart.py           # 知乎自动化 Bot
│
├── run_capture.py               # 单平台抓包运行脚本（CLI）
├── batch_capture.py             # 批量抓包控制器（智能调度）
├── run_batch_loop.sh            # 六平台轮询循环脚本
├── sync_vps_captures.py         # 同步 VPS pcap 到本地
├── process_data.py              # 数据后处理入口
│
├── output/                      # 采集输出目录
│   ├── captures/{platform}/     # macOS 端 pcap
│   └── vps/{platform}/          # VPS 端 pcap（下载后）
│
└── data/                        # 特征数据
    └── {platform}/
        ├── mac/                 # macOS 端特征（csv/npy）
        └── vps/                 # VPS 端特征（csv/npy）
```

---

## 快速开始

### 环境依赖

```bash
pip install selenium selenium-stealth paramiko
```

其他依赖：
- Chrome 浏览器 + 对应版本 ChromeDriver
- macOS 本地 `tcpdump`（系统预装，需 `sudo` 权限）
- VPS 上已安装 `tcpdump`
- SOCKS5/VLESS 代理客户端（默认监听 `127.0.0.1:7897`）

### 浏览器 Profile

各平台使用独立的 Chrome Profile，**首次运行需手动登录**，之后自动复用会话：

| 平台      | Profile 路径                        |
|-----------|-------------------------------------|
| 微博      | `~/selenium_profiles/weibo`         |
| Facebook  | `~/selenium_profiles/facebook`      |
| Instagram | `~/selenium_profiles/instagram`     |
| Twitter   | `~/selenium_profiles/twitter`       |
| TikTok    | `~/selenium_profiles/tiktok`        |
| 知乎      | `~/selenium_profiles/zhihu`         |

### 单次采集

```bash
# 格式：sudo python3 run_capture.py --platform PLATFORM --action ACTION --num N [--timeout T]
sudo python3 run_capture.py --platform weibo      --action like    --num 5
sudo python3 run_capture.py --platform instagram  --action comment --num 3
sudo python3 run_capture.py --platform twitter    --action browse  --num 10 --timeout 600
```

> `sudo` 为运行 tcpdump 所必需。

---

## 核心模块说明

### capture 模块

#### CaptureConfig（`capture/config.py`）

集中管理所有配置，可通过属性覆盖默认值：

```python
from capture import CaptureConfig

config = CaptureConfig()
config.local_output_dir = "output/captures/weibo"  # 自定义输出目录
config.capture_timeout  = 600                       # 自定义超时（秒）
```

关键配置项：

| 参数                     | 默认值  | 说明                              |
|--------------------------|---------|-----------------------------------|
| `capture_timeout`        | `300`   | 单次抓包最大时长（秒）            |
| `local_interface`        | `en0`   | macOS 抓包网卡                    |
| `remote_interface`       | `eth0`  | VPS 抓包网卡                      |
| `enable_vps_ip_filter`   | `False` | 是否按平台 IP 过滤 VPS 流量       |
| `ssh_key_path`           | `""`    | SSH 密钥路径（优先于密码认证）    |
| `ssh_keepalive_interval` | `30`    | SSH 心跳间隔（秒）                |

BPF 过滤规则：

| 端      | 规则                                              |
|---------|---------------------------------------------------|
| macOS   | 排除 SSH（22 端口），保留所有出站流量             |
| VPS     | 排除 SSH / DNS / ARP / 隧道端口，保留平台流量    |

#### CaptureManager（`capture/manager.py`）

双端采集的核心协调器：

```python
from capture import CaptureManager, CaptureConfig

config = CaptureConfig()
manager = CaptureManager(config=config)

manager.start("weibo_like_1", timeout=300)
# ... 执行 Bot 行为 ...
result = manager.stop()

print(result['local_pcap'])   # macOS 端 pcap 路径
print(result['vps_pcap'])     # VPS 端 pcap 路径（None 表示 VPS 不可用）
print(result['duration'])     # 本次采集时长（秒）
```

#### SSHController（`capture/ssh_client.py`）

- **自动重连**：指数退避（1s → 2s → 4s，最多 3 次）
- **心跳保活**：防止长时间采集时连接断开
- **命令重试**：执行期间断连自动重连并重试一次
- **SFTP 下载**：含本地/远端文件大小校验

#### 自定义异常层级（`capture/exceptions.py`）

```
CaptureError
├── SSHConnectionError
├── SSHCommandError
├── TcpdumpError
│   └── TcpdumpPermissionError
├── FileTransferError
└── CaptureTimeoutError
```

### Bot 自动化

各平台 Bot 共同特性：

- **selenium-stealth**：模拟真实浏览器指纹，绕过自动化检测
- **SOCKS5 代理**：通过本地代理访问目标平台
- **独立 Chrome Profile**：保留登录状态，无需重复登录
- **人类行为模拟**：随机滚动、阅读停留、操作间隔
- **确保模式**：每个启用的行为至少成功 1 次后才结束本轮采集

---

## 采集流程

每次迭代的完整流程：

```
1. 生成 label        →  "{platform}_{action}_{序号}"
2. 连接 VPS          →  SSH
3. 启动 VPS tcpdump  →  先于本地启动（抵消 SSH 延迟）
4. 启动本地 tcpdump  →  sudo tcpdump on en0
5. 执行 Bot 行为     →  Selenium 模拟用户操作
6. 停止本地 tcpdump  →  保存 *_mac.pcap
7. 停止 VPS tcpdump  →  SFTP 下载 *_vps.pcap 并校验大小
8. 保存 metadata     →  JSON（label、时间戳、路径、BPF 等）
9. 迭代间隔          →  约 30 秒，避免行为特征过于规律
```

VPS 不可用时自动降级为仅本地单端采集，不中断整体流程。

---

## 批量采集

### 使用预定义计划

```bash
# 预定义计划
sudo python3 batch_capture.py --config instagram_full
sudo python3 batch_capture.py --config weibo_full

# 演练模式（只打印调度计划，不实际执行）
sudo python3 batch_capture.py --config twitter_full --dry-run

# 自定义计划
sudo python3 batch_capture.py --platform zhihu --tasks like:10 comment:5 browse:20
```

### 预定义计划一览

| 计划名称         | 平台      | 任务内容                                               |
|------------------|-----------|--------------------------------------------------------|
| `weibo_full`     | 微博      | like×5, comment×3, repost×2, post×2, browse×10         |
| `weibo_test`     | 微博      | 各行为×2                                               |
| `instagram_full` | Instagram | like×10, comment×2, browse×25                          |
| `instagram_test` | Instagram | 各行为×1                                               |
| `facebook_full`  | Facebook  | like×1, browse×15                                      |
| `tiktok_full`    | TikTok    | like×15, comment×5, browse×35                          |
| `twitter_full`   | Twitter   | like×5, comment×1, browse×20                           |
| `twitter_test`   | Twitter   | 各行为×1                                               |
| `zhihu_full`     | 知乎      | like×15, comment×5, share×2, post×2, browse×25         |
| `zhihu_test`     | 知乎      | 各行为×1                                               |

### 智能调度策略

- 随机打乱执行顺序，避免固定模式
- 尽量避免连续相同行为（降低被检测风险）
- 每完成 20 个任务后随机休息 3～5 分钟
- 连续失败 ≥ 3 次，或总失败 ≥ 10 次时自动停止

行为间隔配置：

| 场景              | 间隔范围    |
|-------------------|-------------|
| 连续相同行为      | 30～60 秒   |
| 切换不同行为      | 20～40 秒   |
| 每 20 个任务后    | 3～5 分钟   |
| 单次抓包超时上限  | 600 秒      |

### 六平台轮询循环

```bash
bash run_batch_loop.sh
```

执行顺序：**Instagram → Facebook → 知乎 → Twitter → TikTok → 微博**，无限循环直到 `Ctrl+C`。

脚本启动时获取一次 `sudo` 认证，并每 60 秒自动刷新，全程无需再次输入密码。

---

## 数据同步与处理

### 同步 VPS pcap

```bash
# 预览（只列出文件，不下载不删除）
python3 sync_vps_captures.py --dry-run

# 正式同步（下载 → 校验 → 删除 VPS 文件）
python3 sync_vps_captures.py
```

同步逻辑：按文件名中的平台字段分类，下载到 `output/vps/{platform}/`，校验文件大小一致后删除 VPS 文件；有任意失败则保留不删。

### 批量处理 pcap

```bash
# 处理所有平台的 VPS 端 pcap
python3 process_data.py output/vps

# 只处理某个平台
python3 process_data.py output/vps/weibo

# 增量模式（跳过已处理文件）
python3 process_data.py output/vps --skip-existing

# 导出 NumPy 格式（适合机器学习直接读取）
python3 process_data.py output/vps --format npy
```

处理结果保存到：
```
data/{platform}/mac/   ←  macOS 端特征（来自 *_mac.pcap）
data/{platform}/vps/   ←  VPS 端特征（来自 *_vps.pcap）
```

特征格式（CSV）：
```
timestamp,packet_size
1779103502.184566,568       ← 正数 = 发送方向
1779103502.193112,-4284     ← 负数 = 接收方向
```

---

## 输出格式

### 文件命名规则

```
{YYYYMMDD}_{HHMMSS}_{platform}_{action}_{num}_{side}.pcap
```

示例：
```
20260520_143022_weibo_like_3_mac.pcap
20260520_143022_weibo_like_3_vps.pcap
```

### Metadata JSON

每对 pcap 文件附带一个 JSON 元数据文件：

```json
{
  "label": "weibo_like_3",
  "platform": "weibo",
  "action": "like",
  "start_time": "2026-05-20T14:30:22",
  "end_time": "2026-05-20T14:32:45",
  "duration": 143.2,
  "local_pcap": "output/captures/weibo/20260520_143022_weibo_like_3_mac.pcap",
  "vps_pcap": "output/vps/weibo/20260520_143022_weibo_like_3_vps.pcap",
  "local_bpf": "not port 22",
  "vps_available": true
}
```

---

## 配置说明

### VPS 连接（`capture/config.py`）

```python
ssh_host: str       # VPS IP 地址
ssh_port: int       # SSH 端口（默认 22）
ssh_user: str       # SSH 用户名
ssh_password: str   # SSH 密码（与 ssh_key_path 二选一）
ssh_key_path: str   # SSH 密钥路径（优先）
```

### 代理地址

各 Bot 默认使用 `socks5://127.0.0.1:7897`。如需更改，在对应 Bot 文件的 `create_driver()` 中修改 `--proxy-server` 参数。

### 快速模式（微博）

```bash
FAST_MODE=1 sudo python3 run_capture.py --platform weibo --action browse --num 1
```

减少等待延迟，提速约 50～70%。

---

## 注意事项

- 所有涉及 tcpdump 的脚本均需通过 `sudo` 运行
- 首次使用各平台前，须在浏览器中手动完成登录；后续自动复用 Profile
- Instagram 暂不支持 `post` 行为；TikTok 暂不支持 `share` 行为
- VPS 端不可用时，系统自动降级为仅本地单端采集，不影响整体流程
- `batch_capture.py` 每轮休息前会自动清理 VPS 上的僵尸 tcpdump 进程

### 紧急停止

```bash
# 停止本地所有相关进程
sudo pkill -9 -f "batch_capture"
sudo pkill -9 -f "run_capture"
sudo pkill -9 tcpdump

# 停止 VPS 端所有 tcpdump（替换为实际用户名和 IP）
ssh user@your-vps-ip "pkill -9 tcpdump"
```
