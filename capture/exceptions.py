#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义异常层级
用于capture包的错误处理
"""


class CaptureError(Exception):
    """抓包相关错误的基类"""
    pass


class SSHConnectionError(CaptureError):
    """SSH连接失败"""
    pass


class SSHCommandError(CaptureError):
    """SSH命令执行失败"""
    pass


class TcpdumpError(CaptureError):
    """tcpdump执行失败"""
    pass


class TcpdumpPermissionError(TcpdumpError):
    """tcpdump权限不足"""
    pass


class FileTransferError(CaptureError):
    """文件传输失败（SFTP/SCP）"""
    pass


class CaptureTimeoutError(CaptureError):
    """抓包超时"""
    pass
