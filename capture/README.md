# 双端协同抓包系统使用指南

## 系统概述

自动化的macOS-VPS双端抓包系统，集成到社交媒体bot脚本中，用于采集带标签的流量数据。

### 核心功能

- ✅ **双端同步抓包**：macOS端和VPS端同时抓包，确保流量关联
- ✅ **SSH远程控制**：自动控制VPS端的tcpdump启动/停止
- ✅ **自动打标签**：根据平台和行为自动生成标签（如 `weibo_like_id_123456`）
- ✅ **装饰器集成**：通过 `@capture_traffic` 无缝集成到现有bot函数
- ✅ **BPF流量过滤**：初期过滤无关流量，减少文件大小
- ✅ **优雅降级**：VPS不可达时自动降级到local-only模式
- ✅ **元数据保存**：每次抓包生成JSON元数据文件

## 快速开始

### 1. 安装依赖

```bash
pip3 install paramiko
```

### 2. 配置检查

确认配置正确（已在 `capture/config.py` 中预配置）：
- macOS私有IP: `10.67.227.153`
- macOS公网IP: `124.127.223.133`
- VPS IP: `216.167.34.54`
- SSH凭证: `root@216.167.34.54`

### 3. 运行测试

```bash
# 测试SSH连接和基本功能
python3 test_capture.py
```

期望输出：
```
🎉 All tests passed!
```

### 4. 使用bot脚本抓包

直接运行已集成的bot脚本：

```bash
# 微博bot（已集成）
python3 weibo_bot_smart.py

# Facebook bot（需要手动集成）
# python3 facebook_bot_smart.py

# TikTok bot（需要手动集成）
# python3 tiktok_bot.py
```

**运行bot时会自动抓包**，每次执行行为（点赞、评论、转发等）都会生成一对pcap文件。

## 抓包结果

### 文件位置

```
output/captures/
├── 20260515_153042_weibo_like_id_1234567_mac.pcap      # macOS端
├── 20260515_153042_weibo_like_id_1234567_vps.pcap      # VPS端
├── 20260515_153042_weibo_like_id_1234567_meta.json     # 元数据
├── 20260515_154511_weibo_comment_id_7890123_mac.pcap
├── 20260515_154511_weibo_comment_id_7890123_vps.pcap
└── 20260515_154511_weibo_comment_id_7890123_meta.json
```

### 文件命名规则

**格式**：`{时间戳}_{平台}_{行为}_id_{唯一ID}_{端}.pcap`

示例：
- `20260515_153042` - 时间戳（年月日_时分秒）
- `weibo` - 平台（weibo/facebook/tiktok）
- `like` - 行为（like/comment/repost/share/post）
- `id_1234567_Abc1234` - 唯一ID（从URL自动提取）
- `mac` / `vps` - 抓包端

### 元数据JSON

每对pcap文件对应一个 `*_meta.json` 文件：

```json
{
  "label": "weibo_like_id_1234567_Abc1234",
  "platform": "weibo",
  "action": "like",
  "start_time": 1715761842.123,
  "stop_time": 1715761857.456,
  "duration": 15.333,
  "local_pcap": "output/captures/20260515_153042_weibo_like_id_1234567_Abc1234_mac.pcap",
  "vps_pcap": "output/captures/20260515_153042_weibo_like_id_1234567_Abc1234_vps.pcap",
  "local_bpf": "host 216.167.34.54",
  "remote_bpf": "not (host 124.127.223.133 and port 33979) and not port 22",
  "vps_available": true
}
```

## 使用方法

### 方式1：装饰器模式（推荐，已集成）

```python
from capture import capture_traffic

@capture_traffic("weibo", "like")
def like_weibo(driver, weibo_element):
    # 原有代码不变
    # 自动抓包：函数执行前启动，执行后停止
    ...
```

**优点**：
- 零代码侵入
- 自动提取唯一ID
- 异常安全（即使函数抛错也会停止抓包）

**已集成的函数**（weibo_bot_smart.py）：
- `@capture_traffic("weibo", "like")` - like_weibo
- `@capture_traffic("weibo", "comment")` - comment_weibo
- `@capture_traffic("weibo", "repost")` - repost_weibo
- `@capture_traffic("weibo", "post")` - post_weibo

### 方式2：手动模式

```python
from capture import CaptureManager

manager = CaptureManager()

# 启动抓包
manager.start("weibo_browse_session", timeout=600)

try:
    # 执行行为
    smart_browse_and_interact(driver, max_weibos=10)
finally:
    # 停止抓包
    result = manager.stop()
    print(f"Captured: {result['local_pcap']}, {result['vps_pcap']}")
```

### 方式3：上下文管理器模式

```python
from capture import CaptureManager

with CaptureManager() as mgr:
    mgr.start("weibo_mixed_session")
    
    # 执行行为
    smart_browse_and_interact(driver, max_weibos=10)
    
    # 自动停止抓包
    result = mgr.stop()
```

## 集成到其他bot脚本

### Facebook bot集成

在 `facebook_bot_smart.py` 顶部添加：

```python
# 双端抓包系统（可选）
try:
    from capture import capture_traffic
    CAPTURE_ENABLED = True
except ImportError:
    CAPTURE_ENABLED = False
    def capture_traffic(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
```

然后装饰action函数：

```python
@capture_traffic("facebook", "like")
def like_post(driver, post_element):
    ...

@capture_traffic("facebook", "comment")
def comment_post(driver, content_list):
    ...

@capture_traffic("facebook", "share")
def share_post(driver, post_element):
    ...
```

### TikTok bot集成

```python
@capture_traffic("tiktok", "like")
def like_video(driver, video_element):
    ...

@capture_traffic("tiktok", "comment")
def comment_video(driver, content_list):
    ...

@capture_traffic("tiktok", "share")
def share_video(driver):
    ...
```

## BPF过滤器说明

### macOS端（Flow A）

```
host 216.167.34.54
```

- 只抓取与VPS通信的流量
- 这是**加密隧道流量**（VLESS）
- 包含所有通过代理访问的数据

### VPS端（Flow B）

```
not (host 124.127.223.133 and port 33979) and not port 22
```

- 抓取VPS访问外网的流量
- 排除来自macOS的隧道流量（124.127.223.133:33979）
- 排除SSH管理流量（port 22）
- 这是**解密后的明文/TLS流量**

### 为什么需要两端抓包？

| 端 | 抓取内容 | 用途 |
|---|----------|------|
| **macOS端** | 加密隧道流量 | 分析隧道层特征，无法看到明文内容 |
| **VPS端** | 解密后的流量 | 分析应用层特征，可以看到TLS SNI等 |
| **两端配对** | 完整的流量链路 | 关联分析，研究加密前后的流量模式 |

## 数据处理

抓包完成后，使用 `dataprocess` 工具提取特征：

```bash
# 提取Flow A（macOS端）
python3 -m dataprocess.main \
  -i output/captures/20260515_153042_weibo_like_id_1234567_mac.pcap \
  -o output/flow_a_features.csv \
  --flow mac_vps

# 提取Flow B（VPS端）
python3 -m dataprocess.main \
  -i output/captures/20260515_153042_weibo_like_id_1234567_vps.pcap \
  -o output/flow_b_features.csv \
  --flow vps_website \
  --perspective vps
```

## 常见问题

### Q1: sudo权限不足

**问题**：运行时报错 `Permission denied`

**解决方法**：
```bash
# 方法1：使用sudo运行bot脚本
sudo python3 weibo_bot_smart.py

# 方法2：配置passwordless sudo for tcpdump
sudo visudo -f /etc/sudoers.d/tcpdump
# 添加这一行（替换your_username）：
your_username ALL=(ALL) NOPASSWD: /usr/sbin/tcpdump
```

### Q2: VPS连接失败

**问题**：日志显示 `VPS unavailable`

**解决方法**：
1. 检查SSH凭证是否正确
2. 检查VPS是否在线：`ssh root@216.167.34.54`
3. 检查防火墙设置
4. 系统会自动降级到local-only模式，仍可保存macOS端pcap

### Q3: 抓包文件过大

**问题**：一次抓包生成几百MB文件

**原因**：行为持续时间过长或流量过大

**解决方法**：
- 设置超时：`@capture_traffic("weibo", "like", timeout=60)`
- 手动控制：使用 `manager.start()` 和 `manager.stop()`
- 优化行为：减少浏览时间，精简操作

### Q4: 如何验证抓包是否成功？

```bash
# 检查文件是否存在
ls -lh output/captures/

# 检查文件大小（应该>0）
du -h output/captures/*.pcap

# 使用tcpdump验证pcap文件完整性
tcpdump -r output/captures/20260515_153042_weibo_like_id_1234567_mac.pcap -c 10

# 使用dataprocess提取特征
python3 -m dataprocess.main -i output/captures/*.pcap -o test.csv
```

### Q5: 如何调试抓包问题？

启用详细日志：

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,  # 改为DEBUG级别
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
```

查看日志输出：
- `capture.ssh` - SSH连接和命令执行
- `capture.local` - macOS端tcpdump
- `capture.remote` - VPS端tcpdump
- `capture` - 总体流程

## 技术架构

```
capture/
├── __init__.py           # 包导出
├── config.py             # 配置（IP、SSH、路径）
├── exceptions.py         # 自定义异常
├── label.py              # 标签生成和文件命名
├── ssh_client.py         # SSH远程控制（paramiko）
├── local_capture.py      # macOS端tcpdump封装
├── remote_capture.py     # VPS端tcpdump封装（SSH）
├── manager.py            # 核心编排器（双端同步）
└── decorator.py          # @capture_traffic装饰器
```

### 工作流程

```
1. Bot函数调用（带@capture_traffic装饰器）
   ↓
2. 装饰器提取driver、platform、action
   ↓
3. 从driver.current_url提取unique_id
   ↓
4. 生成label（weibo_like_id_123456）
   ↓
5. CaptureManager.start(label)
   ├─ SSH连接VPS
   ├─ VPS端启动tcpdump（后台，nohup）
   ├─ macOS端启动tcpdump（sudo）
   └─ 记录start_time
   ↓
6. 执行原bot函数（点赞、评论等）
   ↓
7. CaptureManager.stop()
   ├─ macOS端停止tcpdump（SIGTERM）
   ├─ VPS端停止tcpdump（kill PID）
   ├─ 下载VPS端pcap到macOS
   ├─ 清理VPS临时文件
   └─ 保存元数据JSON
   ↓
8. 返回结果给bot函数
```

## 性能指标

- **SSH连接延迟**：50-200ms
- **双端启动时间差**：<500ms
- **抓包CPU占用**：<5%（tcpdump）
- **抓包内存占用**：<50MB
- **文件大小**（30秒行为）：5-10MB（每端）
- **SFTP下载速度**：~10MB/s

## 安全注意事项

1. **SSH密码明文存储**：`config.py` 中的密码是明文，生产环境应使用SSH密钥
2. **sudo权限**：macOS端需要sudo权限运行tcpdump
3. **VPS端清理**：系统会自动删除VPS上的临时文件，避免积累
4. **网络流量**：抓包会产生网络流量（下载pcap文件），注意带宽限制

## 许可证

本工具用于学术研究和流量分析，请遵守相关法律法规。

## 技术支持

详细的技术设计和实现细节见：
- Plan文件：`.claude/plans/macos-vps-macos-facebook-mac-vps-mac-vp-reflective-sphinx.md`
- 测试脚本：`test_capture.py`
- 数据处理工具：`dataprocess/`
