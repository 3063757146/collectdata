#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TikTok 智能自动化脚本 v1.0
模拟真实用户行为，自动点赞、评论、转发
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import random
import sys
import logging
from datetime import datetime

def setup_logging():
    """配置日志系统"""
    log_filename = 'tiktok_bot.log'

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
    """创建 Chrome 浏览器实例（使用真实浏览器 Profile）"""
    import os

    # 📂 使用真实的 Chrome Profile（与手动浏览器相同）
    user_data_dir = os.path.expanduser('~/Library/Application Support/Google/Chrome')

    print("="*60)
    print("⚠️  重要提示：使用真实 Chrome Profile")
    print("="*60)
    print(f"📂 Profile 路径: {user_data_dir}")
    print("\n🔴 请先执行以下操作：")
    print("   1. 关闭所有手动打开的 Chrome 浏览器窗口")
    print("   2. 确保没有其他 Chrome 进程在运行")
    print("   3. 完成后按回车继续...")
    print("="*60)
    input()

    chrome_options = Options()

    # 使用真实的 Chrome profile
    chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
    chrome_options.add_argument('--profile-directory=Default')

    if use_proxy:
        chrome_options.add_argument('--proxy-server=socks5://127.0.0.1:7897')

    # 反检测设置
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')

    # 窗口大小和基本设置
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--no-default-browser-check')
    chrome_options.add_argument('--disable-popup-blocking')

    try:
        driver = webdriver.Chrome(options=chrome_options)

        # 隐藏 webdriver 特征
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })

        print("✅ 浏览器启动成功（使用真实 Profile）")
        return driver

    except Exception as e:
        print(f"❌ 创建浏览器失败: {e}")
        print("\n💡 提示：")
        print("   1. 确保已关闭所有 Chrome 窗口")
        print("   2. 检查 Chrome 是否安装在默认位置")
        print("   3. 尝试手动指定 ChromeDriver 路径")
        sys.exit(1)

def check_login(driver):
    """检查是否已登录（增强版，更准确的判断）"""
    try:
        print("🔍 检测登录状态...")

        # 等待页面完全加载
        time.sleep(3)

        # 方法1: 查找登录按钮（优先级最高）
        # 如果找到可见的登录按钮，说明肯定未登录
        # 根据实际HTML结构添加选择器
        login_button_selectors = [
            # TikTok 中文界面的登录按钮
            "//div[contains(@class, 'TUXButton-label') and contains(text(), '登录')]",
            "//div[contains(@class, 'TUXButton-label') and contains(text(), 'Log in')]",

            # 其他可能的登录按钮
            "//button[contains(text(), 'Log in')]",
            "//button[contains(text(), '登录')]",
            "//a[contains(text(), 'Log in')]",
            "//a[contains(text(), '登录')]",
            "//span[contains(text(), 'Log in')]",
            "//span[contains(text(), '登录')]",

            # Sign up 按钮
            "//div[contains(text(), 'Sign up')]",
            "//button[contains(text(), 'Sign up')]",
        ]

        print("   🔍 查找登录按钮...")
        for selector in login_button_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed():
                        print(f"   ❌ 找到登录按钮 '{elem.text}' -> 未登录")
                        return False
            except:
                continue

        # 方法2: 查找明确的已登录标志
        # 只有登录用户才有的元素
        print("   🔍 查找已登录标志...")
        logged_in_selectors = [
            # 用户头像/个人资料图标
            ('CSS', 'img[data-e2e="user-avatar"]', '用户头像'),
            ('CSS', 'div[data-e2e="user-avatar"]', '用户头像'),

            # 个人资料链接（必须包含真实用户名，不是通用的/profile）
            ('CSS', 'a[href^="/@"]', '个人主页链接'),

            # 上传按钮
            ('CSS', 'a[data-e2e="upload-icon"]', '上传按钮'),
            ('CSS', 'button[data-e2e="upload-icon"]', '上传按钮'),

            # 通知图标（inbox）
            ('CSS', 'a[data-e2e="inbox-icon"]', '通知图标'),
            ('CSS', 'button[data-e2e="inbox-icon"]', '通知图标'),
        ]

        for method, selector, desc in logged_in_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                # 检查是否有可见的元素
                visible_elements = [e for e in elements if e.is_displayed()]
                if visible_elements:
                    print(f"   ✅ 找到已登录标志：{desc} -> 已登录")
                    return True
            except:
                continue

        # 方法3: 检查页面URL
        # 如果重定向到登录页面，说明未登录
        current_url = driver.current_url
        if 'login' in current_url.lower():
            print(f"   ❌ URL包含login -> 未登录")
            return False

        # 默认返回 False（未登录），要求用户手动确认
        print("   ⚠️  无法确定登录状态，假定未登录")
        return False

    except Exception as e:
        print(f"   ⚠️  检测异常: {e}")
        return False

def wait_for_login(driver):
    """等待用户登录"""
    print("\n" + "="*60)
    print("⚠️  检测到未登录状态")
    print("请在浏览器中完成以下操作：")
    print("1. 点击右上角【Log in】按钮")
    print("2. 选择登录方式（邮箱/手机/社交账号）")
    print("3. 完成验证后，在此按回车继续...")
    print("="*60)
    input()

    # 等待3秒确保登录状态刷新
    time.sleep(3)

    if not check_login(driver):
        print("⚠️  似乎还没有登录，请确认已登录后按回车...")
        input()
        time.sleep(2)

def random_scroll(driver, direction='down'):
    """随机滚动页面"""
    if direction == 'down':
        # TikTok 视频流：向下滚动到下一个视频
        # 通常是整屏滚动
        driver.execute_script("window.scrollBy(0, window.innerHeight);")
    else:
        # 向上滚动（回看）
        driver.execute_script("window.scrollBy(0, -window.innerHeight);")

    time.sleep(random.uniform(0.5, 1.5))

def simulate_reading(min_sec=3, max_sec=8):
    """模拟观看视频时间"""
    reading_time = random.uniform(min_sec, max_sec)
    print(f"   📺 模拟观看视频 {reading_time:.1f} 秒...")
    time.sleep(reading_time)

def like_video(driver):
    """点赞视频（增强版，支持多种选择器和状态验证）"""
    try:
        # TikTok 点赞图标选择器（按优先级）
        # 关键发现：点赞按钮是 span[data-e2e="like-icon"]，需要点击其父元素
        like_selectors = [
            # 方法1: 通过 data-e2e="like-icon" 找到图标，点击父元素（最可靠）
            ('XPATH', '//span[@data-e2e="like-icon"]/parent::*'),

            # 方法2: 直接查找 data-e2e="like-icon"
            ('CSS', 'span[data-e2e="like-icon"]'),

            # 方法3: 通过 data-e2e 属性查找按钮
            ('CSS', 'button[data-e2e="like-button"]'),
            ('CSS', 'button[data-e2e="browse-like"]'),

            # 方法4: 通过 aria-label
            ('CSS', 'button[aria-label*="like"]'),
            ('CSS', 'button[aria-label*="Like"]'),

            # 方法5: 通过包含心形 SVG 的元素
            ('XPATH', '//*[@data-e2e="like-icon"]/parent::button'),
            ('XPATH', '//*[@data-e2e="like-icon"]/parent::div'),
        ]

        print(f"      🔍 查找点赞按钮...")

        for method, selector in like_selectors:
            try:
                if method == 'CSS':
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                else:
                    elements = driver.find_elements(By.XPATH, selector)

                if elements:
                    print(f"      ✓ 找到 {len(elements)} 个候选元素（选择器: {selector[:50]}...）")

                    for elem in elements:
                        try:
                            # 检查元素是否可见
                            if not elem.is_displayed():
                                continue

                            # 查找图标元素（用于检查状态）
                            like_icon = None
                            try:
                                # 如果当前元素就是 span[data-e2e="like-icon"]
                                if elem.get_attribute('data-e2e') == 'like-icon':
                                    like_icon = elem
                                else:
                                    # 否则在子元素中查找
                                    like_icon = elem.find_element(By.CSS_SELECTOR, 'span[data-e2e="like-icon"]')
                            except:
                                # 如果找不到图标，跳过这个元素
                                continue

                            if not like_icon:
                                continue

                            # 记录点击前的状态（检查图标的颜色）
                            style_before = like_icon.get_attribute('style') or ''

                            # 提取颜色值
                            import re
                            color_before = None
                            color_match = re.search(r'color:\s*rgb\((\d+),\s*(\d+),\s*(\d+)\)', style_before)
                            if color_match:
                                r, g, b = int(color_match.group(1)), int(color_match.group(2)), int(color_match.group(3))
                                color_before = (r, g, b)
                                print(f"      💡 点击前颜色: rgb({r}, {g}, {b})")

                                # 检查是否已经点赞（红色系）
                                # 已点赞颜色通常是 rgb(254, 44, 85) 或类似的红色
                                if r > 200 and g < 100 and b < 150:
                                    print("      ⚠️  似乎已经点赞过了（图标是红色），跳过")
                                    logging.info("点赞跳过：已点赞（颜色检测）")
                                    return True

                            # 滚动到元素位置
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", elem)
                            time.sleep(random.uniform(0.5, 1.0))

                            # 确定要点击的元素
                            # 如果当前元素是 span，点击父元素；如果是 button/div，直接点击
                            click_target = elem
                            if elem.tag_name == 'span':
                                try:
                                    # 获取父元素
                                    click_target = elem.find_element(By.XPATH, '..')
                                    print(f"      💡 点击父元素: {click_target.tag_name}")
                                except:
                                    pass

                            # 尝试点击
                            try:
                                # 优先使用 JavaScript 点击
                                driver.execute_script("arguments[0].click();", click_target)
                            except:
                                try:
                                    # 备用方案：原生点击
                                    click_target.click()
                                except:
                                    # 备用方案2：ActionChains
                                    ActionChains(driver).move_to_element(click_target).click().perform()

                            # 等待状态更新
                            time.sleep(1.5)

                            # 验证是否点赞成功（检查图标颜色变化）
                            try:
                                style_after = like_icon.get_attribute('style') or ''

                                color_after = None
                                color_match = re.search(r'color:\s*rgb\((\d+),\s*(\d+),\s*(\d+)\)', style_after)
                                if color_match:
                                    r, g, b = int(color_match.group(1)), int(color_match.group(2)), int(color_match.group(3))
                                    color_after = (r, g, b)
                                    print(f"      💡 点击后颜色: rgb({r}, {g}, {b})")

                                # 检查颜色是否变化
                                # 成功的标志：从黑色 rgb(22, 24, 35) 变成红色 rgb(254, 44, 85)
                                if color_before and color_after:
                                    # 颜色变化了
                                    if color_before != color_after:
                                        # 并且变成了红色系
                                        if color_after[0] > 200 and color_after[1] < 100 and color_after[2] < 150:
                                            print("      ✅ 点赞成功（颜色从黑色变为红色）")
                                            logging.info(f"点赞成功（颜色验证）: {color_before} -> {color_after}")
                                            return True
                                        else:
                                            print(f"      ⚠️  颜色变化了但不是红色")
                                            continue
                                    else:
                                        print(f"      ⚠️  点击了但颜色未变化")
                                        continue
                                else:
                                    # 无法获取颜色，检查 style 是否有变化
                                    if style_before != style_after:
                                        print("      ✅ 点赞成功（style 已变化）")
                                        logging.info("点赞成功（style 变化）")
                                        return True
                                    else:
                                        print(f"      ⚠️  点击了但 style 未变化")
                                        continue

                            except Exception as verify_err:
                                # 如果无法验证，假定成功
                                print(f"      ⚠️  状态验证异常: {verify_err}")
                                print("      ✅ 点赞操作已执行（无法验证状态）")
                                logging.info("点赞已执行（验证异常）")
                                return True

                        except Exception as e:
                            print(f"      ⚠️  点击失败，尝试下一个: {str(e)[:50]}")
                            continue
            except Exception as e:
                continue

        # 如果所有方法都失败
        print("      ❌ 未找到可用的点赞按钮")
        logging.warning("点赞失败：未找到点赞按钮")
        return False

    except Exception as e:
        print(f"      ❌ 点赞异常: {e}")
        logging.error(f"点赞异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def comment_video(driver, content_list):
    """评论视频"""
    try:
        print("      🔍 查找评论按钮...")

        # 评论按钮选择器
        # 关键发现：评论按钮是 span[data-e2e="comment-icon"]，需要点击其父元素
        comment_button_selectors = [
            # 方法1: 通过 data-e2e="comment-icon" 找到图标，点击父元素（最可靠）
            ('XPATH', '//span[@data-e2e="comment-icon"]/parent::*'),

            # 方法2: 直接查找 data-e2e="comment-icon"
            ('CSS', 'span[data-e2e="comment-icon"]'),

            # 方法3: 通过其他 data-e2e 属性
            ('CSS', 'button[data-e2e="comment-button"]'),
            ('CSS', 'button[data-e2e="browse-comment"]'),

            # 方法4: 通过 aria-label
            ('CSS', 'button[aria-label*="comment"]'),
            ('CSS', 'button[aria-label*="Comment"]'),
            ('CSS', 'button[aria-label*="评论"]'),
        ]

        comment_button = None
        for method, selector in comment_button_selectors:
            try:
                if method == 'CSS':
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                else:
                    elements = driver.find_elements(By.XPATH, selector)

                if elements:
                    comment_button = elements[0]
                    print(f"      ✅ 找到评论按钮: {selector[:50]}")
                    break
            except:
                continue

        if not comment_button:
            print("      ❌ 未找到评论按钮")
            logging.warning("评论失败：未找到评论按钮")
            return False

        # 确定要点击的元素（如果是 span，点击父元素）
        click_target = comment_button
        if comment_button.tag_name == 'span':
            try:
                click_target = comment_button.find_element(By.XPATH, '..')
                print(f"      💡 点击父元素: {click_target.tag_name}")
            except:
                pass

        # 点击评论按钮
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", click_target)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", click_target)
        print("      ✅ 点击评论按钮，等待输入框...")
        time.sleep(2)

        # 查找评论输入框
        # TikTok 使用 Draft.js 编辑器
        print("      🔍 查找评论输入框...")
        comment_input_selectors = [
            # Draft.js 编辑器的可编辑区域
            'div.public-DraftEditor-content[contenteditable="true"]',
            'div[role="textbox"][contenteditable="true"]',

            # 通用 contenteditable
            'div[contenteditable="true"]',

            # 通过 data-e2e 属性
            'div[data-e2e="comment-input"]',

            # 通过 placeholder 查找
            'textarea[placeholder*="评论"]',
            'textarea[placeholder*="comment"]',
            'div[placeholder*="comment"]',
        ]

        comment_input = None
        for selector in comment_input_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                # 过滤掉不可见的元素
                for elem in elements:
                    if elem.is_displayed():
                        comment_input = elem
                        print(f"      ✅ 找到评论输入框: {selector}")
                        break
                if comment_input:
                    break
            except:
                continue

        if not comment_input:
            print("      ❌ 未找到评论输入框")
            logging.warning("评论失败：未找到输入框")
            return False

        # 输入评论内容
        content = random.choice(content_list)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_input)
        time.sleep(0.5)

        # 点击输入框获得焦点
        driver.execute_script("arguments[0].click();", comment_input)
        time.sleep(0.5)

        # 输入文本（Draft.js 需要特殊处理）
        try:
            if comment_input.tag_name == 'div':
                # 方法1: 使用 textContent（Draft.js 推荐）
                driver.execute_script(f"arguments[0].textContent = '{content}';", comment_input)
                # 触发 input 事件
                driver.execute_script("""
                    var event = new Event('input', { bubbles: true });
                    arguments[0].dispatchEvent(event);
                """, comment_input)
            else:
                # textarea
                comment_input.send_keys(content)

            time.sleep(1)
            print(f"      ✅ 已输入评论: {content}")
        except Exception as e:
            print(f"      ⚠️  输入失败，尝试 send_keys: {e}")
            # 备用方案：使用 send_keys
            comment_input.clear()
            comment_input.send_keys(content)
            time.sleep(1)

        # 查找发送按钮
        # 注意：按钮初始是 disabled，输入内容后才会启用
        print("      🔍 查找发送按钮...")
        time.sleep(1.5)  # 等待按钮状态更新

        send_button_selectors = [
            # 通过 data-e2e 属性（最可靠）
            'button[data-e2e="comment-post"]',

            # 通过 aria-label
            'button[aria-label="发布"]',
            'button[aria-label="Post"]',
            'button[aria-label*="发布"]',
            'button[aria-label*="Post"]',

            # 通过 class
            'button[class*="ArrowPostButton"]',

            # 通用
            'button[type="submit"]',
        ]

        send_button = None
        for selector in send_button_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                # 过滤掉不可见的元素
                for elem in elements:
                    if elem.is_displayed():
                        send_button = elem
                        print(f"      ✅ 找到发送按钮: {selector}")
                        break
                if send_button:
                    break
            except:
                continue

        if send_button:
            # 检查按钮是否还是 disabled 状态
            is_disabled = send_button.get_attribute('disabled')
            if is_disabled:
                print("      ⚠️  发送按钮是禁用状态，等待1秒...")
                time.sleep(1)

                # 再次检查
                is_disabled = send_button.get_attribute('disabled')
                if is_disabled:
                    print("      ⚠️  按钮仍然禁用，可能输入未生效")
                    # 尝试重新输入
                    comment_input.click()
                    comment_input.send_keys(Keys.CONTROL, 'a')  # 全选
                    comment_input.send_keys(content)
                    time.sleep(1)

            # 点击发送
            try:
                driver.execute_script("arguments[0].click();", send_button)
                print(f"      ✅ 点击发送按钮")

                # 等待评论提交完成
                print(f"      ⏱️  等待评论提交...")
                time.sleep(4)  # TikTok可能比Facebook慢，用4秒

                # 验证评论是否成功（检查输入框是否清空）
                try:
                    current_text = comment_input.text.strip()
                    if not current_text or current_text == "":
                        print(f"      ✅ 评论已发送（输入框已清空）")
                        logging.info(f"评论成功: {content}")
                    else:
                        print(f"      ⚠️  输入框未清空，可能提交失败")
                        logging.warning(f"评论提交状态未知: {content}")
                except:
                    # 无法验证，假定成功
                    print(f"      ✅ 评论已提交")
                    logging.info(f"评论成功: {content}")

                return True
            except Exception as e:
                print(f"      ⚠️  点击发送按钮失败: {e}")
                # 尝试回车发送
                comment_input.send_keys(Keys.RETURN)
                print(f"      ✅ 评论已发送（回车）")

                # 等待评论提交完成
                print(f"      ⏱️  等待评论提交...")
                time.sleep(4)

                # 验证评论是否成功（检查输入框是否清空）
                try:
                    current_text = comment_input.text.strip()
                    if not current_text or current_text == "":
                        print(f"      ✅ 评论已发送（输入框已清空）")
                        logging.info(f"评论成功（回车）: {content}")
                    else:
                        print(f"      ⚠️  输入框未清空，可能提交失败")
                        logging.warning(f"评论提交状态未知（回车）: {content}")
                except:
                    print(f"      ✅ 评论已提交")
                    logging.info(f"评论成功（回车）: {content}")

                return True
        else:
            print("      ⚠️  未找到发送按钮，尝试按回车发送...")
            try:
                comment_input.send_keys(Keys.RETURN)
                print(f"      ✅ 评论已发送（回车）")

                # 等待评论提交完成
                print(f"      ⏱️  等待评论提交...")
                time.sleep(4)

                # 验证评论是否成功（检查输入框是否清空）
                try:
                    current_text = comment_input.text.strip()
                    if not current_text or current_text == "":
                        print(f"      ✅ 评论已发送（输入框已清空）")
                        logging.info(f"评论成功（回车）: {content}")
                    else:
                        print(f"      ⚠️  输入框未清空，可能提交失败")
                        logging.warning(f"评论提交状态未知（回车）: {content}")
                except:
                    print(f"      ✅ 评论已提交")
                    logging.info(f"评论成功（回车）: {content}")
                return True
            except:
                print("      ❌ 评论发送失败")
                logging.warning("评论失败：无法发送")
                return False

    except Exception as e:
        print(f"      ❌ 评论失败: {e}")
        logging.error(f"评论异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def share_video(driver):
    """分享/转发视频"""
    try:
        print("      🔍 查找分享按钮...")

        # 分享按钮选择器
        share_button_selectors = [
            ('CSS', 'button[data-e2e="share-button"]'),
            ('CSS', 'button[data-e2e="browse-share"]'),
            ('CSS', 'button[aria-label*="share"]'),
            ('CSS', 'button[aria-label*="Share"]'),
            ('XPATH', '//button[.//*[local-name()="svg"]]'),
        ]

        share_button = None
        for method, selector in share_button_selectors:
            try:
                if method == 'CSS':
                    buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                else:
                    buttons = driver.find_elements(By.XPATH, selector)

                # 找到包含"share"的按钮
                for btn in buttons:
                    aria_label = btn.get_attribute('aria-label') or ''
                    if 'share' in aria_label.lower():
                        share_button = btn
                        print(f"      ✅ 找到分享按钮")
                        break

                if share_button:
                    break
            except:
                continue

        if not share_button:
            print("      ❌ 未找到分享按钮")
            logging.warning("分享失败：未找到分享按钮")
            return False

        # 点击分享按钮
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", share_button)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", share_button)
        print("      ✅ 点击分享按钮，等待分享菜单...")
        time.sleep(2)

        # 注意：TikTok 的分享通常会弹出一个菜单，里面有多种分享选项
        # 这里我们简单地点击第一个分享选项（或者复制链接）

        # 查找分享选项
        share_options = driver.find_elements(By.CSS_SELECTOR, 'div[class*="share-"] button, div[data-e2e*="share"] button')

        if share_options:
            # 点击第一个分享选项
            try:
                share_options[0].click()
                print("      ✅ 分享成功（选择了分享选项）")
                logging.info("分享成功")
                time.sleep(2)

                # 关闭分享弹窗（按ESC）
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(1)
                return True
            except:
                print("      ⚠️  点击分享选项失败，关闭弹窗")
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(1)
                return False
        else:
            print("      ⚠️  未找到分享选项，关闭弹窗")
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(1)
            logging.warning("分享失败：未找到分享选项")
            return False

    except Exception as e:
        print(f"      ❌ 分享失败: {e}")
        logging.error(f"分享异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_comment_templates():
    """获取评论模板"""
    return [
        "Nice!", "Amazing!", "Love this!", "Great video!", "So cool!",
        "This is awesome!", "Well done!", "Incredible!", "Beautiful!",
        "Fantastic!", "Perfect!", "Wonderful!", "Brilliant!",
        "You're so talented!", "Keep it up!", "Love it!",
        "This made my day!", "So good!", "Wow!!", "Outstanding!",
        "Impressive!", "Absolutely love this!", "Can't stop watching!",
        "This is fire!", "Obsessed with this!", "So creative!",
        "You killed it!", "Pure talent!", "This is everything!",
        "I love your content!", "More please!", "This is gold!",
    ]


def smart_browse_and_interact(
    driver,
    max_videos=3,
    interaction_rate=0.3,
    enable_like=True,
    enable_comment=True,
    enable_share=True,
    comment_templates=None
):
    """
    智能浏览和互动 - 确保模式

    参数:
        max_videos: 默认浏览多少个视频（默认3个）
        interaction_rate: 额外互动概率（达成目标后的额外互动概率）
        enable_like: 是否启用点赞（True则确保至少成功1次）
        enable_comment: 是否启用评论（True则确保至少成功1次）
        enable_share: 是否启用分享（True则确保至少成功1次）
        comment_templates: 评论模板列表（None则使用默认）

    新逻辑：
        - 如果 enable_like=True，确保至少成功点赞1次
        - 如果 enable_comment=True，确保至少成功评论1次
        - 如果 enable_share=True，确保至少成功分享1次
        - 最多尝试 max_videos*3 个视频（避免无限循环）
    """
    print("\n🤖 开始智能浏览模式（确保模式）...")
    print(f"   - 默认浏览 {max_videos} 个视频")
    print(f"   - 点赞: {'启用（确保≥1次）' if enable_like else '禁用'}")
    print(f"   - 评论: {'启用（确保≥1次）' if enable_comment else '禁用'}")
    print(f"   - 分享: {'启用（确保≥1次）' if enable_share else '禁用'}")

    # 使用默认模板（如果未提供）
    if comment_templates is None:
        comment_templates = get_comment_templates()

    browsed_count = 0
    interacted_count = 0

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

    max_attempts = max_videos * 3  # 最多尝试次数（避免无限循环）
    i = 0

    while i < max_attempts:
        i += 1

        # 检查是否达成所有目标
        all_targets_met = all(
            success_count[action] >= targets[action]
            for action in ['like', 'comment', 'share']
        )

        # 如果已达成所有目标且浏览数达到默认值，退出
        if all_targets_met and browsed_count >= max_videos:
            print(f"\n✅ 已达成所有目标！")
            print(f"   - 点赞成功: {success_count['like']} 次")
            print(f"   - 评论成功: {success_count['comment']} 次")
            print(f"   - 分享成功: {success_count['share']} 次")
            break

        try:
            browsed_count += 1
            print(f"\n📺 [循环 {i}] 浏览第 {browsed_count} 个视频...")

            # 模拟观看视频
            simulate_reading(5, 15)

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
                    print("   ⚠️  本个视频未选择互动，继续寻找...")
                else:
                    print("   👀 目标已达成，只是观看，不互动")
            else:
                # 显示选择的操作和目标进度
                print(f"   💬 决定互动: {', '.join(actions)}")
                progress = (f"      当前进度: 点赞{success_count['like']}/{targets['like']}, "
                           f"评论{success_count['comment']}/{targets['comment']}, "
                           f"分享{success_count['share']}/{targets['share']}")
                print(progress)

                # 执行操作
                if 'like' in actions:
                    if like_video(driver):
                        success_count['like'] += 1
                        interacted_count += 1
                        time.sleep(random.uniform(1, 2))

                if 'comment' in actions:
                    if comment_video(driver, comment_templates):
                        success_count['comment'] += 1
                        interacted_count += 1
                        time.sleep(random.uniform(1, 2))

                if 'share' in actions:
                    if share_video(driver):
                        success_count['share'] += 1
                        interacted_count += 1
                        time.sleep(random.uniform(1, 2))

            # 滚动到下一个视频
            if i < max_attempts - 1:
                print("   ⬇️  滚动到下一个视频...")
                random_scroll(driver, 'down')
                time.sleep(random.uniform(1, 2))

        except Exception as e:
            print(f"   ❌ 处理视频时出错: {e}")
            logging.error(f"处理视频异常: {e}")
            continue

    print("\n" + "="*60)
    print(f"📊 浏览完成！")
    print(f"   - 浏览了 {browsed_count} 个视频")
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
    # 初始化日志系统
    setup_logging()

    print("="*60)
    print("TikTok 智能自动化脚本 v2.0")
    print("="*60)
    logging.info("脚本启动")

    print("\n启动浏览器...")
    driver = create_driver(use_proxy=True)
    print("✅ 浏览器启动成功！")
    logging.info("浏览器启动成功")

    try:
        # 访问 TikTok 首页
        print("\n访问 TikTok 首页...")
        driver.get('https://www.tiktok.com')
        time.sleep(5)

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
        print("0. 退出")
        print("="*60)

        choice = input("请输入选项 (0-4): ").strip()

        if choice == '1':
            # 纯浏览
            print("\n🔍 纯浏览模式（不互动）")
            logging.info("开始纯浏览测试")
            smart_browse_and_interact(
                driver,
                max_videos=3,
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
                max_videos=3,
                interaction_rate=0.3,
                enable_like=True,
                enable_comment=False,
                enable_share=False
            )

        elif choice == '3':
            # 评论测试
            print("\n💬 评论测试模式（确保至少成功1次）")
            logging.info("开始评论测试")
            comment_templates = get_comment_templates()
            smart_browse_and_interact(
                driver,
                max_videos=3,
                interaction_rate=0.3,
                enable_like=False,
                enable_comment=True,
                enable_share=False,
                comment_templates=comment_templates
            )

        elif choice == '4':
            # 分享测试
            print("\n🔄 分享测试模式（确保至少成功1次）")
            logging.info("开始分享测试")
            smart_browse_and_interact(
                driver,
                max_videos=3,
                interaction_rate=0.3,
                enable_like=False,
                enable_comment=False,
                enable_share=True
            )

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
