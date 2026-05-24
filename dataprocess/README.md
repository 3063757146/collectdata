# 数据处理模块 (dataprocess)

## 概述

从 pcap 抓包文件中提取流量特征，生成 `(timestamp, signed_packet_size)` 格式的数据集，用于后续流量分类/指纹识别等机器学习任务。

## 网络拓扑

```
Mac (本地设备) ←──VLESS隧道──→ VPS ←──明文请求──→ 目的网站
      |                          |
  mac端抓包                   vps端抓包
  (加密隧道流量)              (明文应用流量)
```

## 两种流量类型

| 流量类型 | 抓包位置 | 通信双方 | BPF过滤器 | 说明 |
|---------|---------|---------|----------|------|
| `mac_vps` | Mac本地 | Mac ↔ VPS | `host {vps_ip} and port {tunnel_port}` | 加密隧道流量，观察者视角 |
| `vps_website` | VPS端 | VPS ↔ 目的网站 | `host {vps_ip} and not port {tunnel_port} and not port 22` | 明文应用流量，作为ground truth |

## 特征格式

每个 pcap 文件处理后生成一个 CSV，每行表示一个数据包：

```csv
timestamp,packet_size
1779000243.861230,652
1779000243.972258,-1420
```

- **timestamp**: Unix epoch 时间戳（微秒精度）
- **packet_size**: 有符号 IP 包总长度（字节）
  - **正数**: 发送方向（从抓包视角看的出站包）
  - **负数**: 接收方向（从抓包视角看的入站包）
  - 大小 = IP总长度（IP头 + TCP/UDP头 + 载荷），不含链路层头

## 方向定义

| 抓包视角 | 正方向（发送） | 负方向（接收） |
|---------|--------------|--------------|
| mac (本地) | Mac → VPS（用户请求） | VPS → Mac（网站响应） |
| vps | VPS → 网站（转发请求） | 网站 → VPS（网站响应） |

## 过滤规则

- **skip_zero**: 过滤 TCP payload=0 的纯控制包（ACK、SYN、FIN、RST）
- 仅保留有实际数据传输的包，减少噪声

## 输出目录结构

```
data/
├── facebook/
│   ├── mac/          # Mac端抓取的 Mac↔VPS 隧道流量
│   │   ├── 20260519_201635_facebook_browse_1_mac.csv
│   │   └── ...
│   └── vps/          # VPS端抓取的 VPS↔目的网站 流量
│       ├── 20260519_201635_facebook_browse_1_vps.csv
│       └── ...
├── instagram/
│   ├── mac/
│   └── vps/
├── twitter/
│   ├── mac/
│   └── vps/
├── weibo/
│   ├── mac/
│   └── vps/
├── tiktok/
│   ├── mac/
│   └── vps/
└── zhihu/
    ├── mac/
    └── vps/
```

## 文件命名规范

```
{timestamp}_{platform}_{action}_{repeat}_{side}.csv
```

- `timestamp`: 抓包开始时间 `YYYYMMDD_HHMMSS`
- `platform`: 社交平台 (facebook/instagram/twitter/weibo/tiktok/zhihu)
- `action`: 用户行为 (browse/like/comment/repost/retweet)
- `repeat`: 第几次重复采集
- `side`: 抓包端 (mac/vps)

## 使用方法

```bash
# 处理所有 Mac 端抓包
python3 process_data.py output/captures

# 处理所有 VPS 端抓包
python3 process_data.py output/vps

# 只处理某个平台
python3 process_data.py output/captures/weibo
python3 process_data.py output/vps/weibo

# 增量处理（跳过已存在的）
python3 process_data.py output/captures --skip-existing

# 输出为 NumPy 格式
python3 process_data.py output/captures --format npy

# 预览不实际执行
python3 process_data.py output/captures --dry-run
```

## 模块结构

| 文件 | 功能 |
|------|------|
| `config.py` | 配置管理（IP、端口、BPF过滤器生成、方向判断） |
| `pcap_parser.py` | 调用 tcpdump -v 解析 pcap，流式输出 PacketInfo |
| `feature_extractor.py` | 从 PacketInfo 提取 (timestamp, signed_size) 特征 |
| `data_exporter.py` | 导出为 CSV/JSON/NumPy/Pickle 格式 |
| `utils.py` | 工具函数（验证、计数器等） |

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `vps_ip` | `216.167.34.54` | VPS IP 地址 |
| `vps_tunnel_port` | `33979` | VLESS 隧道端口 |
| `skip_zero_length` | `True` | 过滤 payload=0 的控制包 |

命令行可通过 `--vps-ip` 和 `--local-ip` 覆盖。
