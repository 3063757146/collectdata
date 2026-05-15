#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH客户端模块
提供SSH远程控制VPS的功能
"""

import time
import logging
import threading
from typing import Tuple, Optional

try:
    import paramiko
except ImportError:
    paramiko = None

from .config import CaptureConfig
from .exceptions import SSHConnectionError, SSHCommandError, FileTransferError


class SSHController:
    """
    SSH客户端，负责VPS端的远程控制

    功能：
    - 建立和维护SSH连接
    - 执行远程命令
    - 文件传输（SFTP）
    - 自动重连机制
    """

    def __init__(self, config: CaptureConfig):
        """
        初始化SSH控制器

        Args:
            config: 抓包配置对象
        """
        if paramiko is None:
            raise ImportError(
                "paramiko is not installed. Install it with: pip install paramiko"
            )

        self._config = config
        self._client: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None
        self._lock = threading.Lock()
        self._connected = False
        self._logger = logging.getLogger('capture.ssh')

    def connect(self) -> None:
        """
        建立SSH连接（带重试机制）

        重试策略：
        - 3次重试，指数退避（1s, 2s, 4s）
        - 全部失败后抛出SSHConnectionError

        Raises:
            SSHConnectionError: 连接失败
        """
        with self._lock:
            if self._connected and self._is_transport_active():
                return

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self._logger.info(
                        f"Connecting to VPS {self._config.ssh_host}:{self._config.ssh_port} "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )

                    # 创建SSH客户端
                    self._client = paramiko.SSHClient()
                    self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                    # 连接参数
                    connect_kwargs = {
                        'hostname': self._config.ssh_host,
                        'port': self._config.ssh_port,
                        'username': self._config.ssh_user,
                        'timeout': self._config.ssh_timeout,
                    }

                    # 优先使用密钥，否则使用密码
                    if self._config.ssh_key_path:
                        connect_kwargs['key_filename'] = self._config.ssh_key_path
                    else:
                        connect_kwargs['password'] = self._config.ssh_password

                    # 执行连接
                    self._client.connect(**connect_kwargs)

                    # 设置心跳
                    transport = self._client.get_transport()
                    if transport:
                        transport.set_keepalive(self._config.ssh_keepalive_interval)

                    self._connected = True
                    self._logger.info(f"SSH connected successfully to {self._config.ssh_host}")
                    return

                except Exception as e:
                    self._logger.warning(f"SSH connection attempt {attempt + 1} failed: {e}")

                    # 清理
                    if self._client:
                        try:
                            self._client.close()
                        except Exception:
                            pass
                        self._client = None

                    # 如果不是最后一次尝试，等待后重试
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                        self._logger.info(f"Retrying in {wait_time}s...")
                        time.sleep(wait_time)

            # 所有尝试都失败
            raise SSHConnectionError(
                f"Failed to connect to {self._config.ssh_host} after {max_retries} attempts"
            )

    def disconnect(self) -> None:
        """关闭SSH连接"""
        with self._lock:
            if self._sftp:
                try:
                    self._sftp.close()
                except Exception:
                    pass
                self._sftp = None

            if self._client:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None

            self._connected = False
            self._logger.info("SSH disconnected")

    def ensure_connected(self) -> None:
        """
        确保SSH连接是活跃的，如果断开则重连

        Raises:
            SSHConnectionError: 重连失败
        """
        if not self._connected or not self._is_transport_active():
            self._logger.warning("SSH connection lost, attempting to reconnect...")
            self._connected = False
            self.connect()

    def exec_command(
        self,
        cmd: str,
        timeout: int = 30
    ) -> Tuple[int, str, str]:
        """
        执行SSH命令

        Args:
            cmd: 要执行的命令
            timeout: 命令超时（秒）

        Returns:
            (exit_code, stdout, stderr) 元组

        Raises:
            SSHCommandError: 命令执行失败
        """
        self.ensure_connected()

        try:
            self._logger.debug(f"Executing command: {cmd}")

            stdin, stdout, stderr = self._client.exec_command(cmd, timeout=timeout)

            # 等待命令完成
            exit_code = stdout.channel.recv_exit_status()
            stdout_str = stdout.read().decode('utf-8', errors='ignore')
            stderr_str = stderr.read().decode('utf-8', errors='ignore')

            if exit_code != 0:
                self._logger.warning(
                    f"Command failed (exit code {exit_code}): {cmd}\n"
                    f"stderr: {stderr_str}"
                )

            return exit_code, stdout_str, stderr_str

        except Exception as e:
            raise SSHCommandError(f"Command execution failed: {cmd}\nError: {e}")

    def exec_command_background(self, cmd: str) -> paramiko.Channel:
        """
        在后台执行命令（不等待完成）

        Args:
            cmd: 要执行的命令

        Returns:
            paramiko.Channel对象，可用于后续控制

        Raises:
            SSHCommandError: 命令执行失败
        """
        self.ensure_connected()

        try:
            self._logger.debug(f"Executing background command: {cmd}")
            transport = self._client.get_transport()
            channel = transport.open_session()
            channel.exec_command(cmd)
            return channel

        except Exception as e:
            raise SSHCommandError(f"Background command failed: {cmd}\nError: {e}")

    def download_file(self, remote_path: str, local_path: str) -> None:
        """
        通过SFTP下载文件

        Args:
            remote_path: 远程文件路径
            local_path: 本地文件路径

        Raises:
            FileTransferError: 文件传输失败
        """
        self.ensure_connected()

        try:
            # 确保SFTP会话
            if not self._sftp:
                self._sftp = self._client.open_sftp()

            self._logger.info(f"Downloading {remote_path} -> {local_path}")

            # 下载文件（带重试）
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    self._sftp.get(remote_path, local_path)
                    self._logger.info(f"Download successful: {local_path}")
                    return
                except Exception as e:
                    if attempt < max_retries - 1:
                        self._logger.warning(f"Download attempt {attempt + 1} failed: {e}, retrying...")
                        time.sleep(1)
                    else:
                        raise

        except Exception as e:
            raise FileTransferError(
                f"Failed to download {remote_path}: {e}\n"
                f"You can manually retrieve it with: scp {self._config.ssh_user}@{self._config.ssh_host}:{remote_path} {local_path}"
            )

    def remove_remote_file(self, remote_path: str) -> None:
        """
        删除远程文件

        Args:
            remote_path: 远程文件路径

        Raises:
            SSHCommandError: 删除失败
        """
        try:
            exit_code, _, stderr = self.exec_command(f"rm -f {remote_path}")
            if exit_code != 0:
                self._logger.warning(f"Failed to remove remote file: {stderr}")
        except Exception as e:
            self._logger.warning(f"Error removing remote file {remote_path}: {e}")

    def is_connected(self) -> bool:
        """检查SSH连接是否活跃"""
        return self._connected and self._is_transport_active()

    def _is_transport_active(self) -> bool:
        """检查底层transport是否活跃"""
        if not self._client:
            return False

        try:
            transport = self._client.get_transport()
            return transport is not None and transport.is_active()
        except Exception:
            return False
