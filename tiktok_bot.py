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
from selenium_stealth import stealth
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
    """创建 Chrome 浏览器实例（保留登录状态）"""
    import os

    # 📂 设置用户数据目录（保存登录状态）
    user_data_dir = os.path.expanduser('~/selenium_profiles/tiktok')

    # 检查目录是否存在
    if not os.path.exists(user_data_dir):
        print(f"📁 创建配置文件目录: {user_data_dir}")
        os.makedirs(user_data_dir, exist_ok=True)
    else:
        print(f"💾 使用现有配置文件: {user_data_dir}")

    chrome_options = Options()

    chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
    chrome_options.add_argument('--profile-directory=Default')

    if use_proxy:
        chrome_options.add_argument('--proxy-server=socks5://127.0.0.1:10818')

    # 反检测设置
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')

    # ⚠️ 注意：使用配置文件时不要设置随机 User-Agent
    # 因为每次随机会导致浏览器指纹不一致，可能触发安全检测

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
    """随机滚动页面（使用键盘方向键切换视频）"""
    try:
        # TikTok 使用方向键切换视频（更可靠）
        from selenium.webdriver.common.keys import Keys

        # 找到 body 元素并发送按键
        body = driver.find_element(By.TAG_NAME, 'body')

        if direction == 'down':
            # 按下方向键向下（切换到下一个视频）
            body.send_keys(Keys.ARROW_DOWN)
            print(f"      ⬇️  按下向下键")
        else:
            # 按下方向键向上（回到上一个视频）
            body.send_keys(Keys.ARROW_UP)
            print(f"      ⬆️  按下向上键")

        # 等待视频切换
        time.sleep(random.uniform(1.0, 2.0))

    except Exception as e:
        print(f"      ⚠️  滚动失败: {e}")
        # 备用方案：使用鼠标滚轮
        try:
            driver.execute_script("window.scrollBy(0, window.innerHeight);")
            time.sleep(random.uniform(0.5, 1.5))
        except:
            pass

def simulate_reading(min_sec=3, max_sec=8):
    """模拟观看视频时间"""
    reading_time = random.uniform(min_sec, max_sec)
    print(f"   📺 模拟观看视频 {reading_time:.1f} 秒...")
    time.sleep(reading_time)

def like_video(driver):
    """点赞视频"""
    import re

    def _is_liked(icon_elem):
        try:
            style = icon_elem.get_attribute('style') or ''
            m = re.search(r'color:\s*rgb\((\d+),\s*(\d+),\s*(\d+)\)', style)
            if m:
                r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
                return r > 200 and g < 100 and b < 150
        except:
            pass
        return False

    try:
        print("      🔍 查找点赞按钮...")

        # 只取第一个可见的点赞图标，避免找到多个导致重复点击
        elements = driver.find_elements(By.CSS_SELECTOR, 'span[data-e2e="like-icon"]')
        visible = [e for e in elements if e.is_displayed()]
        if not visible:
            print("      ❌ 未找到点赞按钮")
            logging.warning("点赞失败：未找到点赞按钮")
            return False

        like_icon = visible[0]

        # 已点赞则跳过（防止重复执行时取消点赞）
        if _is_liked(like_icon):
            print("      ⚠️  已经点赞，跳过")
            logging.info("点赞跳过：已点赞")
            return True

        # 点击父按钮（span 本身不可点击）
        click_target = like_icon.find_element(By.XPATH, '..')
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", click_target)
        time.sleep(random.uniform(0.3, 0.8))

        # 只点击一次，不使用 fallback（多次点击会导致取消点赞）
        driver.execute_script("arguments[0].click();", click_target)
        print("      ✅ 点赞按钮已点击")

        time.sleep(1.5)

        if _is_liked(like_icon):
            print("      ✅ 点赞成功（颜色确认）")
            logging.info("点赞成功（颜色确认）")
        else:
            print("      ✅ 点赞已操作（假定成功）")
            logging.info("点赞已操作")

        return True

    except Exception as e:
        print(f"      ❌ 点赞失败: {e}")
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

        # 等待评论面板完全加载
        time.sleep(1.5)

        comment_input_selectors = [
            # Draft.js 编辑器的可编辑区域（优先使用role="textbox"）
            'div[role="textbox"][contenteditable="true"]',
            'div.public-DraftEditor-content[contenteditable="true"]',

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
                # 过滤掉不可见的元素，并检查父元素是否在评论区域
                for elem in elements:
                    try:
                        if elem.is_displayed():
                            # 检查元素高度，确保它是真实的输入框而不是隐藏元素
                            rect = elem.rect
                            if rect['height'] > 10 and rect['width'] > 100:
                                comment_input = elem
                                print(f"      ✅ 找到评论输入框: {selector}")
                                break
                    except:
                        continue
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

        # 滚动到输入框位置
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_input)
        time.sleep(0.8)

        # 使用 ActionChains 点击输入框（避免被placeholder拦截）
        print(f"      📝 准备输入评论: {content}")
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(driver)

            # 移动到元素并点击
            actions.move_to_element(comment_input).click().perform()
            time.sleep(0.5)

            # 使用 ActionChains 模拟真实输入（Draft.js推荐方式）
            # 逐字符输入，触发所有必要的事件
            actions.send_keys(content).perform()

            time.sleep(1.5)
            print(f"      ✅ 已输入评论: {content}")

        except Exception as e:
            print(f"      ⚠️  ActionChains输入失败，尝试JavaScript方式: {e}")

            # 备用方案1: 使用JavaScript直接focus并输入
            try:
                driver.execute_script("arguments[0].focus();", comment_input)
                time.sleep(0.3)

                # 使用send_keys输入
                comment_input.send_keys(content)
                time.sleep(1.5)
                print(f"      ✅ 已输入评论（备用方式）: {content}")

            except Exception as e2:
                print(f"      ❌ 输入失败: {e2}")
                return False

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
                print("      ⚠️  发送按钮是禁用状态，等待2秒...")
                time.sleep(2)

                # 再次检查
                is_disabled = send_button.get_attribute('disabled')
                if is_disabled:
                    print("      ⚠️  按钮仍然禁用，尝试重新触发输入事件")

                    # 使用ActionChains再次点击并输入
                    try:
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(driver)

                        # 清空并重新输入
                        actions.move_to_element(comment_input).click().perform()
                        time.sleep(0.3)

                        # 全选并删除
                        actions.key_down(Keys.COMMAND if driver.capabilities['platformName'].lower() == 'mac' else Keys.CONTROL).send_keys('a').key_up(Keys.COMMAND if driver.capabilities['platformName'].lower() == 'mac' else Keys.CONTROL).perform()
                        time.sleep(0.2)
                        actions.send_keys(Keys.BACKSPACE).perform()
                        time.sleep(0.3)

                        # 重新输入
                        actions.send_keys(content).perform()
                        time.sleep(2)

                        # 再次检查按钮状态
                        is_disabled = send_button.get_attribute('disabled')
                        if is_disabled:
                            print("      ❌ 按钮仍然禁用，尝试使用回车发送")
                            comment_input.send_keys(Keys.RETURN)
                            time.sleep(4)
                            logging.info(f"评论成功（回车）: {content}")
                            return True
                    except Exception as e:
                        print(f"      ⚠️  重新输入失败: {e}")
                        # 尝试直接用回车
                        comment_input.send_keys(Keys.RETURN)
                        time.sleep(4)
                        logging.info(f"评论成功（回车）: {content}")
                        return True

            # 点击发送按钮
            try:
                print("      🚀 准备点击发送按钮...")

                # 滚动按钮到可见位置
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", send_button)
                time.sleep(0.5)

                # 使用JavaScript点击（避免被其他元素遮挡）
                driver.execute_script("arguments[0].click();", send_button)
                print(f"      ✅ 已点击发送按钮")

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
                try:
                    comment_input.send_keys(Keys.RETURN)
                    print(f"      ✅ 尝试用回车发送")

                    # 等待评论提交完成
                    time.sleep(4)

                    # 验证评论是否成功
                    try:
                        current_text = comment_input.text.strip()
                        if not current_text or current_text == "":
                            print(f"      ✅ 评论已发送（回车方式）")
                            logging.info(f"评论成功（回车）: {content}")
                        else:
                            print(f"      ⚠️  输入框未清空")
                            logging.warning(f"评论提交状态未知（回车）: {content}")
                    except:
                        print(f"      ✅ 评论已提交（回车）")
                        logging.info(f"评论成功（回车）: {content}")

                    return True
                except Exception as e2:
                    print(f"      ❌ 回车发送也失败: {e2}")
                    return False

        else:
            print("      ⚠️  未找到发送按钮，尝试按回车发送...")
            try:
                comment_input.send_keys(Keys.RETURN)
                print(f"      ✅ 使用回车发送")

                # 等待评论提交完成
                time.sleep(4)

                # 验证评论是否成功
                try:
                    current_text = comment_input.text.strip()
                    if not current_text or current_text == "":
                        print(f"      ✅ 评论已发送（回车）")
                        logging.info(f"评论成功（回车）: {content}")
                    else:
                        print(f"      ⚠️  输入框未清空")
                        logging.warning(f"评论提交状态未知（回车）: {content}")
                except:
                    print(f"      ✅ 评论已提交（回车）")
                    logging.info(f"评论成功（回车）: {content}")

                return True
            except Exception as e:
                print(f"      ❌ 回车发送失败: {e}")
                return False
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
    comment_templates=None
):
   

    """
    智能浏览和互动 - 确保模式

    参数:
        max_videos: 默认浏览多少个视频（默认3个）
        interaction_rate: 额外互动概率（达成目标后的额外互动概率）
        enable_like: 是否启用点赞（True则确保至少成功1次）
        enable_comment: 是否启用评论（True则确保至少成功1次）
        comment_templates: 评论模板列表（None则使用默认）

    新逻辑：
        - 如果 enable_like=True，确保至少成功点赞1次
        - 如果 enable_comment=True，确保至少成功评论1次
        - 最多尝试 max_videos*3 个视频（避免无限循环）
    """
    print("\n🤖 开始智能浏览模式（确保模式）...")
    print(f"   - 默认浏览 {max_videos} 个视频")
    print(f"   - 点赞: {'启用（确保≥1次）' if enable_like else '禁用'}")
    print(f"   - 评论: {'启用（确保≥1次）' if enable_comment else '禁用'}")

    # 使用默认模板（如果未提供）
    if comment_templates is None:
        comment_templates = get_comment_templates()

    browsed_count = 0
    interacted_count = 0

    # 成功计数器
    success_count = {
        'like': 0,
        'comment': 0,
    }

    # 目标：每个启用的操作至少成功1次
    targets = {
        'like': 1 if enable_like else 0,
        'comment': 1 if enable_comment else 0,
    }

    max_attempts = max_videos * 3  # 最多尝试次数（避免无限循环）
    i = 0

    while i < max_attempts:
        i += 1

        # 检查是否达成所有目标
        all_targets_met = all(
            success_count[action] >= targets[action]
            for action in ['like', 'comment']
        )

        # 如果已达成所有目标且浏览数达到默认值，退出
        if all_targets_met and browsed_count >= max_videos:
            print(f"\n✅ 已达成所有目标！")
            print(f"   - 点赞成功: {success_count['like']} 次")
            print(f"   - 评论成功: {success_count['comment']} 次")
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
                           f"评论{success_count['comment']}/{targets['comment']}")
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
    print("="*60)

    # 记录统计信息到日志
    summary = (f"浏览完成 - 浏览: {browsed_count}, 互动: {interacted_count}, "
               f"点赞: {success_count['like']}, 评论: {success_count['comment']}")
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
        # 访问 TikTok 首页（让它自动重定向到对应地区）
        print("\n访问 TikTok 首页...")
        driver.get('https://www.tiktok.com/')
        time.sleep(5)

        # 检查当前 URL，适应不同地区
        current_url = driver.current_url
        print(f"   🔗 当前页面: {current_url}")

        # 处理 about 欢迎页面
        if 'about' in current_url:
            print("   📄 检测到欢迎页面（about），尝试跳过...")

            # 方法1: 查找并点击"开始使用"或"进入"按钮
            try:
                # 可能的按钮文本
                button_texts = ['Watch now', 'Get Started', 'Start', 'Enter', '开始', '进入']
                button_found = False

                for text in button_texts:
                    try:
                        buttons = driver.find_elements(By.XPATH, f"//button[contains(., '{text}')] | //a[contains(., '{text}')]")
                        if buttons:
                            print(f"   ✅ 找到按钮: {text}")
                            driver.execute_script("arguments[0].click();", buttons[0])
                            button_found = True
                            time.sleep(3)
                            break
                    except:
                        continue

                if not button_found:
                    print("   ⚠️  未找到进入按钮，直接访问 foryou 页面...")
                    # 方法2: 直接访问 foryou
                    driver.get('https://www.tiktok.com/foryou')
                    time.sleep(5)

            except Exception as e:
                print(f"   ⚠️  处理欢迎页面失败: {e}")
                # 备用方案：直接访问 foryou
                driver.get('https://www.tiktok.com/foryou')
                time.sleep(5)

        # 如果跳转到 notfound，尝试访问首页根路径
        elif 'notfound' in current_url:
            print("   ⚠️  检测到 404 页面，尝试访问根路径...")
            # 提取地区代码（如 /hk/）
            import re
            region_match = re.search(r'tiktok\.com/([a-z]{2})/', current_url)
            if region_match:
                region = region_match.group(1)
                print(f"   📍 检测到地区: {region}")
                # 访问该地区的首页
                driver.get(f'https://www.tiktok.com/{region}/')
                time.sleep(5)
            else:
                # 直接访问根路径
                driver.get('https://www.tiktok.com/')
                time.sleep(5)

        # 最终检查：如果还在 about 页面，给出提示
        current_url = driver.current_url
        if 'about' in current_url:
            print("\n" + "="*60)
            print("⚠️  仍在欢迎页面，可能需要手动操作")
            print("请在浏览器中：")
            print("1. 点击页面上的【Watch now】或【开始】按钮")
            print("2. 或者直接在地址栏访问: https://www.tiktok.com/foryou")
            print("3. 完成后按回车继续...")
            print("="*60)
            input()

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
        print("0. 退出")
        print("="*60)

        choice = input("请输入选项 (0-3): ").strip()

        if choice == '1':
            # 纯浏览
            print("\n🔍 纯浏览模式（不互动）")
            logging.info("开始纯浏览测试")
            smart_browse_and_interact(
                driver,
                max_videos=3,
                interaction_rate=0.0,
                enable_like=False,
                enable_comment=False
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
                enable_comment=False
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
                comment_templates=comment_templates
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
