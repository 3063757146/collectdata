#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
定义CaptureConfig数据类，集中管理所有抓包相关配置
"""

import dataclasses
from typing import Optional, List


# ============================================================
# 平台目标IP映射（用于VPS端过滤）
# ============================================================
PLATFORM_IPS = {
    'weibo': [
        # 微博服务器IP列表（从用户提供 + 可能需要补充）
        '36.51.224.27',
        '36.51.224.123',
        '36.51.224.126',
        '107.151.158.226',
        '128.14.219.131',
        # 微博常用的IP段（可根据实际抓包结果补充）
        # 注意：微博使用CDN，IP可能很多，建议先抓一次全量，再提取完整IP列表
    ],

    'facebook': [
        # Facebook/Meta服务器IP段
        # 需要根据实际抓包结果补充
    ],

    'tiktok': [
        # TikTok服务器IP段
        # 需要根据实际抓包结果补充
    ],
}


@dataclasses.dataclass
class CaptureConfig:
    """抓包系统配置"""

    # === 网络配置 ===
    vps_ip: str = "216.167.34.54"
    mac_private_ip: str = "10.67.227.153"
    mac_public_ip: str = "124.127.223.133"
    vps_tunnel_port: int = 33979

    # === SSH配置 ===
    ssh_host: str = "216.167.34.54"
    ssh_port: int = 22
    ssh_user: str = "root"
    ssh_password: str = "rXQUHMhMh4AnlgO5"
    ssh_key_path: Optional[str] = None
    ssh_timeout: int = 10  # 连接超时（秒）
    ssh_keepalive_interval: int = 30  # 心跳间隔（秒）

    # === 路径配置 ===
    local_tcpdump: str = "/usr/sbin/tcpdump"
    remote_tcpdump: str = "/usr/bin/tcpdump"  # VPS上tcpdump在/usr/bin
    local_output_dir: str = "output/captures"
    remote_output_dir: str = "/root/captures"  # VPS上的pcap存储目录（永久保存）

    # === 抓包配置 ===
    default_timeout: int = 300  # 默认抓包超时（秒）- 5分钟
    interface_local: str = "en0"  # macOS网络接口
    interface_remote: str = "eth0"  # VPS网络接口
    snaplen: int = 0  # 抓包长度（0=完整包）

    # === VPS端过滤配置 ===
    enable_vps_ip_filter: bool = False  # 是否启用VPS端IP过滤（默认False，抓全量）
    # 设置为True后，VPS端只抓取PLATFORM_IPS中的目标IP
    # 建议：先关闭过滤抓一次全量，提取完整IP列表后再启用

    def get_local_bpf(self) -> str:
        """
        生成macOS端的BPF过滤器

        只抓取与VPS的隧道流量，排除SSH管理流量
        """
        return f"host {self.vps_ip} and not port 22"

    def get_remote_bpf(self, platform: str = None, target_ips: List[str] = None) -> str:
        """
        生成VPS端的BPF过滤器

        Args:
            platform: 平台名称（'weibo', 'facebook', 'tiktok'），自动使用对应的IP列表
            target_ips: 自定义目标IP列表（优先于platform）

        Returns:
            BPF过滤器字符串

        过滤策略：
        1. 排除来自macOS的隧道流量
        2. 排除SSH管理流量
        3. 如果 enable_vps_ip_filter=True 且指定了target_ips或platform，只抓取到这些IP的流量
        """
        # 基础排除规则
        exclude_rules = [
            # 排除VPS的隧道端口流量（不依赖macOS的公网IP，因为IP会变）
            # f"not port {self.vps_tunnel_port}",
            # 排除SSH管理流量（mac ↔ vps的SSH连接）
            "not port 22",
            # 排除DNS流量（vps → 外部的DNS查询/响应）
            "not port 53",
            # 排除ARP包（链路层协议，无意义）
            "not arp"
        ]

        # 目标IP过滤（仅在启用过滤时）
        ip_filter = None
        if self.enable_vps_ip_filter:
            if target_ips:
                # 使用自定义IP列表
                ip_filter = " or ".join([f"host {ip}" for ip in target_ips])
            elif platform and platform in PLATFORM_IPS:
                # 使用平台预定义IP列表
                platform_ips = PLATFORM_IPS[platform]
                if platform_ips:
                    ip_filter = " or ".join([f"host {ip}" for ip in platform_ips])

        # 组合过滤器
        if ip_filter:
            # 有目标IP：排除规则 AND 目标IP
            bpf = f"({' and '.join(exclude_rules)}) and ({ip_filter})"
        else:
            # 无目标IP：只使用排除规则（全量抓包）
            bpf = " and ".join(exclude_rules)

        return bpf

    @staticmethod
    def get_platform_ips(platform: str) -> List[str]:
        """
        获取指定平台的IP列表

        Args:
            platform: 平台名称

        Returns:
            IP列表
        """
        return PLATFORM_IPS.get(platform, [])
