#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博智能自动化脚本 v3.0
模拟真实用户行为，随机浏览和互动
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import random
import sys
import logging
from datetime import datetime
import re

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

def create_driver(use_proxy=True):
    """创建 Chrome 浏览器实例（保留登录状态）"""
    chrome_options = Options()

    # 📂 设置用户数据目录（保存登录状态）
    import os
    user_data_dir = os.path.expanduser('~/selenium_profiles/weibo')
    chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
    chrome_options.add_argument('--profile-directory=Default')
    print(f"💾 使用配置文件: {user_data_dir}")

    if use_proxy:
        chrome_options.add_argument('--proxy-server=socks5://127.0.0.1:10818')

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
                print(f"      ✅ 评论成功: {content}")
                logging.info(f"评论成功: {content}")
                return True

        logging.warning("评论失败：未找到发送按钮")
        return False
    except Exception as e:
        print(f"      ❌ 评论失败: {e}")
        logging.error(f"评论异常: {e}")
        return False

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

        # 查找转发输入框并输入内容
        try:
            textarea_selectors = [
                'textarea[placeholder*="分享"]',
                'textarea[placeholder*="转发"]',
                'textarea[class*="_input"]',
            ]

            textarea = None
            for selector in textarea_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        textarea = elements[0]
                        break
                except:
                    continue

            # 随机选择转发评论
            if textarea:
                content = random.choice(repost_templates)
                driver.execute_script("arguments[0].click();", textarea)
                time.sleep(0.5)
                textarea.send_keys(content)
                time.sleep(1)
                print(f"      ✅ 已输入转发评论: {content}")
            else:
                print("      ⚠️  未找到输入框，直接转发")

        except Exception as e:
            print(f"      ⚠️  输入转发内容失败: {e}")

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

def post_weibo(driver, post_templates):
    """发布微博"""
    try:
        print("\n📝 准备发布微博...")

        # 第一步：找到并点击"发微博"按钮
        print("   查找发微博按钮...")

        # 多种选择器（按优先级）
        post_button_selectors = [
            # 通过title属性（最可靠）- 实际是"发微博"
            "//button[@title='发微博']",
            "//*[contains(@title, '发微博')]",
            "//*[contains(@title, '写微博')]",

            # 通过class包含_pub（发布）关键字
            "//button[contains(@class, '_pub')]",

            # 通过SVG的title标签
            "//*[.//*[local-name()='svg']/*[local-name()='title' and contains(text(), '写微博')]]",

            # 通过aria-label
            "//*[contains(@aria-label, '写微博')]",
            "//*[contains(@aria-label, '发微博')]",

            # 通过文本内容
            "//button[contains(text(), '写微博')]",
            "//button[contains(text(), '发微博')]",
        ]

        post_button = None
        for selector in post_button_selectors:
            try:
                buttons = driver.find_elements(By.XPATH, selector)
                if buttons:
                    post_button = buttons[0]
                    print(f"   ✅ 找到写微博按钮: {selector}")
                    break
            except Exception as e:
                continue

        if not post_button:
            # 调试模式：打印所有可能相关的按钮
            print("   ⚠️  未找到写微博按钮，开启调试模式...")
            print("\n   【调试信息】页面上的所有按钮和链接（包含'写'或'发'字的）：")

            all_clickable = driver.find_elements(By.XPATH, "//button | //a")
            found_candidates = []

            for elem in all_clickable[:50]:  # 只检查前50个
                try:
                    text = elem.text.strip()
                    title = elem.get_attribute('title') or ''
                    aria_label = elem.get_attribute('aria-label') or ''
                    class_name = elem.get_attribute('class') or ''

                    if '写' in text or '发' in text or '写' in title or '发' in title:
                        info = f"文本: {text[:20]} | title: {title[:30]} | aria: {aria_label[:30]}"
                        print(f"   - {info}")
                        found_candidates.append(elem)
                except:
                    pass

            if found_candidates:
                print(f"\n   找到 {len(found_candidates)} 个可能的候选按钮，尝试点击第一个...")
                post_button = found_candidates[0]
            else:
                print("   ❌ 未找到任何相关按钮")
                return False

        # 点击打开发帖框
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", post_button)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", post_button)
        print("   ✅ 点击写微博按钮，等待输入框...")
        time.sleep(3)

        # 第二步：查找发帖输入框
        print("   查找输入框...")
        textarea_selectors = [
            # 实际的placeholder文本
            'textarea[placeholder*="有什么新鲜事想分享给大家"]',
            'textarea[placeholder*="有什么新鲜事"]',
            'textarea[placeholder*="分享"]',
            # 通过class
            'textarea[class*="_input"]',
            'textarea[class*="input"]',
            # 通用选择器
            'div[contenteditable="true"]',
            'textarea',
        ]

        textarea = None
        for selector in textarea_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    textarea = elements[0]
                    print(f"   ✅ 找到输入框: {selector}")
                    break
            except:
                continue

        if not textarea:
            print("   ❌ 未找到输入框")
            return False

        # 第三步：输入内容
        content = random.choice(post_templates)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", textarea)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", textarea)
        time.sleep(0.5)
        textarea.send_keys(content)
        print(f"   ✅ 已输入内容: {content}")
        time.sleep(2)

        # 第四步：查找并点击发布按钮
        print("   查找发布按钮...")
        time.sleep(2)  # 等待按钮状态更新（输入内容后才可点击）

        publish_button_selectors = [
            # 包含"发布"文字的按钮
            "//button[contains(., '发布')]",
            "//button[contains(text(), '发布')]",
            "//span[contains(text(), '发布')]/parent::button",

            # 包含"发送"文字的按钮
            "//button[contains(., '发送')]",

            # 通过class（woo-button开头的主按钮）
            "//button[contains(@class, 'woo-button-primary')]",
            "//button[contains(@class, 'woo-button-main')]",

            # submit类型的按钮
            "//button[@type='submit']",
        ]

        publish_button = None
        for selector in publish_button_selectors:
            try:
                buttons = driver.find_elements(By.XPATH, selector)

                for btn in buttons:
                    btn_text = btn.text.strip()
                    if '发布' in btn_text or '发送' in btn_text:
                        publish_button = btn
                        print(f"   ✅ 找到发布按钮: {btn_text}")
                        break
                if publish_button:
                    break
            except:
                continue

        if publish_button:
            # 检查按钮是否可点击
            is_disabled = publish_button.get_attribute('disabled')
            if is_disabled:
                print("   ⚠️  按钮是禁用状态，等待1秒...")
                time.sleep(1)

            # 点击发布
            driver.execute_script("arguments[0].click();", publish_button)
            print(f"   ✅ 发布成功！")
            logging.info(f"发布微博成功: {content}")
            time.sleep(3)
            return True
        else:
            print("   ⚠️  未找到发布按钮，显示调试信息...")
            logging.warning("发布失败：未找到发布按钮")
            # 打印所有按钮
            all_buttons = driver.find_elements(By.TAG_NAME, 'button')
            print(f"\n   当前弹窗中的所有按钮（前10个）：")
            for i, btn in enumerate(all_buttons[:10], 1):
                try:
                    text = btn.text.strip()[:30]
                    class_name = btn.get_attribute('class')[:50]
                    print(f"   {i}. 文本: '{text}' | class: {class_name}")
                except:
                    pass

            print("\n   请手动点击发布按钮...")
            input("   手动点击后按回车继续...")
            logging.info("手动发布微博完成")
            return True

    except Exception as e:
        print(f"   ❌ 发帖失败: {e}")
        logging.error(f"发布微博异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def smart_browse_and_interact(driver, max_weibos=10, interaction_rate=0.3, post_templates=None, post_rate=0.08):
    """
    智能浏览和互动

    参数:
        max_weibos: 最多浏览多少条微博
        interaction_rate: 互动概率（0-1），例如 0.3 表示 30% 的微博会互动
        post_templates: 发帖文案模板列表
        post_rate: 发帖概率（0-1），例如 0.08 表示每次循环有 8% 的概率发帖
    """
    print("\n🤖 开始智能浏览模式...")
    print(f"   - 最多浏览 {max_weibos} 条微博")
    print(f"   - 互动概率: {interaction_rate*100:.0f}%")
    print(f"   - 发帖概率: {post_rate*100:.0f}%" if post_templates else "   - 发帖功能: 未启用")

    # 预定义的评论内容（丰富多样，50+条，移除emoji避免编码问题）
    comment_templates = [
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

        # 简短赞美类（替代emoji）
        "赞", "火", "顶", "棒", "妙", "好", "强", "赞一个", "给力",
    ]

    # 预定义的转发评论（更多样化，50+条）
    repost_templates = [
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

    browsed_count = 0
    interacted_count = 0
    interacted_weibo_ids = set()  # 记录已互动的微博ID（通过URL去重，更可靠）
    posted_count = 0  # 记录发帖次数

    for i in range(max_weibos):
        try:
            # 每次循环开始时，随机判断是否发帖（小概率）
            if post_templates and random.random() < post_rate:
                print(f"\n📝 [循环 {i+1}] 准备发帖...")
                logging.info(f"触发自动发帖（第 {i+1} 次循环）")
                if post_weibo(driver, post_templates):
                    posted_count += 1
                    print("   ✅ 发帖成功！")
                    # 发帖后等待较长时间（模拟真人发帖后的停顿）
                    wait_time = random.uniform(30, 60)
                    print(f"   ⏱️  发帖后暂停 {wait_time:.1f} 秒...")
                    time.sleep(wait_time)

                    # 发帖后回到首页，继续浏览
                    print("   🏠 返回首页继续浏览...")
                    driver.get('https://weibo.com')
                    time.sleep(random.uniform(3, 5))
                else:
                    print("   ⚠️  发帖失败，继续浏览")
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

            # 随机决定是否互动
            if random.random() < interaction_rate:
                print("   💬 决定互动...")

                # 随机选择互动方式（可以多选）
                actions = []

                # 70% 概率点赞
                if random.random() < 0.9:
                    actions.append('like')

                # 45% 概率评论
                if random.random() < 0.8:
                    actions.append('comment')

                # 35% 概率转发
                if random.random() < 0.6:
                    actions.append('repost')

                # 如果没有选中任何操作，默认点赞
                if not actions:
                    actions = ['like']

                print(f"      选择操作: {', '.join(actions)}")

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
                                interacted_count += 1
                                time.sleep(random.uniform(1, 2))

                        if 'repost' in actions:
                            if repost_weibo(driver, repost_templates):
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
                            interacted_count += 1
                            print("      ✅ 点赞成功（列表页）")
                            time.sleep(random.uniform(1, 2))
            else:
                print("   👀 只是浏览，不互动")

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
    print(f"   - 互动了 {interacted_count} 次")
    if post_templates:
        print(f"   - 发帖了 {posted_count} 次")
    print("="*60)

    # 记录统计信息到日志
    summary = f"浏览完成 - 浏览: {browsed_count}, 互动: {interacted_count}"
    if post_templates:
        summary += f", 发帖: {posted_count}"
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

        # 预定义的发帖文案（丰富多样，移除emoji避免编码问题）
        post_templates = [
            "今天天气真不错，心情也跟着好起来了",
            "分享一个今天学到的小知识～",
            "周末愉快！大家有什么计划吗？",
            "刚看了一部很棒的电影，强烈推荐！",
            "早安！新的一天，加油",
            "晚安，好梦～",
            "今天的晚霞真美啊",
            "读了一本好书，受益匪浅",
            "美好的一天从一杯咖啡开始",
            "记录一下今天的小确幸",
            "生活需要仪式感，今天给自己买了束花",
            "周一加油！这周也要元气满满！",
            "下午茶时间到～",
            "今天的运动打卡完成！",
            "分享一下今天的好心情",
            "又是充实的一天！",
            "今天遇到了一件很有趣的事情～",
            "保持热爱，奔赴山海",
            "慢慢来，一切都会好起来的",
            "今天也要开心呀！",
            "生活就是要慢慢品味",
            "记录平凡生活中的小美好",
            "今天的心情：晴转多云再转晴",
            "感恩遇见，珍惜拥有",
            "做自己喜欢的事，过自己想要的生活",
            "人生就是要不断尝试新事物",
            "今天的自己比昨天更进步一点点",
            "保持好奇心，保持童心",
            "简单的生活，简单的快乐",
            "每一天都是新的开始",
            "今天学到了一个新技能，很开心",
            "又是美好的一天",
            "今天吃到了超级好吃的东西",
            "分享一下最近的读书笔记",
            "记录生活中的点点滴滴",
            "今天天气好适合出门走走",
            "周末时光，悠闲惬意",
            "今天的小目标完成了",
            "努力生活，认真热爱",
            "保持微笑，保持善良",
            "今天也是充满希望的一天",
            "生活虽平凡，但依然要认真对待",
            "今天发现了一个好地方",
            "分享一下今天的随手拍",
            "简单的幸福，简单的满足",
            "今天的工作告一段落，可以放松一下了",
            "周五啦，期待周末",
            "今天学习了新东西，很有收获",
            "保持学习，保持进步",
            "今天的心情很不错",
        ]

        # 选择浏览模式
        print("\n" + "="*60)
        print("请选择浏览模式:")
        print("1. 智能浏览首页（推荐）")
        print("2. 浏览指定话题")
        print("3. 访问指定微博详情页")
        print("4. 发布微博")
        print("0. 退出")
        print("="*60)

        choice = input("请输入选项 (0-4): ").strip()

        if choice == '1':
            # 智能浏览首页
            max_weibos = int(input("浏览多少条微博？(建议 10-20): ") or "10")
            interaction_rate = float(input("互动概率？(0.1-0.5，例如 0.3 表示 30%): ") or "0.3")

            # 询问是否启用自动发帖
            enable_post = input("是否启用自动发帖功能？(y/n，默认y): ").strip().lower()
            if enable_post != 'n':
                post_rate = float(input("发帖概率？(0.05-0.15，例如 0.08 表示 8%，默认 0.08): ") or "0.08")
                logging.info(f"开始智能浏览首页 - 浏览数: {max_weibos}, 互动率: {interaction_rate*100}%, 发帖率: {post_rate*100}%")
                smart_browse_and_interact(driver, max_weibos, interaction_rate, post_templates, post_rate)
            else:
                logging.info(f"开始智能浏览首页 - 浏览数: {max_weibos}, 互动率: {interaction_rate*100}%, 发帖: 禁用")
                smart_browse_and_interact(driver, max_weibos, interaction_rate)

        elif choice == '2':
            # 浏览话题
            topic = input("请输入话题名称（例如: Python）: ")
            search_url = f"https://s.weibo.com/weibo?q=%23{topic}%23"
            print(f"\n访问话题: {topic}")
            logging.info(f"访问话题: {topic}")
            driver.get(search_url)
            time.sleep(3)

            max_weibos = int(input("浏览多少条微博？: ") or "10")
            interaction_rate = float(input("互动概率？(0.1-0.5): ") or "0.3")

            # 询问是否启用自动发帖
            enable_post = input("是否启用自动发帖功能？(y/n，默认y): ").strip().lower()
            if enable_post != 'n':
                post_rate = float(input("发帖概率？(0.05-0.15，默认 0.08): ") or "0.08")
                logging.info(f"开始话题浏览 - 话题: {topic}, 浏览数: {max_weibos}, 互动率: {interaction_rate*100}%, 发帖率: {post_rate*100}%")
                smart_browse_and_interact(driver, max_weibos, interaction_rate, post_templates, post_rate)
            else:
                logging.info(f"开始话题浏览 - 话题: {topic}, 浏览数: {max_weibos}, 互动率: {interaction_rate*100}%, 发帖: 禁用")
                smart_browse_and_interact(driver, max_weibos, interaction_rate)

        elif choice == '3':
            # 访问指定详情页（保留原功能）
            weibo_url = input("请输入微博详情页链接: ")
            if weibo_url.startswith('http'):
                driver.get(weibo_url)
                time.sleep(3)
                print("已打开详情页，可以手动操作或按回车退出...")
                input()

        elif choice == '4':
            # 发布微博
            print("\n" + "="*60)
            print("📝 发布微博模式")
            print("="*60)

            # 询问发布数量
            post_count_input = input("要发布几条微博？(默认1条，输入0则随机选择): ").strip()
            if post_count_input == '0':
                post_count = 1
            else:
                post_count = int(post_count_input or "1")

            # 询问是否自定义内容
            custom = input("使用预设文案？(y/n，默认y): ").strip().lower()

            for i in range(post_count):
                print(f"\n发布第 {i+1}/{post_count} 条微博...")

                if custom == 'n':
                    content = input("请输入微博内容: ")
                    if content:
                        # 手动模式：临时创建包含用户输入的列表
                        post_weibo(driver, [content])
                else:
                    # 自动模式：使用预设模板
                    post_weibo(driver, post_templates)

                # 如果还有下一条，等待一段时间（模拟人类行为）
                if i < post_count - 1:
                    wait_time = random.uniform(30, 90)
                    print(f"\n   ⏰ 等待 {wait_time:.0f} 秒后发布下一条...")
                    time.sleep(wait_time)

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
