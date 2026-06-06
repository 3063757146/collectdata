#!/usr/bin/env python3 -u
# -*- coding: utf-8 -*-
"""
批量抓包控制脚本

功能：
1. 智能调度 run_capture.py，模拟人类行为模式
2. 随机化行为顺序和时间间隔，避免被检测
3. 错误监控和自动停止
4. 详细日志记录

使用示例：
    python3 batch_capture.py --config weibo_full
    python3 batch_capture.py --platform weibo --dry-run
"""

import sys
import os

# 禁用输出缓冲（确保日志实时显示）
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
import time
import random
import logging
import argparse
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

# 导入抓包模块（用于SSH自动登录）
from capture.ssh_client import SSHController
from capture.config import CaptureConfig


# ============================================================
# 日志配置
# ============================================================
def setup_logger(log_file: str = None) -> logging.Logger:
    """配置日志系统"""
    logger = logging.getLogger('batch_capture')
    logger.setLevel(logging.INFO)

    # 格式化
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# ============================================================
# 采集任务配置
# ============================================================

# 预定义的采集计划
CAPTURE_PLANS = {
    # 微博完整采集（5个行为，每个10次）
    'weibo_full': {
        'platform': 'weibo',
        'tasks': [
            ('like', 10),
            ('comment', 5),
            ('repost', 5),
            ('post', 3),      # 发帖少一点
            ('browse', 20),
        ]
    },

    # 微博快速测试（每个行为2次）
    'weibo_test': {
        'platform': 'weibo',
        'tasks': [
            ('like', 2),
            ('comment', 2),
            ('repost', 2),
            ('browse', 2),
        ]
    },

    # Instagram完整采集
    'instagram_full': {
        'platform': 'instagram',
        'tasks': [
            ('like', 0),
            ('comment', 5),
            ('share', 3),
            ('browse', 0),
        ]
    },

    # Instagram快速测试
    'instagram_test': {
        'platform': 'instagram',
        'tasks': [
            ('like', 1),
            ('comment', 1),
            ('share', 1),
            ('browse', 1),
        ]
    },

    # Facebook完整采集
    'facebook_full': {
        'platform': 'facebook',
        'tasks': [
            ('like', 0),
            ('comment', 3),
            ('share', 0),     # Facebook 使用 share 而不是 repost
            ('post', 0),      # 发帖少一点
            ('browse', 0),
        ]
    },

    # TikTok完整采集
    'tiktok_full': {
        'platform': 'tiktok',
        'tasks': [
            ('like', 10),
            ('comment', 5),
            ('browse', 20),
        ]
    },

    # Twitter完整采集
    'twitter_full': {
        'platform': 'twitter',
        'tasks': [
            ('like', 2),
            ('comment', 3),
            ('retweet', 4),
            ('post', 4),
            ('browse', 0),
        ]
    },

    # Twitter快速测试
    'twitter_test': {
        'platform': 'twitter',
        'tasks': [
            ('like', 1),
            ('comment', 1),
            ('retweet', 1),
            ('browse', 1),
        ]
    },

    # 知乎完整采集
    'zhihu_full': {
        'platform': 'zhihu',
        'tasks': [
            ('like', 10),
            ('comment', 5),
            ('share', 3),      # 转发到想法
            ('post', 1),       # 发布想法
            ('browse', 20),
        ]
    },

    # 知乎快速测试
    'zhihu_test': {
        'platform': 'zhihu',
        'tasks': [
            ('like', 1),
            ('comment', 1),
            ('share', 1),
            ('browse', 1),
            ('post', 1)
        ]
    },
}


# ============================================================
# 时间间隔配置（模拟人类行为）
# ============================================================
class TimingConfig:
    """时间控制配置"""

    # 同一行为之间的最小间隔（秒）- 避免连续相同行为
    SAME_ACTION_MIN_INTERVAL = 30  # 5分钟
    SAME_ACTION_MAX_INTERVAL = 60  # 15分钟

    # 不同行为之间的间隔（秒）
    DIFF_ACTION_MIN_INTERVAL = 20  # 2分钟
    DIFF_ACTION_MAX_INTERVAL = 40  # 5分钟

    # 休息时段（每采集N次后休息一段时间）
    REST_AFTER_TASKS = 20           # 每20次任务后休息
    REST_MIN_DURATION = 180        # 休息30分钟
    REST_MAX_DURATION = 300        # 休息1小时

    # 单次抓包超时（秒）
    CAPTURE_TIMEOUT = 600           # 10分钟

    @staticmethod
    def get_interval(last_action: str, current_action: str) -> int:
        """
        根据上次和当前行为，计算等待时间

        Args:
            last_action: 上次行为类型
            current_action: 当前行为类型

        Returns:
            等待秒数
        """
        if last_action == current_action:
            # 同一行为：间隔长一些
            interval = random.randint(
                TimingConfig.SAME_ACTION_MIN_INTERVAL,
                TimingConfig.SAME_ACTION_MAX_INTERVAL
            )
        else:
            # 不同行为：间隔短一些
            interval = random.randint(
                TimingConfig.DIFF_ACTION_MIN_INTERVAL,
                TimingConfig.DIFF_ACTION_MAX_INTERVAL
            )

        return interval


# ============================================================
# 错误控制配置
# ============================================================
class ErrorConfig:
    """错误处理配置"""

    MAX_CONSECUTIVE_FAILURES = 3    # 最多连续失败3次就停止
    MAX_TOTAL_FAILURES = 10         # 总失败次数上限

    # 需要重试的错误类型
    RETRY_ERRORS = [
        'SSH',          # SSH连接失败
        'timeout',      # 超时
        'network',      # 网络错误
    ]

    MAX_RETRIES = 2                 # 单个任务最多重试2次
    RETRY_DELAY = 60                # 重试前等待60秒


# ============================================================
# 任务调度器
# ============================================================
class TaskScheduler:
    """智能任务调度器"""

    def __init__(self, platform: str, tasks: List[Tuple[str, int]], logger: logging.Logger):
        """
        Args:
            platform: 平台名称
            tasks: [(action, count), ...] 例如 [('like', 10), ('comment', 5)]
            logger: 日志记录器
        """
        self.platform = platform
        self.logger = logger

        # 展开任务列表（例如 ('like', 3) → [('like', 1), ('like', 2), ('like', 3)]）
        self.task_queue = []
        for action, count in tasks:
            for i in range(1, count + 1):
                self.task_queue.append((action, i, count))

        # 打乱顺序（避免按顺序执行）
        random.shuffle(self.task_queue)

        # 优化：避免连续相同行为
        self._optimize_task_order()

        # 统计
        self.total_tasks = len(self.task_queue)
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.consecutive_failures = 0

        # 行为统计（用于计算间隔）
        self.last_action = None
        self.action_history = defaultdict(list)  # action -> [timestamp, ...]

    def _optimize_task_order(self):
        """优化任务顺序，尽量避免连续相同行为"""
        optimized = []
        remaining = self.task_queue.copy()

        while remaining:
            # 如果已有任务，尽量选择不同的行为
            if optimized:
                last_action = optimized[-1][0]

                # 先尝试找不同的行为
                different_actions = [t for t in remaining if t[0] != last_action]

                if different_actions:
                    chosen = random.choice(different_actions)
                else:
                    # 没有不同的行为了，只能选相同的
                    chosen = remaining[0]
            else:
                # 第一个任务，随机选
                chosen = remaining[0]

            optimized.append(chosen)
            remaining.remove(chosen)

        self.task_queue = optimized
        self.logger.info(f"Task order optimized: {len(self.task_queue)} tasks scheduled")

    def get_next_task(self) -> Optional[Tuple[str, int, int]]:
        """
        获取下一个任务

        Returns:
            (action, iteration, total_count) 或 None
        """
        if not self.task_queue:
            return None

        return self.task_queue.pop(0)

    def calculate_wait_time(self, current_action: str) -> int:
        """
        计算等待时间

        Args:
            current_action: 当前要执行的行为

        Returns:
            等待秒数
        """
        # 基础间隔
        interval = TimingConfig.get_interval(self.last_action, current_action)

        # 如果需要休息（每N个任务后）
        if self.completed_tasks > 0 and self.completed_tasks % TimingConfig.REST_AFTER_TASKS == 0:
            rest_time = random.randint(
                TimingConfig.REST_MIN_DURATION,
                TimingConfig.REST_MAX_DURATION
            )
            self.logger.info(f"📴 Rest period: {rest_time//60} minutes")
            interval += rest_time

        return interval

    def mark_success(self, action: str):
        """标记任务成功"""
        self.completed_tasks += 1
        self.consecutive_failures = 0
        self.last_action = action
        self.action_history[action].append(time.time())

    def mark_failure(self, action: str):
        """标记任务失败"""
        self.failed_tasks += 1
        self.consecutive_failures += 1

    def should_stop(self) -> Tuple[bool, str]:
        """
        检查是否应该停止

        Returns:
            (should_stop, reason)
        """
        # 检查连续失败
        if self.consecutive_failures >= ErrorConfig.MAX_CONSECUTIVE_FAILURES:
            return True, f"连续失败 {self.consecutive_failures} 次"

        # 检查总失败次数
        if self.failed_tasks >= ErrorConfig.MAX_TOTAL_FAILURES:
            return True, f"总失败次数达到 {self.failed_tasks} 次"

        return False, ""

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total': self.total_tasks,
            'completed': self.completed_tasks,
            'failed': self.failed_tasks,
            'remaining': len(self.task_queue),
            'success_rate': (self.completed_tasks / max(1, self.completed_tasks + self.failed_tasks)) * 100,
        }


# ============================================================
# 任务执行器
# ============================================================
class TaskExecutor:
    """任务执行器"""

    def __init__(self, logger: logging.Logger, dry_run: bool = False):
        """
        Args:
            logger: 日志记录器
            dry_run: 是否为演练模式（不实际执行）
        """
        self.logger = logger
        self.dry_run = dry_run

    def execute(self, platform: str, action: str, iteration: int) -> bool:
        """
        执行单个采集任务

        Args:
            platform: 平台名称
            action: 行为类型
            iteration: 迭代编号

        Returns:
            是否成功
        """
        run_capture_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'run_capture.py')
        cmd = [
            sys.executable, run_capture_path,
            '--platform', platform,
            '--action', action,
            '--num', '1',
            '--timeout', str(TimingConfig.CAPTURE_TIMEOUT)
        ]

        self.logger.info("="*70)
        self.logger.info(f"📍 Task: {platform} {action} (#{iteration})")
        self.logger.info(f"📝 Command: {' '.join(cmd)}")

        if self.dry_run:
            self.logger.info("🔍 [DRY RUN] Skipping actual execution")
            time.sleep(2)  # 模拟执行
            return True

        try:
            # 执行命令
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=False,  # 不捕获输出，直接显示到控制台
                text=True,
                timeout=TimingConfig.CAPTURE_TIMEOUT + 60  # 额外缓冲时间
            )
            duration = time.time() - start_time

            # 检查返回值
            if result.returncode == 0:
                self.logger.info(f"✅ Task completed successfully ({duration:.1f}s)")
                return True
            else:
                self.logger.error(f"❌ Task failed with exit code {result.returncode}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"❌ Task timeout (>{TimingConfig.CAPTURE_TIMEOUT}s)")
            return False

        except KeyboardInterrupt:
            self.logger.warning("⚠️  User interrupted")
            raise

        except Exception as e:
            self.logger.error(f"❌ Task execution error: {e}", exc_info=True)
            return False


# ============================================================
# 主控制器
# ============================================================
class BatchController:
    """批量采集控制器"""

    def __init__(self, plan_name: str = None, platform: str = None,
                 tasks: List[Tuple[str, int]] = None, dry_run: bool = False):
        """
        Args:
            plan_name: 预定义计划名称（'weibo_full', 'weibo_test' 等）
            platform: 平台名称（如果不使用预定义计划）
            tasks: 任务列表（如果不使用预定义计划）
            dry_run: 是否为演练模式
        """
        # 设置日志
        log_dir = 'logs/batch_capture'
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        self.logger = setup_logger(log_file)

        self.logger.info("="*70)
        self.logger.info("🚀 Batch Capture Controller Started")
        self.logger.info("="*70)

        # 加载计划
        if plan_name:
            if plan_name not in CAPTURE_PLANS:
                raise ValueError(f"Unknown plan: {plan_name}. Available: {list(CAPTURE_PLANS.keys())}")

            plan = CAPTURE_PLANS[plan_name]
            platform = plan['platform']
            tasks = plan['tasks']
            self.logger.info(f"📋 Using plan: {plan_name}")
        else:
            if not platform or not tasks:
                raise ValueError("Must provide either plan_name or (platform + tasks)")
            self.logger.info(f"📋 Using custom plan")

        self.logger.info(f"🌐 Platform: {platform}")
        self.logger.info(f"📊 Tasks: {tasks}")
        self.logger.info(f"🔍 Dry run: {dry_run}")

        # 初始化调度器和执行器
        self.scheduler = TaskScheduler(platform, tasks, self.logger)
        self.executor = TaskExecutor(self.logger, dry_run)
        self.dry_run = dry_run

        # 初始化SSH控制器（用于VPS操作）
        self.config = CaptureConfig()
        self.ssh = SSHController(self.config)

        # 开始时间
        self.start_time = time.time()

    def cleanup_vps_zombie_processes(self):
        """清理VPS上的僵尸tcpdump进程，并删除它们正在写的pcap文件"""
        try:
            self.ssh.connect()

            # 获取僵尸进程正在写的文件列表（提取 -w 后面的参数）
            _, stdout, _ = self.ssh.exec_command(
                "ps aux | grep tcpdump | grep -v grep | awk '{for(i=1;i<=NF;i++) if($i==\"-w\") print $(i+1)}'",
                timeout=30
            )
            zombie_files = [f.strip() for f in stdout.strip().splitlines() if f.strip()]

            if not zombie_files:
                self.logger.info("✅ No zombie processes on VPS")
                return

            self.logger.warning(f"⚠️  Found {len(zombie_files)} zombie tcpdump process(es) on VPS")

            # 先 kill 所有 tcpdump
            self.logger.info("🧹 Killing zombie processes...")
            self.ssh.exec_command("pkill -9 tcpdump", timeout=30)
            time.sleep(1)

            # 再删除这些僵尸进程写的 pcap 文件
            for fpath in zombie_files:
                self.logger.info(f"🗑️  Removing zombie pcap: {fpath}")
                self.ssh.exec_command(f"rm -f {fpath}", timeout=30)

            self.logger.info(f"✅ VPS cleanup completed: killed {len(zombie_files)} process(es), removed {len(zombie_files)} zombie pcap(s)")

        except Exception as e:
            self.logger.warning(f"⚠️  VPS cleanup failed (non-critical): {e}")

    def run(self):
        """运行批量采集"""
        # 清理VPS僵尸进程
        self.cleanup_vps_zombie_processes()

        self.logger.info("="*70)
        self.logger.info(f"📌 Total tasks: {self.scheduler.total_tasks}")
        self.logger.info("="*70)

        try:
            while True:
                # 获取下一个任务
                task = self.scheduler.get_next_task()
                if task is None:
                    self.logger.info("✅ All tasks completed!")
                    break

                action, iteration, total = task

                # 检查是否应该停止
                should_stop, reason = self.scheduler.should_stop()
                if should_stop:
                    self.logger.error(f"🛑 Stopping due to: {reason}")
                    break

                # 计算等待时间
                if self.scheduler.completed_tasks > 0:
                    is_rest_period = (
                        self.scheduler.completed_tasks % TimingConfig.REST_AFTER_TASKS == 0
                    )
                    wait_time = self.scheduler.calculate_wait_time(action)
                    self.logger.info(f"⏳ Waiting {wait_time}s before next task...")

                    if not self.dry_run:
                        if is_rest_period:
                            # 先等5秒让上次 capture 完全收尾，再清理 VPS 僵尸进程
                            time.sleep(5)
                            self.logger.info("🧹 Rest period: killing any leftover VPS tcpdump...")
                            self.cleanup_vps_zombie_processes()
                            remaining = wait_time - 5
                            if remaining > 0:
                                time.sleep(remaining)
                        else:
                            time.sleep(wait_time)

                # 执行任务（带重试）
                success = False
                for retry in range(ErrorConfig.MAX_RETRIES + 1):
                    if retry > 0:
                        self.logger.warning(f"🔄 Retry {retry}/{ErrorConfig.MAX_RETRIES}")
                        time.sleep(ErrorConfig.RETRY_DELAY)

                    success = self.executor.execute(
                        self.scheduler.platform,
                        action,
                        iteration
                    )

                    if success:
                        break

                # 更新统计
                if success:
                    self.scheduler.mark_success(action)
                else:
                    self.scheduler.mark_failure(action)

                # 显示进度
                stats = self.scheduler.get_stats()
                self.logger.info(
                    f"📊 Progress: {stats['completed']}/{stats['total']} "
                    f"(Success rate: {stats['success_rate']:.1f}%)"
                )

        except KeyboardInterrupt:
            self.logger.warning("\n\n⚠️  Batch capture interrupted by user")

        except Exception as e:
            self.logger.error(f"❌ Unexpected error: {e}", exc_info=True)

        finally:
            # 断开SSH连接
            try:
                self.ssh.disconnect()
            except Exception as e:
                self.logger.warning(f"⚠️  SSH disconnect error: {e}")

            self._print_summary()

    def _print_summary(self):
        """打印执行总结"""
        duration = time.time() - self.start_time
        stats = self.scheduler.get_stats()

        self.logger.info("\n" + "="*70)
        self.logger.info("📊 Batch Capture Summary")
        self.logger.info("="*70)
        self.logger.info(f"⏱️  Total duration: {duration/60:.1f} minutes")
        self.logger.info(f"✅ Completed: {stats['completed']}")
        self.logger.info(f"❌ Failed: {stats['failed']}")
        self.logger.info(f"⏭️  Skipped: {stats['remaining']}")
        self.logger.info(f"📈 Success rate: {stats['success_rate']:.1f}%")
        self.logger.info("="*70)


# ============================================================
# 命令行接口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description='批量抓包控制脚本 - 智能调度，模拟人类行为',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用预定义计划
  %(prog)s --config weibo_full
  %(prog)s --config weibo_test --dry-run

  # 自定义计划
  %(prog)s --platform weibo --tasks like:10 comment:5 browse:10

  # 演练模式（不实际执行）
  %(prog)s --config weibo_full --dry-run

可用的预定义计划:
  weibo_full      - 微博完整采集（5个行为 x 10次）
  weibo_test      - 微博测试（4个行为 x 2次）
  instagram_full  - Instagram完整采集（4个行为）
  instagram_test  - Instagram测试（4个行为 x 1次）
  facebook_full   - Facebook完整采集
  tiktok_full     - TikTok完整采集
  twitter_full    - Twitter完整采集（5个行为 x 10次）
  twitter_test    - Twitter测试（4个行为 x 2次）
  zhihu_full      - 知乎完整采集（5个行为 x 10次）
  zhihu_test      - 知乎测试（4个行为 x 2次）
        """
    )

    parser.add_argument(
        '--config', '-c',
        help='预定义计划名称（weibo_full, weibo_test 等）'
    )

    parser.add_argument(
        '--platform', '-p',
        choices=['weibo', 'facebook', 'tiktok', 'twitter', 'zhihu', 'instagram'],
        help='平台名称（自定义计划时使用）'
    )

    parser.add_argument(
        '--tasks', '-t',
        nargs='+',
        help='任务列表，格式: action:count（例如 like:10 comment:5）'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='演练模式（不实际执行，只显示计划）'
    )

    args = parser.parse_args()

    # 验证参数
    if not args.config and not (args.platform and args.tasks):
        parser.error("必须提供 --config 或 (--platform + --tasks)")

    # 解析自定义任务
    tasks = None
    if args.tasks:
        tasks = []
        for task_str in args.tasks:
            try:
                action, count = task_str.split(':')
                tasks.append((action, int(count)))
            except ValueError:
                parser.error(f"Invalid task format: {task_str}. Expected format: action:count")

    # 创建控制器并运行
    try:
        controller = BatchController(
            plan_name=args.config,
            platform=args.platform,
            tasks=tasks,
            dry_run=args.dry_run
        )
        controller.run()
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
