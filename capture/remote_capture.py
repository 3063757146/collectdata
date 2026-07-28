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
            # 执行命令并获取PID（增加超时时间）
            exit_code, stdout, stderr = self._ssh.exec_command(cmd, timeout=30)

            if exit_code != 0:
                raise TcpdumpError(f"Failed to start remote tcpdump: {stderr}")

            # 解析PID
            try:
                pid_str = stdout.strip()
                if not pid_str:
                    raise TcpdumpError("Empty PID from remote tcpdump")
                self._pid = int(pid_str)
                self._logger.info(f"Got PID: {self._pid}")
            except ValueError:
                raise TcpdumpError(f"Invalid PID from remote tcpdump: {repr(stdout)}")

            # 等待tcpdump初始化（增加等待时间，最多重试3次）
            max_checks = 3
            check_interval = 1.0
            process_found = False
            
            for check_attempt in range(max_checks):
                time.sleep(check_interval)
                
                # 使用kill -0检查进程是否存在
                check_code, _, _ = self._ssh.exec_command(f"kill -0 {self._pid} 2>/dev/null")
                if check_code == 0:
                    process_found = True
                    self._logger.info(f"Remote tcpdump process verified (PID: {self._pid}, attempt {check_attempt + 1})")
                    break
                
                self._logger.warning(f"Process check {check_attempt + 1}/{max_checks}: tcpdump PID {self._pid} not found, waiting...")

            if not process_found:
                # 进程不存在，尝试获取退出状态和错误信息
                self._logger.error(f"Remote tcpdump process (PID: {self._pid}) exited prematurely")
                
                # 检查是否有core dump或错误日志
                exit_code, stdout, stderr = self._ssh.exec_command(
                    f"ps aux | grep tcpdump | grep -v grep; echo '---'; cat nohup.out 2>/dev/null; echo '---'; ls -la {remote_path} 2>/dev/null"
                )
                
                self._logger.error(f"Debug info:\n{stdout}\n{stderr}")
                
                # 检查pcap文件是否被创建
                exit_code, stdout, _ = self._ssh.exec_command(f"ls -la {remote_path} 2>/dev/null")
                if exit_code == 0:
                    self._logger.warning(f"Pcap file exists despite process exit: {stdout.strip()}")
                    self._remote_path = remote_path
                    return
                
                raise TcpdumpError(
                    f"Remote tcpdump process (PID: {self._pid}) not found after start. "
                    f"The process may have failed to initialize. Check VPS logs for details."
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
            # 不要清空 _remote_path，download() 需要它

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
        下载远程pcap文件到本地，验证完整性后删除远程文件

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
            # 第1步：获取远程文件大小
            exit_code, remote_size_str, _ = self._ssh.exec_command(
                f"stat -c %s {self._remote_path} 2>/dev/null || stat -f %z {self._remote_path}"
            )
            remote_size = int(remote_size_str.strip()) if exit_code == 0 else None

            if remote_size is not None:
                self._logger.info(f"Remote file size: {remote_size / 1024 / 1024:.2f} MB")

            # 第2步：下载文件
            self._ssh.download_file(self._remote_path, local_path)

            # 第3步：验证本地文件
            import os
            if not os.path.exists(local_path):
                raise TcpdumpError(f"Downloaded file not found: {local_path}")

            local_size = os.path.getsize(local_path)
            self._logger.info(f"Local file size: {local_size / 1024 / 1024:.2f} MB")

            # 第4步：比较文件大小（如果能获取到远程大小）
            if remote_size is not None:
                if local_size != remote_size:
                    raise TcpdumpError(
                        f"File size mismatch: remote={remote_size}, local={local_size}. "
                        f"Download may be corrupted!"
                    )
                else:
                    self._logger.info("✅ File size verification passed")

            # 第5步：验证通过后删除远程文件
            self._logger.info(f"Deleting remote file: {self._remote_path}")
            self._ssh.remove_remote_file(self._remote_path)
            self._logger.info(f"✅ Remote file deleted successfully")

            # 第6步：清空远程路径状态
            self._remote_path = None

            return local_path

        except Exception as e:
            self._logger.error(f"Failed to download remote pcap: {e}")
            self._logger.error(f"⚠️  Remote file NOT deleted (for safety): {self._remote_path}")
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
