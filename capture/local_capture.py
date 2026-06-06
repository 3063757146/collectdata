#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地抓包模块
封装macOS端的tcpdump进程管理
"""

import os
import time
import signal
import logging
import subprocess
from typing import Optional

from .config import CaptureConfig
from .exceptions import TcpdumpError, TcpdumpPermissionError


class LocalCapture:
    """
    封装macOS端的tcpdump进程

    负责：
    - 启动tcpdump捕获流量
    - 停止tcpdump并保存pcap文件
    - 进程状态监控
    """

    def __init__(self, config: CaptureConfig):
        """
        初始化本地抓包器

        Args:
            config: 抓包配置对象
        """
        self._config = config
        self._process: Optional[subprocess.Popen] = None
        self._output_path: Optional[str] = None
        self._logger = logging.getLogger('capture.local')

    def start(self, output_path: str, bpf_filter: Optional[str] = None) -> None:
        """
        启动tcpdump抓包

        Args:
            output_path: 输出pcap文件路径
            bpf_filter: BPF过滤器（可选）

        Raises:
            TcpdumpError: tcpdump启动失败
            TcpdumpPermissionError: 权限不足
        """
        if self._process is not None:
            raise TcpdumpError("tcpdump is already running")

        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # 启动前清理同接口同输出文件的残留进程，避免僵尸 tcpdump 累积。
        self._cleanup_stale_capture(output_path)

        # 构建tcpdump命令
        cmd = [
            self._config.local_tcpdump,
            '-i', self._config.interface_local,
            '-s', str(self._config.snaplen),
            '-w', output_path,
        ]

        # 普通用户场景下，若 tcpdump 无能力位则回退 sudo。
        if os.geteuid() != 0 and not self._can_run_tcpdump_without_sudo():
            cmd.insert(0, 'sudo')

        # 添加BPF过滤器
        if bpf_filter:
            cmd.append(bpf_filter)

        # 明显地打印命令
        cmd_str = ' '.join(cmd)
        self._logger.info("="*70)
        self._logger.info("【本地抓包命令】macOS端tcpdump")
        self._logger.info("="*70)
        self._logger.info(f"完整命令: {cmd_str}")
        self._logger.info(f"输出文件: {output_path}")
        self._logger.info(f"BPF过滤器: {bpf_filter or '(无)'}")
        self._logger.info("="*70)

        try:
            # 启动tcpdump子进程
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            # 等待一小段时间，检查进程是否成功启动
            time.sleep(0.5)

            if self._process.poll() is not None:
                # 进程已退出，读取错误信息
                _, stderr = self._process.communicate()

                # 检查权限错误
                if 'permission denied' in stderr.lower() or 'operation not permitted' in stderr.lower():
                    raise TcpdumpPermissionError(
                        f"Permission denied. Please ensure:\n"
                        f"1. You have sudo privileges\n"
                        f"2. Run with: sudo python3 your_script.py\n"
                        f"3. Or configure passwordless sudo for tcpdump:\n"
                        f"   sudo visudo -f /etc/sudoers.d/tcpdump\n"
                        f"   Add line: {os.getenv('USER')} ALL=(ALL) NOPASSWD: {self._config.local_tcpdump}\n"
                        f"\nError: {stderr}"
                    )

                raise TcpdumpError(f"tcpdump exited immediately: {stderr}")

            # 等待pcap文件创建（最多5秒）
            self._logger.info(f"Waiting for pcap file to be created...")
            for i in range(50):  # 50 * 0.1 = 5秒
                if os.path.exists(output_path):
                    break
                # 同时检查进程是否还在运行
                if self._process.poll() is not None:
                    _, stderr = self._process.communicate()
                    raise TcpdumpError(
                        f"tcpdump exited before creating pcap file.\n"
                        f"This usually means sudo password is required.\n"
                        f"Run with: sudo python3 your_script.py\n"
                        f"Error: {stderr}"
                    )
                time.sleep(0.1)
            else:
                # 检查进程状态
                if self._process.poll() is None:
                    # 进程还在运行但没创建文件，可能卡在sudo密码
                    self._process.terminate()
                    raise TcpdumpPermissionError(
                        f"Pcap file not created after 5 seconds.\n"
                        f"tcpdump process is still running but not capturing.\n"
                        f"This usually means sudo password prompt is waiting.\n"
                        f"Solution: Run with sudo:\n"
                        f"  sudo python3 your_script.py"
                    )
                else:
                    raise TcpdumpError(f"Pcap file not created after 5 seconds: {output_path}")

            # 等待tcpdump真正开始写入数据（最多5秒）
            # 检查文件大小是否增长，说明tcpdump已经开始抓包
            initial_size = os.path.getsize(output_path)
            self._logger.info(f"Pcap file created, waiting for tcpdump to start capturing...")

            for i in range(50):  # 50 * 0.1 = 5秒
                time.sleep(0.1)
                current_size = os.path.getsize(output_path)
                if current_size > initial_size:
                    self._logger.info(f"tcpdump is ready (file growing: {initial_size} -> {current_size} bytes)")
                    break
            else:
                # 5秒后仍然没有数据，可能网卡没有流量，这是正常的
                # 只记录警告，不抛异常
                self._logger.warning(f"No packets captured in first 5 seconds (this is OK if no traffic yet)")

            self._output_path = output_path
            self._logger.info(f"Local tcpdump started (PID: {self._process.pid})")

        except FileNotFoundError:
            raise TcpdumpError(
                f"tcpdump not found at {self._config.local_tcpdump}. "
                f"Install with: brew install tcpdump"
            )
        except TcpdumpPermissionError:
            # 重新抛出权限错误
            raise
        except Exception as e:
            raise TcpdumpError(f"Failed to start tcpdump: {e}")

    def _can_run_tcpdump_without_sudo(self) -> bool:
        """判断当前环境是否可以在非 root 下直接运行 tcpdump。"""
        try:
            result = subprocess.run(
                ['getcap', self._config.local_tcpdump],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False
            )
            caps = result.stdout.strip()
            return 'cap_net_raw' in caps and 'cap_net_admin' in caps
        except Exception:
            return False

    def _cleanup_stale_capture(self, output_path: str) -> None:
        """清理同接口同输出文件的残留 tcpdump 进程（仅 root 下执行）。"""
        if os.geteuid() != 0:
            return

        pattern = f"{self._config.local_tcpdump} -i {self._config.interface_local} -s {self._config.snaplen} -w {output_path}"

        try:
            pid_result = subprocess.run(
                ['pgrep', '-f', pattern],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False
            )

            stale_pids = []
            for line in pid_result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    pid = int(line)
                except ValueError:
                    continue

                if pid != os.getpid():
                    stale_pids.append(pid)

            if not stale_pids:
                return

            self._logger.warning(
                f"Found stale tcpdump processes for current target, cleaning up: {stale_pids}"
            )

            for pid in stale_pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    continue
                except Exception as e:
                    self._logger.warning(f"Failed to terminate stale pid {pid}: {e}")

            time.sleep(0.3)

            for pid in stale_pids:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    continue
                except Exception:
                    continue

                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    continue
                except Exception as e:
                    self._logger.warning(f"Failed to kill stale pid {pid}: {e}")

        except Exception as e:
            self._logger.warning(f"Stale capture cleanup failed (non-fatal): {e}")

    def stop(self) -> str:
        """
        停止tcpdump并返回pcap文件路径

        停止策略：
        1. 发送SIGTERM（允许tcpdump刷新缓冲）
        2. 等待最多5秒
        3. 如果仍未退出，发送SIGKILL

        Returns:
            pcap文件路径

        Raises:
            TcpdumpError: 停止失败
        """
        if self._process is None:
            raise TcpdumpError("tcpdump is not running")

        pid = self._process.pid
        self._logger.info(f"Stopping local tcpdump (PID: {pid})")

        try:
            # 1. 发送SIGTERM（优雅关闭）
            self._process.terminate()

            # 2. 等待进程退出（最多5秒）
            try:
                self._process.wait(timeout=5)
                self._logger.info(f"Local tcpdump stopped gracefully")
            except subprocess.TimeoutExpired:
                # 3. 超时后强制kill
                self._logger.warning(f"tcpdump did not exit gracefully, sending SIGKILL")
                self._process.kill()
                self._process.wait()

            # 检查退出码
            if self._process.returncode not in (0, -signal.SIGTERM, -signal.SIGKILL):
                self._logger.warning(
                    f"tcpdump exited with code {self._process.returncode}"
                )

        except Exception as e:
            self._logger.error(f"Error stopping tcpdump: {e}")
        finally:
            output_path = self._output_path
            self._process = None
            self._output_path = None

        # 验证pcap文件存在
        if output_path and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            self._logger.info(f"Local pcap saved: {output_path} ({file_size} bytes)")
            return output_path
        else:
            raise TcpdumpError(f"Pcap file not found: {output_path}")

    def is_running(self) -> bool:
        """检查tcpdump进程是否正在运行"""
        return self._process is not None and self._process.poll() is None

    @property
    def pid(self) -> Optional[int]:
        """返回tcpdump进程的PID（用于诊断）"""
        return self._process.pid if self._process else None
