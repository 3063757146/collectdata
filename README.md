# Social Media Traffic Capture System

社交媒体流量双端协同采集系统。macOS 端通过 Xray VLESS 代理访问目标平台，同时在 macOS 和 VPS 两端同步抓包，为流量分类研究提供标注数据集。

---

## 架构概览

```
macOS (Selenium Bot)
    │  Xray VLESS 隧道
    ↓  port 33979
VPS (ip)
    │  明文流量
    ↓
目标网站 (weibo / facebook / tiktok / twitter / zhihu)
```

**双端抓包：**
- **macOS 端**（Flow A）：抓取 macOS ↔ VPS 加密隧道流量，存入 `output/captures/{platform}/`
- **VPS 端**（Flow B）：抓取 VPS ↔ 目标网站明文流量，下载后存入 `output/vps/{platform}/`

每次抓包生成一对 pcap 文件，文件名完全对应，便于关联两端流量。

---

## 目录结构

```
collcetdata/
├── capture/                    # 抓包系统（核心包）
│   ├── config.py               # CaptureConfig：网络/SSH/路径/BPF 配置
│   ├── manager.py              # CaptureManager：双端协同编排器
│   ├── ssh_client.py           # SSHController：SSH 远程控制 VPS
│   ├── local_capture.py        # LocalCapture：macOS 端 tcpdump
│   ├── remote_capture.py       # RemoteCapture：VPS 端 tcpdump（含下载/删除）
│   ├── label.py                # 文件命名规则
│   ├── decorator.py            # @capture_traffic 装饰器
│   └── exceptions.py           # 自定义异常
│
├── dataprocess/                # 数据预处理包
│   ├── config.py               # Config：IP/BPF/方向配置
│   ├── pcap_parser.py          # 调用 tcpdump 解析包字段
│   ├── feature_extractor.py    # 提取 (timestamp, signed_size) 特征
│   ├── data_exporter.py        # 导出 CSV / JSON / NumPy / Pickle
│   └── main.py                 # 单文件处理入口
│
├── weibo_bot_smart.py          # 微博自动化 bot
├── facebook_bot_smart.py       # Facebook 自动化 bot
├── tiktok_bot.py               # TikTok 自动化 bot
├── twitter_bot_smart.py        # Twitter 自动化 bot
├── zhihu_bot_smart.py          # 知乎自动化 bot
│
├── run_capture.py              # 单平台抓包入口（执行 N 次指定行为）
├── batch_capture.py            # 批量调度：随机化顺序 + 人类行为间隔
├── run_batch_loop.sh           # 持续循环脚本（多平台轮流执行）
├── process_data.py             # 批量 pcap 预处理入口
│
├── output/
│   ├── captures/{platform}/    # macOS 端 pcap（_mac.pcap）
│   └── vps/{platform}/         # VPS 端 pcap（_vps.pcap，自动下载）
│
└── data/
    └── {platform}/
        ├── mac/                # macOS 端特征文件（csv/npy）
        └── vps/                # VPS 端特征文件（csv/npy）
```

---

## 支持的平台和行为

| 平台 | 支持的行为 |
|------|-----------|
| `weibo` | `like` `comment` `repost` `post` `browse` |
| `facebook` | `like` `comment` `share` `post` `browse` |
| `tiktok` | `like` `comment` `share` `browse` |
| `twitter` | `like` `comment` `retweet` `post` `browse` |
| `zhihu` | `like` `comment` `share` `post` `browse` |

---

## 文件命名规则

```
{YYYYMMDD}_{HHMMSS}_{platform}_{action}_{num}_{side}.pcap
```

示例：
```
20260519_131404_twitter_like_1_mac.pcap   ← macOS 端
20260519_131404_twitter_like_1_vps.pcap   ← VPS 端（自动下载）
```

---

## 快速使用

### 1. 单次抓包

```bash
# 执行 5 次微博点赞，每次生成一对 pcap
sudo python3 run_capture.py --platform weibo --action like --num 5

# 执行 3 次 Twitter 浏览，超时 600 秒
sudo python3 run_capture.py --platform twitter --action browse --num 3 --timeout 600

# 快速模式（跳过部分页面等待，速度提升约 50%）
FAST_MODE=1 sudo python3 run_capture.py --platform weibo --action browse --num 1
```

### 2. 批量采集

```bash
# 使用预定义计划（含随机化顺序 + 人类行为间隔）
sudo python3 batch_capture.py --config weibo_full
sudo python3 batch_capture.py --config tiktok_full
sudo python3 batch_capture.py --config twitter_full
sudo python3 batch_capture.py --config zhihu_full

# 演练模式（不实际执行，只显示调度计划）
sudo python3 batch_capture.py --config weibo_full --dry-run

# 自定义任务
sudo python3 batch_capture.py --platform weibo --tasks like:10 comment:5
```

**预定义计划：**

| 计划名 | 平台 | 任务配置 |
|--------|------|---------|
| `weibo_full` | 微博 | like×10, comment×3, repost×2, post×2, browse×20 |
| `weibo_test` | 微博 | 每种行为各 2 次 |
| `facebook_full` | Facebook | like×1, browse×5 |
| `tiktok_full` | TikTok | like×15, comment×5, browse×35 |
| `twitter_full` | Twitter | like×5, comment×1, browse×20 |
| `twitter_test` | Twitter | 每种行为各 1 次 |
| `zhihu_full` | 知乎 | like×15, comment×5, share×2, post×2, browse×25 |
| `zhihu_test` | 知乎 | 每种行为各 2 次 |

### 3. 持续循环（多平台轮流）

```bash
# 按 知乎 → Twitter → TikTok → 微博 顺序循环，Ctrl+C 停止
./run_batch_loop.sh
# 开始时输入一次 sudo 密码，后续自动保持认证
```

### 4. 批量预处理 pcap

```bash
# 处理所有 VPS 抓包，按平台分开保存
python3 process_data.py output/vps

# 只处理某个平台
python3 process_data.py output/vps/weibo
python3 process_data.py output/captures/twitter

# 增量模式（跳过已处理的文件）
python3 process_data.py output/vps --skip-existing

# NumPy 格式（适合机器学习直接读取）
python3 process_data.py output/vps --format npy

# 预览不处理
python3 process_data.py output/vps --dry-run
```

预处理结果保存到：
```
data/{platform}/mac/   ← macOS 端特征（来自 _mac.pcap）
data/{platform}/vps/   ← VPS 端特征（来自 _vps.pcap）
```

特征格式（CSV）：
```
timestamp,packet_size
1779103502.184566,568      ← 正数 = 发送方向
1779103502.193112,-4284    ← 负数 = 接收方向
```

---

## 配置

### 网络和 SSH（capture/config.py）

```python
vps_ip          = "xxx"
mac_private_ip  = "xx"
vps_tunnel_port = 33979

ssh_host = "xxx"
ssh_user = "root"
```

### BPF 过滤规则

| 端 | 过滤规则 |
|----|---------|
| macOS | `host {vps_ip} and not port 22` |
| VPS | `not port {tunnel} and not port 22 and not port 53 and not arp` |

### 行为间隔（batch_capture.py，模拟人类节奏）

| 场景 | 间隔范围 |
|------|---------|
| 同一行为连续执行 | 30 ~ 60 秒 |
| 不同行为切换 | 20 ~ 40 秒 |
| 每完成 20 个任务后休息 | 3 ~ 5 分钟 |
| 单次抓包超时上限 | 600 秒 |

---

## 依赖

```bash
pip install paramiko selenium
```

系统：macOS `/usr/sbin/tcpdump`（预装），VPS `/usr/bin/tcpdump`（预装）

---

## 紧急停止

```bash
# 停止本地所有相关进程
sudo pkill -9 -f "batch_capture"
sudo pkill -9 -f "run_capture"
sudo pkill -9 tcpdump

# 停止 VPS 端所有 tcpdump
ssh root@xx "pkill -9 tcpdump"
```
