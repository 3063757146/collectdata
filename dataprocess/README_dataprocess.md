# PCAP流量特征提取工具

从pcap抓包文件中提取流量特征，用于流量分析研究。

## 功能特点

- ✅ 提取流量特征：(时间戳, 正负包大小)
- ✅ 支持两类流量分类：
  - **Flow A**: macOS ↔ VPS（加密隧道流量）
  - **Flow B**: VPS ↔ 社交网站（明文/TLS流量）
- ✅ 多种输出格式：CSV、JSON、NumPy、Pickle
- ✅ 高性能：30万包/秒处理速度
- ✅ 无需额外依赖（仅需tcpdump + Python 3.7+）
- ✅ 流式处理：内存占用低

## 目录结构

```
dataprocess/
├── __init__.py              # 包初始化
├── config.py                # 配置管理
├── pcap_parser.py           # tcpdump调用和解析
├── feature_extractor.py     # 流量分类和特征提取
├── data_exporter.py         # 多格式导出
├── utils.py                 # 辅助函数
└── main.py                  # CLI入口

data/                        # 输入数据
├── weibo-15.pcapng          # macOS端抓包（307MB）
└── all_outbound.pcap        # VPS端抓包（568MB）

output/                      # 输出结果
├── flow_a_mac_vps.csv       # Flow A特征（211,624条）
└── flow_b_vps_website.csv   # Flow B特征（24,983条）
```

## 快速开始

### 1. 提取Flow A（macOS ↔ VPS隧道流量）

```bash
python3 -m dataprocess.main \
  --input data/weibo-15.pcapng \
  --output output/flow_a_mac_vps.csv \
  --flow mac_vps \
  --perspective mac
```

**输出示例**：
```csv
timestamp,packet_size
2026-05-14 17:25:22.228825,600
2026-05-14 17:25:22.256251,536
2026-05-14 17:25:22.490760,-1368
2026-05-14 17:25:22.492973,-1368
```
- 正数 = 发送（macOS → VPS）
- 负数 = 接收（VPS → macOS）

### 2. 提取Flow B（VPS ↔ 社交网站流量）

```bash
python3 -m dataprocess.main \
  --input data/all_outbound.pcap \
  --output output/flow_b_vps_website.csv \
  --flow vps_website \
  --perspective vps
```

### 3. 其他格式导出

**JSON格式**：
```bash
python3 -m dataprocess.main \
  -i data/weibo-15.pcapng \
  -o output/flow_a.json \
  --format json \
  --flow mac_vps
```

**NumPy格式**（用于机器学习）：
```bash
python3 -m dataprocess.main \
  -i data/weibo-15.pcapng \
  -o output/flow_a.npy \
  --format numpy \
  --flow mac_vps
```

## 命令行参数

### 必需参数
- `--input, -i`: 输入pcap/pcapng文件路径
- `--output, -o`: 输出文件路径

### 流量配置
- `--flow`: 流量类型（`mac_vps`/`vps_website`/`all`），默认 `mac_vps`
- `--perspective`: 抓包视角（`mac`/`vps`），默认 `mac`

### 输出格式
- `--format, -f`: 输出格式（`csv`/`json`/`numpy`/`pickle`），默认 `csv`
- `--epoch-time`: 使用epoch时间戳而非可读格式（仅CSV/JSON）

### 处理选项
- `--include-zero`: 包含0字节包（默认跳过TCP ACK等）
- `--no-progress`: 不显示进度条
- `--no-stats`: 不显示统计摘要

### IP/端口配置
- `--local-ip`: macOS私有IP（默认 `10.67.227.153`）
- `--local-public-ip`: macOS公网IP（默认 `124.127.223.133`）
- `--vps-ip`: VPS IP（默认 `216.167.34.54`）
- `--vps-port`: VPS隧道端口（默认 `33979`）

## 实际数据统计

### Flow A (macOS ↔ VPS)
- **数据量**: 211,624 条（跳过0字节包）
- **时间跨度**: 575 秒（~9.6分钟）
- **流量**: 上传 1.21 MB，下载 268.41 MB
- **特征**: 下载远大于上传（网络浏览特征）
- **处理速度**: 383,300 包/秒，耗时 0.9 秒

### Flow B (VPS ↔ 网站)
- **数据量**: 24,983 条
- **时间跨度**: 785 秒（~13分钟）
- **流量**: 上传 920 KB，下载 267 MB
- **处理速度**: 98,245 包/秒，耗时 0.3 秒

## 输出格式说明

### CSV格式（推荐）
```csv
timestamp,packet_size
2026-05-14 17:25:22.228825,600      # 发送600字节
2026-05-14 17:25:22.490760,-1368   # 接收1368字节
```
- 易于分析、可用pandas加载
- 文件大小：~6.9MB（21万条）

### JSON格式
```json
[
  {"timestamp": "2026-05-14 17:25:22.228825", "size": 600},
  {"timestamp": "2026-05-14 17:25:22.490760", "size": -1368}
]
```
- 易于Web应用集成
- 文件大小：~12MB（21万条）

### NumPy格式
```python
import numpy as np
data = np.load('output/flow_a.npy')
# shape: (211624, 2)
# 列0: epoch时间戳，列1: 有符号包大小
```
- 用于机器学习、数据分析
- 文件大小：~3.3MB（21万条）

## 技术原理

### 数据流程
```
pcap文件 → tcpdump解析 → 正则提取 → 流量分类 → 特征计算 → 格式导出
```

### 核心技术
1. **tcpdump**：BPF过滤器实现高性能预过滤
2. **流式处理**：generator模式，内存占用O(1)
3. **正则解析**：匹配TCP/UDP两种格式
4. **方向判断**：基于源IP判断发送/接收

### BPF过滤器示例
```bash
# Flow A (macOS视角)
host 216.167.34.54 and port 33979

# Flow B (VPS视角)
host 216.167.34.54 and not port 33979 and not port 22
```

## 性能基准

| 指标 | 数值 |
|------|------|
| 处理速度 | ~380,000 包/秒 |
| 内存占用 | < 100 MB |
| CPU占用 | 单核 ~30% |
| 输出文件大小 | CSV ~33字节/条，NumPy ~16字节/条 |

## 常见问题

### Q: 为什么跳过0字节包？
A: 0字节包通常是TCP ACK、SYN、FIN等控制包，不携带应用数据。默认跳过以减少噪声，可通过`--include-zero`包含。

### Q: 如何区分两类流量？
A: 
- **Flow A**: 通过端口33979识别（VLESS隧道端口）
- **Flow B**: VPS IP的非隧道、非SSH流量

### Q: 时间戳精度是多少？
A: 微秒级（6位小数），精确到百万分之一秒。

### Q: 如何处理大文件（>1GB）？
A: 工具使用流式处理，理论上可处理任意大小文件，内存占用恒定。

## 示例：Python脚本调用

```python
from dataprocess import extract_features, Config, export_csv

# 配置
config = Config(
    local_ip="10.67.227.153",
    vps_ip="216.167.34.54"
)

# 提取特征
features = extract_features(
    pcap_path="data/weibo-15.pcapng",
    config=config,
    flow_type="mac_vps",
    perspective="mac"
)

# 导出CSV
export_csv(features, "output/my_features.csv")

print(f"提取了 {len(features)} 条特征")
```

## 验证测试

```bash
# 验证CSV格式
head -5 output/flow_a_mac_vps.csv

# 统计数据量
wc -l output/flow_a_mac_vps.csv

# 统计发送/接收比例
grep -c '^[^-]*,-' output/flow_a_mac_vps.csv  # 接收包数
grep -c '^[^-]*,[0-9]' output/flow_a_mac_vps.csv  # 发送包数
```

## 许可证

本工具用于学术研究和流量分析，请遵守相关法律法规。

## 技术支持

如有问题，请参考计划文档：
- 计划文件位置见项目根目录 `.claude/plans/`
- 包含详细的技术设计和实现细节
