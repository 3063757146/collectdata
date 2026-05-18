#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓包管理器模块
核心编排器，负责双端协同抓包的流程控制
"""

import os
import time
import json
import logging
import threading
from typing import Optional, Dict

from .config import CaptureConfig
from .ssh_client import SSHController
from .local_capture import LocalCapture
from .remote_capture import RemoteCapture
from .label import generate_filename
from .exceptions import SSHConnectionError, TcpdumpError


class CaptureManager:
    """
    双端协同抓包的核心编排器

    负责：
    - 协调macOS端和VPS端的tcpdump启动/停止
    - 确保双端同步
    - 文件命名和元数据管理
    - 错误处理和优雅降级
    """

    def __init__(self, config: Optional[CaptureConfig] = None):
        """
        初始化抓包管理器

        Args:
            config: 抓包配置对象（默认使用CaptureConfig()）
        """
        self._config = config or CaptureConfig()
        self._ssh = SSHController(self._config)
        self._local = LocalCapture(self._config)
        self._remote = RemoteCapture(self._ssh, self._config)

        self._running = False
        self._start_time: Optional[float] = None
        self._timer: Optional[threading.Timer] = None
        self._logger = logging.getLogger('capture')

        self._vps_available = False
        self._current_label: Optional[str] = None
        self._local_pcap: Optional[str] = None
        self._vps_pcap: Optional[str] = None

    def start(self, label: str, timeout: Optional[int] = None) -> None:
        """
        启动双端抓包

        同步策略：
        1. 建立SSH连接（或标记VPS不可用）
        2. 生成输出路径（基于label和timestamp）
        3. 创建输出目录（本地 + 远程）
        4. 启动VPS端tcpdump（先启动，抵消SSH延迟）
        5. 启动macOS端tcpdump（后启动）
        6. 记录开始时间
        7. 如果指定timeout，启动定时器

        Args:
            label: 抓包标签（由label.py生成）
            timeout: 抓包超时（秒），None表示不自动停止

        Raises:
            TcpdumpError: 本地tcpdump启动失败
        """
        if self._running:
            raise TcpdumpError("Capture is already running")

        self._current_label = label
        timestamp = time.time()

        # 生成文件路径
        mac_filename = generate_filename(label, "mac", timestamp)
        vps_filename = generate_filename(label, "vps", timestamp)

        self._local_pcap = os.path.join(self._config.local_output_dir, mac_filename)
        remote_pcap_path = os.path.join(self._config.remote_output_dir, vps_filename)

        # 创建本地输出目录
        os.makedirs(self._config.local_output_dir, exist_ok=True)

        self._logger.info("="*60)
        self._logger.info(f"Starting dual-end capture: {label}")
        self._logger.info("="*60)

        # === 第1步：尝试连接VPS ===
        try:
            self._ssh.connect()
            self._vps_available = True
            self._logger.info("VPS connection established")
        except SSHConnectionError as e:
            self._logger.warning(f"VPS unavailable: {e}")
            self._logger.warning("Falling back to local-only capture")
            self._vps_available = False
            self._vps_pcap = None

        # === 第2步：启动VPS端tcpdump（如果可用）===
        if self._vps_available:
            try:
                # 创建VPS端输出目录
                self._ssh.exec_command(f"mkdir -p {self._config.remote_output_dir}")

                # 从label中提取平台名称（格式: platform_action_...）
                platform = label.split('_')[0] if '_' in label else None

                # 生成BPF过滤器
                bpf_filter = self._config.get_remote_bpf(platform=platform)
                self._remote.start(remote_pcap_path, bpf_filter)
                self._logger.info(f"Remote capture started: {remote_pcap_path}")

                # 显示过滤状态
                if self._config.enable_vps_ip_filter:
                    if platform:
                        platform_ips = self._config.get_platform_ips(platform)
                        if platform_ips:
                            self._logger.info(f"VPS IP filter: ENABLED for {platform} ({len(platform_ips)} IPs)")
                        else:
                            self._logger.warning(f"VPS IP filter: ENABLED but no IP list for {platform}")
                    else:
                        self._logger.info("VPS IP filter: ENABLED (no platform specified)")
                else:
                    self._logger.info("VPS IP filter: DISABLED (capturing all traffic)")
            except Exception as e:
                self._logger.error(f"Failed to start remote capture: {e}")
                self._logger.warning("Continuing with local-only capture")
                self._vps_available = False
                self._vps_pcap = None

        # === 第3步：启动macOS端tcpdump ===
        try:
            bpf_filter = self._config.get_local_bpf()
            self._local.start(self._local_pcap, bpf_filter)
            self._logger.info(f"Local capture started: {self._local_pcap}")
        except Exception as e:
            # 本地抓包失败是致命错误
            if self._vps_available:
                # 清理VPS端
                try:
                    self._remote.stop()
                except Exception:
                    pass
            raise TcpdumpError(f"Failed to start local capture: {e}")

        # === 第4步：额外预热（可选）===
        # local_capture.start() 已经等待tcpdump准备就绪
        # 这里额外等待1秒，确保VPS端也ready
        warmup_time = 1  # 减少到1秒（local_capture已经包含等待）
        self._logger.info(f"Final warmup: {warmup_time}s...")
        time.sleep(warmup_time)

        # === 第5步：记录开始时间 ===
        self._start_time = time.time()
        self._running = True

        # === 第6步：设置超时（如果指定）===
        if timeout is not None:
            self._timer = threading.Timer(timeout, self._on_timeout)
            self._timer.daemon = True
            self._timer.start()
            self._logger.info(f"Timeout set to {timeout}s")

        self._logger.info("Dual-end capture started successfully")
        self._logger.info(f"VPS available: {self._vps_available}")

    def stop(self) -> Dict:
        """
        停止双端抓包

        停止顺序：
        1. 取消timeout定时器
        2. 停止macOS端tcpdump（先停止，确保窗口⊆VPS窗口）
        3. 停止VPS端tcpdump
        4. 下载VPS端pcap
        5. 清理远程文件
        6. 保存元数据JSON
        7. 返回结果字典

        Returns:
            结果字典，包含：
            - label: 标签
            - local_pcap: macOS端pcap路径
            - vps_pcap: VPS端pcap路径（或None）
            - start_time: 开始时间（epoch）
            - stop_time: 停止时间（epoch）
            - duration: 持续时间（秒）
            - vps_available: VPS是否可用

        Raises:
            TcpdumpError: 停止失败
        """
        if not self._running:
            raise TcpdumpError("Capture is not running")

        self._logger.info("="*60)
        self._logger.info("Stopping dual-end capture")
        self._logger.info("="*60)

        # === 第1步：取消定时器 ===
        if self._timer:
            self._timer.cancel()
            self._timer = None

        stop_time = time.time()

        # === 第2步：停止macOS端tcpdump ===
        try:
            self._local.stop()
            self._logger.info("Local capture stopped")
        except Exception as e:
            self._logger.error(f"Failed to stop local capture: {e}")

        # === 第3步：停止VPS端tcpdump ===
        if self._vps_available:
            try:
                remote_path = self._remote.stop()
                self._logger.info("Remote capture stopped")

                # === 第4步：下载VPS端pcap到本地 ===
                # 生成本地VPS目录路径（与local_output_dir平级）
                # local_output_dir = "output/captures" -> local_vps_dir = "output/vps"
                base_output_dir = os.path.dirname(self._config.local_output_dir)
                if not base_output_dir:  # 如果是顶级目录（如"captures"），使用当前目录
                    base_output_dir = "output"

                local_vps_dir = os.path.join(base_output_dir, "vps")

                # 转换为绝对路径（基于当前工作目录）
                local_vps_dir = os.path.abspath(local_vps_dir)
                os.makedirs(local_vps_dir, exist_ok=True)

                # 本地文件路径（保持原文件名）
                local_vps_path = os.path.join(local_vps_dir, os.path.basename(remote_path))

                self._logger.info(f"Downloading VPS pcap: {remote_path} -> {local_vps_path}")
                self._remote.download(local_vps_path)

                # 验证文件下载成功
                if os.path.exists(local_vps_path):
                    file_size = os.path.getsize(local_vps_path)
                    self._logger.info(f"✅ VPS pcap downloaded: {local_vps_path} ({file_size / 1024 / 1024:.2f} MB)")
                    self._vps_pcap = local_vps_path  # 保存本地路径
                else:
                    self._logger.error(f"❌ VPS pcap download failed: file not found")
                    self._vps_pcap = remote_path  # 降级：保存远程路径

            except Exception as e:
                self._logger.error(f"Failed to stop/download remote capture: {e}")
                import traceback
                traceback.print_exc()
                self._vps_pcap = None

        # === 第5步：构建结果 ===
        duration = stop_time - (self._start_time or stop_time)

        result = {
            'label': self._current_label,
            'local_pcap': self._local_pcap,
            'vps_pcap': self._vps_pcap,
            'start_time': self._start_time,
            'stop_time': stop_time,
            'duration': duration,
            'vps_available': self._vps_available,
        }

        # === 第6步：保存元数据JSON ===
        try:
            self._save_metadata(result)
        except Exception as e:
            self._logger.error(f"Failed to save metadata: {e}")

        # === 清理状态 ===
        self._running = False
        self._start_time = None
        self._current_label = None

        self._logger.info("="*60)
        self._logger.info(f"Capture complete: {duration:.1f}s")
        self._logger.info(f"  Local: {self._local_pcap}")
        if self._vps_pcap:
            self._logger.info(f"  VPS:   {self._vps_pcap}")
        self._logger.info("="*60)

        return result

    def wait_for_keypress(self) -> None:
        """
        阻塞等待用户按Enter（手动停止模式）

        用法：
            manager.start("label")
            manager.wait_for_keypress()  # 用户按Enter后停止
            result = manager.stop()
        """
        print("\n[Capture running] Press Enter to stop...\n")
        try:
            input()
        except KeyboardInterrupt:
            pass

    def _on_timeout(self) -> None:
        """超时回调（由threading.Timer调用）"""
        self._logger.info(f"Capture timeout reached")
        try:
            self.stop()
        except Exception as e:
            self._logger.error(f"Error in timeout callback: {e}")

    def _save_metadata(self, result: Dict) -> None:
        """保存抓包元数据为JSON文件"""
        if not result.get('local_pcap'):
            return

        # 元数据文件路径（与local_pcap同名，扩展名为.json）
        local_pcap = result['local_pcap']
        meta_path = local_pcap.rsplit('.', 1)[0] + '_meta.json'

        # 构建元数据
        metadata = {
            'label': result['label'],
            'platform': result['label'].split('_')[0] if '_' in result['label'] else 'unknown',
            'action': result['label'].split('_')[1] if result['label'].count('_') >= 1 else 'unknown',
            'start_time': result['start_time'],
            'stop_time': result['stop_time'],
            'duration': result['duration'],
            'local_pcap': result['local_pcap'],
            'vps_pcap': result['vps_pcap'],
            'vps_available': result['vps_available'],
            'local_bpf': self._config.get_local_bpf(),
            'remote_bpf': self._config.get_remote_bpf() if result['vps_available'] else None,
        }

        # 保存JSON
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self._logger.info(f"Metadata saved: {meta_path}")

    # === 上下文管理器支持 ===

    def __enter__(self):
        """进入上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器（自动停止抓包和断开SSH）"""
        if self._running:
            try:
                self.stop()
            except Exception as e:
                self._logger.error(f"Error stopping capture in __exit__: {e}")

        try:
            self._ssh.disconnect()
        except Exception:
            pass

        # 不抑制异常
        return False
