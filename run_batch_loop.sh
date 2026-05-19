#!/bin/bash
# 交替执行 TikTok 和 Weibo 批量抓包的循环脚本

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}======================================${NC}"
echo -e "${YELLOW}  批量抓包循环脚本${NC}"
echo -e "${YELLOW}  TikTok <-> Weibo 交替执行${NC}"
echo -e "${YELLOW}  按 Ctrl+C 停止${NC}"
echo -e "${YELLOW}======================================${NC}"
echo ""

# ============================================================
# sudo 认证保持机制（输入一次密码，全程有效）
# ============================================================
echo -e "${YELLOW}🔐 请输入一次 sudo 密码（后续将自动保持认证）${NC}"
sudo -v  # 先认证一次

# 后台进程：每60秒刷新一次 sudo 认证
while true; do
    sleep 60
    sudo -n true 2>/dev/null
done &
SUDO_REFRESH_PID=$!

echo -e "${GREEN}✅ sudo 认证已激活（PID: $SUDO_REFRESH_PID）${NC}"
echo ""

# 计数器
iteration=1

# 捕获 Ctrl+C 信号，优雅退出（同时杀死认证刷新进程）
cleanup() {
    echo -e "\n${YELLOW}收到停止信号，清理并退出...${NC}"
    kill $SUDO_REFRESH_PID 2>/dev/null
    echo -e "${GREEN}✅ sudo 认证刷新已停止${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# 无限循环
while true; do
    # 打印当前轮次
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}第 ${iteration} 轮${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # 执行 TikTok
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] 开始执行: TikTok 批量抓包${NC}"
    sudo python3 batch_capture.py --config tiktok_full
    tiktok_exit_code=$?

    if [ $tiktok_exit_code -ne 0 ]; then
        echo -e "${YELLOW}⚠️  TikTok 批量抓包异常退出 (exit code: $tiktok_exit_code)${NC}"
    else
        echo -e "${GREEN}✅ TikTok 批量抓包完成${NC}"
    fi

    echo ""
    sleep 3  # 间隔3秒

    # 执行 Weibo
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] 开始执行: Weibo 批量抓包${NC}"
    sudo python3 batch_capture.py --config weibo_full
    weibo_exit_code=$?

    if [ $weibo_exit_code -ne 0 ]; then
        echo -e "${YELLOW}⚠️  Weibo 批量抓包异常退出 (exit code: $weibo_exit_code)${NC}"
    else
        echo -e "${GREEN}✅ Weibo 批量抓包完成${NC}"
    fi

    echo ""
    echo -e "${BLUE}第 ${iteration} 轮完成${NC}"
    echo ""

    # 增加计数器
    ((iteration++))

    # 轮次间隔（可选）
    sleep 5
done
