#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标签生成和文件命名模块
提供自动生成标签和pcap文件名的功能
"""

import re
import time
import datetime
from typing import Optional


def generate_label(platform: str, action: str, unique_id: str = "") -> str:
    """
    生成标签字符串

    Args:
        platform: 平台名称（weibo, facebook, tiktok）
        action: 行为类型（like, comment, repost, share, post, browse）
        unique_id: 唯一ID（微博ID、帖子ID等，可选）

    Returns:
        标签字符串，例如: "weibo_like_id_1234567_Abc1234"

    Examples:
        >>> generate_label("weibo", "like", "1234567_Abc1234")
        'weibo_like_id_1234567_Abc1234'
        >>> generate_label("facebook", "comment", "pfbid02xyz")
        'facebook_comment_id_pfbid02xyz'
        >>> generate_label("tiktok", "browse")
        'tiktok_browse'
    """
    platform = platform.lower()
    action = action.lower()

    # 清理unique_id中的非法字符
    if unique_id:
        # 只保留字母、数字、下划线
        unique_id = re.sub(r'[^a-zA-Z0-9_]', '_', unique_id)
        return f"{platform}_{action}_id_{unique_id}"
    else:
        return f"{platform}_{action}"


def generate_filename(label: str, side: str, timestamp: Optional[float] = None) -> str:
    """
    生成pcap文件名

    Args:
        label: 标签（由generate_label生成）
        side: 抓包端（"mac" 或 "vps"）
        timestamp: Unix时间戳（默认为当前时间）

    Returns:
        文件名，例如: "20260515_153042_weibo_like_id_1234567_Abc1234_mac.pcap"

    Examples:
        >>> generate_filename("weibo_like_id_123", "mac", 1715761842.123)
        '20260515_153042_weibo_like_id_123_mac.pcap'
    """
    if timestamp is None:
        timestamp = time.time()

    # 转换时间戳为可读格式
    dt = datetime.datetime.fromtimestamp(timestamp)
    ts_str = dt.strftime('%Y%m%d_%H%M%S')

    # 清理label中的非法字符
    safe_label = re.sub(r'[^a-zA-Z0-9_]', '_', label)

    # 确保side是小写
    side = side.lower()

    return f"{ts_str}_{safe_label}_{side}.pcap"


def extract_unique_id(driver, platform: str) -> str:
    """
    从Selenium driver的当前URL自动提取唯一ID

    Args:
        driver: Selenium WebDriver实例（可能为None）
        platform: 平台名称（weibo, facebook, tiktok）

    Returns:
        唯一ID字符串，如果无法提取则返回基于时间戳的ID

    Examples:
        微博URL: https://weibo.com/1234567/Abc1234 -> "1234567_Abc1234"
        Facebook URL: https://www.facebook.com/user/posts/123456 -> "123456"
        TikTok URL: https://www.tiktok.com/@user/video/7123456789 -> "7123456789"
    """
    if driver is None:
        return _generate_fallback_id()

    try:
        url = driver.current_url

        if platform == "weibo":
            # 微博URL模式: /用户ID/微博ID
            # 参考 weibo_bot_smart.py:849
            match = re.search(r'/(\d+)/([A-Za-z0-9]+)', url)
            if match:
                return f"{match.group(1)}_{match.group(2)}"

        elif platform == "facebook":
            # Facebook URL模式: /posts/帖子ID 或 /pfbid...
            match = re.search(r'/posts/(\w+)', url)
            if match:
                return match.group(1)
            # 另一种格式: pfbid在URL中
            match = re.search(r'/(pfbid\w+)', url)
            if match:
                return match.group(1)

        elif platform == "tiktok":
            # TikTok URL模式: /video/视频ID
            match = re.search(r'/video/(\d+)', url)
            if match:
                return match.group(1)

    except Exception:
        # URL提取失败，使用回退方案
        pass

    return _generate_fallback_id()


def _generate_fallback_id() -> str:
    """生成回退ID（基于时间戳）"""
    # 使用毫秒时间戳的后6位，避免ID过长
    return str(int(time.time() * 1000) % 1000000)
