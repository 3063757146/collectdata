# batch_capture.py 使用指南

## 概述

`batch_capture.py` 是智能批量采集控制脚本，用于自动化调度 `run_capture.py`，实现大规模数据采集。

### 核心特性

1. **🎭 模拟人类行为**
   - 随机化任务顺序，避免连续相同行为
   - 智能时间间隔（2-15分钟不等）
   - 定期休息（每10个任务休息30-60分钟）

2. **🛡️ 错误控制**
   - 连续失败3次自动停止
   - 总失败次数达到10次停止
   - 自动重试失败任务（最多2次）

3. **📊 详细日志**
   - 实时进度显示
   - 成功率统计
   - 保存到 `logs/batch_capture/` 目录

4. **🔍 演练模式**
   - 使用 `--dry-run` 预览执行计划
   - 不实际执行，只显示时间安排

## 快速开始

### 1. 使用预定义计划

```bash
# 微博完整采集（5个行为，每个10次）
sudo python3 batch_capture.py --config weibo_full

# 微博快速测试（每个行为2次）
sudo python3 batch_capture.py --config weibo_test

# Facebook完整采集
sudo python3 batch_capture.py --config facebook_full

# TikTok完整采集
sudo python3 batch_capture.py --config tiktok_full
```

### 2. 自定义采集计划

```bash
# 微博：点赞20次，评论10次，浏览15次
sudo python3 batch_capture.py \
  --platform weibo \
  --tasks like:20 comment:10 browse:15
```

### 3. 演练模式（推荐先测试）

```bash
# 查看执行计划，不实际运行
python3 batch_capture.py --config weibo_test --dry-run
```

## 预定义计划详情

| 计划名称 | 平台 | 行为 | 总任务数 | 预计时长 |
|---------|------|------|---------|----------|
| `weibo_full` | 微博 | like(10), comment(10), repost(10), post(5), browse(10) | 45 | 6-8小时 |
| `weibo_test` | 微博 | like(2), comment(2), repost(2), browse(2) | 8 | 30-60分钟 |
| `facebook_full` | Facebook | like(10), comment(10), share(10), browse(10) | 40 | 5-7小时 |
| `tiktok_full` | TikTok | like(10), comment(10), share(10), browse(10) | 40 | 5-7小时 |

## 时间控制策略

### 行为间隔

| 场景 | 最小间隔 | 最大间隔 |
|------|---------|---------|
| **相同行为**（如 like → like） | 5分钟 | 15分钟 |
| **不同行为**（如 like → comment） | 2分钟 | 5分钟 |

### 休息策略

- **触发条件**：每完成10个任务
- **休息时长**：30-60分钟（随机）
- **目的**：模拟人类休息，避免被检测为机器人

### 示例时间线

```
09:00 - Task 1: weibo like #1
09:07 - Task 2: weibo comment #1    (不同行为，间隔7分钟)
09:12 - Task 3: weibo browse #1     (不同行为，间隔5分钟)
09:22 - Task 4: weibo like #2       (相同行为，间隔10分钟)
...
11:30 - [休息45分钟]                (完成10个任务)
12:15 - Task 11: weibo repost #1
...
```

## 错误处理

### 自动停止条件

1. **连续失败3次**
   ```
   Task 1: ❌ Failed
   Task 2: ❌ Failed
   Task 3: ❌ Failed
   🛑 Stopping due to: 连续失败 3 次
   ```

2. **总失败次数达到10次**
   ```
   Total failed: 10
   🛑 Stopping due to: 总失败次数达到 10 次
   ```

### 自动重试

失败的任务会自动重试最多2次：

```
📍 Task: weibo like #1
❌ Task failed with exit code 1
🔄 Retry 1/2
⏳ Waiting 60s before retry...
📍 Task: weibo like #1 (retry)
✅ Task completed successfully
```

### 用户中断

按 `Ctrl+C` 可随时安全退出：

```
^C
⚠️  Batch capture interrupted by user

📊 Batch Capture Summary
...
```

## 日志系统

### 日志位置

所有日志保存在：
```
logs/batch_capture/
├── 20260515_180000.log
├── 20260515_190000.log
└── ...
```

### 日志内容

```log
[2026-05-15 18:00:00] INFO: 🚀 Batch Capture Controller Started
[2026-05-15 18:00:00] INFO: 📋 Using plan: weibo_full
[2026-05-15 18:00:00] INFO: 🌐 Platform: weibo
[2026-05-15 18:00:00] INFO: 📊 Tasks: [('like', 10), ('comment', 10), ...]
[2026-05-15 18:00:00] INFO: Task order optimized: 45 tasks scheduled
[2026-05-15 18:00:00] INFO: ======================================================================
[2026-05-15 18:00:00] INFO: 📌 Total tasks: 45
[2026-05-15 18:00:00] INFO: ======================================================================
[2026-05-15 18:00:05] INFO: 📍 Task: weibo like (#1)
[2026-05-15 18:00:05] INFO: 📝 Command: sudo python3 run_capture.py --platform weibo --action like --num 1 --timeout 600
[2026-05-15 18:01:30] INFO: ✅ Task completed successfully (85.2s)
[2026-05-15 18:01:30] INFO: 📊 Progress: 1/45 (Success rate: 100.0%)
[2026-05-15 18:01:30] INFO: ⏳ Waiting 423s before next task...
[2026-05-15 18:08:33] INFO: 📍 Task: weibo comment (#1)
...
```

### 执行总结

任务完成或中断后会显示总结：

```
======================================================================
📊 Batch Capture Summary
======================================================================
⏱️  Total duration: 385.7 minutes
✅ Completed: 42
❌ Failed: 3
⏭️  Skipped: 0
📈 Success rate: 93.3%
======================================================================
```

## 高级用法

### 自定义时间间隔

编辑 `batch_capture.py` 中的 `TimingConfig` 类：

```python
class TimingConfig:
    # 同一行为之间的最小间隔（秒）
    SAME_ACTION_MIN_INTERVAL = 300  # 改为你想要的值
    SAME_ACTION_MAX_INTERVAL = 900

    # 不同行为之间的间隔（秒）
    DIFF_ACTION_MIN_INTERVAL = 120
    DIFF_ACTION_MAX_INTERVAL = 300

    # 休息配置
    REST_AFTER_TASKS = 10           # 每N个任务后休息
    REST_MIN_DURATION = 1800        # 休息时长（秒）
    REST_MAX_DURATION = 3600
```

### 自定义错误控制

编辑 `ErrorConfig` 类：

```python
class ErrorConfig:
    MAX_CONSECUTIVE_FAILURES = 3    # 连续失败上限
    MAX_TOTAL_FAILURES = 10         # 总失败上限
    MAX_RETRIES = 2                 # 重试次数
    RETRY_DELAY = 60                # 重试间隔（秒）
```

### 添加新的预定义计划

在 `CAPTURE_PLANS` 字典中添加：

```python
CAPTURE_PLANS = {
    # ... 现有计划 ...

    # 新计划：微博高频采集
    'weibo_intensive': {
        'platform': 'weibo',
        'tasks': [
            ('like', 20),
            ('comment', 20),
            ('browse', 30),
        ]
    },
}
```

## 使用场景

### 场景1：周末批量采集

```bash
# 周六早上启动，采集整天
sudo python3 batch_capture.py --config weibo_full

# 预计：6-8小时完成45个任务
# 建议：定期检查日志，确保正常运行
```

### 场景2：多平台采集

```bash
# 分批执行，避免单一平台流量过大
sudo python3 batch_capture.py --config weibo_full
# 等待1-2小时后...
sudo python3 batch_capture.py --config facebook_full
# 等待1-2小时后...
sudo python3 batch_capture.py --config tiktok_full
```

### 场景3：快速测试

```bash
# 使用测试计划，验证系统正常
sudo python3 batch_capture.py --config weibo_test

# 预计：30-60分钟完成8个任务
```

### 场景4：特定行为大量采集

```bash
# 只采集点赞行为50次
sudo python3 batch_capture.py \
  --platform weibo \
  --tasks like:50
```

## 注意事项

### 1. 权限要求

需要 `sudo` 权限（tcpdump需要）：
```bash
sudo python3 batch_capture.py --config weibo_full
```

### 2. 首次登录

第一个任务会要求手动登录，后续任务会复用登录状态。

### 3. 磁盘空间

- **macOS端**：每个任务约10-30MB
- **VPS端**：每个任务约10-30MB（保存在VPS上）
- **总计**：100个任务约需要2-6GB空间

### 4. 网络稳定性

- 确保网络连接稳定
- VPS连接中断会触发错误控制
- 建议在稳定的网络环境下运行

### 5. 执行时间

- 计划执行时间 = 任务数 × (平均执行时间 + 平均间隔 + 休息时间)
- 推荐在非工作时间运行（晚上、周末）
- 可以使用 `screen` 或 `tmux` 后台运行

## 故障排除

### Q1: 任务一直失败

**检查**：
1. VPS是否在线：`ping 216.167.34.54`
2. SSH连接是否正常：`ssh root@216.167.34.54`
3. 本地tcpdump权限：`sudo tcpdump --version`

### Q2: 时间间隔太长

**调整**：编辑 `TimingConfig`，减小最小/最大间隔值。

### Q3: 想要更频繁的休息

**调整**：编辑 `REST_AFTER_TASKS`，例如改为5（每5个任务休息一次）。

### Q4: 演练模式不工作

**检查**：确保使用了 `--dry-run` 参数，不需要 `sudo`：
```bash
python3 batch_capture.py --config weibo_test --dry-run
```

### Q5: 日志文件太大

**清理**：
```bash
# 删除旧日志（保留最近7天）
find logs/batch_capture/ -name "*.log" -mtime +7 -delete
```

## 最佳实践

1. **先演练**：使用 `--dry-run` 预览执行计划
2. **小规模测试**：先用 `weibo_test` 验证系统正常
3. **分批执行**：避免一次性执行过多任务
4. **监控日志**：定期查看日志文件，确保正常运行
5. **备份数据**：定期备份 `output/captures/` 目录

## 扩展开发

如果你想修改脚本行为，主要的类包括：

- **TimingConfig**：时间控制配置
- **ErrorConfig**：错误处理配置
- **TaskScheduler**：任务调度逻辑
- **TaskExecutor**：任务执行逻辑
- **BatchController**：主控制器

所有类都有详细的文档字符串，易于理解和修改。
