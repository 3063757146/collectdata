#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Facebook 智能自动化脚本 v1.0
模拟真实用户行为，随机浏览和互动
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium_stealth import stealth  # 反检测库
import time
import random
import sys
import logging
from datetime import datetime

def setup_logging():
    """配置日志系统"""
    log_filename = 'facebook_bot.log'
    log_format = '[%(asctime)s] %(levelname)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_filename, mode='a', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.info("="*60)
    logging.info("新的运行会话开始")
    logging.info("="*60)

    return logging.getLogger(__name__)

def create_driver(use_proxy=True):
    """创建 Chrome 浏览器实例（保留登录状态）"""
    chrome_options = Options()

    # 📂 设置用户数据目录（保存登录状态）
    import os
    user_data_dir = os.path.expanduser('~/selenium_profiles/facebook')

    if not os.path.exists(user_data_dir):
        print(f"📁 创建配置文件目录: {user_data_dir}")
        os.makedirs(user_data_dir, exist_ok=True)
    else:
        print(f"💾 使用现有配置文件: {user_data_dir}")

    chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
    chrome_options.add_argument('--profile-directory=Default')

    if use_proxy:
        # Clash HTTP 代理（如果是 SOCKS5，改为 socks5://127.0.0.1:7897）
        chrome_options.add_argument('--proxy-server=socks5://127.0.0.1:10818')

    # 反检测设置
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')

    # 注意：使用配置文件时不要设置随机 User-Agent
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--no-default-browser-check')
    chrome_options.add_argument('--disable-popup-blocking')

    try:
        driver = webdriver.Chrome(options=chrome_options)

        # 应用 selenium-stealth 反检测（自动隐藏所有自动化特征）
        print("🛡️  应用 Stealth 反检测模式...")
        stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="MacIntel",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        print("✅ Stealth 模式已启用")

        return driver
    except Exception as e:
        print(f"❌ 创建浏览器失败: {e}")
        sys.exit(1)

def random_scroll(driver):
    """随机滚动页面，模拟人类浏览（主要向下滚动）"""
    # 95% 向下滚动，5% 向上回看（减少向上滚动概率）
    if random.random() < 0.95:
        # 向下滚动（80%小幅，20%大幅）
        if random.random() < 0.8:
            distance = random.randint(300, 600)  # 小幅滚动
        else:
            distance = random.randint(800, 1200)  # 大幅滚动
        driver.execute_script(f"window.scrollBy(0, {distance});")
    else:
        # 偶尔向上回看
        distance = random.randint(100, 300)
        driver.execute_script(f"window.scrollBy(0, -{distance});")

    time.sleep(random.uniform(0.5, 1.5))

def simulate_reading(min_sec=3, max_sec=8):
    """模拟阅读时间"""
    reading_time = random.uniform(min_sec, max_sec)
    print(f"   📖 模拟阅读 {reading_time:.1f} 秒...")
    time.sleep(reading_time)

def check_login(driver):
    """检查是否已登录 - 通过导航栏头像图片判断"""
    try:
        print("🔍 检测登录状态...")
        time.sleep(2)

        # 主要判断：导航栏存在 fbcdn.net 头像图片 = 已登录
        try:
            avatar_imgs = driver.find_elements(By.CSS_SELECTOR, 'img[src*="fbcdn.net"]')
            visible_avatars = [img for img in avatar_imgs if img.is_displayed()]
            if visible_avatars:
                print(f"   ✅ 检测到头像图片（{len(visible_avatars)} 个）-> 已登录")
                return True
        except:
            pass

        # 备用：查找未登录标志（登录按钮）
        try:
            login_elements = driver.find_elements(By.XPATH,
                "//a[contains(text(), 'Log In') or contains(text(), '登录') or contains(text(), '登錄')]"
                " | //button[contains(text(), 'Log In') or contains(text(), '登录')]"
            )
            visible_logins = [e for e in login_elements if e.is_displayed()]
            if visible_logins:
                print("   ❌ 找到登录按钮 -> 未登录")
                return False
        except:
            pass

        print("   ⚠️  无法确定登录状态，假定未登录")
        return False

    except Exception as e:
        print(f"   ⚠️  检测异常: {e}")
        return False

def wait_for_login(driver):
    """等待用户登录"""
    print("\n" + "="*60)
    print("⚠️  检测到未登录状态")
    print("请在浏览器中完成登录后，按回车继续...")
    print("="*60)
    input()

    if not check_login(driver):
        print("⚠️  似乎还没有登录，请确认已登录后按回车...")
        input()

def like_post(driver, post_element):
    """点赞帖子（Facebook 版本）"""
    try:
        print(f"      🔍 查找点赞按钮...")

        # 策略1: 使用 data-ad-rendering-role="like_button"（最可靠）
        try:
            like_markers = post_element.find_elements(By.CSS_SELECTOR, '[data-ad-rendering-role="like_button"]')
            if like_markers:
                print(f"      ✓ 找到 {len(like_markers)} 个点赞标识元素")

                for marker in like_markers:
                    try:
                        # 向上查找可点击的容器（通常是祖父或曾祖父元素）
                        clickable = marker.find_element(By.XPATH, './ancestor::div[@class][1]')

                        if clickable and clickable.is_displayed():
                            # 滚动到元素
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clickable)
                            time.sleep(0.5)

                            # 点击
                            driver.execute_script("arguments[0].click();", clickable)
                            print("      ✅ 点赞成功（通过 data-ad-rendering-role）")
                            logging.info("点赞成功")
                            time.sleep(random.uniform(1.0, 2.0))
                            return True
                    except:
                        continue
        except:
            pass

        # 策略2: 查找包含"赞"或"Like"文字的元素
        try:
            text_elements = post_element.find_elements(By.XPATH, './/span[text()="赞" or text()="Like"]')
            if text_elements:
                print(f"      ✓ 找到 {len(text_elements)} 个文字匹配元素")

                for elem in text_elements:
                    try:
                        if not elem.is_displayed():
                            continue

                        # 向上找到最外层的可点击容器
                        # 结构: span -> span -> div -> div (最外层)
                        clickable = elem.find_element(By.XPATH, './ancestor::div[contains(@class, "x9f619")][1]')

                        if clickable:
                            # 滚动
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clickable)
                            time.sleep(0.5)

                            # 点击
                            driver.execute_script("arguments[0].click();", clickable)
                            print("      ✅ 点赞成功（通过文字匹配）")
                            logging.info("点赞成功")
                            time.sleep(random.uniform(1.0, 2.0))
                            return True
                    except:
                        continue
        except:
            pass

        # 策略3: 查找点赞图标（i 标签，包含特定背景图片）
        try:
            icons = post_element.find_elements(By.CSS_SELECTOR, 'i[data-visualcompletion="css-img"]')
            for icon in icons:
                try:
                    style = icon.get_attribute('style') or ''
                    # 检查是否是点赞图标（通过背景图片 URL 特征）
                    if 'background-image' in style:
                        # 向上找可点击容器
                        clickable = icon.find_element(By.XPATH, './ancestor::div[contains(@class, "x9f619")][1]')

                        if clickable and clickable.is_displayed():
                            # 检查附近是否有"赞"或"Like"文字（确认是点赞按钮）
                            text = clickable.text or ''
                            if '赞' in text or 'Like' in text:
                                # 滚动
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clickable)
                                time.sleep(0.5)

                                # 点击
                                driver.execute_script("arguments[0].click();", clickable)
                                print("      ✅ 点赞成功（通过图标匹配）")
                                logging.info("点赞成功")
                                time.sleep(random.uniform(1.0, 2.0))
                                return True
                except:
                    continue
        except:
            pass

        print("      ❌ 未找到可用的点赞按钮")
        logging.warning("点赞失败：未找到点赞按钮")
        return False

    except Exception as e:
        print(f"      ❌ 点赞异常: {e}")
        logging.error(f"点赞异常: {e}")
        return False

def close_comment_popup(driver):
    """关闭评论弹出框"""
    try:
        print(f"      🔍 查找关闭按钮...")
        close_selectors = [
            '//div[@aria-label="关闭"][@role="button"]',
            '//div[@aria-label="Close"][@role="button"]',
            '//div[contains(@aria-label, "关闭")][@role="button"]',
            '//div[contains(@aria-label, "Close")][@role="button"]',
        ]

        for selector in close_selectors:
            try:
                close_buttons = driver.find_elements(By.XPATH, selector)
                # 找最后一个可见的
                visible = [b for b in close_buttons if b.is_displayed()]
                if visible:
                    close_btn = visible[-1]
                    driver.execute_script("arguments[0].click();", close_btn)
                    print(f"      ✅ 已关闭评论弹出框")
                    time.sleep(0.5)
                    return True
            except:
                continue
    except Exception as e:
        print(f"      ⚠️  关闭弹出框失败（不影响评论结果）: {e}")
    return False


def comment_post(driver, post_element, comment_list):
    """评论帖子（Facebook 版本）"""
    try:
        print(f"      🔍 查找评论按钮...")

        # 查找评论按钮（中英文，多种策略）
        comment_btn_selectors = [
            # 中文
            ('XPATH', './/span[text()="评论"]', '文本"评论"（精确）'),
            ('XPATH', './/span[contains(text(), "评论")]', '文本"评论"（包含）'),
            # 英文
            ('XPATH', './/span[text()="Comment"]', '文本"Comment"（精确）'),
            ('XPATH', './/span[contains(text(), "Comment")]', '文本"Comment"（包含）'),
            # aria-label
            ('XPATH', './/*[@aria-label="评论" or @aria-label="Comment"]', 'aria-label'),
        ]

        comment_btn = None
        for method, selector, desc in comment_btn_selectors:
            try:
                elements = post_element.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed():
                        # 找到文字元素后，向上找可点击的父容器
                        try:
                            clickable = elem.find_element(By.XPATH, './ancestor::div[contains(@class, "x9f619")][1]')
                            if clickable:
                                comment_btn = clickable
                                print(f"      ✓ 找到评论按钮（{desc}）")
                                break
                        except:
                            # 如果找不到特定父元素，就点击元素本身
                            comment_btn = elem
                            print(f"      ✓ 找到评论按钮（{desc}，直接元素）")
                            break
                if comment_btn:
                    break
            except:
                continue

        if not comment_btn:
            print("      ⚠️  未找到评论按钮")
            return False

        # 点击评论按钮
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", comment_btn)
        time.sleep(2)  # 等待评论界面加载

        # 检查是否有干扰性弹窗（不包含评论输入框的弹窗）
        try:
            dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
            if dialogs:
                for dialog in dialogs:
                    # 检查弹窗中是否有评论输入框
                    has_input = dialog.find_elements(By.CSS_SELECTOR,
                        '[contenteditable="true"], [role="textbox"]')

                    # 如果没有输入框，说明是干扰性弹窗，需要关闭
                    if not has_input and dialog.is_displayed():
                        print(f"      ⚠️  检测到干扰性弹窗，关闭...")

                        # 尝试找关闭按钮
                        close_btn = dialog.find_elements(By.XPATH,
                            './/div[@aria-label="关闭" or @aria-label="Close"]')

                        if close_btn and close_btn[0].is_displayed():
                            driver.execute_script("arguments[0].click();", close_btn[0])
                            print(f"      ✅ 已关闭干扰弹窗")
                            time.sleep(1)
                        else:
                            # 按 ESC 关闭
                            from selenium.webdriver.common.action_chains import ActionChains
                            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                            print(f"      ✅ 已关闭干扰弹窗（ESC）")
                            time.sleep(1)
                        break
        except:
            pass

        time.sleep(0.5)

        # 查找评论输入框
        print(f"      🔍 查找评论输入框...")
        input_selectors = [
            # 优先使用 aria-label（最可靠）
            ('XPATH', '//div[@aria-label="写评论…"]', 'aria-label 写评论'),
            ('XPATH', '//div[@aria-label="Write a comment…"]', 'aria-label Write a comment'),
            ('XPATH', '//div[contains(@aria-label, "评论")][@contenteditable="true"]', 'aria-label 包含评论'),
            ('XPATH', '//div[contains(@aria-label, "comment")][@contenteditable="true"]', 'aria-label contains comment'),

            # 使用 data-lexical-editor（新发现的特征）
            ('CSS', 'div[data-lexical-editor="true"]', 'data-lexical-editor'),

            # 通用选择器
            ('CSS', 'div[contenteditable="true"][role="textbox"]', 'contenteditable div with role'),
            ('XPATH', '//div[@role="textbox"][@contenteditable="true"]', 'role textbox contenteditable'),

            # 基于 class（备用）
            ('CSS', 'div.xzsf02u.x1a2a7pz', 'class xzsf02u'),
            ('CSS', 'p.xdj266r.x14z9mp', 'class xdj266r'),
        ]

        input_box = None
        for method, selector, desc in input_selectors:
            try:
                if method == 'CSS':
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                else:
                    elements = driver.find_elements(By.XPATH, selector)

                # 找最后一个可见的（刚才点击评论后出现的）
                visible = [e for e in elements if e.is_displayed()]
                if visible:
                    input_box = visible[-1]
                    print(f"      ✓ 找到输入框（{desc}）")
                    break
            except:
                continue

        if not input_box:
            print("      ❌ 未找到评论输入框")
            return False

        # 输入评论
        content = random.choice(comment_list)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_box)
        time.sleep(0.5)

        # 尝试多种输入方式
        try:
            # 方式1: 先点击激活，再用 send_keys
            driver.execute_script("arguments[0].click();", input_box)
            time.sleep(0.5)
            input_box.send_keys(content)
            print(f"      ✅ 已输入评论: {content}")
        except:
            try:
                # 方式2: 使用 JavaScript 设置 textContent
                driver.execute_script("arguments[0].textContent = arguments[1];", input_box, content)
                print(f"      ✅ 已输入评论（JS）: {content}")
            except:
                # 方式3: 查找内部的 p 元素并设置
                try:
                    p_element = input_box.find_element(By.TAG_NAME, 'p')
                    driver.execute_script("arguments[0].textContent = arguments[1];", p_element, content)
                    print(f"      ✅ 已输入评论（p元素）: {content}")
                except Exception as e:
                    print(f"      ❌ 输入失败: {e}")
                    return False

        time.sleep(1)

        # 查找并点击发送按钮
        print(f"      🔍 查找发送按钮...")

        send_success = False

        # 策略1: 使用 aria-label 查找发送按钮（最可靠）
        try:
            print("      🔍 尝试使用 aria-label 查找发送按钮...")
            aria_label_selectors = [
                "//div[@aria-label='发布评论'][@role='button']",
                "//div[@aria-label='发布'][@role='button']",
                "//div[contains(@aria-label, '发布')][@role='button']",
                "//div[@aria-label='Post comment'][@role='button']",
                "//div[@aria-label='Post'][@role='button']",
            ]

            send_btn = None
            for selector in aria_label_selectors:
                try:
                    buttons = driver.find_elements(By.XPATH, selector)
                    # 找最后一个可见的（刚才输入后出现的）
                    visible = [b for b in buttons if b.is_displayed()]
                    if visible:
                        send_btn = visible[-1]
                        print(f"      ✓ 找到发送按钮（aria-label）")
                        break
                except:
                    continue

            if send_btn:
                # 等待按钮从禁用变为启用（最多等待10秒）
                print(f"      ⏱️  等待发送按钮激活...")
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC

                try:
                    # 等待 aria-disabled 属性消失或变为 false
                    wait = WebDriverWait(driver, 10)
                    wait.until(lambda d: send_btn.get_attribute('aria-disabled') != 'true')
                    print(f"      ✅ 发送按钮已激活")
                except:
                    print(f"      ⚠️  等待超时，尝试直接点击")

                # 点击发送按钮
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", send_btn)
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].click();", send_btn)
                    print(f"      ✅ 点击发送按钮成功（aria-label）")

                    # 等待评论提交完成
                    print(f"      ⏱️  等待评论提交...")
                    time.sleep(5)

                    # 验证评论是否成功（检查输入框是否清空）
                    try:
                        current_text = input_box.text.strip()
                        if not current_text or current_text == "":
                            print(f"      ✅ 评论已发送（输入框已清空）")
                            logging.info(f"评论成功: {content}")
                        else:
                            print(f"      ⚠️  输入框未清空，可能提交失败")
                            logging.warning(f"评论提交状态未知: {content}")
                    except:
                        print(f"      ⚠️  无法验证评论状态，假定成功")
                        logging.info(f"评论已提交: {content}")

                    # 关闭评论弹出框
                    close_comment_popup(driver)

                    send_success = True
                except Exception as e:
                    print(f"      ⚠️  点击失败: {e}")
        except Exception as e:
            print(f"      ⚠️  策略1失败: {e}")

        if send_success:
            return True

        # 策略2: 查找包含特定class组合的覆盖层（基于用户提供的HTML）
        try:
            print("      🔍 尝试使用覆盖层查找发送按钮...")
            # 等待发送按钮激活（输入内容后按钮才会激活）
            time.sleep(2)

            # 用户提供的发送按钮有这些class特征
            overlay_selectors = [
                # 完整的class组合
                'div.x1ey2m1c.xtijo5x[role="none"][data-visualcompletion="ignore"]',
                # 部分关键class
                'div.x1ey2m1c[role="none"]',
                # 通用选择器
                'div[data-visualcompletion="ignore"][role="none"]',
            ]

            for selector in overlay_selectors:
                try:
                    overlays = driver.find_elements(By.CSS_SELECTOR, selector)
                    if overlays:
                        print(f"      ✓ 找到 {len(overlays)} 个候选覆盖层（{selector[:30]}...）")

                        # 从后往前找（最新出现的）
                        for overlay in reversed(overlays):
                            try:
                                if not overlay.is_displayed():
                                    continue

                                # 找父元素（真正的按钮）
                                parent = overlay.find_element(By.XPATH, '..')

                                # 检查父元素是否禁用
                                if parent.get_attribute('aria-disabled') == 'true':
                                    print(f"      ⚠️  按钮仍处于禁用状态，跳过")
                                    continue

                                # 尝试点击父元素
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", parent)
                                    time.sleep(0.3)
                                    driver.execute_script("arguments[0].click();", parent)
                                    print(f"      ✅ 点击发送按钮成功（父元素）")

                                    # 等待评论提交完成（增加到5秒）
                                    print(f"      ⏱️  等待评论提交...")
                                    time.sleep(5)

                                    # 验证评论是否成功（检查输入框是否清空）
                                    try:
                                        current_text = input_box.text.strip()
                                        if not current_text or current_text == "":
                                            print(f"      ✅ 评论已发送（输入框已清空）")
                                            logging.info(f"评论成功: {content}")
                                        else:
                                            print(f"      ⚠️  输入框未清空，可能提交失败")
                                            logging.warning(f"评论提交状态未知: {content}")
                                    except:
                                        # 无法验证，假定成功
                                        print(f"      ⚠️  无法验证评论状态，假定成功")
                                        logging.info(f"评论已提交: {content}")

                                    # 关闭评论弹出框
                                    close_comment_popup(driver)

                                    send_success = True
                                    break
                                except:
                                    # 如果父元素点击失败，尝试点击覆盖层本身
                                    driver.execute_script("arguments[0].click();", overlay)
                                    print(f"      ✅ 点击发送按钮成功（覆盖层）")

                                    # 等待评论提交完成（增加到5秒）
                                    print(f"      ⏱️  等待评论提交...")
                                    time.sleep(5)

                                    # 验证评论是否成功（检查输入框是否清空）
                                    try:
                                        current_text = input_box.text.strip()
                                        if not current_text or current_text == "":
                                            print(f"      ✅ 评论已发送（输入框已清空）")
                                            logging.info(f"评论成功: {content}")
                                        else:
                                            print(f"      ⚠️  输入框未清空，可能提交失败")
                                            logging.warning(f"评论提交状态未知: {content}")
                                    except:
                                        # 无法验证，假定成功
                                        print(f"      ⚠️  无法验证评论状态，假定成功")
                                        logging.info(f"评论已提交: {content}")

                                    # 关闭评论弹出框
                                    close_comment_popup(driver)

                                    send_success = True
                                    break
                            except:
                                continue

                        if send_success:
                            break
                except:
                    continue

                if send_success:
                    break
        except Exception as e:
            print(f"      ⚠️  策略1失败: {e}")

        if send_success:
            return True

        # 策略2: 查找包含 "发表" 或 "Post" 文字的按钮
        try:
            print("      🔍 尝试查找发表/Post按钮...")
            button_selectors = [
                "//div[@role='button' and contains(., '发表')]",
                "//div[@role='button' and contains(., 'Post')]",
                "//span[contains(text(), '发表')]/ancestor::div[@role='button']",
                "//span[contains(text(), 'Post')]/ancestor::div[@role='button']",
            ]

            for selector in button_selectors:
                try:
                    buttons = driver.find_elements(By.XPATH, selector)
                    if buttons:
                        for btn in buttons:
                            if btn.is_displayed():
                                driver.execute_script("arguments[0].click();", btn)
                                print(f"      ✅ 点击发送按钮成功（文字匹配）")

                                # 等待评论提交完成（增加到5秒）
                                print(f"      ⏱️  等待评论提交...")
                                time.sleep(5)

                                # 验证评论是否成功（检查输入框是否清空）
                                try:
                                    current_text = input_box.text.strip()
                                    if not current_text or current_text == "":
                                        print(f"      ✅ 评论已发送（输入框已清空）")
                                        logging.info(f"评论成功: {content}")
                                    else:
                                        print(f"      ⚠️  输入框未清空，可能提交失败")
                                        logging.warning(f"评论提交状态未知: {content}")
                                except:
                                    # 无法验证，假定成功
                                    print(f"      ⚠️  无法验证评论状态，假定成功")
                                    logging.info(f"评论已提交: {content}")

                                # 关闭评论弹出框
                                close_comment_popup(driver)

                                return True
                except:
                    continue
        except:
            pass

        # 策略3: 尝试按回车发送
        print("      ⚠️  未找到发送按钮，尝试按回车发送...")
        try:
            input_box.send_keys(Keys.ENTER)
            print(f"      ✅ 评论已发送（回车）")

            # 等待评论提交完成（增加到5秒）
            print(f"      ⏱️  等待评论提交...")
            time.sleep(5)

            # 验证评论是否成功（检查输入框是否清空）
            try:
                current_text = input_box.text.strip()
                if not current_text or current_text == "":
                    print(f"      ✅ 评论已发送（输入框已清空）")
                    logging.info(f"评论成功（回车）: {content}")
                else:
                    print(f"      ⚠️  输入框未清空，可能提交失败")
                    logging.warning(f"评论提交状态未知（回车）: {content}")
            except:
                # 无法验证，假定成功
                print(f"      ⚠️  无法验证评论状态，假定成功")
                logging.info(f"评论已提交（回车）: {content}")

            return True
        except Exception as e:
            print(f"      ❌ 回车发送失败: {e}")
            return False

    except Exception as e:
        print(f"      ❌ 评论失败: {e}")
        logging.error(f"评论异常: {e}")
        return False

def create_post(driver, content):
    """发帖（Facebook 版本）

    Args:
        driver: WebDriver 实例
        content: 要发布的内容

    Returns:
        bool: 发帖是否成功
    """
    try:
        print(f"\n📝 开始发帖...")

        # 步骤1: 查找并点击 "分享你的新鲜事" 按钮
        print(f"   🔍 查找发帖入口按钮...")
        create_btn = None

        # 策略1: 通过文本查找
        create_btn_selectors = [
            # 中文
            "//span[contains(text(), '分享你的新鲜事')]",
            "//div[contains(text(), '分享你的新鲜事')]",
            # 英文
            "//span[contains(text(), \"What's on your mind\")]",
            "//div[contains(text(), \"What's on your mind\")]",
        ]

        for selector in create_btn_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed():
                        # 向上查找可点击的容器
                        try:
                            clickable = elem.find_element(By.XPATH, './ancestor::div[@role="button"][1]')
                            if clickable:
                                create_btn = clickable
                                print(f"   ✓ 找到发帖入口按钮")
                                break
                        except:
                            # 如果找不到 role="button"，尝试其他祖先元素
                            try:
                                clickable = elem.find_element(By.XPATH, './ancestor::div[@tabindex="0"][1]')
                                if clickable:
                                    create_btn = clickable
                                    print(f"   ✓ 找到发帖入口按钮（备用）")
                                    break
                            except:
                                pass
                if create_btn:
                    break
            except:
                continue

        if not create_btn:
            print("   ❌ 未找到发帖入口按钮")
            return False

        # 点击发帖入口按钮
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", create_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", create_btn)
        print("   ✅ 已点击发帖入口，等待输入框...")
        time.sleep(3)  # 等待发帖对话框加载

        # 步骤2: 查找输入框
        print(f"   🔍 查找发帖输入框...")
        input_box = None

        input_selectors = [
            # 使用 data-lexical-editor 和 role="textbox"
            ('CSS', 'div[data-lexical-editor="true"][role="textbox"]', 'data-lexical-editor + role'),
            # 使用 aria-placeholder
            ('XPATH', '//div[@role="textbox"][contains(@aria-placeholder, "分享你的新鲜事")]', 'aria-placeholder 中文'),
            ('XPATH', '//div[@role="textbox"][contains(@aria-placeholder, "What\'s on your mind")]', 'aria-placeholder 英文'),
            # 通用选择器
            ('CSS', 'div[contenteditable="true"][role="textbox"]', 'contenteditable + role'),
        ]

        for method, selector, desc in input_selectors:
            try:
                if method == 'CSS':
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                else:
                    elements = driver.find_elements(By.XPATH, selector)

                # 找最后一个可见的（刚才点击后出现的）
                visible = [e for e in elements if e.is_displayed()]
                if visible:
                    input_box = visible[-1]
                    print(f"   ✓ 找到输入框（{desc}）")
                    break
            except:
                continue

        if not input_box:
            print("   ❌ 未找到发帖输入框")
            return False

        # 步骤3: 输入内容
        print(f"   📝 输入内容...")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_box)
        time.sleep(0.5)

        # 先清空输入框（如果有默认内容）
        try:
            # 点击激活输入框
            driver.execute_script("arguments[0].click();", input_box)
            time.sleep(0.5)

            # 全选并删除（如果有内容）
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(driver)
            actions.key_down(Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL)
            actions.send_keys('a')
            actions.key_up(Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL)
            actions.send_keys(Keys.BACKSPACE)
            actions.perform()
            time.sleep(0.3)
        except:
            pass

        # 使用 send_keys 输入（最可靠的方式）
        input_success = False
        try:
            # 方式1: 直接使用 send_keys（推荐）
            input_box.send_keys(content)
            print(f"   ✅ 已输入内容: {content[:50]}...")
            input_success = True
        except Exception as e1:
            print(f"   ⚠️  send_keys 失败: {e1}")
            # 方式2: 查找内部的 p 元素
            try:
                p_element = input_box.find_element(By.TAG_NAME, 'p')
                driver.execute_script("arguments[0].click();", p_element)
                time.sleep(0.3)
                p_element.send_keys(content)
                print(f"   ✅ 已输入内容（p元素）: {content[:50]}...")
                input_success = True
            except Exception as e2:
                print(f"   ⚠️  p元素 send_keys 失败: {e2}")
                # 方式3: 使用 ActionChains
                try:
                    driver.execute_script("arguments[0].click();", input_box)
                    time.sleep(0.3)
                    actions = ActionChains(driver)
                    actions.send_keys(content)
                    actions.perform()
                    print(f"   ✅ 已输入内容（ActionChains）: {content[:50]}...")
                    input_success = True
                except Exception as e3:
                    print(f"   ❌ 所有输入方式都失败: {e3}")
                    return False

        if not input_success:
            print(f"   ❌ 输入失败")
            return False

        # 等待更长时间让 Facebook 检测到输入
        time.sleep(3)

        # 步骤4: 查找并点击 "发帖" 按钮
        print(f"   🔍 查找发帖按钮...")
        post_btn = None

        # 策略1: 使用 aria-label
        post_btn_selectors = [
            "//div[@aria-label='发帖'][@role='button']",
            "//div[@aria-label='Post'][@role='button']",
            "//span[text()='发帖']/ancestor::div[@role='button'][1]",
            "//span[text()='Post']/ancestor::div[@role='button'][1]",
        ]

        for selector in post_btn_selectors:
            try:
                buttons = driver.find_elements(By.XPATH, selector)
                # 找最后一个可见的
                visible = [b for b in buttons if b.is_displayed()]
                if visible:
                    post_btn = visible[-1]
                    print(f"   ✓ 找到发帖按钮")
                    break
            except:
                continue

        if not post_btn:
            print("   ❌ 未找到发帖按钮")
            return False

        # 等待按钮激活（输入内容后按钮才会激活）
        print(f"   ⏱️  等待发帖按钮激活...")
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            wait = WebDriverWait(driver, 10)
            wait.until(lambda d: post_btn.get_attribute('aria-disabled') != 'true')
            print(f"   ✅ 发帖按钮已激活")
        except:
            print(f"   ⚠️  等待超时，尝试直接点击")

        # 点击发帖按钮
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", post_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", post_btn)
        print(f"   ✅ 已点击发帖按钮")

        # 等待发帖完成
        print(f"   ⏱️  等待发帖完成...")
        time.sleep(5)

        print(f"   ✅ 发帖成功！")
        logging.info(f"发帖成功: {content[:50]}")
        return True

    except Exception as e:
        print(f"   ❌ 发帖失败: {e}")
        logging.error(f"发帖异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def share_post(driver, post_element, share_templates):
    """分享帖子（Facebook 版本）"""
    try:
        print(f"      🔍 查找分享按钮...")

        share_btn = None

        # 策略1: 使用 data-ad-rendering-role="share_button"（最可靠，类似点赞按钮）
        try:
            share_markers = post_element.find_elements(By.CSS_SELECTOR, '[data-ad-rendering-role="share_button"]')
            if share_markers:
                print(f"      ✓ 找到 {len(share_markers)} 个分享标识元素")

                for marker in share_markers:
                    try:
                        # 向上查找可点击的容器（和点赞按钮类似的结构）
                        # 通常需要向上多层才能找到最外层可点击容器
                        clickable = marker.find_element(By.XPATH, './ancestor::div[contains(@class, "x9f619")][1]')

                        if clickable and clickable.is_displayed():
                            share_btn = clickable
                            print("      ✓ 找到分享按钮（通过 data-ad-rendering-role）")
                            break
                    except:
                        # 如果找不到特定容器，尝试向上2层
                        try:
                            clickable = marker.find_element(By.XPATH, '../..')
                            if clickable and clickable.is_displayed():
                                share_btn = clickable
                                print("      ✓ 找到分享按钮（向上2层）")
                                break
                        except:
                            continue
        except:
            pass

        # 策略2: 文本匹配 + 容器查找
        if not share_btn:
            share_btn_selectors = [
                # 文本匹配 + 向上查找容器
                ('XPATH', './/span[text()="分享"]/ancestor::div[contains(@class, "x9f619")][1]', '文本"分享"+容器'),
                ('XPATH', './/span[text()="Share"]/ancestor::div[contains(@class, "x9f619")][1]', '文本"Share"+容器'),

                # 文本匹配（精确）
                ('XPATH', './/span[text()="分享"]', '文本"分享"'),
                ('XPATH', './/span[text()="Share"]', '文本"Share"'),

                # aria-label
                ('XPATH', './/*[@aria-label="分享"]', 'aria-label 分享'),
                ('XPATH', './/*[@aria-label="Share"]', 'aria-label Share'),
            ]

            for method, selector, desc in share_btn_selectors:
                try:
                    elements = post_element.find_elements(By.XPATH, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            share_btn = elem
                            print(f"      ✓ 找到分享按钮（{desc}）")
                            break
                    if share_btn:
                        break
                except:
                    continue

        if not share_btn:
            print("      ⚠️  未找到分享按钮")
            return False

        # 点击分享按钮
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", share_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", share_btn)
        print("      ✅ 点击分享按钮，等待弹窗...")
        time.sleep(3)  # 等待弹窗完全加载

        # 检查是否弹出了分享输入框（有些帖子可以添加分享文案）
        try:
            # 查找分享输入框（可能是 p.xdj266r 或其他类型）
            share_input_selectors = [
                'p.xdj266r.x14z9mp',
                'div[contenteditable="true"]',
                'textarea',
            ]

            share_input = None
            for selector in share_input_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    visible = [e for e in elements if e.is_displayed()]
                    if visible:
                        share_input = visible[-1]
                        print(f"      ✓ 找到分享输入框")
                        break
                except:
                    continue

            # 如果有输入框且提供了分享模板，输入文案
            if share_input and share_templates:
                try:
                    content = random.choice(share_templates)
                    driver.execute_script("arguments[0].click();", share_input)
                    time.sleep(0.3)
                    share_input.send_keys(content)
                    print(f"      ✅ 已输入分享文案: {content}")
                    time.sleep(1)
                except Exception as e:
                    print(f"      ⚠️  输入分享文案失败: {e}")
        except:
            pass

        # 查找"立即分享"按钮（基于用户提供的HTML结构）
        print(f"      🔍 查找立即分享按钮...")
        share_submit_btn = None

        # 策略1: 查找包含 "立即分享" 文本的 span，向上找可点击容器
        try:
            share_text_selectors = [
                # 中文
                "//span[text()='立即分享']",
                "//span[contains(text(), '立即分享')]",
                "//span[text()='分享']",  # 可能只显示"分享"

                # 英文
                "//span[text()='Share now']",
                "//span[contains(text(), 'Share now')]",
                "//span[text()='Share']",
            ]

            for selector in share_text_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            # 向上查找最外层容器（可能有多层 div）
                            try:
                                # 向上找到包含 role="none" 的父容器
                                clickable = elem.find_element(By.XPATH, './ancestor::div[@role="none"][1]')
                                if clickable:
                                    share_submit_btn = clickable
                                    print(f"      ✓ 找到立即分享按钮（role=none容器）")
                                    break
                            except:
                                # 如果找不到 role="none"，向上找任意可点击的 div
                                try:
                                    clickable = elem.find_element(By.XPATH, './ancestor::div[contains(@class, "x1ja2u2z")][1]')
                                    if clickable:
                                        share_submit_btn = clickable
                                        print(f"      ✓ 找到立即分享按钮（class容器）")
                                        break
                                except:
                                    pass

                    if share_submit_btn:
                        break
                except:
                    continue
        except:
            pass

        # 策略2: 查找覆盖层（data-visualcompletion="ignore"），向上找父容器
        if not share_submit_btn:
            try:
                overlays = driver.find_elements(By.CSS_SELECTOR, 'div[data-visualcompletion="ignore"][role="none"]')
                if overlays:
                    # 从后往前找最新的
                    for overlay in reversed(overlays):
                        try:
                            if overlay.is_displayed():
                                parent = overlay.find_element(By.XPATH, '..')
                                # 检查父元素是否包含 "立即分享" 文字
                                parent_text = parent.text or ''
                                if '立即分享' in parent_text or 'Share now' in parent_text or 'Share' in parent_text:
                                    share_submit_btn = parent
                                    print(f"      ✓ 找到立即分享按钮（覆盖层父元素）")
                                    break
                        except:
                            continue
            except:
                pass

        if share_submit_btn:
            # 点击立即分享按钮
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", share_submit_btn)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", share_submit_btn)
            print("      ✅ 分享成功")
            logging.info("分享成功")
            time.sleep(2)
            return True
        else:
            print("      ⚠️  未找到立即分享按钮")

            # 调试：打印所有可见的按钮文本
            try:
                print("      🔧 调试：打印所有可见的 span 元素...")
                all_spans = driver.find_elements(By.TAG_NAME, 'span')
                visible_texts = []
                for span in all_spans:
                    try:
                        if span.is_displayed():
                            text = span.text.strip()
                            if text and text not in visible_texts:
                                visible_texts.append(text)
                    except:
                        pass

                for i, text in enumerate(visible_texts[:15], 1):
                    print(f"      - {i}. {text}")
            except:
                pass

            print("      ⚠️  取消操作，关闭弹窗...")
            # 按 ESC 关闭
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(1)
            return False

    except Exception as e:
        print(f"      ❌ 分享失败: {e}")
        logging.error(f"分享异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def smart_browse_and_interact(
    driver,
    max_posts=10,
    interaction_rate=0.3,
    enable_like=True,
    enable_comment=True,
    enable_share=False,
    comment_templates=None,
    share_templates=None
):
    """智能浏览和互动 - 确保模式

    Args:
        driver: WebDriver 实例
        max_posts: 默认浏览多少条帖子（默认10条）
        interaction_rate: 额外互动概率（达成目标后的额外互动概率，暂未使用）
        enable_like: 是否启用点赞（True则确保至少成功1次）
        enable_comment: 是否启用评论（True则确保至少成功1次）
        enable_share: 是否启用分享（True则确保至少成功1次）
        comment_templates: 评论模板列表（None则使用默认）
        share_templates: 分享模板列表（None则使用默认）

    新逻辑：
        - 如果 enable_like=True，确保至少成功点赞1次
        - 如果 enable_comment=True，确保至少成功评论1次
        - 如果 enable_share=True，确保至少成功分享1次
        - 最多尝试 max_posts*3 条帖子（避免无限循环）
    """
    print("\n🤖 开始智能浏览模式（确保模式）...")
    print(f"   - 默认浏览 {max_posts} 条帖子")
    print(f"   - 点赞: {'启用（确保≥1次）' if enable_like else '禁用'}")
    print(f"   - 评论: {'启用（确保≥1次）' if enable_comment else '禁用'}")
    print(f"   - 分享: {'启用（确保≥1次）' if enable_share else '禁用'}")

    # 使用默认模板（如果未提供）
    if comment_templates is None:
        comment_templates = [
            # Thoughtful agreement and appreciation
            "This is exactly what I needed to hear today. Thank you so much for sharing your perspective!",
            "I couldn't agree more with this. You've articulated something I've been thinking about for a while.",
            "Wow, this really resonates with me on so many levels. Thanks for putting it into words!",
            "Absolutely love this take. It's refreshing to see someone speaking so honestly about this topic.",
            "This is such an important message. I really appreciate you taking the time to share this.",
            "You've hit the nail on the head with this one. Couldn't have said it better myself!",
            "This is incredibly well said. I've been feeling the same way but couldn't express it as clearly.",
            "Such a powerful message. Thank you for bringing attention to this important topic!",

            # Personal connection and empathy
            "I can totally relate to this. It's nice to know I'm not the only one who feels this way.",
            "This really speaks to my experience. Thanks for making me feel less alone in this!",
            "Feeling this so much right now. It's like you read my mind with this post.",
            "This hits different. I've been going through something similar and this gives me hope.",
            "Your words really touched my heart. Thank you for being so genuine and vulnerable.",
            "I needed to see this today. It's crazy how timing works sometimes!",
            "This is so relatable it hurts. Thanks for putting yourself out there like this.",

            # Encouragement and support
            "Keep doing what you're doing! The world needs more content like this.",
            "This is amazing work. I can't wait to see what you share next!",
            "You're making such a positive impact with posts like this. Keep it up!",
            "This deserves so much more attention. Thank you for your consistent quality content!",
            "I always look forward to your posts. You never disappoint!",
            "Your perspective is always so refreshing. Thanks for being authentic!",
            "This is why I follow you. Always bringing value and positivity!",

            # Engagement and curiosity
            "This is fascinating! Would love to hear more about your thoughts on this.",
            "Really interesting perspective. I'd never thought about it this way before.",
            "This opened my eyes to something I hadn't considered. Thanks for the new perspective!",
            "I'm curious to learn more about this. Do you have any recommendations for further reading?",
            "This is such a thought-provoking post. You've given me a lot to think about!",
            "I love how you always bring unique insights to these topics. Keep sharing!",

            # Enthusiastic reactions
            "This is absolutely brilliant! One of the best posts I've seen in a while.",
            "I'm obsessed with this content! It's exactly what my feed needed right now.",
            "This is pure gold! Saving this for future reference.",
            "Mind. Blown. This completely changed my perspective on the topic.",
            "I can't stop thinking about this post. It's that good!",
            "This is the kind of content that makes social media worthwhile!",

            # Learning and growth
            "I learned so much from this post. Thank you for taking the time to educate us!",
            "This is incredibly informative. I appreciate you breaking it down so clearly.",
            "Thanks for sharing your knowledge on this. It's been really helpful!",
            "I've bookmarked this to come back to later. So much valuable information here!",
            "Your expertise really shines through in posts like this. Thank you for sharing!",

            # Humor and lightness
            "This made me laugh out loud! Thanks for brightening my day.",
            "I felt this in my soul 😂 Too real!",
            "This is hilariously accurate. You nailed it!",
            "I wasn't ready for how funny this would be. Thanks for the laughs!",

            # Simple but meaningful
            "Love this so much! 💯",
            "This is everything! Thank you for sharing.",
            "Absolutely beautiful. No notes.",
            "Perfect timing for this message. Thank you!",
            "This deserves all the love it's getting!",
        ]

    if share_templates is None:
        share_templates = [
            # Inspirational sharing
            "This is too good not to share! Everyone needs to see this message.",
            "Sharing this because I think everyone in my circle could benefit from reading it.",
            "This post really hit home for me. Had to share it with all of you!",
            "I rarely share posts, but this one is absolutely worth spreading. Check it out!",
            "This deserves to be seen by more people. Such an important message!",
            "Passing this along because it's exactly what we all need to hear right now.",
            "Couldn't keep this to myself. This is gold and everyone should read it!",

            # Enthusiastic recommendations
            "This is one of the best things I've seen on here in ages. Must read!",
            "Wow, just wow. Everyone needs to read this. Sharing immediately!",
            "This is the kind of content that makes the internet a better place. Sharing widely!",
            "I've read this three times already and I'm still not over it. You all need to see this!",
            "Stop scrolling and read this. It's that important. Sharing for visibility!",

            # Personal endorsement
            "I stand behind this message 100%. That's why I'm sharing it with all of you.",
            "This perfectly captures what I've been trying to say. Sharing because it's spot on!",
            "I wish I could articulate things this well. Sharing this brilliant perspective!",
            "This resonates with me on every level. Had to share it with my network!",
            "Everything about this is correct. Sharing because people need to hear this!",

            # Educational and informative
            "This is incredibly informative and well-researched. Sharing for those who want to learn more!",
            "I learned so much from this post. Sharing in case others find it helpful too!",
            "Great insights here that everyone should know about. Sharing for educational purposes!",
            "This breaks down a complex topic really well. Sharing for anyone interested!",

            # Community building
            "Sharing this with my community because I think it will spark important conversations!",
            "This is relevant to so many people I know. Sharing in hopes it helps someone!",
            "Passing this along to my network. I think a lot of you will appreciate this!",
            "This is worth a share. I know several people who need to see this message!",

            # Simple but impactful
            "Too good not to share. Read this!",
            "Everyone needs to see this. Sharing now!",
            "This is important. Please read and share!",
            "Sharing this masterpiece with the world!",
            "This needs more attention. Spreading the word!",
            "Must share. This is everything!",
        ]

    browsed_count = 0
    interacted_count = 0
    interacted_post_ids = set()  # 记录已互动的帖子ID（从URL提取）

    # 成功计数器
    success_count = {
        'like': 0,
        'comment': 0,
        'share': 0,
    }

    # 目标：每个启用的操作至少成功1次
    targets = {
        'like': 1 if enable_like else 0,
        'comment': 1 if enable_comment else 0,
        'share': 1 if enable_share else 0,
    }

    max_attempts = max_posts * 3  # 最多尝试次数（避免无限循环）
    i = 0

    while i < max_attempts:
        i += 1

        # 检查是否达成所有目标
        all_targets_met = all(
            success_count[action] >= targets[action]
            for action in ['like', 'comment', 'share']
        )

        # 如果已达成所有目标且浏览数达到默认值，退出
        if all_targets_met and browsed_count >= max_posts:
            print(f"\n✅ 已达成所有目标！")
            print(f"   - 点赞成功: {success_count['like']} 次")
            print(f"   - 评论成功: {success_count['comment']} 次")
            print(f"   - 分享成功: {success_count['share']} 次")
            break

        try:
            # 检查当前页面状态
            current_url = driver.current_url
            if 'data:' in current_url or 'about:blank' in current_url or 'facebook.com' not in current_url:
                print(f"\n   ⚠️  检测到页面异常: {current_url}")
                print(f"   🔄 返回首页...")
                driver.get('https://www.facebook.com')
                time.sleep(3)

            # 随机滚动
            scroll_times = random.randint(1, 3)
            for _ in range(scroll_times):
                random_scroll(driver)

            # 模拟阅读
            simulate_reading(2, 5)

            # 查找帖子（Facebook 使用 div[role="article"]）
            posts = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')

            if not posts or len(posts) < 2:
                print("   ⚠️  未找到足够的帖子，继续滚动...")
                driver.execute_script("window.scrollBy(0, 1200);")  # 强制向下滚动
                time.sleep(2)
                continue

            print(f"   ✅ 找到 {len(posts)} 个帖子")

            # 从中间靠后的位置选择帖子（避免重复选前几个）
            start_idx = min(3, len(posts) - 5)
            end_idx = min(start_idx + 5, len(posts))
            candidate_posts = posts[start_idx:end_idx]

            # 随机选择一个帖子（不在列表页过滤，等进入详情页后用URL去重）
            current_post = random.choice(candidate_posts)
            browsed_count += 1
            print(f"\n📄 浏览第 {browsed_count} 条帖子...")

            # 滚动到该帖子
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", current_post)
            simulate_reading(3, 7)

            # 智能决定互动操作（新逻辑）
            actions = []

            # 优先执行未达成目标的操作
            if enable_like and success_count['like'] < targets['like']:
                actions.append('like')

            if enable_comment and success_count['comment'] < targets['comment']:
                actions.append('comment')

            if enable_share and success_count['share'] < targets['share']:
                actions.append('share')

            # 如果没有任何操作可执行，跳过
            if not actions:
                # 如果还有未达成的目标，提示继续尝试
                if not all_targets_met:
                    print("   ⚠️  本条帖子未选择互动，继续寻找...")
                else:
                    print("   👀 目标已达成，只是浏览，不互动")
                continue

            # 显示选择的操作和目标进度
            print(f"   💬 决定互动: {', '.join(actions)}")
            progress = (f"      当前进度: 点赞{success_count['like']}/{targets['like']}, "
                       f"评论{success_count['comment']}/{targets['comment']}, "
                       f"分享{success_count['share']}/{targets['share']}")
            print(progress)

            # 新逻辑：不进详情页，直接在列表页操作
            # 先提取帖子ID（从帖子内的链接，不访问）
            post_id = None
            try:
                links = current_post.find_elements(By.TAG_NAME, 'a')
                for link in links:
                    href = link.get_attribute('href')
                    if href:
                        import re
                        # 尝试从链接中提取帖子ID
                        patterns = [
                            r'/posts/(\d+)',
                            r'/permalink/(\d+)',
                            r'fbid=(\d+)',
                            r'story_fbid=(\d+)',
                            r'/(\d{10,})',  # 至少10位数字
                        ]
                        for pattern in patterns:
                            match = re.search(pattern, href)
                            if match:
                                post_id = match.group(1)
                                break
                        if post_id:
                            break

                if not post_id:
                    # 使用帖子文本的hash作为备用ID
                    post_text = current_post.text[:100]
                    post_id = str(hash(post_text))

                # 检查是否已互动
                if post_id in interacted_post_ids:
                    print(f"      ⚠️  这条帖子已经互动过（ID: {post_id}），跳过")
                    continue

                interacted_post_ids.add(post_id)
                print(f"      📌 帖子ID: {post_id}")
            except Exception as e:
                print(f"      ⚠️  提取ID失败: {e}")
                # 即使提取ID失败，也继续尝试操作（不阻塞）

            # 在列表页直接执行所有操作
            if 'like' in actions:
                print("      💬 执行点赞...")
                if like_post(driver, current_post):
                    success_count['like'] += 1
                    interacted_count += 1
                    time.sleep(random.uniform(1, 2))

            if 'comment' in actions:
                print("      💬 执行评论...")
                if comment_post(driver, current_post, comment_templates):
                    success_count['comment'] += 1
                    interacted_count += 1
                    time.sleep(random.uniform(2, 3))

            if 'share' in actions:
                print("      💬 执行分享...")
                if share_post(driver, current_post, share_templates):
                    success_count['share'] += 1
                    interacted_count += 1
                    time.sleep(random.uniform(1, 2))


            # 随机暂停
            time.sleep(random.uniform(2, 5))

            # 每次循环后向下滚动一段距离，确保下次能看到新内容
            scroll_distance = random.randint(600, 1000)
            driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            time.sleep(random.uniform(1, 2))

        except Exception as e:
            print(f"   ❌ 处理帖子时出错: {e}")
            continue

    print("\n" + "="*60)
    print(f"📊 浏览完成！")
    print(f"   - 浏览了 {browsed_count} 条帖子")
    print(f"   - 总互动次数: {interacted_count} 次")
    print(f"   - 成功点赞: {success_count['like']} 次")
    print(f"   - 成功评论: {success_count['comment']} 次")
    print(f"   - 成功分享: {success_count['share']} 次")
    print("="*60)

    # 记录统计信息到日志
    summary = (f"浏览完成 - 浏览: {browsed_count}, 互动: {interacted_count}, "
               f"点赞: {success_count['like']}, 评论: {success_count['comment']}, "
               f"分享: {success_count['share']}")
    logging.info(summary)

def main():
    setup_logging()

    print("="*60)
    print("Facebook 智能自动化脚本 v1.0")
    print("="*60)
    logging.info("脚本启动")

    print("\n启动浏览器...")
    # 使用 Clash 代理（7897 端口）
    driver = create_driver(use_proxy=True)
    print("✅ 浏览器启动成功！")
    logging.info("浏览器启动成功")

    try:
        # 访问 Facebook 首页
        print("\n访问 Facebook 首页...")
        driver.get('https://www.facebook.com')
        time.sleep(3)

        # 检查登录状态
        if not check_login(driver):
            logging.warning("检测到未登录状态，等待用户登录")
            wait_for_login(driver)
            logging.info("用户登录完成")
        else:
            print("✅ 已登录")
            logging.info("已登录状态")

        # 选择测试模式
        print("\n" + "="*60)
        print("请选择测试行为:")
        print("1. 纯浏览（不互动）")
        print("2. 点赞测试")
        print("3. 评论测试")
        print("4. 分享测试")
        print("5. 发帖测试")
        print("0. 退出")
        print("="*60)

        choice = input("请输入选项 (0-5): ").strip()

        if choice == '1':
            # 纯浏览
            print("\n🔍 纯浏览模式（不互动）")
            logging.info("开始纯浏览测试")
            smart_browse_and_interact(
                driver,
                max_posts=5,
                interaction_rate=0.0,
                enable_like=False,
                enable_comment=False,
                enable_share=False
            )

        elif choice == '2':
            # 点赞测试
            print("\n👍 点赞测试模式（确保至少成功1次）")
            logging.info("开始点赞测试")
            smart_browse_and_interact(
                driver,
                max_posts=5,
                interaction_rate=0.3,
                enable_like=True,
                enable_comment=False,
                enable_share=False
            )

        elif choice == '3':
            # 评论测试
            print("\n💬 评论测试模式（确保至少成功1次）")
            logging.info("开始评论测试")
            smart_browse_and_interact(
                driver,
                max_posts=5,
                interaction_rate=0.3,
                enable_like=False,
                enable_comment=True,
                enable_share=False
            )

        elif choice == '4':
            # 分享测试
            print("\n🔄 分享测试模式（确保至少成功1次）")
            logging.info("开始分享测试")
            smart_browse_and_interact(
                driver,
                max_posts=5,
                interaction_rate=0.3,
                enable_like=False,
                enable_comment=False,
                enable_share=True
            )

        elif choice == '5':
            # 发帖测试
            print("\n📝 发帖测试模式")
            logging.info("开始发帖测试")

            # 发帖内容模板
            post_templates = [
                "Just finished an amazing workout session! Feeling energized and ready to take on the day! 💪",
                "Grateful for all the wonderful people in my life. Sometimes it's the little things that matter most. ❤️",
                "Beautiful sunset today! Nature never fails to amaze me. 🌅",
                "Coffee and good vibes - that's all I need to start the day right! ☕",
                "Excited to share that I've reached a personal milestone today. Hard work really does pay off! 🎉",
                "Taking time to appreciate the present moment. Life moves fast, so it's important to slow down sometimes. 🧘",
                "Just discovered a new favorite spot in the city. Can't wait to go back! 📍",
                "Finished reading an incredible book today. Highly recommend it to anyone looking for inspiration! 📚",
                "Sometimes you just need to step back and appreciate how far you've come. Proud of the progress! 🌟",
                "Weekend plans: relaxation and recharging. Self-care isn't selfish! 🛀",
            ]

            # 随机选择一条内容
            content = random.choice(post_templates)
            print(f"\n将要发布的内容：\n{content}\n")

            # 执行发帖
            if create_post(driver, content):
                print("\n✅ 发帖测试成功！")

                # 发帖后浏览3条帖子
                print("\n📱 发帖完成，开始浏览帖子...")
                logging.info("发帖成功，开始浏览")
                smart_browse_and_interact(
                    driver,
                    max_posts=3,
                    interaction_rate=0.0,
                    enable_like=False,
                    enable_comment=False,
                    enable_share=False
                )
            else:
                print("\n❌ 发帖测试失败")

        elif choice == '0':
            print("\n👋 退出程序")
            logging.info("用户主动退出程序")

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        logging.warning("用户中断程序（Ctrl+C）")

    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        logging.error(f"程序异常: {e}")
        import traceback
        traceback.print_exc()

    finally:
        input("\n按回车关闭浏览器...")
        driver.quit()
        print("✅ 浏览器已关闭")
        logging.info("浏览器已关闭，程序结束")
        logging.info("="*60 + "\n")

if __name__ == "__main__":
    main()
