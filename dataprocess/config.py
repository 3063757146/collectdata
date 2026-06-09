#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
定义流量特征提取的所有配置参数
"""

import dataclasses
from typing import Optional


@dataclasses.dataclass
class Config:
    """流量特征提取配置"""

    # IP地址配置
    local_ip: str = "172.16.10.129"          # 本机私有IP
    local_public_ip: str = "223.88.96.205" # 本机公网IP（NAT后）
    vps_ip: str = "216.167.34.54"            # VPS IP

    # 端口配置
    vps_tunnel_port: int = 33979             # VLESS隧道端口

    # tcpdump配置
    tcpdump_path: str = "tcpdump"            # tcpdump可执行文件路径

    # 数据处理选项
    skip_zero_length: bool = True            # 跳过0字节包（TCP ACK等）
    include_control_packets: bool = False    # 包含控制包（SYN/FIN/RST）

    # 流量类型定义
    FLOW_MAC_VPS: str = "mac_vps"            # macOS <-> VPS流量
    FLOW_VPS_WEBSITE: str = "vps_website"    # VPS <-> 网站流量
    FLOW_ALL: str = "all"                    # 所有流量

    def get_bpf_filter(self, flow_type: str, perspective: str = "mac") -> str:
        """
        根据流量类型和视角生成BPF过滤器

        Args:
            flow_type: 流量类型（mac_vps/vps_website/all）
            perspective: 抓包视角（mac/vps）

        Returns:
            BPF过滤器字符串
        """
        if flow_type == self.FLOW_MAC_VPS:
            # Flow A: macOS <-> VPS隧道流量
            if perspective == "mac":
                # macOS端：过滤VPS IP和隧道端口
                return f'host {self.vps_ip} and port {self.vps_tunnel_port}'
            else:
                # VPS端：过滤macOS公网IP和隧道端口
                return f'host {self.local_public_ip} and port {self.vps_tunnel_port}'

        elif flow_type == self.FLOW_VPS_WEBSITE:
            # Flow B: VPS <-> 网站流量（排除隧道和SSH）
            return f'host {self.vps_ip} and not port {self.vps_tunnel_port} and not port 22'

        elif flow_type == self.FLOW_ALL:
            # 所有IP流量
            return 'ip'

        else:
            raise ValueError(f"未知的流量类型: {flow_type}")

    def is_outgoing(self, src_ip: str, perspective: str = "mac") -> bool:
        """
        判断数据包是否为发送方向（用于确定符号）

        Args:
            src_ip: 源IP地址
            perspective: 抓包视角（mac/vps）

        Returns:
            True表示发送（正数），False表示接收（负数）
        """
        if perspective == "mac":
            # macOS视角：源IP不是VPS则为发送（避免依赖变化的local_ip）
            return src_ip != self.vps_ip
        else:
            # VPS视角：源IP是VPS IP则为发送
            return src_ip == self.vps_ip
