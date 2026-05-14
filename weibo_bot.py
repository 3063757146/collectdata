#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博自动化脚本
功能：点赞、转发、评论
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys

def create_driver(use_proxy=True):
    """创建 Chrome 浏览器实例"""
    chrome_options = Options()

    # 使用 Xray SOCKS5 代理（VPS2）
    if use_proxy:
        chrome_options.add_argument('--proxy-server=socks5://127.0.0.1:10818')

    # 禁用自动化检测
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # 设置 User-Agent（模拟真实浏览器）
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    # 窗口大小
    chrome_options.add_argument('--window-size=1920,1080')

    # 忽略证书错误
    chrome_options.add_argument('--ignore-certificate-errors')

    # 加速选项
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--no-default-browser-check')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--disable-extensions')

    try:
        driver = webdriver.Chrome(options=chrome_options)

        # 隐藏自动化特征
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })

        return driver
    except Exception as e:
        print(f"❌ 创建浏览器失败: {e}")
        print("\n提示：确保已安装 ChromeDriver")
        print("macOS 安装命令: brew install --cask chromedriver")
        sys.exit(1)

def check_proxy(driver):
    """检查代理是否生效"""
    print("🔍 检查代理连接...")
    try:
        driver.get('https://api.ipify.org?format=json')
        time.sleep(2)
        ip_info = driver.find_element(By.TAG_NAME, 'pre').text
        print(f"✅ 当前 IP: {ip_info}")

        if '216.167.34.54' in ip_info:
            print("✅ 代理连接成功！使用 VPS IP")
            return True
        else:
            print("⚠️  未使用代理或代理失败")
            return False
    except Exception as e:
        print(f"❌ 检查代理失败: {e}")
        return False

def login_weibo(driver):
    """访问微博并等待登录"""
    print("\n📱 访问微博...")
    driver.get('https://weibo.com')
    time.sleep(3)

    print("\n" + "="*60)
    print("请在浏览器中手动登录微博")
    print("登录完成后，在此按回车继续...")
    print("="*60)
    input()

def like_weibo(driver):
    """点赞微博"""
    try:
        # 常见的点赞按钮选择器（从新到老）
        like_selectors = [
            'button.woo-like-main',  # 新版微博
            'button[aria-label*="赞"]',
            '.toolbar_item[action-type="feed_list_like"]',
            'a[action-type="feed_list_like"]',
            'div[class*="like"]',
        ]

        for selector in like_selectors:
            try:
                like_btn = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                like_btn.click()
                print("✅ 点赞成功！")
                return True
            except:
                continue

        print("❌ 未找到点赞按钮（页面结构可能已变化）")
        return False

    except Exception as e:
        print(f"❌ 点赞失败: {e}")
        return False

def repost_weibo(driver, content="转发微博"):
    """转发微博"""
    try:
        # 常见的转发按钮选择器
        repost_selectors = [
            'button[aria-label*="转发"]',
            '.toolbar_item[action-type="feed_list_forward"]',
            'a[action-type="feed_list_forward"]',
        ]

        for selector in repost_selectors:
            try:
                repost_btn = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                repost_btn.click()
                time.sleep(2)

                # 尝试输入转发内容（可选）
                try:
                    textarea = driver.find_element(By.CSS_SELECTOR, 'textarea')
                    textarea.clear()
                    textarea.send_keys(content)
                    time.sleep(1)
                except:
                    pass

                # 点击确认按钮
                try:
                    confirm_btn = driver.find_element(By.CSS_SELECTOR, 'button[class*="confirm"]')
                    confirm_btn.click()
                except:
                    pass

                print(f"✅ 转发成功！内容: {content}")
                return True
            except:
                continue

        print("❌ 未找到转发按钮")
        return False

    except Exception as e:
        print(f"❌ 转发失败: {e}")
        return False

def comment_weibo(driver, content):
    """评论微博"""
    try:
        # 查找评论输入框
        comment_selectors = [
            'textarea[placeholder*="评论"]',
            'textarea[class*="comment"]',
            'div[contenteditable="true"]',
        ]

        for selector in comment_selectors:
            try:
                comment_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                comment_input.click()
                time.sleep(1)
                comment_input.send_keys(content)
                time.sleep(1)

                # 查找发送按钮
                send_btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
                send_btn.click()

                print(f"✅ 评论成功！内容: {content}")
                return True
            except:
                continue

        print("❌ 未找到评论输入框")
        return False

    except Exception as e:
        print(f"❌ 评论失败: {e}")
        return False

def main():
    """主函数"""
    print("="*60)
    print("微博自动化脚本 v1.0")
    print("="*60)

    # 创建浏览器实例
    driver = create_driver(use_proxy=True)
    print("✅ 浏览器已启动")
    try:
        # 检查代理
        if not check_proxy(driver):
            print("\n⚠️  警告：代理未生效，将使用本地 IP")
            response = input("是否继续？(y/n): ")
            if response.lower() != 'y':
                return

        # 登录微博
        login_weibo(driver)
    
        # 获取微博链接
        print("\n请输入要操作的微博链接:")
        weibo_url = input("> ")

        if not weibo_url.startswith('http'):
            print("❌ 无效的链接")
            return

        # 访问微博
        print(f"\n📄 访问微博: {weibo_url}")
        driver.get(weibo_url)
        time.sleep(3)

        # 操作选择
        while True:
            print("\n" + "="*60)
            print("请选择操作:")
            print("1. 点赞")
            print("2. 转发")
            print("3. 评论")
            print("4. 全部执行（点赞+转发+评论）")
            print("5. 访问新的微博")
            print("0. 退出")
            print("="*60)

            choice = input("请输入选项 (0-5): ").strip()

            if choice == '1':
                like_weibo(driver)

            elif choice == '2':
                repost_content = input("请输入转发内容（留空则不添加文字）: ")
                repost_weibo(driver, repost_content if repost_content else "转发微博")

            elif choice == '3':
                comment_content = input("请输入评论内容: ")
                if comment_content:
                    comment_weibo(driver, comment_content)
                else:
                    print("❌ 评论内容不能为空")

            elif choice == '4':
                print("\n⚙️  执行全部操作...")
                like_weibo(driver)
                time.sleep(2)
                repost_weibo(driver, "转发微博")
                time.sleep(2)
                comment_content = input("请输入评论内容: ")
                if comment_content:
                    comment_weibo(driver, comment_content)

            elif choice == '5':
                weibo_url = input("请输入新的微博链接: ")
                if weibo_url.startswith('http'):
                    driver.get(weibo_url)
                    time.sleep(3)

            elif choice == '0':
                print("\n👋 退出程序")
                break

            else:
                print("❌ 无效的选项")

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")

    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n按回车关闭浏览器...")
        input()
        driver.quit()
        print("✅ 浏览器已关闭")

if __name__ == "__main__":
    main()
