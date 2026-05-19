#!/bin/bash

# 清除 Selenium 用户配置文件的缓存脚本
# 使用方法: ./clear_profile.sh [weibo|facebook|tiktok|zhihu|twitter|all]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置文件路径
WEIBO_PROFILE="/Users/shuai/selenium_profiles/weibo"
FACEBOOK_PROFILE="/Users/shuai/selenium_profiles/facebook"
TIKTOK_PROFILE="/Users/shuai/selenium_profiles/tiktok"
ZHIHU_PROFILE="/Users/shuai/selenium_profiles/zhihu"
TWITTER_PROFILE="/Users/shuai/selenium_profiles/twitter"

# 显示菜单
show_menu() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Selenium 配置文件清理工具${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "请选择清理方式:"
    echo "  1) 完全清除 (删除所有数据，需要重新登录)"
    echo "  2) 只清除缓存 (保留登录状态)"
    echo "  3) 退出"
    echo ""
}

# 显示平台选择菜单
show_platform_menu() {
    echo "请选择要清理的平台:"
    echo "  1) 微博 (Weibo)"
    echo "  2) Facebook"
    echo "  3) TikTok"
    echo "  4) 知乎 (Zhihu)"
    echo "  5) Twitter"
    echo "  6) 全部 (All)"
    echo "  7) 返回上级菜单"
    echo ""
}

# 检查并关闭 Chrome 进程
kill_chrome_process() {
    local profile_name=$1
    echo -e "${YELLOW}🔍 检查正在运行的 Chrome 进程...${NC}"

    if pgrep -f "chrome.*${profile_name}" > /dev/null; then
        echo -e "${YELLOW}⚠️  发现正在运行的 Chrome 进程，正在关闭...${NC}"
        pkill -f "chrome.*${profile_name}" || true
        sleep 2
        echo -e "${GREEN}✅ Chrome 进程已关闭${NC}"
    else
        echo -e "${GREEN}✅ 没有运行中的 Chrome 进程${NC}"
    fi
}

# 完全清除配置文件
clear_all() {
    local profile_path=$1
    local profile_name=$2

    echo -e "${YELLOW}🗑️  完全清除 ${profile_name} 配置文件...${NC}"

    if [ -d "$profile_path" ]; then
        kill_chrome_process "$profile_name"

        # 使用 sudo 删除
        if sudo rm -rf "$profile_path"; then
            echo -e "${GREEN}✅ ${profile_name} 配置文件已完全清除${NC}"
            echo -e "${YELLOW}⚠️  下次运行需要重新登录 ${profile_name}${NC}"
        else
            echo -e "${RED}❌ 清除失败${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  ${profile_name} 配置文件不存在: $profile_path${NC}"
    fi
}

# 只清除缓存
clear_cache_only() {
    local profile_path=$1
    local profile_name=$2

    echo -e "${YELLOW}🧹 清除 ${profile_name} 缓存文件...${NC}"

    if [ ! -d "$profile_path" ]; then
        echo -e "${YELLOW}⚠️  ${profile_name} 配置文件不存在: $profile_path${NC}"
        return
    fi

    kill_chrome_process "$profile_name"

    # 清除缓存相关目录
    local cache_dirs=(
        "Default/Cache"
        "Default/Code Cache"
        "Default/GPUCache"
        "Default/Service Worker"
        "Default/DawnCache"
        "ShaderCache"
        "Default/History"
        "Default/History-journal"
        "Default/Top Sites"
        "Default/Top Sites-journal"
    )

    local cleared_count=0
    for cache_dir in "${cache_dirs[@]}"; do
        local full_path="$profile_path/$cache_dir"
        if [ -e "$full_path" ]; then
            if sudo rm -rf "$full_path"; then
                echo -e "${GREEN}  ✓ 已清除: $cache_dir${NC}"
                ((cleared_count++))
            else
                echo -e "${RED}  ✗ 清除失败: $cache_dir${NC}"
            fi
        fi
    done

    if [ $cleared_count -gt 0 ]; then
        echo -e "${GREEN}✅ ${profile_name} 缓存清除完成 (共 $cleared_count 项)${NC}"
        echo -e "${GREEN}✅ 登录状态已保留${NC}"
    else
        echo -e "${YELLOW}⚠️  没有找到需要清除的缓存${NC}"
    fi
}

# 处理平台选择
process_platform() {
    local mode=$1  # "all" 或 "cache"
    local platform=$2

    case $platform in
        1)
            if [ "$mode" == "all" ]; then
                clear_all "$WEIBO_PROFILE" "Weibo"
            else
                clear_cache_only "$WEIBO_PROFILE" "Weibo"
            fi
            ;;
        2)
            if [ "$mode" == "all" ]; then
                clear_all "$FACEBOOK_PROFILE" "Facebook"
            else
                clear_cache_only "$FACEBOOK_PROFILE" "Facebook"
            fi
            ;;
        3)
            if [ "$mode" == "all" ]; then
                clear_all "$TIKTOK_PROFILE" "TikTok"
            else
                clear_cache_only "$TIKTOK_PROFILE" "TikTok"
            fi
            ;;
        4)
            if [ "$mode" == "all" ]; then
                clear_all "$ZHIHU_PROFILE" "Zhihu"
            else
                clear_cache_only "$ZHIHU_PROFILE" "Zhihu"
            fi
            ;;
        5)
            if [ "$mode" == "all" ]; then
                clear_all "$TWITTER_PROFILE" "Twitter"
            else
                clear_cache_only "$TWITTER_PROFILE" "Twitter"
            fi
            ;;
        6)
            # 全部平台
            if [ "$mode" == "all" ]; then
                clear_all "$WEIBO_PROFILE" "Weibo"
                clear_all "$FACEBOOK_PROFILE" "Facebook"
                clear_all "$TIKTOK_PROFILE" "TikTok"
                clear_all "$ZHIHU_PROFILE" "Zhihu"
                clear_all "$TWITTER_PROFILE" "Twitter"
            else
                clear_cache_only "$WEIBO_PROFILE" "Weibo"
                clear_cache_only "$FACEBOOK_PROFILE" "Facebook"
                clear_cache_only "$TIKTOK_PROFILE" "TikTok"
                clear_cache_only "$ZHIHU_PROFILE" "Zhihu"
                clear_cache_only "$TWITTER_PROFILE" "Twitter"
            fi
            ;;
    esac
}

# 主程序
main() {
    # 如果有命令行参数，直接执行
    if [ $# -gt 0 ]; then
        case $1 in
            weibo)
                clear_cache_only "$WEIBO_PROFILE" "Weibo"
                ;;
            facebook)
                clear_cache_only "$FACEBOOK_PROFILE" "Facebook"
                ;;
            tiktok)
                clear_cache_only "$TIKTOK_PROFILE" "TikTok"
                ;;
            zhihu)
                clear_cache_only "$ZHIHU_PROFILE" "Zhihu"
                ;;
            twitter)
                clear_cache_only "$TWITTER_PROFILE" "Twitter"
                ;;
            all)
                clear_cache_only "$WEIBO_PROFILE" "Weibo"
                clear_cache_only "$FACEBOOK_PROFILE" "Facebook"
                clear_cache_only "$TIKTOK_PROFILE" "TikTok"
                clear_cache_only "$ZHIHU_PROFILE" "Zhihu"
                clear_cache_only "$TWITTER_PROFILE" "Twitter"
                ;;
            *)
                echo -e "${RED}错误: 未知参数 '$1'${NC}"
                echo "使用方法: $0 [weibo|facebook|tiktok|zhihu|twitter|all]"
                exit 1
                ;;
        esac
        exit 0
    fi

    # 交互式菜单
    while true; do
        show_menu
        read -p "请输入选项 (1-3): " choice

        case $choice in
            1)
                echo ""
                show_platform_menu
                read -p "请输入选项 (1-7): " platform

                if [ "$platform" == "7" ]; then
                    continue
                elif [[ "$platform" =~ ^[1-6]$ ]]; then
                    echo ""
                    process_platform "all" "$platform"
                    echo ""
                    read -p "按回车键继续..."
                else
                    echo -e "${RED}❌ 无效选项${NC}"
                    sleep 1
                fi
                ;;
            2)
                echo ""
                show_platform_menu
                read -p "请输入选项 (1-7): " platform

                if [ "$platform" == "7" ]; then
                    continue
                elif [[ "$platform" =~ ^[1-6]$ ]]; then
                    echo ""
                    process_platform "cache" "$platform"
                    echo ""
                    read -p "按回车键继续..."
                else
                    echo -e "${RED}❌ 无效选项${NC}"
                    sleep 1
                fi
                ;;
            3)
                echo -e "${GREEN}👋 再见！${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}❌ 无效选项，请重新选择${NC}"
                sleep 1
                ;;
        esac
    done
}

main "$@"
