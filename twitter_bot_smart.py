#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter/X 智能自动化脚本 v1.0
模拟真实用户行为，随机浏览和互动
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium_stealth import stealth  # 反检测库
import time
import random
import sys
import logging
from datetime import datetime
import re

# 双端抓包系统（可选）
import os

# 检查是否通过环境变量禁用装饰器抓包（用于run_capture.py场景）
if os.getenv('DISABLE_DECORATOR_CAPTURE') == '1':
    CAPTURE_ENABLED = False
    # 使用空装饰器（run_capture.py会在会话级别抓包）
    def capture_traffic(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
else:
    try:
        from capture import capture_traffic
        CAPTURE_ENABLED = True
    except ImportError:
        CAPTURE_ENABLED = False
        # 如果capture包不存在，使用空装饰器
        def capture_traffic(*args, **kwargs):
            def decorator(func):
                return func
            return decorator


# === 模板数据 ===

def get_comment_templates():
    """获取评论模板（英文为主）"""
    return [
        # 简短赞同类
        "Great point!", "So true!", "Exactly!", "Well said!", "Agreed!",
        "This!", "Facts!", "100%", "Absolutely!", "Couldn't agree more!",

        # 表扬类
        "Amazing!", "Awesome!", "Brilliant!", "Love this!", "Excellent!",
        "This is gold!", "So good!", "Fantastic!", "Outstanding!",

        # 感谢分享类
        "Thanks for sharing!", "Thank you!", "Appreciate this!",
        "Thanks!", "Helpful, thanks!",

        # 学习类
        "Learned something new!", "Great insight!", "Interesting!",
        "Mind-blown!", "Never thought of it this way!",

        # 情感表达类
        "😂😂😂", "🔥🔥🔥", "👏👏👏", "💯", "🎯",
        "This made my day!", "LOL", "Haha!", "😍",

        # 互动类
        "Thoughts?", "What do you think?", "Same here!",
        "Couldn't have said it better!", "Spot on!",
    ]


def get_retweet_templates():
    """获取转发模板"""
    return [
        # 转发标记
        "", "👀", "📌", "🔥", "💯", "🎯", "⬆️",

        # 推荐类
        "Must read!", "Worth reading!", "Check this out!",
        "Don't miss this!", "Important thread!",

        # 认同类
        "This!", "Exactly this!", "So true!", "Facts!",
        "Couldn't agree more!", "Well said!",

        # 感悟类
        "Great insight!", "Mind-blown!", "This is gold!",
        "Everyone should see this!", "Sharing for visibility!",

        # 学习类
        "Learned a lot from this!", "Great thread!",
        "Valuable information!", "Insightful!",
    ]


def get_post_templates():
    """获取发帖模板"""
    return [
        # 日常分享
        "Just thinking...", "Good morning everyone!", "Happy Friday!",
        "Starting the weekend right!", "Beautiful day today!",

        # 学习分享
        "Learning something new every day!", "Today's insight:",
        "Just realized...", "Quick thought:",

        # 励志正能量
        "Keep pushing forward!", "You got this! 💪",
        "Stay positive!", "Make today count!",
        "One step at a time!", "Progress over perfection!",

        # 生活态度
        "Life is good! 😊", "Grateful for today!",
        "Living in the moment!", "Small wins matter!",

        # 简短感悟
        "Sometimes less is more.", "Quality over quantity.",
        "Focus on what matters.", "Every day is a new opportunity.",
    ]


def setup_logging():
    """配置日志系统"""
    # 日志文件名（固定，追加模式）
    log_filename = 'twitter_bot.log'

    # 配置日志格式
    log_format = '[%(asctime)s] %(levelname)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # 配置 logging
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # 文件 handler（追加模式）
            logging.FileHandler(log_filename, mode='a', encoding='utf-8'),
            # 控制台 handler（同时输出到终端）
            logging.StreamHandler(sys.stdout)
        ]
    )

    # 记录新的运行会话开始
    logging.info("="*60)
    logging.info("新的运行会话开始")
    logging.info("="*60)

    return logging.getLogger(__name__)


def create_driver(use_proxy=False):
    """
    创建 Chrome 浏览器实例（保留登录状态）

    Args:
        use_proxy: 是否使用代理（Twitter通常不需要，除非在受限地区）
    """
    chrome_options = Options()

    # 📂 设置用户数据目录（保存登录状态）
    import os
    user_data_dir = os.path.expanduser('~/selenium_profiles/twitter')
    chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
    chrome_options.add_argument('--profile-directory=Default')
    print(f"💾 使用配置文件: {user_data_dir}")

    if use_proxy:
        # 根据需要修改代理端口
        chrome_options.add_argument('--proxy-server=socks5://127.0.0.1:7897')
        print("🌐 代理已启用")

    # 反检测设置
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')

    # 随机 User-Agent
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')

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
    """随机滚动页面，模拟人类浏览"""
    # 90% 向下滚动，10% 向上滚动
    if random.random() < 0.9:
        # 向下滚动
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
    """检查是否已登录"""
    try:
        # Twitter登录状态检查：查找侧边栏的用户信息
        user_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="SideNav_AccountSwitcher_Button"]')
        if user_elements:
            return True

        # 备用检查：是否有"Log in"按钮
        login_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Log in') or contains(text(), 'Sign in')]")
        return len(login_buttons) == 0
    except:
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


def like_tweet(driver, tweet_element):
    """点赞推文"""
    try:
        print(f"      🔍 查找点赞按钮...")

        # Twitter的点赞按钮选择器
        like_selectors = [
            # 方法1: 通过 data-testid（最可靠）
            ('CSS', '[data-testid="like"]'),
            ('CSS', 'button[data-testid="like"]'),

            # 方法2: 通过 aria-label
            ('CSS', 'button[aria-label*="Like"]'),
            ('CSS', 'button[aria-label*="like"]'),

            # 方法3: 通过SVG路径查找喜欢图标
            ('XPATH', './/button[.//*[local-name()="svg"]]'),
        ]

        for method, selector in like_selectors:
            try:
                if method == 'CSS':
                    elements = tweet_element.find_elements(By.CSS_SELECTOR, selector)
                else:
                    elements = tweet_element.find_elements(By.XPATH, selector)

                if elements:
                    for elem in elements:
                        try:
                            if not elem.is_displayed():
                                continue

                            # 检查是否已经点赞
                            aria_label = elem.get_attribute('aria-label') or ''
                            data_testid = elem.get_attribute('data-testid') or ''

                            # 如果是"unlike"说明已经点赞过了
                            if 'unlike' in data_testid.lower() or 'liked' in aria_label.lower():
                                print("      ⚠️  已经点赞过了，跳过")
                                logging.info("点赞跳过：已点赞")
                                return True

                            # 滚动到元素位置
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                            time.sleep(random.uniform(0.3, 0.6))

                            # 点击
                            try:
                                driver.execute_script("arguments[0].click();", elem)
                            except:
                                elem.click()

                            # 等待状态更新
                            time.sleep(1.5)

                            # 验证点赞成功（检查按钮是否变成unlike）
                            try:
                                new_testid = elem.get_attribute('data-testid') or ''
                                new_aria = elem.get_attribute('aria-label') or ''

                                if 'unlike' in new_testid.lower() or 'liked' in new_aria.lower():
                                    print("      ✅ 点赞成功（已验证）")
                                    logging.info("点赞成功")
                                    return True
                                else:
                                    print(f"      ⚠️  点击了但状态未变化")
                                    # 继续尝试下一个元素
                                    continue
                            except:
                                # 无法验证，假定成功
                                print("      ✅ 点赞操作已执行")
                                logging.info("点赞已执行（验证异常）")
                                return True

                        except Exception as e:
                            print(f"      ⚠️  点击失败: {str(e)[:50]}")
                            continue
            except:
                continue

        print("      ❌ 未找到点赞按钮")
        logging.warning("点赞失败：未找到点赞按钮")
        return False

    except Exception as e:
        print(f"      ❌ 点赞异常: {e}")
        logging.error(f"点赞异常: {e}")
        return False


def comment_tweet(driver, tweet_element, content_list):
    """评论推文"""
    try:
        print(f"      🔍 查找回复按钮...")

        # 查找回复按钮
        reply_button = None
        reply_selectors = [
            '[data-testid="reply"]',
            'button[data-testid="reply"]',
            'button[aria-label*="Reply"]',
        ]

        for selector in reply_selectors:
            try:
                elements = tweet_element.find_elements(By.CSS_SELECTOR, selector)
                if elements and elements[0].is_displayed():
                    reply_button = elements[0]
                    print(f"      ✅ 找到回复按钮")
                    break
            except:
                continue

        if not reply_button:
            print("      ❌ 未找到回复按钮")
            logging.warning("评论失败：未找到回复按钮")
            return False

        # 点击回复按钮
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", reply_button)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", reply_button)
        print("      ✅ 点击回复按钮，等待输入框...")
        time.sleep(2)

        # 查找回复输入框
        print("      🔍 查找回复输入框...")
        input_selectors = [
            '[data-testid="tweetTextarea_0"]',
            'div[contenteditable="true"][role="textbox"]',
            'div[data-testid*="tweet"][contenteditable="true"]',
        ]

        reply_input = None
        for selector in input_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and elements[0].is_displayed():
                    reply_input = elements[0]
                    print(f"      ✅ 找到输入框: {selector}")
                    break
            except:
                continue

        if not reply_input:
            print("      ❌ 未找到输入框")
            logging.warning("评论失败：未找到输入框")
            # 尝试关闭弹窗
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(1)
            except:
                pass
            return False

        # 输入评论内容
        content = random.choice(content_list)
        print(f"      📝 准备输入评论: {content}")

        # 点击输入框获得焦点
        driver.execute_script("arguments[0].focus();", reply_input)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", reply_input)
        time.sleep(0.5)

        # 使用ActionChains输入（模拟真实用户）
        try:
            actions = ActionChains(driver)
            actions.move_to_element(reply_input).click().send_keys(content).perform()
            time.sleep(1.5)
            print(f"      ✅ 已输入评论: {content}")
        except:
            # 备用方案：直接send_keys
            reply_input.send_keys(content)
            time.sleep(1.5)
            print(f"      ✅ 已输入评论（备用方式）: {content}")

        # 查找发送按钮
        print("      🔍 查找发送按钮...")
        time.sleep(1)

        send_button_selectors = [
            '[data-testid="tweetButton"]',
            '[data-testid="tweetButtonInline"]',
            'button[data-testid*="tweet"]',
            '//button[contains(., "Reply")]',
            '//button[contains(., "Post")]',
        ]

        send_button = None
        for selector in send_button_selectors:
            try:
                if selector.startswith('//'):
                    elements = driver.find_elements(By.XPATH, selector)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)

                for elem in elements:
                    if elem.is_displayed():
                        send_button = elem
                        print(f"      ✅ 找到发送按钮")
                        break
                if send_button:
                    break
            except:
                continue

        if send_button:
            # 检查按钮是否可点击
            is_disabled = send_button.get_attribute('disabled')
            if is_disabled:
                print("      ⚠️  按钮是禁用状态，等待1秒...")
                time.sleep(1)

            # 点击发送
            driver.execute_script("arguments[0].click();", send_button)
            print(f"      ✅ 点击发送按钮")
            time.sleep(3)

            print(f"      ✅ 评论已发送")
            logging.info(f"评论成功: {content}")
            return True
        else:
            print("      ⚠️  未找到发送按钮，尝试按回车...")
            reply_input.send_keys(Keys.RETURN)
            time.sleep(3)
            print(f"      ✅ 评论已发送（回车）")
            logging.info(f"评论成功（回车）: {content}")
            return True

    except Exception as e:
        print(f"      ❌ 评论失败: {e}")
        logging.error(f"评论异常: {e}")
        # 尝试关闭弹窗
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(1)
        except:
            pass
        return False


def retweet_tweet(driver, tweet_element, retweet_templates):
    """转发推文"""
    try:
        print(f"      🔍 查找转发按钮...")

        # 查找转发按钮
        retweet_button = None
        retweet_selectors = [
            '[data-testid="retweet"]',
            'button[data-testid="retweet"]',
            'button[aria-label*="Retweet"]',
        ]

        for selector in retweet_selectors:
            try:
                elements = tweet_element.find_elements(By.CSS_SELECTOR, selector)
                if elements and elements[0].is_displayed():
                    retweet_button = elements[0]
                    print(f"      ✅ 找到转发按钮")
                    break
            except:
                continue

        if not retweet_button:
            print("      ❌ 未找到转发按钮")
            logging.warning("转发失败：未找到转发按钮")
            return False

        # 点击转发按钮（会弹出菜单）
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", retweet_button)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", retweet_button)
        print("      ✅ 点击转发按钮，等待菜单...")
        time.sleep(1.5)

        # 查找转发选项（Retweet 或 Quote）
        # 这里选择"Quote Tweet"以便添加评论
        print("      🔍 查找Quote Tweet选项...")
        quote_selectors = [
            '[data-testid="retweetConfirm"]',  # 直接转发
            '//span[contains(text(), "Quote")]',  # Quote Tweet
        ]

        # 随机选择：70%直接转发，30% Quote转发
        use_quote = random.random() < 0.3

        if use_quote:
            # Quote转发（带评论）
            try:
                quote_option = driver.find_element(By.XPATH, '//span[contains(text(), "Quote")]')
                driver.execute_script("arguments[0].click();", quote_option)
                print("      ✅ 选择Quote Tweet")
                time.sleep(2)

                # 查找Quote输入框
                quote_input = None
                input_selectors = [
                    '[data-testid="tweetTextarea_0"]',
                    'div[contenteditable="true"][role="textbox"]',
                ]

                for selector in input_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements and elements[0].is_displayed():
                            quote_input = elements[0]
                            break
                    except:
                        continue

                if quote_input:
                    # 输入转发评论
                    content = random.choice(retweet_templates)
                    driver.execute_script("arguments[0].focus();", quote_input)
                    time.sleep(0.3)
                    quote_input.send_keys(content)
                    time.sleep(1)
                    print(f"      ✅ 已输入Quote评论: {content}")

                    # 查找并点击发送按钮
                    send_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="tweetButton"]')
                    driver.execute_script("arguments[0].click();", send_button)
                    print("      ✅ Quote转发成功")
                    logging.info(f"Quote转发成功: {content}")
                    time.sleep(2)
                    return True
                else:
                    print("      ⚠️  未找到Quote输入框，降级为直接转发")
                    # 关闭弹窗，重新尝试直接转发
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(1)
            except:
                print("      ⚠️  Quote转发失败，降级为直接转发")
                pass

        # 直接转发（无评论）
        try:
            # 重新点击转发按钮（如果之前关闭了菜单）
            if use_quote:
                driver.execute_script("arguments[0].click();", retweet_button)
                time.sleep(1.5)

            # 查找并点击"Retweet"确认按钮
            retweet_confirm = driver.find_element(By.CSS_SELECTOR, '[data-testid="retweetConfirm"]')
            driver.execute_script("arguments[0].click();", retweet_confirm)
            print("      ✅ 直接转发成功")
            logging.info("转发成功")
            time.sleep(2)
            return True
        except Exception as e:
            print(f"      ❌ 直接转发失败: {e}")
            logging.error(f"转发异常: {e}")
            return False

    except Exception as e:
        print(f"      ❌ 转发失败: {e}")
        logging.error(f"转发异常: {e}")
        return False


def post_tweet(driver, post_templates):
    """发布推文"""
    try:
        print("\n📝 准备发布推文...")

        # 查找"What is happening?!"输入框
        print("   查找发推文输入框...")

        # 在首页顶部通常有快捷发推框
        input_selectors = [
            '[data-testid="tweetTextarea_0"]',
            'div[contenteditable="true"][role="textbox"]',
            'div[data-testid*="tweet"][contenteditable="true"]',
        ]

        tweet_input = None
        for selector in input_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        # 检查是否是发推框（不是回复框）
                        placeholder = elem.get_attribute('data-placeholder') or elem.text
                        if 'happening' in placeholder.lower() or not placeholder:
                            tweet_input = elem
                            print(f"   ✅ 找到发推文输入框: {selector}")
                            break
                if tweet_input:
                    break
            except:
                continue

        if not tweet_input:
            print("   ❌ 未找到发推文输入框")
            logging.warning("发推文失败：未找到输入框")
            return False

        # 输入内容
        content = random.choice(post_templates)
        print(f"   📝 准备输入内容: {content}")

        # 滚动到输入框位置
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tweet_input)
        time.sleep(0.5)

        # 点击输入框获得焦点
        driver.execute_script("arguments[0].focus();", tweet_input)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", tweet_input)
        time.sleep(0.5)

        # 输入内容
        try:
            actions = ActionChains(driver)
            actions.move_to_element(tweet_input).click().send_keys(content).perform()
            time.sleep(1.5)
            print(f"   ✅ 已输入内容: {content}")
        except:
            tweet_input.send_keys(content)
            time.sleep(1.5)
            print(f"   ✅ 已输入内容（备用方式）: {content}")

        # 查找发送按钮
        print("   🔍 查找发送按钮...")
        time.sleep(1)

        post_button_selectors = [
            '[data-testid="tweetButtonInline"]',
            '[data-testid="tweetButton"]',
            'button[data-testid*="tweet"]',
            '//button[contains(., "Post")]',
        ]

        post_button = None
        for selector in post_button_selectors:
            try:
                if selector.startswith('//'):
                    elements = driver.find_elements(By.XPATH, selector)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)

                for elem in elements:
                    if elem.is_displayed():
                        # 确保不是回复按钮
                        aria_label = elem.get_attribute('aria-label') or ''
                        if 'reply' not in aria_label.lower():
                            post_button = elem
                            print(f"   ✅ 找到发送按钮")
                            break
                if post_button:
                    break
            except:
                continue

        if post_button:
            # 检查按钮是否可点击
            is_disabled = post_button.get_attribute('disabled')
            if is_disabled:
                print("   ⚠️  按钮是禁用状态，等待1秒...")
                time.sleep(1)

            # 点击发送
            driver.execute_script("arguments[0].click();", post_button)
            print(f"   ✅ 发推文成功！")
            logging.info(f"发推文成功: {content}")
            time.sleep(3)
            return True
        else:
            print("   ❌ 未找到发送按钮")
            logging.warning("发推文失败：未找到发送按钮")
            return False

    except Exception as e:
        print(f"   ❌ 发推文失败: {e}")
        logging.error(f"发推文异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def smart_browse_and_interact(
    driver,
    max_tweets=3,
    interaction_rate=0.3,
    enable_like=True,
    enable_comment=True,
    enable_retweet=True,
    enable_post=False,
    comment_templates=None,
    retweet_templates=None,
    post_templates=None
):
    """
    智能浏览和互动 - 确保模式

    参数:
        max_tweets: 默认浏览多少条推文（默认3条）
        interaction_rate: 额外互动概率（达成目标后的额外互动概率）
        enable_like: 是否启用点赞（True则确保至少成功1次）
        enable_comment: 是否启用评论（True则确保至少成功1次）
        enable_retweet: 是否启用转发（True则确保至少成功1次）
        enable_post: 是否启用发推文（True则确保至少成功1次）
        comment_templates: 评论模板列表（None则使用默认）
        retweet_templates: 转发模板列表（None则使用默认）
        post_templates: 发推文模板列表（None则使用默认）

    新逻辑：
        - 如果 enable_like=True，确保至少成功点赞1次
        - 如果 enable_comment=True，确保至少成功评论1次
        - 如果 enable_retweet=True，确保至少成功转发1次
        - 如果 enable_post=True，确保至少成功发推文1次
        - 最多尝试 max_tweets*3 条推文（避免无限循环）
    """
    print("\n🤖 开始智能浏览模式（确保模式）...")
    print(f"   - 默认浏览 {max_tweets} 条推文")
    print(f"   - 点赞: {'启用（确保≥1次）' if enable_like else '禁用'}")
    print(f"   - 评论: {'启用（确保≥1次）' if enable_comment else '禁用'}")
    print(f"   - 转发: {'启用（确保≥1次）' if enable_retweet else '禁用'}")
    print(f"   - 发推文: {'启用（确保≥1次）' if enable_post else '禁用'}")

    # 使用默认模板（如果未提供）
    if comment_templates is None:
        comment_templates = get_comment_templates()
    if retweet_templates is None:
        retweet_templates = get_retweet_templates()
    if post_templates is None:
        post_templates = get_post_templates()

    browsed_count = 0
    interacted_count = 0
    interacted_tweet_ids = set()

    # 成功计数器
    success_count = {
        'like': 0,
        'comment': 0,
        'retweet': 0,
        'post': 0,
    }

    # 目标：每个启用的操作至少成功1次
    targets = {
        'like': 1 if enable_like else 0,
        'comment': 1 if enable_comment else 0,
        'retweet': 1 if enable_retweet else 0,
        'post': 1 if enable_post else 0,
    }

    max_attempts = max_tweets * 3
    i = 0

    while i < max_attempts:
        i += 1

        # 检查是否达成所有目标
        all_targets_met = all(
            success_count[action] >= targets[action]
            for action in ['like', 'comment', 'retweet', 'post']
        )

        # 如果已达成所有目标且浏览数达到默认值，退出
        if all_targets_met and browsed_count >= max_tweets:
            print(f"\n✅ 已达成所有目标！")
            print(f"   - 点赞成功: {success_count['like']} 次")
            print(f"   - 评论成功: {success_count['comment']} 次")
            print(f"   - 转发成功: {success_count['retweet']} 次")
            if enable_post:
                print(f"   - 发推文成功: {success_count['post']} 次")
            break

        try:
            # 如果启用发推文且还没发够，则发推文
            if enable_post and success_count['post'] < targets['post']:
                print(f"\n📝 [循环 {i}] 准备发推文（确保至少1次）...")
                logging.info(f"触发自动发推文（第 {i} 次循环）")

                if post_tweet(driver, post_templates):
                    success_count['post'] += 1
                    print("   ✅ 发推文成功！")
                    time.sleep(random.uniform(5, 10))

                    # 发推文后刷新页面
                    print("   🔄 刷新页面继续浏览...")
                    driver.refresh()
                    time.sleep(random.uniform(3, 5))
                else:
                    print("   ⚠️  发推文失败，继续尝试")
                    time.sleep(random.uniform(2, 4))

            # 随机滚动
            scroll_times = random.randint(1, 3)
            for _ in range(scroll_times):
                random_scroll(driver)

            # 模拟阅读
            simulate_reading(2, 5)

            # 查找当前可见的推文（article标签）
            tweets = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')

            if not tweets or len(tweets) < 2:
                print("   ⚠️  未找到足够的推文，继续滚动...")
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(2)
                continue

            print(f"   ✅ 找到 {len(tweets)} 条推文")

            # 从中间位置选择推文（避免重复选前几个）
            start_idx = min(2, len(tweets) - 3)
            end_idx = min(start_idx + 5, len(tweets))
            candidate_tweets = tweets[start_idx:end_idx]

            # 随机选择一条推文
            current_tweet = random.choice(candidate_tweets)

            browsed_count += 1
            print(f"\n📄 浏览第 {browsed_count} 条推文...")

            # 滚动到该推文位置
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", current_tweet)
            simulate_reading(3, 7)

            # 智能决定互动操作
            actions = []

            # 优先执行未达成目标的操作
            if enable_like and success_count['like'] < targets['like']:
                actions.append('like')

            if enable_comment and success_count['comment'] < targets['comment']:
                actions.append('comment')

            if enable_retweet and success_count['retweet'] < targets['retweet']:
                actions.append('retweet')

            # 如果没有任何操作可执行，跳过
            if not actions:
                if not all_targets_met:
                    print("   ⚠️  本条推文未选择互动，继续寻找...")
                else:
                    print("   👀 目标已达成，只是浏览，不互动")
                continue

            # 显示选择的操作和目标进度
            print(f"   💬 决定互动: {', '.join(actions)}")
            progress = (f"      当前进度: 点赞{success_count['like']}/{targets['like']}, "
                       f"评论{success_count['comment']}/{targets['comment']}, "
                       f"转发{success_count['retweet']}/{targets['retweet']}")
            if enable_post:
                progress += f", 发推文{success_count['post']}/{targets['post']}"
            print(progress)

            # 执行操作
            if 'like' in actions:
                if like_tweet(driver, current_tweet):
                    success_count['like'] += 1
                    interacted_count += 1
                    time.sleep(random.uniform(1, 2))

            if 'comment' in actions:
                if comment_tweet(driver, current_tweet, comment_templates):
                    success_count['comment'] += 1
                    interacted_count += 1
                    time.sleep(random.uniform(1, 2))

            if 'retweet' in actions:
                if retweet_tweet(driver, current_tweet, retweet_templates):
                    success_count['retweet'] += 1
                    interacted_count += 1
                    time.sleep(random.uniform(1, 2))

            # 随机暂停
            time.sleep(random.uniform(2, 5))

            # 向下滚动
            scroll_distance = random.randint(400, 800)
            driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            time.sleep(random.uniform(1, 2))

        except Exception as e:
            print(f"   ❌ 处理推文时出错: {e}")
            logging.error(f"处理推文异常: {e}")
            continue

    print("\n" + "="*60)
    print(f"📊 浏览完成！")
    print(f"   - 浏览了 {browsed_count} 条推文")
    print(f"   - 总互动次数: {interacted_count} 次")
    print(f"   - 成功点赞: {success_count['like']} 次")
    print(f"   - 成功评论: {success_count['comment']} 次")
    print(f"   - 成功转发: {success_count['retweet']} 次")
    if enable_post:
        print(f"   - 成功发推文: {success_count['post']} 次")
    print("="*60)

    # 记录统计信息到日志
    summary = (f"浏览完成 - 浏览: {browsed_count}, 互动: {interacted_count}, "
               f"点赞: {success_count['like']}, 评论: {success_count['comment']}, "
               f"转发: {success_count['retweet']}")
    if enable_post:
        summary += f", 发推文: {success_count['post']}"
    logging.info(summary)


def main():
    # 初始化日志系统
    setup_logging()

    print("="*60)
    print("Twitter/X 智能自动化脚本 v1.0")
    print("="*60)
    logging.info("脚本启动")

    # 询问是否使用代理
    print("\n是否使用代理？")
    print("1. 是（推荐在受限地区使用）")
    print("2. 否（默认）")
    proxy_choice = input("请选择 (1/2，默认2): ").strip()
    use_proxy = (proxy_choice == '1')

    print("\n启动浏览器...")
    driver = create_driver(use_proxy=use_proxy)
    print("✅ 浏览器启动成功！")
    logging.info("浏览器启动成功")

    try:
        # 访问Twitter首页
        print("\n访问Twitter首页...")
        driver.get('https://x.com/home')
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
        print("4. 转发测试")
        print("5. 发推文测试")
        print("0. 退出")
        print("="*60)

        choice = input("请输入选项 (0-5): ").strip()

        if choice == '1':
            # 纯浏览
            print("\n🔍 纯浏览模式（不互动）")
            logging.info("开始纯浏览测试")
            smart_browse_and_interact(
                driver,
                max_tweets=3,
                interaction_rate=0.0,
                enable_like=False,
                enable_comment=False,
                enable_retweet=False,
                enable_post=False
            )

        elif choice == '2':
            # 点赞测试
            print("\n👍 点赞测试模式（确保至少成功1次）")
            logging.info("开始点赞测试")
            smart_browse_and_interact(
                driver,
                max_tweets=3,
                interaction_rate=0.3,
                enable_like=True,
                enable_comment=False,
                enable_retweet=False,
                enable_post=False
            )

        elif choice == '3':
            # 评论测试
            print("\n💬 评论测试模式（确保至少成功1次）")
            logging.info("开始评论测试")
            comment_templates = get_comment_templates()
            smart_browse_and_interact(
                driver,
                max_tweets=3,
                interaction_rate=0.3,
                enable_like=False,
                enable_comment=True,
                enable_retweet=False,
                enable_post=False,
                comment_templates=comment_templates
            )

        elif choice == '4':
            # 转发测试
            print("\n🔄 转发测试模式（确保至少成功1次）")
            logging.info("开始转发测试")
            retweet_templates = get_retweet_templates()
            smart_browse_and_interact(
                driver,
                max_tweets=3,
                interaction_rate=0.3,
                enable_like=False,
                enable_comment=False,
                enable_retweet=True,
                enable_post=False,
                retweet_templates=retweet_templates
            )

        elif choice == '5':
            # 发推文测试
            print("\n📝 发推文测试模式")
            logging.info("开始发推文测试")
            post_templates = get_post_templates()
            smart_browse_and_interact(
                driver,
                max_tweets=3,
                interaction_rate=0.0,
                enable_like=False,
                enable_comment=False,
                enable_retweet=False,
                enable_post=True,
                post_templates=post_templates
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
