#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博智能自动化脚本 v3.0
模拟真实用户行为，随机浏览和互动
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import random
import sys
import logging
import shutil
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
    """获取评论模板"""
    return [
        # 赞同认可类
        "说得好", "有道理", "赞同", "说到心坎里了", "深有同感", "确实如此",
        "太对了", "一针见血", "说得太好了", "非常认同", "完全赞同", "正解",
        # 学习收获类
        "学到了", "涨知识了", "长见识了", "受教了", "学习了", "get到了",
        "原来如此", "恍然大悟", "又学到新东西了", "涨姿势了", "受益匪浅",
        # 表扬夸赞类
        "厉害厉害", "很棒", "太棒了", "优秀", "牛", "nb", "666", "绝了",
        "高手", "大神", "强", "真棒", "amazing", "great",
        # 支持鼓励类
        "支持一下", "加油", "顶", "挺你", "支持", "给你点赞", "冲冲冲",
        # 情感表达类
        "哈哈哈", "笑死", "太真实了", "破防了", "绷不住了", "爱了爱了",
        "心动了", "感动", "泪目", "好暖", "治愈", "舒服了",
        # 互动交流类
        "同问", "我也是", "同感", "握爪", "抱抱", "求更新", "期待后续",
        "想知道更多", "能详细说说吗", "可以展开讲讲吗",
        # 简短赞美类
        "赞", "火", "顶", "棒", "妙", "好", "强", "赞一个", "给力",
    ]


def get_repost_templates():
    """获取转发模板"""
    return [
        # 转发标记类
        "转发微博", "转发", "repost", "分享", "分享一下", "分享给大家",
        # 收藏标记类
        "马克", "mark", "马克一下", "收藏", "收藏了", "先收藏", "收藏慢慢看",
        "存一下", "留着", "记下了", "保存", "码住", "存档",
        # 学习类
        "学习学习", "学习了", "学习一下", "涨知识了", "涨姿势", "长见识了",
        "学到了", "又学到了", "get", "好好学习", "值得学习",
        # 认同推荐类
        "说得好", "有道理", "说的对", "赞同这个观点", "很有道理", "确实",
        "推荐", "强烈推荐", "值得一看", "值得分享", "值得关注", "不错不错",
        "好文", "干货", "精华", "优质内容", "高质量",
        # 感悟启发类
        "很有启发", "受益匪浅", "深受启发", "引人深思", "值得思考",
        "说到心坎里了", "深有感触", "感同身受",
        # 实用标记类
        "转需", "有用", "实用", "干货满满", "建议收藏", "新技能get",
        "tips", "笔记", "做个记录", "记录一下",
        # 情感表达类
        "太真实了", "破防了", "爱了", "赞", "顶", "支持", "给力",
        "精彩", "brilliant", "amazing", "nice", "cool", "awesome",
    ]


def get_post_templates():
    """获取发帖模板"""
    return [
        # 日常生活感悟
        "今天天气真不错", "周末愉快", "美好的一天", "新的一周开始了",
        "阳光明媚", "心情不错", "今日份快乐", "岁月静好",
        # 学习分享
        "学习使我快乐", "今日学习打卡", "每天进步一点点", "知识就是力量",
        "终身学习", "学无止境", "读书笔记", "今日所学",
        # 生活态度
        "保持热爱，奔赴山海", "认真生活", "享受当下", "不负时光",
        "珍惜每一天", "活在当下", "简单生活", "慢生活",
        # 励志正能量
        "加油", "一起努力", "不放弃", "坚持就是胜利",
        "相信自己", "越努力越幸运", "每天都要加油鸭", "奥利给",
    ]


def setup_logging():
    """配置日志系统"""
    # 日志文件名（固定，追加模式）
    log_filename = 'weibo_bot.log'

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

def create_driver(use_proxy=True, fast_mode=False):
    """
    创建 Chrome 浏览器实例（保留登录状态）

    Args:
        use_proxy: 是否使用代理
        fast_mode: 快速模式（禁用图片/CSS，提速50-70%）
    """
    chrome_options = Options()

    # 📂 设置用户数据目录（保存登录状态）
    sudo_user = os.getenv('SUDO_USER')
    if sudo_user and sudo_user != 'root':
        user_home = os.path.expanduser(f'~{sudo_user}')
    else:
        user_home = os.path.expanduser('~')

    user_data_dir = os.path.join(user_home, 'selenium_profiles', 'weibo')
    os.makedirs(user_data_dir, exist_ok=True)
    chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
    chrome_options.add_argument('--profile-directory=Default')
    print(f"💾 使用配置文件: {user_data_dir}")

    if use_proxy:
        chrome_options.add_argument('--proxy-server=socks5://127.0.0.1:10818')

    # ⚡ 快速模式优化
    if fast_mode:
        print("⚡ 快速模式已启用（禁用图片/CSS，预计提速50-70%）")

        # 禁用图片加载（最大提速）
        prefs = {
            'profile.default_content_setting_values': {
                'images': 2,  # 2=禁用图片
                'stylesheet': 2,  # 2=禁用CSS
            }
        }
        chrome_options.add_experimental_option('prefs', prefs)

        # 性能优化参数
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')

    # 反检测设置
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')

    # 随机 User-Agent（模拟真实浏览器）
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

    # Linux 环境稳定参数
    if sys.platform.startswith('linux'):
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-zygote')
        chrome_options.add_argument('--remote-debugging-port=9222')

        if not os.getenv('DISPLAY'):
            chrome_options.add_argument('--headless=new')
            print("🖥️ 未检测到 DISPLAY，自动启用 headless 模式")

    # 自动探测浏览器可执行文件
    browser_candidates = [
        shutil.which('chromium-browser'),
        shutil.which('chromium'),
        shutil.which('google-chrome'),
        '/snap/bin/chromium',
    ]
    browser_binary = next((p for p in browser_candidates if p and os.path.exists(p)), None)
    if browser_binary:
        chrome_options.binary_location = browser_binary
        print(f"🌐 浏览器二进制: {browser_binary}")

    # 自动探测 chromedriver
    driver_candidates = [
        shutil.which('chromedriver'),
        '/usr/bin/chromedriver',
        '/usr/lib/chromium-browser/chromedriver',
        '/snap/bin/chromedriver',
    ]
    driver_path = next((p for p in driver_candidates if p and os.path.exists(p)), None)

    try:
        if driver_path:
            print(f"🧭 使用驱动: {driver_path}")
            driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
        else:
            print("⚠️ 未找到 chromedriver，尝试 Selenium 自动发现...")
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

def random_scroll(driver):
    """随机滚动页面，模拟人类浏览（主要向下滚动）"""
    # 90% 向下滚动，10% 向上滚动（回看）
    if random.random() < 0.9:
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
    """检查是否已登录"""
    try:
        login_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), '登录') or contains(text(), '注册')]")
        if login_buttons:
            return False
        user_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/u/"]')
        return len(user_elements) > 0
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

# @capture_traffic("weibo", "like")  # 已被 run_capture.py 的会话级抓包替代
def like_weibo(driver, weibo_element):
    """点赞微博（增强版，支持多种选择器）"""
    try:
        # 多种点赞按钮选择器（按优先级）
        like_selectors = [
            # 方法1: 通过 class 包含 woo-like
            ('CSS', 'button[class*="woo-like"]'),
            ('CSS', 'button[class*="like"]'),

            # 方法2: 通过 aria-label
            ('CSS', 'button[aria-label*="赞"]'),
            ('CSS', 'button[title*="赞"]'),

            # 方法3: 通过图标 class
            ('CSS', 'i[class*="woo-font--like"]'),
            ('CSS', 'i[class*="icon-like"]'),

            # 方法4: 通过文本内容
            ('XPATH', './/*[contains(text(), "赞") and not(contains(text(), "转发"))]'),
            ('XPATH', './/button[contains(., "赞")]'),

            # 方法5: 通过 SVG 图标
            ('XPATH', './/*[.//*[local-name()="svg"]]//*[contains(@class, "like")]'),
        ]

        print(f"      🔍 查找点赞按钮...")

        for method, selector in like_selectors:
            try:
                if method == 'CSS':
                    elements = weibo_element.find_elements(By.CSS_SELECTOR, selector)
                else:  # XPATH
                    elements = weibo_element.find_elements(By.XPATH, selector)

                if elements:
                    print(f"      ✓ 找到 {len(elements)} 个候选元素（选择器: {selector[:50]}...）")

                    for elem in elements:
                        try:
                            # 检查元素是否可见
                            if not elem.is_displayed():
                                continue

                            # 检查是否已经点赞（避免重复点赞）
                            class_name = elem.get_attribute('class') or ''
                            aria_label = elem.get_attribute('aria-label') or ''

                            # 如果包含 "active" 或 "checked" 可能表示已点赞
                            if 'active' in class_name.lower() or 'checked' in class_name.lower():
                                print("      ⚠️  似乎已经点赞过了，跳过")
                                logging.info("点赞跳过：已点赞")
                                return True

                            # 滚动到元素位置
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", elem)
                            time.sleep(random.uniform(0.5, 1.0))

                            # 记录点击前的状态
                            class_before = elem.get_attribute('class') or ''
                            aria_before = elem.get_attribute('aria-label') or ''

                            # 尝试多种点击方式
                            try:
                                # 方式1: JavaScript 点击
                                driver.execute_script("arguments[0].click();", elem)
                            except:
                                try:
                                    # 方式2: Selenium 原生点击
                                    elem.click()
                                except:
                                    # 方式3: 模拟鼠标点击
                                    from selenium.webdriver.common.action_chains import ActionChains
                                    ActionChains(driver).move_to_element(elem).click().perform()

                            # 等待状态更新
                            time.sleep(1.5)

                            # 验证是否真的点赞成功（检查状态变化）
                            try:
                                class_after = elem.get_attribute('class') or ''
                                aria_after = elem.get_attribute('aria-label') or ''

                                # 方法1: 检查按钮本身的 class 是否包含 active/checked/liked 等状态
                                button_status_changed = (
                                    ('active' in class_after and 'active' not in class_before) or
                                    ('checked' in class_after and 'checked' not in class_before) or
                                    ('liked' in class_after and 'liked' not in class_before) or
                                    (class_after != class_before)
                                )

                                # 方法2: 检查子元素（点赞数）是否包含 woo-like-liked
                                child_status_changed = False
                                try:
                                    count_spans = elem.find_elements(By.CSS_SELECTOR, 'span.woo-like-count')
                                    if count_spans:
                                        count_class = count_spans[0].get_attribute('class') or ''
                                        child_status_changed = 'woo-like-liked' in count_class
                                        if child_status_changed:
                                            print(f"      💡 检测到点赞数span包含 woo-like-liked")
                                except:
                                    pass

                                # 任一方法检测到状态变化即为成功
                                status_changed = button_status_changed or child_status_changed

                                if status_changed:
                                    print("      ✅ 点赞成功（已验证状态变化）")
                                    logging.info("点赞成功（已验证）")
                                    return True
                                else:
                                    print(f"      ⚠️  点击了但状态未变化")
                                    print(f"      - 按钮点击前 class: {class_before[:50]}")
                                    print(f"      - 按钮点击后 class: {class_after[:50]}")
                                    # 继续尝试下一个元素
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

        # 如果所有方法都失败，输出调试信息
        print("      ❌ 未找到可用的点赞按钮")
        print("      🔧 调试信息：")

        # 输出当前微博卡片中所有的按钮
        all_buttons = weibo_element.find_elements(By.TAG_NAME, 'button')
        print(f"      - 找到 {len(all_buttons)} 个按钮")

        for i, btn in enumerate(all_buttons[:5], 1):  # 只显示前5个
            try:
                text = btn.text.strip()[:20] if btn.text else '(无文本)'
                class_name = btn.get_attribute('class')[:50] if btn.get_attribute('class') else '(无class)'
                print(f"      - 按钮{i}: 文本='{text}' class='{class_name}'")
            except:
                pass

        logging.warning("点赞失败：未找到点赞按钮")
        return False

    except Exception as e:
        print(f"      ❌ 点赞异常: {e}")
        logging.error(f"点赞异常: {e}")
        import traceback
        traceback.print_exc()
        return False

# @capture_traffic("weibo", "comment")  # 已被 run_capture.py 的会话级抓包替代
def comment_weibo(driver, content_list):
    """评论微博"""
    try:
        # 查找评论图标
        comment_icon = driver.find_element(By.CSS_SELECTOR, 'i[class*="woo-font--comment"]')
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_icon)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", comment_icon)
        time.sleep(2)

        # 查找输入框
        comment_input = driver.find_element(By.CSS_SELECTOR, 'textarea[placeholder*="评论"]')
        driver.execute_script("arguments[0].click();", comment_input)
        time.sleep(0.5)

        # 随机选择评论内容
        content = random.choice(content_list)
        comment_input.send_keys(content)
        time.sleep(1)

        # 查找发送按钮
        buttons = driver.find_elements(By.CSS_SELECTOR, 'button[class*="woo-button-primary"]')
        for btn in buttons:
            if '评论' in btn.text:
                driver.execute_script("arguments[0].click();", btn)
                print(f"      ✅ 点击发送按钮")

                # 等待评论提交完成
                print(f"      ⏱️  等待评论提交...")
                time.sleep(3)  # 微博通常比Facebook快，3秒足够

                # 验证评论是否成功（检查输入框是否清空或隐藏）
                try:
                    # 微博评论成功后，评论框会关闭或清空
                    is_empty = comment_input.get_attribute('value') == "" or not comment_input.is_displayed()
                    if is_empty:
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

        logging.warning("评论失败：未找到发送按钮")
        return False
    except Exception as e:
        print(f"      ❌ 评论失败: {e}")
        logging.error(f"评论异常: {e}")
        return False

# @capture_traffic("weibo", "repost")  # 已被 run_capture.py 的会话级抓包替代
def repost_weibo(driver, repost_templates):
    """转发微博（带评论）"""
    try:
        # 查找转发图标
        repost_icon = driver.find_element(By.CSS_SELECTOR, 'i[class*="woo-font--retweet"]')
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", repost_icon)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", repost_icon)
        print("      点击转发图标，等待弹窗...")

        # 等待转发弹窗完全加载
        time.sleep(3)

        # 先定位转发弹窗，避免误选页面顶部的快捷发帖框
        try:
            print("      🔍 查找转发弹窗...")
            dialog_selectors = [
                'div[class*="woo-dialog"]',
                'div[class*="dialog"]',
                'div[class*="Dialog"]',
                'div[role="dialog"]',
                'div[class*="modal"]',
                'div[class*="Modal"]',
                'div[class*="popup"]',
            ]

            dialog = None
            for selector in dialog_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            # 检查是否是转发弹窗（包含"转发"文字）
                            if '转发' in elem.text:
                                dialog = elem
                                print(f"      ✅ 找到转发弹窗: {selector}")
                                break
                    if dialog:
                        break
                except:
                    continue

            if not dialog:
                print("      ⚠️  未找到转发弹窗，使用整个页面查找")
                dialog = driver  # 降级：在整个页面查找

        except Exception as e:
            print(f"      ⚠️  定位弹窗失败: {e}，使用整个页面")
            dialog = driver

        # 在弹窗内查找转发输入框并输入内容
        try:
            print("      🔍 在弹窗内查找输入框...")
            textarea_selectors = [
                # 优先匹配转发评论框的特征
                'textarea[id^="comment-textarea-"]',  # id 以 comment-textarea- 开头
                'textarea[placeholder*="评论"]',      # placeholder 包含"评论"
                'textarea[placeholder*="转发"]',
                'textarea[placeholder*="说点什么"]',
                'textarea[class*="input"]',
                'div[contenteditable="true"]',
                'textarea',  # 兜底
            ]

            textarea = None
            for selector in textarea_selectors:
                try:
                    elements = dialog.find_elements(By.CSS_SELECTOR, selector)  # 在弹窗内查找
                    if elements:
                        # 检查元素是否可见，并排除快捷发帖框
                        for elem in elements:
                            if elem.is_displayed():
                                placeholder = elem.get_attribute('placeholder') or ''
                                # 排除快捷发帖框（包含"新鲜事"）
                                if '新鲜事' in placeholder:
                                    print(f"      ⚠️  跳过快捷发帖框: {placeholder}")
                                    continue
                                textarea = elem
                                print(f"      ✅ 找到输入框: {selector}, placeholder='{placeholder}'")
                                break
                        if textarea:
                            break
                except:
                    continue

            # 随机选择转发评论并输入
            if textarea:
                content = random.choice(repost_templates)
                print(f"      📝 准备输入转发评论: {content}")

                # 滚动到输入框位置
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", textarea)
                time.sleep(0.5)

                # 点击输入框激活
                driver.execute_script("arguments[0].click();", textarea)
                time.sleep(0.5)

                # 输入内容
                textarea.send_keys(content)
                time.sleep(1.5)  # 增加等待时间，确保输入完成

                print(f"      ✅ 已输入转发评论: {content}")
            else:
                print("      ⚠️  未找到输入框，将直接转发（不带评论）")
                # 调试信息：打印弹窗内所有 textarea
                all_textareas = dialog.find_elements(By.TAG_NAME, 'textarea')
                print(f"      🔧 调试：弹窗内共有 {len(all_textareas)} 个 textarea")
                for i, ta in enumerate(all_textareas[:3], 1):
                    try:
                        placeholder = ta.get_attribute('placeholder') or '(无)'
                        class_name = ta.get_attribute('class')[:50] or '(无)'
                        visible = ta.is_displayed()
                        print(f"      - textarea{i}: placeholder='{placeholder}', visible={visible}, class='{class_name}'")
                    except:
                        pass

        except Exception as e:
            print(f"      ⚠️  输入转发内容失败: {e}")
            import traceback
            traceback.print_exc()

        # 等待转发按钮可见并点击
        try:
            wait = WebDriverWait(driver, 5)
            # 查找转发弹窗中的转发按钮
            repost_btn = wait.until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'woo-button') and contains(., '转发')]"))
            )

            # 再等一下确保按钮可点击（输入内容后 disabled 属性会被移除）
            time.sleep(1)

            driver.execute_script("arguments[0].click();", repost_btn)
            print("      ✅ 转发成功")
            logging.info("转发成功")
            time.sleep(2)
            return True
        except:
            print("      ⚠️  未找到转发按钮，取消转发")
            logging.warning("转发失败：未找到转发按钮")
            # 尝试关闭弹窗（按 ESC）
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(1)
            return False

    except Exception as e:
        print(f"      ❌ 转发失败: {e}")
        logging.error(f"转发异常: {e}")
        return False

# @capture_traffic("weibo", "post")  # 已被 run_capture.py 的会话级抓包替代
def post_weibo(driver, post_templates):
    """发布微博（直接使用页面顶部快捷发帖框）"""
    try:
        print("\n📝 准备发布微博...")

        # 直接找快捷发帖框（首页顶部，始终存在，无需点击写微博按钮）
        textarea = None
        for selector in [
            'textarea[placeholder*="有什么新鲜事想分享给大家"]',
            'textarea[placeholder*="有什么新鲜事"]',
            'textarea[class*="_input"]',
            'textarea',
        ]:
            try:
                elements = [e for e in driver.find_elements(By.CSS_SELECTOR, selector) if e.is_displayed()]
                if elements:
                    textarea = elements[0]
                    print(f"   ✅ 找到快捷发帖框: {selector}")
                    break
            except:
                continue

        if not textarea:
            print("   ❌ 未找到输入框")
            logging.warning("发帖失败：未找到快捷发帖框")
            return False

        # 输入内容
        content = random.choice(post_templates)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", textarea)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", textarea)
        time.sleep(0.5)
        textarea.send_keys(content)
        print(f"   ✅ 已输入内容: {content}")
        time.sleep(2)

        # 查找并点击发布按钮（输入内容后按钮才激活）
        publish_button = None
        for btn in driver.find_elements(By.XPATH, "//button[contains(., '发布') or contains(., '发送')]"):
            if btn.is_displayed() and ('发布' in btn.text or '发送' in btn.text):
                publish_button = btn
                break

        if not publish_button:
            print("   ❌ 未找到发布按钮")
            logging.warning("发帖失败：未找到发布按钮")
            return False

        driver.execute_script("arguments[0].click();", publish_button)
        print(f"   ✅ 发布成功！")
        logging.info(f"发布微博成功: {content}")
        time.sleep(3)
        return True

    except Exception as e:
        print(f"   ❌ 发帖失败: {e}")
        logging.error(f"发布微博异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def smart_browse_and_interact(
    driver,
    max_weibos=3,
    interaction_rate=0.3,
    enable_like=True,
    enable_comment=True,
    enable_repost=True,
    enable_post=False,  # 新增：是否启用发帖
    comment_templates=None,
    repost_templates=None,
    post_templates=None
):
    """
    智能浏览和互动 - 确保模式

    参数:
        max_weibos: 默认浏览多少条微博（默认3条）
        interaction_rate: 额外互动概率（达成目标后的额外互动概率）
        enable_like: 是否启用点赞（True则确保至少成功1次）
        enable_comment: 是否启用评论（True则确保至少成功1次）
        enable_repost: 是否启用转发（True则确保至少成功1次）
        enable_post: 是否启用发帖（True则确保至少成功1次）
        comment_templates: 评论模板列表（None则使用默认）
        repost_templates: 转发模板列表（None则使用默认）
        post_templates: 发帖文案模板列表（None则使用默认）

    新逻辑：
        - 如果 enable_like=True，确保至少成功点赞1次
        - 如果 enable_comment=True，确保至少成功评论1次
        - 如果 enable_repost=True，确保至少成功转发1次
        - 如果 enable_post=True，确保至少成功发帖1次
        - 最多尝试 max_weibos*3 条微博（避免无限循环）
    """
    print("\n🤖 开始智能浏览模式（确保模式）...")
    print(f"   - 默认浏览 {max_weibos} 条微博")
    print(f"   - 点赞: {'启用（确保≥1次）' if enable_like else '禁用'}")
    print(f"   - 评论: {'启用（确保≥1次）' if enable_comment else '禁用'}")
    print(f"   - 转发: {'启用（确保≥1次）' if enable_repost else '禁用'}")
    print(f"   - 发帖: {'启用（确保≥1次）' if enable_post else '禁用'}")

    # 使用默认模板（如果未提供）
    if comment_templates is None:
        comment_templates = get_comment_templates()
    if repost_templates is None:
        repost_templates = get_repost_templates()

    browsed_count = 0
    interacted_count = 0
    interacted_weibo_ids = set()  # 记录已互动的微博ID（通过URL去重，更可靠）
    posted_count = 0  # 记录发帖次数

    # 成功计数器
    success_count = {
        'like': 0,
        'comment': 0,
        'repost': 0,
        'post': 0,  # 新增：发帖计数
    }

    # 目标：每个启用的操作至少成功1次
    targets = {
        'like': 1 if enable_like else 0,
        'comment': 1 if enable_comment else 0,
        'repost': 1 if enable_repost else 0,
        'post': 1 if enable_post else 0,  # 使用 enable_post 控制
    }

    max_attempts = max_weibos * 3  # 最多尝试次数（避免无限循环）
    i = 0

    while i < max_attempts:
        i += 1

        # 检查是否达成所有目标
        all_targets_met = all(
            success_count[action] >= targets[action]
            for action in ['like', 'comment', 'repost', 'post']
        )

        # 如果已达成所有目标且浏览数达到默认值，退出
        if all_targets_met and browsed_count >= max_weibos:
            print(f"\n✅ 已达成所有目标！")
            print(f"   - 点赞成功: {success_count['like']} 次")
            print(f"   - 评论成功: {success_count['comment']} 次")
            print(f"   - 转发成功: {success_count['repost']} 次")
            if enable_post:
                print(f"   - 发帖成功: {success_count['post']} 次")
            break

        try:
            # 确保模式：如果启用发帖且还没发够，则发帖
            if enable_post and success_count['post'] < targets['post']:
                print(f"\n📝 [循环 {i}] 准备发帖（确保至少1次）...")
                logging.info(f"触发自动发帖（第 {i} 次循环）")

                # 使用发帖模板（如果没传则使用默认）
                templates = post_templates if post_templates else get_post_templates()

                if post_weibo(driver, templates):
                    success_count['post'] += 1
                    posted_count += 1
                    print("   ✅ 发帖成功！")
                    # 发帖后等待较长时间（模拟真人发帖后的停顿）
                    wait_time = random.uniform(5, 10)
                    print(f"   ⏱️  发帖后暂停 {wait_time:.1f} 秒...")
                    time.sleep(wait_time)

                    # 发帖后回到首页，继续浏览
                    print("   🏠 返回首页继续浏览...")
                    driver.get('https://weibo.com')
                    time.sleep(random.uniform(3, 5))
                else:
                    print("   ⚠️  发帖失败，继续尝试")
                    time.sleep(random.uniform(2, 4))

            # 继续正常的浏览和互动流程
            # 检查当前页面状态
            current_url = driver.current_url
            if 'data:' in current_url or 'about:blank' in current_url or 'weibo.com' not in current_url:
                print(f"\n   ⚠️  检测到页面异常: {current_url}")
                print(f"   🔄 返回首页...")
                driver.get('https://weibo.com')
                time.sleep(3)

            # 随机滚动
            scroll_times = random.randint(1, 3)
            for _ in range(scroll_times):
                random_scroll(driver)

            # 模拟阅读
            simulate_reading(2, 5)

            # 查找当前可见的微博卡片
            weibo_cards = driver.find_elements(By.TAG_NAME, 'article')

            if not weibo_cards or len(weibo_cards) < 2:
                print("   ⚠️  未找到足够的微博卡片，继续滚动...")
                # 强制向下滚动加载新内容
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(2)
                continue

            print(f"   ✅ 找到 {len(weibo_cards)} 个微博卡片")

            # 从中间靠后的位置选择微博（避免重复选前几个）
            start_idx = min(3, len(weibo_cards) - 5)
            end_idx = min(start_idx + 5, len(weibo_cards))
            candidate_weibos = weibo_cards[start_idx:end_idx]

            # 随机选择一个微博（暂不过滤，等进入详情页后用URL去重）
            current_weibo = random.choice(candidate_weibos)

            browsed_count += 1
            print(f"\n📄 浏览第 {browsed_count} 条微博...")

            # 滚动到该微博位置
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", current_weibo)
            simulate_reading(3, 7)

            # 智能决定互动操作（新逻辑）
            actions = []

            # 优先执行未达成目标的操作
            if enable_like and success_count['like'] < targets['like']:
                actions.append('like')

            if enable_comment and success_count['comment'] < targets['comment']:
                actions.append('comment')

            if enable_repost and success_count['repost'] < targets['repost']:
                actions.append('repost')

            # 如果没有任何操作可执行，跳过
            if not actions:
                # 如果还有未达成的目标，提示继续尝试
                if not all_targets_met:
                    print("   ⚠️  本条微博未选择互动，继续寻找...")
                else:
                    print("   👀 目标已达成，只是浏览，不互动")
                continue

            # 显示选择的操作和目标进度
            print(f"   💬 决定互动: {', '.join(actions)}")
            progress = (f"      当前进度: 点赞{success_count['like']}/{targets['like']}, "
                       f"评论{success_count['comment']}/{targets['comment']}, "
                       f"转发{success_count['repost']}/{targets['repost']}")
            if enable_post:
                progress += f", 发帖{success_count['post']}/{targets['post']}"
            print(progress)

            # 新逻辑：先进入详情页，再执行所有操作（包括点赞）
            need_detail_page = 'comment' in actions or 'repost' in actions

            if need_detail_page:
                # 需要进入详情页
                try:
                    # 找到微博内的链接（更可靠的方式）
                    print("      🖱️  查找微博详情页链接...")
                    detail_link = None

                    try:
                        # 方法1：查找article内的a标签链接
                        links = current_weibo.find_elements(By.TAG_NAME, 'a')
                        for link in links:
                            href = link.get_attribute('href')
                            # 微博详情页链接格式：包含/数字/字母数字
                            if href and ('/status/' in href or re.search(r'/\d+/[A-Za-z0-9]+', href)):
                                detail_link = href
                                print(f"      ✅ 找到详情页链接: {detail_link}")
                                break

                        if not detail_link:
                            # 方法2：尝试点击微博正文区域
                            print("      ⚠️  未找到详情页链接，尝试点击正文区域...")
                            # 查找微博正文
                            content_areas = current_weibo.find_elements(By.XPATH, ".//*[contains(@class, 'content') or contains(@class, 'text')]")
                            if content_areas:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", content_areas[0])
                                time.sleep(0.5)
                                content_areas[0].click()
                                time.sleep(3)
                            else:
                                # 方法3：点击article本身
                                current_weibo.click()
                                time.sleep(3)
                        else:
                            # 使用链接直接访问（最可靠）
                            print(f"      🔗 直接访问详情页...")
                            driver.get(detail_link)
                            time.sleep(3)

                    except Exception as e:
                        print(f"      ⚠️  查找链接失败: {e}，尝试直接点击...")
                        current_weibo.click()
                        time.sleep(3)

                    # 打印当前URL用于调试
                    print(f"      🔗 当前页面URL: {driver.current_url}")

                    # 检查页面是否正常跳转
                    current_url = driver.current_url
                    if 'data:' in current_url or current_url == 'about:blank' or 'weibo.com' not in current_url:
                        print(f"      ❌ 页面跳转异常！URL: {current_url}")
                        print(f"      🔄 返回首页重试...")
                        driver.get('https://weibo.com')
                        time.sleep(3)

                        # 验证是否成功返回
                        if 'weibo.com' in driver.current_url:
                            print(f"      ✅ 已返回首页")
                        else:
                            print(f"      ❌ 返回失败，再次尝试...")
                            driver.get('https://weibo.com')
                            time.sleep(3)
                        continue

                    # 提取微博ID用于去重（从URL中提取）
                    weibo_id = None
                    try:
                        import re
                        # 打印当前URL用于调试
                        print(f"      🔗 当前URL: {current_url}")

                        # 多种URL格式匹配
                        # 格式1: https://weibo.com/1234567/ABCDEFG
                        # 格式2: https://weibo.com/detail/ABCDEFG
                        # 格式3: https://m.weibo.cn/detail/ABCDEFG
                        patterns = [
                            r'/(\d+)/([A-Za-z0-9]+)',  # 格式1
                            r'/detail/([A-Za-z0-9]+)',  # 格式2
                            r'weibo\.com/([^/]+)/([^/?]+)',  # 通用格式
                        ]

                        for pattern in patterns:
                            match = re.search(pattern, current_url)
                            if match:
                                if len(match.groups()) == 2:
                                    weibo_id = f"{match.group(1)}_{match.group(2)}"
                                else:
                                    weibo_id = match.group(1)
                                break

                        if not weibo_id:
                            # 如果没有匹配到，使用URL的hash值
                            weibo_id = str(hash(current_url))
                            print(f"      ⚠️  使用URL hash作为ID: {weibo_id}")

                        # 检查是否已经互动过这条微博
                        if weibo_id in interacted_weibo_ids:
                            print(f"      ⚠️  这条微博已经互动过（ID: {weibo_id}），跳过")
                            print(f"      🔄 返回首页...")
                            driver.get('https://weibo.com')
                            time.sleep(3)

                            # 验证返回状态
                            if 'weibo.com' in driver.current_url:
                                print(f"      ✅ 已返回首页，继续浏览")
                            else:
                                print(f"      ❌ 返回异常: {driver.current_url}")
                                driver.get('https://weibo.com')
                                time.sleep(3)
                            continue

                        # 记录这条微博（在执行操作之前记录，避免操作失败后重复尝试）
                        interacted_weibo_ids.add(weibo_id)
                        print(f"      📌 微博ID: {weibo_id}")
                    except Exception as e:
                        print(f"      ⚠️  提取微博ID失败: {e}")
                        import traceback
                        traceback.print_exc()

                    # 在详情页内执行所有操作（包括点赞）
                    if 'like' in actions:
                        # 在详情页找到主微博元素（article）
                        try:
                            # 详情页通常第一个 article 就是主微博
                            detail_articles = driver.find_elements(By.TAG_NAME, 'article')
                            if detail_articles:
                                main_weibo = detail_articles[0]
                                print("      📌 使用详情页主微博元素")
                                # 使用增强版 like_weibo 函数（有状态验证）
                                if like_weibo(driver, main_weibo):
                                    success_count['like'] += 1
                                    interacted_count += 1
                                    logging.info("详情页点赞成功")
                                else:
                                    print("      ⚠️  详情页点赞未成功")
                                    logging.warning("详情页点赞失败：未找到按钮或状态未改变")
                            else:
                                # 如果找不到 article，尝试在整个页面查找
                                print("      ⚠️  未找到article元素，在整个页面查找...")
                                body = driver.find_element(By.TAG_NAME, 'body')
                                if like_weibo(driver, body):
                                    success_count['like'] += 1
                                    interacted_count += 1
                                    logging.info("详情页点赞成功（body）")
                                else:
                                    logging.warning("详情页点赞失败")
                            time.sleep(random.uniform(1, 2))
                        except Exception as e:
                            print(f"      ⚠️  详情页点赞异常: {e}")
                            logging.error(f"详情页点赞异常: {e}")
                            import traceback
                            traceback.print_exc()

                    if 'comment' in actions:
                        if comment_weibo(driver, comment_templates):
                            success_count['comment'] += 1
                            interacted_count += 1
                            time.sleep(random.uniform(1, 2))

                    if 'repost' in actions:
                        if repost_weibo(driver, repost_templates):
                            success_count['repost'] += 1
                            interacted_count += 1
                            time.sleep(random.uniform(1, 2))

                    # 返回首页（不使用back，直接访问更稳定）
                    print("      ⬅️  返回首页...")
                    try:
                        # 直接访问首页，比back()更可靠
                        driver.get('https://weibo.com')
                        time.sleep(random.uniform(2, 4))

                        # 验证是否成功返回
                        if 'weibo.com' not in driver.current_url:
                            print("      ⚠️  返回首页失败，重试...")
                            driver.get('https://weibo.com')
                            time.sleep(3)
                        else:
                            print("      ✅  已返回首页")
                    except Exception as e:
                        print(f"      ⚠️  返回首页异常: {e}")
                        driver.get('https://weibo.com')
                        time.sleep(3)

                except Exception as e:
                    print(f"      ⚠️  详情页操作失败: {e}")
                    # 尝试恢复到首页
                    try:
                        if 'data:' in driver.current_url or 'about:blank' in driver.current_url:
                            driver.get('https://weibo.com')
                            time.sleep(3)
                        else:
                            driver.back()
                            time.sleep(2)
                    except:
                        driver.get('https://weibo.com')
                        time.sleep(3)
            else:
                # 只有点赞，在列表页直接操作
                if 'like' in actions:
                    if like_weibo(driver, current_weibo):
                        success_count['like'] += 1
                        interacted_count += 1
                        print("      ✅ 点赞成功（列表页）")
                        time.sleep(random.uniform(1, 2))

            # 随机暂停（模拟思考时间）
            time.sleep(random.uniform(2, 5))

            # 每次循环后向下滚动一段距离，确保下次能看到新内容
            scroll_distance = random.randint(400, 800)
            driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            time.sleep(random.uniform(1, 2))

        except Exception as e:
            print(f"   ❌ 处理微博时出错: {e}")
            continue

    print("\n" + "="*60)
    print(f"📊 浏览完成！")
    print(f"   - 浏览了 {browsed_count} 条微博")
    print(f"   - 总互动次数: {interacted_count} 次")
    print(f"   - 成功点赞: {success_count['like']} 次")
    print(f"   - 成功评论: {success_count['comment']} 次")
    print(f"   - 成功转发: {success_count['repost']} 次")
    if enable_post:
        print(f"   - 成功发帖: {success_count['post']} 次")
    print("="*60)

    # 记录统计信息到日志
    summary = (f"浏览完成 - 浏览: {browsed_count}, 互动: {interacted_count}, "
               f"点赞: {success_count['like']}, 评论: {success_count['comment']}, "
               f"转发: {success_count['repost']}")
    if enable_post:
        summary += f", 发帖: {success_count['post']}"
    logging.info(summary)

def main():
    # 初始化日志系统
    setup_logging()

    print("="*60)
    print("微博智能自动化脚本 v3.0")
    print("="*60)
    logging.info("脚本启动")

    print("\n启动浏览器...")
    driver = create_driver(use_proxy=True)
    print("✅ 浏览器启动成功！")
    logging.info("浏览器启动成功")

    try:
        # 访问微博首页
        print("\n访问微博首页...")
        driver.get('https://weibo.com')
        time.sleep(3)

        # 检查登录状态
        if not check_login(driver):
            logging.warning("检测到未登录状态，等待用户登录")
            wait_for_login(driver)
            logging.info("用户登录完成")
        else:
            print("✅ 已登录")
            logging.info("已登录状态")

        # 获取发帖模板
        post_templates = get_post_templates()

        # 选择测试模式
        print("\n" + "="*60)
        print("请选择测试行为:")
        print("1. 纯浏览（不互动）")
        print("2. 点赞测试")
        print("3. 评论测试")
        print("4. 转发测试")
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
                max_weibos=3,
                interaction_rate=0.0,
                enable_like=False,
                enable_comment=False,
                enable_repost=False,
                enable_post=False
            )

        elif choice == '2':
            # 点赞测试
            print("\n👍 点赞测试模式（确保至少成功1次）")
            logging.info("开始点赞测试")
            smart_browse_and_interact(
                driver,
                max_weibos=3,
                interaction_rate=0.3,
                enable_like=True,
                enable_comment=False,
                enable_repost=False,
                enable_post=False
            )

        elif choice == '3':
            # 评论测试
            print("\n💬 评论测试模式（确保至少成功1次）")
            logging.info("开始评论测试")
            comment_templates = get_comment_templates()
            smart_browse_and_interact(
                driver,
                max_weibos=3,
                interaction_rate=0.3,
                enable_like=False,
                enable_comment=True,
                enable_repost=False,
                enable_post=False,
                comment_templates=comment_templates
            )

        elif choice == '4':
            # 转发测试
            print("\n🔄 转发测试模式（确保至少成功1次）")
            logging.info("开始转发测试")
            repost_templates = get_repost_templates()
            smart_browse_and_interact(
                driver,
                max_weibos=3,
                interaction_rate=0.3,
                enable_like=False,
                enable_comment=False,
                enable_repost=True,
                enable_post=False,
                repost_templates=repost_templates
            )

        elif choice == '5':
            # 发帖测试
            print("\n📝 发帖测试模式（在浏览中发帖）")
            logging.info("开始发帖测试")
            smart_browse_and_interact(
                driver,
                max_weibos=3,
                interaction_rate=0.0,
                enable_like=False,
                enable_comment=False,
                enable_repost=False,
                enable_post=True  # 启用发帖，确保至少1次
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
