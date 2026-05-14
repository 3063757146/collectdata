#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博自动化脚本 v2.0
强制登录检查
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys

def create_driver(use_proxy=True):
    """创建 Chrome 浏览器实例"""
    chrome_options = Options()

    if use_proxy:
        chrome_options.add_argument('--proxy-server=socks5://127.0.0.1:10818')

    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--no-default-browser-check')
    chrome_options.add_argument('--disable-popup-blocking')

    try:
        driver = webdriver.Chrome(options=chrome_options)
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
        sys.exit(1)

def check_login(driver):
    """检查是否已登录"""
    try:
        # 查找"登录/注册"按钮
        login_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), '登录') or contains(text(), '注册')]")

        if login_buttons:
            return False

        # 或者查找用户头像/昵称
        user_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/u/"]')
        return len(user_elements) > 0

    except:
        return False

def wait_for_login(driver):
    """等待用户登录"""
    print("\n" + "="*60)
    print("⚠️  检测到未登录状态")
    print("请在浏览器中完成以下操作：")
    print("1. 点击右上角【登录/注册】按钮")
    print("2. 输入账号密码登录（或扫码登录）")
    print("3. 登录成功后，在此按回车继续...")
    print("="*60)
    input()

    # 再次检查
    if not check_login(driver):
        print("⚠️  似乎还没有登录，请确认已登录后按回车...")
        input()

def like_weibo(driver):
    """点赞微博"""
    try:
        # 方法1: 通过文本查找（最可靠）
        print("尝试方法1: 通过文本查找...")
        like_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '赞') or contains(text(), '点赞')]")

        for elem in like_elements:
            try:
                # 滚动到元素位置
                driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                time.sleep(0.5)

                # 使用 JavaScript 点击
                driver.execute_script("arguments[0].click();", elem)
                print("✅ 点赞成功！")
                return True
            except Exception as e:
                continue

        # 方法2: 查找所有按钮，找包含数字的（点赞数）
        print("尝试方法2: 查找点赞计数...")
        buttons = driver.find_elements(By.TAG_NAME, 'button')

        for btn in buttons:
            try:
                text = btn.text.strip()
                class_name = btn.get_attribute('class') or ''

                # 如果 class 包含 like 或按钮有数字文本
                if 'like' in class_name.lower() or (text and text.replace(',', '').replace('.', '').replace('万', '').replace('k', '').replace('K', '').isdigit()):
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", btn)
                    print(f"✅ 点赞成功！点击了: {text or '点赞按钮'}")
                    return True
            except:
                continue

        print("❌ 未找到点赞按钮")
        print("提示: 请手动点击点赞按钮，或者提供页面截图帮助调试")
        return False

    except Exception as e:
        print(f"❌ 点赞失败: {e}")
        return False

def repost_weibo(driver):
    """转发微博"""
    try:
        # 第一步：找到并点击转发图标（打开转发输入区域）
        print("查找转发图标...")
        repost_icon_selectors = [
            'i[class*="woo-font--retweet"]',
            'i[title="转发"]',
            "*[class*='retweetIcon']"
        ]

        repost_icon = None
        for selector in repost_icon_selectors:
            try:
                icons = driver.find_elements(By.CSS_SELECTOR, selector)
                if icons:
                    repost_icon = icons[0]
                    print(f"✅ 找到转发图标: {selector}")
                    break
            except:
                continue

        if not repost_icon:
            print("❌ 未找到转发图标")
            return False

        # 点击转发图标（打开转发框）
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", repost_icon)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", repost_icon)
        print("✅ 点击转发图标，等待输入框出现...")
        time.sleep(2)

        # 第二步：查找转发输入框（可选输入内容）
        print("查找转发输入框...")
        textarea_selectors = [
            'textarea[placeholder*="分享"]',
            'textarea[placeholder*="转发"]',
            'textarea[class*="_input"]',
            'textarea'
        ]

        textarea = None
        for selector in textarea_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    textarea = elements[0]
                    print(f"✅ 找到转发输入框: {selector}")
                    break
            except:
                continue

        # 第三步：输入转发内容（可选）
        content = input("请输入转发内容（直接回车则不添加文字）: ")
        if content and textarea:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", textarea)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", textarea)
            time.sleep(0.5)
            textarea.send_keys(content)
            time.sleep(1)
            print(f"✅ 已输入转发内容: {content}")
        elif not textarea:
            print("未找到输入框，将直接转发")

        # 第四步：查找转发按钮（和评论按钮结构相同）
        print("查找转发按钮...")
        time.sleep(1)  # 等待按钮状态更新

        send_button_selectors = [
            'button[class*="woo-button-primary"]',
            'button[class*="woo-button-main"]',
            "//button[contains(@class, 'woo-button') and contains(., '转发')]"
        ]

        send_button = None
        for selector in send_button_selectors:
            try:
                if selector.startswith('//'):
                    buttons = driver.find_elements(By.XPATH, selector)
                else:
                    buttons = driver.find_elements(By.CSS_SELECTOR, selector)

                # 找到包含"转发"文字的按钮
                for btn in buttons:
                    if '转发' in btn.text:
                        send_button = btn
                        print(f"✅ 找到转发按钮")
                        break
                if send_button:
                    break
            except:
                continue

        if send_button:
            # 检查按钮是否还是 disabled 状态
            is_disabled = send_button.get_attribute('disabled')
            if is_disabled:
                print("⚠️  转发按钮仍然是禁用状态，等待1秒...")
                time.sleep(1)

            # 使用 JavaScript 点击
            driver.execute_script("arguments[0].click();", send_button)
            print(f"✅ 转发成功！")
            time.sleep(2)
            return True
        else:
            print("❌ 未找到转发按钮，请手动点击发送")
            input("手动点击转发后按回车继续...")
            return True

    except Exception as e:
        print(f"❌ 转发失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def comment_weibo(driver):
    """评论微博"""
    try:
        # 第一步：找到并点击评论图标（打开评论输入区域）
        print("查找评论图标...")
        comment_icon_selectors = [
            'i[class*="woo-font--comment"]',
            'i[title="评论"]',
            "*[class*='commentIcon']"
        ]

        comment_icon = None
        for selector in comment_icon_selectors:
            try:
                icons = driver.find_elements(By.CSS_SELECTOR, selector)
                if icons:
                    comment_icon = icons[0]
                    print(f"✅ 找到评论图标: {selector}")
                    break
            except:
                continue

        if not comment_icon:
            print("❌ 未找到评论图标")
            return False

        # 点击评论图标（打开评论框）
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_icon)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", comment_icon)
        print("✅ 点击评论图标，等待输入框出现...")
        time.sleep(2)

        # 第二步：查找评论输入框
        print("查找评论输入框...")
        comment_selectors = [
            'textarea[placeholder*="评论"]',
            'textarea[placeholder*="发布"]',
            'textarea[class*="_input"]',
            'textarea[id*="comment-textarea"]',
        ]

        comment_input = None
        for selector in comment_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    comment_input = elements[0]
                    print(f"✅ 找到评论输入框: {selector}")
                    break
            except:
                continue

        if not comment_input:
            print("❌ 未找到评论输入框")
            return False

        # 第三步：点击输入框并输入内容
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_input)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", comment_input)
        time.sleep(1)

        content = input("请输入评论内容: ")
        if not content:
            print("❌ 评论内容不能为空")
            return False

        comment_input.send_keys(content)
        time.sleep(1)

        # 第四步：查找发送按钮（输入内容后，disabled 属性会被移除）
        print("查找发送按钮...")
        time.sleep(1)  # 等待按钮状态更新

        send_button_selectors = [
            'button[class*="woo-button-primary"]',
            'button[class*="woo-button-main"]',
            "//button[contains(@class, 'woo-button') and contains(., '评论')]"
        ]

        send_button = None
        for selector in send_button_selectors:
            try:
                if selector.startswith('//'):
                    buttons = driver.find_elements(By.XPATH, selector)
                else:
                    buttons = driver.find_elements(By.CSS_SELECTOR, selector)

                # 找到包含"评论"文字的按钮
                for btn in buttons:
                    if '评论' in btn.text:
                        send_button = btn
                        print(f"✅ 找到发送按钮")
                        break
                if send_button:
                    break
            except:
                continue

        if send_button:
            # 检查按钮是否还是 disabled 状态
            is_disabled = send_button.get_attribute('disabled')
            if is_disabled:
                print("⚠️  按钮仍然是禁用状态，等待1秒...")
                time.sleep(1)

            # 使用 JavaScript 点击
            driver.execute_script("arguments[0].click();", send_button)
            print(f"✅ 评论成功！内容: {content}")
            time.sleep(2)
            return True
        else:
            print("❌ 未找到发送按钮，请手动点击发送")
            input("手动点击发送后按回车继续...")
            return True

    except Exception as e:
        print(f"❌ 评论失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*60)
    print("微博自动化脚本 v2.0")
    print("="*60)

    print("\n启动浏览器（可能需要3-5分钟，请耐心等待）...")
    driver = create_driver(use_proxy=True)
    print("✅ 浏览器启动成功！")

    try:
        # 先访问微博首页
        print("\n访问微博首页...")
        driver.get('https://weibo.com')
        time.sleep(3)

        # 检查登录状态
        if not check_login(driver):
            wait_for_login(driver)
        else:
            print("✅ 已登录")

        # 获取微博链接
        print("\n请输入要操作的微博详情页链接:")
        print("示例: https://weibo.com/7780838481/5106982486181383")
        weibo_url = input("> ")

        if not weibo_url.startswith('http'):
            print("❌ 无效的链接")
            return

        # 访问微博
        print(f"\n📄 访问微博: {weibo_url}")
        driver.get(weibo_url)
        time.sleep(3)

        # 操作菜单
        while True:
            print("\n" + "="*60)
            print("请选择操作:")
            print("1. 点赞")
            print("2. 转发")
            print("3. 评论")
            print("4. 全部执行")
            print("5. 访问新的微博")
            print("0. 退出")
            print("="*60)

            choice = input("请输入选项 (0-5): ").strip()

            if choice == '1':
                like_weibo(driver)

            elif choice == '2':
                repost_weibo(driver)

            elif choice == '3':
                comment_weibo(driver)

            elif choice == '4':
                print("\n⚙️  执行全部操作...")
                like_weibo(driver)
                time.sleep(2)
                repost_weibo(driver)
                time.sleep(2)
                comment_weibo(driver)

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
        input("\n按回车关闭浏览器...")
        driver.quit()
        print("✅ 浏览器已关闭")

if __name__ == "__main__":
    main()
