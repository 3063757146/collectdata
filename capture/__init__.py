#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双端协同抓包系统

提供自动化的macOS-VPS双端抓包功能，用于采集社交媒体流量数据。

主要功能：
- 双端同步抓包（macOS + VPS）
- SSH远程控制VPS
- 自动打标签
- 装饰器模式集成
- BPF流量过滤

基本用法：
    # 装饰器模式（推荐）
    from capture import capture_traffic

    @capture_traffic("weibo", "like")
    def like_weibo(driver, weibo_element):
        # 原有代码不变
        ...

    # 手动模式
    from capture import CaptureManager

    manager = CaptureManager()
    manager.start("weibo_like_session")
    # ... 执行行为 ...
    result = manager.stop()

    # 上下文管理器模式
    with CaptureManager() as mgr:
        mgr.start("weibo_browse_session")
        # ... 执行行为 ...
        result = mgr.stop()
"""

__version__ = '1.0.0'
__author__ = 'Traffic Analysis Tool'

# 导出公共API
from .config import CaptureConfig
from .manager import CaptureManager
from .decorator import capture_traffic
from .label import generate_label, generate_filename, extract_unique_id

# 导出异常
from .exceptions import (
    CaptureError,
    SSHConnectionError,
    SSHCommandError,
    TcpdumpError,
    TcpdumpPermissionError,
    FileTransferError,
    CaptureTimeoutError,
)

__all__ = [
    # 核心类
    'CaptureConfig',
    'CaptureManager',

    # 装饰器
    'capture_traffic',

    # 工具函数
    'generate_label',
    'generate_filename',
    'extract_unique_id',

    # 异常
    'CaptureError',
    'SSHConnectionError',
    'SSHCommandError',
    'TcpdumpError',
    'TcpdumpPermissionError',
    'FileTransferError',
    'CaptureTimeoutError',
]
