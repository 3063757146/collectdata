#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
装饰器模块
提供@capture_traffic装饰器，用于自动抓包
"""

import functools
import logging
import threading
from typing import Optional, Any, Callable

from .manager import CaptureManager
from .label import generate_label, extract_unique_id


# 全局共享的CaptureManager实例（单例模式）
_shared_manager: Optional[CaptureManager] = None
_manager_lock = threading.Lock()

_logger = logging.getLogger('capture.decorator')


def capture_traffic(
    platform: str,
    action: str,
    timeout: Optional[int] = None
) -> Callable:
    """
    装饰器：在bot函数执行前后自动抓包

    Args:
        platform: 平台名称（weibo, facebook, tiktok）
        action: 行为类型（like, comment, repost, share, post, browse）
        timeout: 抓包超时（秒），None表示不自动停止

    Returns:
        装饰器函数

    Examples:
        @capture_traffic("weibo", "like")
        def like_weibo(driver, weibo_element):
            # 原有代码不变
            ...

        @capture_traffic("facebook", "comment", timeout=60)
        def comment_post(driver, content_list):
            # 原有代码不变
            ...

    注意：
        - 装饰器会自动提取driver参数
        - 自动从driver.current_url提取unique_id
        - 如果函数抛出异常，仍然会停止抓包并保存
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # === 第1步：提取driver ===
            driver = _extract_driver(args, kwargs)

            # === 第2步：提取unique_id ===
            unique_id = extract_unique_id(driver, platform) if driver else ""

            # === 第3步：生成标签 ===
            label = generate_label(platform, action, unique_id)

            # === 第4步：获取共享的CaptureManager ===
            manager = _get_shared_manager()

            try:
                # === 第5步：启动抓包 ===
                try:
                    manager.start(label, timeout=timeout)
                except Exception as e:
                    _logger.error(f"Failed to start capture: {e}")
                    _logger.warning("Continuing without capture")
                    # 抓包失败不影响原函数执行
                    return func(*args, **kwargs)

                # === 第6步：执行原函数 ===
                result = func(*args, **kwargs)

                return result

            finally:
                # === 第7步：总是停止抓包（即使函数抛异常）===
                try:
                    capture_result = manager.stop()
                    _logger.info(
                        f"Capture complete: {capture_result['label']} "
                        f"({capture_result['duration']:.1f}s)"
                    )
                except Exception as e:
                    _logger.error(f"Failed to stop capture: {e}")

        return wrapper
    return decorator


def _get_shared_manager() -> CaptureManager:
    """
    获取或创建共享的CaptureManager实例（单例模式）

    为什么用单例？
    - bot脚本的多个action函数在同一会话中顺序调用
    - 共享同一个SSH连接，避免每次都重新连接VPS
    - 线程安全

    Returns:
        CaptureManager实例
    """
    global _shared_manager

    with _manager_lock:
        if _shared_manager is None:
            _shared_manager = CaptureManager()
            _logger.debug("Created shared CaptureManager instance")

        return _shared_manager


def _extract_driver(args: tuple, kwargs: dict) -> Optional[Any]:
    """
    从函数参数中提取driver对象

    常见模式：
    - 第一个位置参数：def like_weibo(driver, ...)
    - 关键字参数：def like_weibo(..., driver=driver)

    Args:
        args: 位置参数元组
        kwargs: 关键字参数字典

    Returns:
        driver对象，如果未找到则返回None
    """
    # 尝试第一个位置参数
    if args and len(args) > 0:
        # 检查是否是Selenium WebDriver（有current_url属性）
        first_arg = args[0]
        if hasattr(first_arg, 'current_url'):
            return first_arg

    # 尝试关键字参数
    if 'driver' in kwargs:
        return kwargs['driver']

    # 未找到driver
    return None
