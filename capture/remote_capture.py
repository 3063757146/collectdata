#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程抓包模块
通过SSH控制VPS端的tcpdump
"""

import time
import logging
from typing import Optional

from .ssh_client import SSHController
from .config import CaptureConfig
from .exceptions import TcpdumpError, SSHCommandError


class RemoteCapture:
    """
    通过SSH控制VPS端的tcpdump

    负责：
    - SSH远程启动tcpdump
    - 停止远程tcpdump
    - 下载pcap文件
    - 清理远程临时文件
    """

    def __init__(self, ssh: SSHController, config: CaptureConfig):
        """
        初始化远程抓包器

        Args:
            ssh: SSH控制器实例
            config: 抓包配置对象
        """
        self._ssh = ssh
        self._config = config
        self._remote_path: Optional[str] = None
        self._pid: Optional[int] = None
        self._logger = logging.getLogger('capture.remote')

    def start(self, remote_path: str, bpf_filter: Optional[str] = None) -> None:
        """
        启动VPS端的tcpdump

        Args:
            remote_path: 远程pcap文件路径
            bpf_filter: BPF过滤器（可选）

        Raises:
            TcpdumpError: tcpdump启动失败
        """
        if self._pid is not None:
            raise TcpdumpError("Remote tcpdump is already running")

        # 确保远程目录存在
        remote_dir = remote_path.rsplit('/', 1)[0] if '/' in remote_path else ''
        if remote_dir:
            try:
                self._ssh.exec_command(f"mkdir -p {remote_dir}")
            except Exception as e:
                raise TcpdumpError(f"Failed to create remote directory: {e}")

        # 构建tcpdump命令
        cmd_parts = [
            'nohup',
            self._config.remote_tcpdump,
            '-i', self._config.interface_remote,
            '-s', str(self._config.snaplen),
            '-w', remote_path,
        ]

        # 添加BPF过滤器（注意引号）
        if bpf_filter:
            cmd_parts.append(f"'{bpf_filter}'")

        # 后台运行并获取PID
        cmd = ' '.join(cmd_parts) + ' > /dev/null 2>&1 & echo $!'

        # 明显地打印命令
        self._logger.info("="*70)
        self._logger.info("【远程抓包命令】VPS端tcpdump")
        self._logger.info("="*70)
        self._logger.info(f"完整命令: {cmd}")
        self._logger.info(f"输出文件: {remote_path}")
        self._logger.info(f"BPF过滤器: {bpf_filter or '(无)'}")
        self._logger.info("="*70)

        try:
            # 执行命令并获取PID
            exit_code, stdout, stderr = self._ssh.exec_command(cmd, timeout=10)

            if exit_code != 0:
                raise TcpdumpError(f"Failed to start remote tcpdump: {stderr}")

            # 解析PID
            try:
                self._pid = int(stdout.strip())
            except ValueError:
                raise TcpdumpError(f"Invalid PID from remote tcpdump: {stdout}")

            # 等待一小段时间，验证进程是否成功启动
            time.sleep(0.5)

            # 使用kill -0检查进程是否存在
            check_code, _, _ = self._ssh.exec_command(f"kill -0 {self._pid} 2>/dev/null")
            if check_code != 0:
                raise TcpdumpError(
                    f"Remote tcpdump process (PID: {self._pid}) not found after start"
                )

            self._remote_path = remote_path
            self._logger.info(f"Remote tcpdump started (PID: {self._pid})")

        except SSHCommandError as e:
            raise TcpdumpError(f"SSH command failed: {e}")
        except Exception as e:
            raise TcpdumpError(f"Failed to start remote tcpdump: {e}")

    def stop(self) -> str:
        """
        停止VPS端的tcpdump

        停止策略：
        1. 发送SIGTERM（允许tcpdump刷新缓冲）
        2. 等待最多5秒
        3. 如果仍未退出，发送SIGKILL

        Returns:
            远程pcap文件路径

        Raises:
            TcpdumpError: 停止失败
        """
        if self._pid is None:
            raise TcpdumpError("Remote tcpdump is not running")

        pid = self._pid
        self._logger.info(f"Stopping remote tcpdump (PID: {pid})")

        try:
            # 1. 发送SIGTERM（优雅关闭）
            self._ssh.exec_command(f"kill -TERM {pid}")

            # 2. 等待进程退出（最多5秒，每次检查间隔0.5秒）
            for i in range(10):
                time.sleep(0.5)
                check_code, _, _ = self._ssh.exec_command(f"kill -0 {pid} 2>/dev/null")
                if check_code != 0:
                    # 进程已退出
                    self._logger.info(f"Remote tcpdump stopped gracefully")
                    break
            else:
                # 3. 超时后强制kill
                self._logger.warning(f"Remote tcpdump did not exit gracefully, sending SIGKILL")
                self._ssh.exec_command(f"kill -9 {pid}")
                time.sleep(0.5)

        except Exception as e:
            self._logger.error(f"Error stopping remote tcpdump: {e}")
        finally:
            remote_path = self._remote_path
            self._pid = None
            self._remote_path = None

        # 验证远程pcap文件存在
        if remote_path:
            try:
                exit_code, stdout, _ = self._ssh.exec_command(f"ls -l {remote_path}")
                if exit_code == 0:
                    self._logger.info(f"Remote pcap saved: {remote_path}")
                    return remote_path
                else:
                    raise TcpdumpError(f"Remote pcap file not found: {remote_path}")
            except Exception as e:
                raise TcpdumpError(f"Failed to verify remote pcap: {e}")
        else:
            raise TcpdumpError("Remote path is None")

    def download(self, local_path: str) -> str:
        """
        下载远程pcap文件到本地，然后删除远程文件

        Args:
            local_path: 本地保存路径

        Returns:
            本地文件路径

        Raises:
            FileTransferError: 下载失败
        """
        if self._remote_path is None:
            raise TcpdumpError("No remote pcap file to download")

        self._logger.info(f"Downloading remote pcap: {self._remote_path} -> {local_path}")

        try:
            # 下载文件
            self._ssh.download_file(self._remote_path, local_path)

            # 下载成功后删除远程文件
            self._ssh.remove_remote_file(self._remote_path)

            return local_path

        except Exception as e:
            self._logger.error(f"Failed to download remote pcap: {e}")
            raise

    def is_running(self) -> bool:
        """检查远程tcpdump是否正在运行"""
        if self._pid is None:
            return False

        try:
            # 使用kill -0检查进程是否存在
            exit_code, _, _ = self._ssh.exec_command(f"kill -0 {self._pid} 2>/dev/null")
            return exit_code == 0
        except Exception:
            return False

    @property
    def pid(self) -> Optional[int]:
        """返回远程tcpdump进程的PID（用于诊断）"""
        return self._pid
