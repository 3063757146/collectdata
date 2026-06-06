#!/bin/bash
# ============================================================
# Ubuntu 环境一键部署脚本
# 用途：在 Ubuntu 22.04/24.04 上部署 collcetdata 流量采集框架
# 使用：chmod +x setup_ubuntu.sh && sudo ./setup_ubuntu.sh
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  CollectData Ubuntu 部署脚本${NC}"
echo -e "${GREEN}======================================${NC}"

# 检查是否为 root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}请使用 sudo 运行此脚本${NC}"
    exit 1
fi

# 获取实际用户（非 root）
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
ARCH="$(dpkg --print-architecture)"

echo -e "${YELLOW}用户: $REAL_USER${NC}"
echo -e "${YELLOW}项目目录: $PROJECT_DIR${NC}"
echo -e "${YELLOW}系统架构: $ARCH${NC}"

# ============================================================
# 1. 系统依赖
# ============================================================
echo -e "\n${GREEN}[1/7] 安装系统依赖...${NC}"
apt-get update
apt-get install -y \
    tcpdump \
    wget \
    curl \
    unzip \
    git \
    xvfb \
    libxi6 \
    libnss3 \
    libxss1 \
    fonts-liberation \
    libgbm1 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2

# 某些包在不同 Ubuntu 版本/架构上名字变化或不存在，按可用性安装
OPTIONAL_PKGS=(
    libappindicator3-1
    libindicator7
)
for pkg in "${OPTIONAL_PKGS[@]}"; do
    if apt-cache show "$pkg" >/dev/null 2>&1; then
        apt-get install -y "$pkg"
    else
        echo -e "${YELLOW}跳过不可用包: $pkg${NC}"
    fi
done

# Ubuntu 24.04 上 libasound2 可能是虚拟包，按可用包名安装
if apt-cache show libasound2t64 >/dev/null 2>&1; then
    apt-get install -y libasound2t64
else
    apt-get install -y libasound2
fi

# ============================================================
# 2. 安装浏览器（按架构）
# ============================================================
echo -e "\n${GREEN}[2/7] 安装浏览器...${NC}"
if [ "$ARCH" = "amd64" ]; then
    if ! command -v google-chrome >/dev/null 2>&1; then
        wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
        apt-get install -y /tmp/chrome.deb || apt-get -f install -y
        rm -f /tmp/chrome.deb
    fi
    echo -e "${GREEN}浏览器就绪: $(google-chrome --version)${NC}"
elif [ "$ARCH" = "arm64" ]; then
    # arm64 无官方 Google Chrome deb，使用 Chromium
    if apt-cache show chromium-browser >/dev/null 2>&1; then
        apt-get install -y chromium-browser
    elif apt-cache show chromium >/dev/null 2>&1; then
        apt-get install -y chromium
    else
        echo -e "${RED}未找到 Chromium 包（chromium-browser/chromium）${NC}"
        exit 1
    fi

    if apt-cache show chromium-chromedriver >/dev/null 2>&1; then
        apt-get install -y chromium-chromedriver
    elif apt-cache show chromium-driver >/dev/null 2>&1; then
        apt-get install -y chromium-driver
    else
        echo -e "${YELLOW}未找到 chromedriver 包，请后续手动安装${NC}"
    fi

    CHROME_CMD=""
    if command -v chromium-browser >/dev/null 2>&1; then
        CHROME_CMD="chromium-browser"
    elif command -v chromium >/dev/null 2>&1; then
        CHROME_CMD="chromium"
    fi

    if [ -n "$CHROME_CMD" ]; then
        # 在 root/sudo 环境下直接执行 snap Chromium 会产生噪音告警；改为用普通用户探测版本。
        REAL_UID="$(id -u "$REAL_USER")"
        BROWSER_VER="$(sudo -u "$REAL_USER" -H env HOME="$REAL_HOME" XDG_RUNTIME_DIR="/run/user/${REAL_UID}" "$CHROME_CMD" --version 2>/dev/null || true)"
        if [ -n "$BROWSER_VER" ]; then
            echo -e "${GREEN}浏览器就绪: ${BROWSER_VER}${NC}"
        else
            echo -e "${YELLOW}Chromium 包已安装（命令: ${CHROME_CMD}）。在无桌面/无用户会话时读取版本可能出现告警，不影响安装。${NC}"
        fi
    else
        echo -e "${YELLOW}Chromium 已安装，但未在 PATH 找到命令${NC}"
    fi
else
    echo -e "${RED}不支持的架构: $ARCH${NC}"
    exit 1
fi

# ============================================================
# 3. 安装 Miniconda（如未安装）
# ============================================================
echo -e "\n${GREEN}[3/7] 配置 Python 环境...${NC}"
CONDA_PATH="$REAL_HOME/miniconda3"
if [ ! -d "$CONDA_PATH" ]; then
    echo "安装 Miniconda..."
    if [ "$ARCH" = "amd64" ]; then
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    elif [ "$ARCH" = "arm64" ]; then
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh"
    else
        echo -e "${RED}不支持的架构: $ARCH${NC}"
        exit 1
    fi
    wget -q -O /tmp/miniconda.sh "$MINICONDA_URL"
    sudo -u "$REAL_USER" bash /tmp/miniconda.sh -b -p "$CONDA_PATH"
    rm -f /tmp/miniconda.sh
    sudo -u "$REAL_USER" "$CONDA_PATH/bin/conda" init bash
else
    echo -e "${YELLOW}Miniconda 已安装${NC}"
fi

# 新版 conda 可能要求先接受默认仓库 ToS（非交互环境会直接报错）
if sudo -u "$REAL_USER" "$CONDA_PATH/bin/conda" tos --help >/dev/null 2>&1; then
    echo "接受 Conda 默认 channel ToS..."
    sudo -u "$REAL_USER" "$CONDA_PATH/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main >/dev/null 2>&1 || true
    sudo -u "$REAL_USER" "$CONDA_PATH/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r >/dev/null 2>&1 || true
else
    echo -e "${YELLOW}当前 conda 不支持 tos 子命令，跳过 ToS 自动处理${NC}"
fi

echo "创建 datacollect 环境..."
if ! sudo -u "$REAL_USER" "$CONDA_PATH/bin/conda" env list | awk '{print $1}' | grep -qx "datacollect"; then
    ENV_CREATED=0
    for PY_VER in 3.13 3.12 3.11; do
        echo "尝试创建环境: python=${PY_VER}"
        if sudo -u "$REAL_USER" "$CONDA_PATH/bin/conda" create -n datacollect "python=${PY_VER}" -y; then
            ENV_CREATED=1
            break
        fi
    done

    if [ "$ENV_CREATED" -ne 1 ]; then
        echo -e "${RED}创建 datacollect 环境失败（3.13/3.12/3.11 均不可用）${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}datacollect 环境已存在，跳过创建${NC}"
fi

# 校验环境可用
if ! sudo -u "$REAL_USER" "$CONDA_PATH/bin/conda" run -n datacollect python -V >/dev/null 2>&1; then
    echo -e "${RED}datacollect 环境不可用，请检查 conda 配置${NC}"
    exit 1
fi

echo "安装 Python 依赖..."
sudo -u "$REAL_USER" "$CONDA_PATH/bin/conda" install -n datacollect -y pip
sudo -u "$REAL_USER" "$CONDA_PATH/bin/conda" run -n datacollect python -m pip install -r "$PROJECT_DIR/requirements.txt"

# ============================================================
# 4. 安装 Xray（按架构）
# ============================================================
echo -e "\n${GREEN}[4/7] 安装 Xray...${NC}"
XRAY_DIR="$PROJECT_DIR/xray_linux"
if [ ! -f "$XRAY_DIR/xray" ]; then
    mkdir -p "$XRAY_DIR"
    if [ "$ARCH" = "amd64" ]; then
        XRAY_URL="https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"
    elif [ "$ARCH" = "arm64" ]; then
        XRAY_URL="https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-arm64-v8a.zip"
    else
        echo -e "${RED}不支持的架构: $ARCH${NC}"
        exit 1
    fi
    wget -q -O /tmp/xray.zip "$XRAY_URL"
    unzip -o /tmp/xray.zip -d "$XRAY_DIR"
    chmod +x "$XRAY_DIR/xray"
    rm -f /tmp/xray.zip
    echo -e "${GREEN}Xray 安装完成${NC}"
else
    echo -e "${YELLOW}Xray 已存在${NC}"
fi

# ============================================================
# 5. 配置 tcpdump 权限（免 sudo）
# ============================================================
echo -e "\n${GREEN}[5/7] 配置 tcpdump 权限...${NC}"
TCPDUMP_PATH=$(which tcpdump)
setcap cap_net_raw,cap_net_admin=eip "$TCPDUMP_PATH" 2>/dev/null || true
echo -e "${GREEN}已设置 tcpdump capabilities（可免 sudo 抓包）${NC}"

# ============================================================
# 6. 创建 Selenium profiles 目录
# ============================================================
echo -e "\n${GREEN}[6/7] 创建 Selenium profiles 目录...${NC}"
sudo -u "$REAL_USER" mkdir -p "$REAL_HOME/selenium_profiles"/{weibo,facebook,tiktok,zhihu,twitter,instagram}
echo -e "${GREEN}Selenium profiles 目录已创建${NC}"

# ============================================================
# 7. 创建目录结构
# ============================================================
echo -e "\n${GREEN}[7/7] 创建输出目录...${NC}"
sudo -u "$REAL_USER" mkdir -p "$PROJECT_DIR/output"/{captures,vps}/{weibo,facebook,tiktok,zhihu,twitter,instagram}
sudo -u "$REAL_USER" mkdir -p "$PROJECT_DIR/data"/{weibo,facebook,tiktok,zhihu,twitter,instagram}/{mac,vps}
sudo -u "$REAL_USER" mkdir -p "$PROJECT_DIR/logs"/{batch_capture,batch_loop}

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  部署完成！以下需要手动配置：${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${YELLOW}1. 网络接口名称${NC}"
echo "   运行: ip link show"
echo "   修改 capture/config.py 中 interface_local 为实际接口名（如 eth0, ens33）"
echo ""
echo -e "${YELLOW}2. 本机 IP 地址${NC}"
echo "   运行: ip addr show"
echo "   修改 capture/config.py 中:"
echo "     mac_private_ip = \"<本机内网IP>\""
echo "     mac_public_ip = \"<本机公网IP>\""
echo "   修改 dataprocess/config.py 中:"
echo "     local_ip = \"<本机内网IP>\""
echo "     local_public_ip = \"<本机公网IP>\""
echo ""
echo -e "${YELLOW}3. Xray 启动${NC}"
echo "   cd $PROJECT_DIR && ./xray_linux/xray run -c config.json &"
echo ""
echo -e "${YELLOW}4. 如果是无桌面环境（headless），启动 Xvfb：${NC}"
echo "   Xvfb :99 -screen 0 1920x1080x24 &"
echo "   export DISPLAY=:99"
echo ""
echo -e "${YELLOW}5. 激活环境并运行${NC}"
echo "   conda activate datacollect"
echo "   sudo python3 run_capture.py --platform weibo --action browse --num 1"
echo ""
