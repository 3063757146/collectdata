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
        chrome_options.add_argument('--proxy-server=http://127.0.0.1:7897')

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
    """随机滚动页面，模拟人类浏览"""
    if random.random() < 0.9:
        if random.random() < 0.8:
            distance = random.randint(300, 600)
        else:
            distance = random.randint(800, 1200)
        driver.execute_script(f"window.scrollBy(0, {distance});")
    else:
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
        print("🔍 检测登录状态...")
        time.sleep(2)

        # 方法1: 查找登录按钮（如果存在则未登录）
        login_selectors = [
            "//a[contains(text(), '登录')]",
            "//a[contains(text(), '登錄')]",
            "//a[contains(text(), 'Log In')]",
            "//button[contains(text(), '登录')]",
            "//button[contains(text(), 'Log In')]",
        ]

        for selector in login_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed():
                        print(f"   ❌ 找到登录按钮 -> 未登录")
                        return False
            except:
                continue

        # 方法2: 查找已登录标志
        logged_in_selectors = [
            ('XPATH', "//div[@aria-label='你的个人主页']", '个人主页'),
            ('XPATH', "//div[@aria-label='Your profile']", 'Your profile'),
            ('XPATH', "//a[@aria-label='首页']", '首页链接'),
            ('XPATH', "//a[@aria-label='Home']", 'Home link'),
            ('CSS', 'img[data-visualcompletion="media-vc-image"]', '头像图片'),
        ]

        for method, selector, desc in logged_in_selectors:
            try:
                if method == 'XPATH':
                    elements = driver.find_elements(By.XPATH, selector)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)

                visible_elements = [e for e in elements if e.is_displayed()]
                if visible_elements:
                    print(f"   ✅ 找到已登录标志：{desc} -> 已登录")
                    return True
            except:
                continue

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
            # 基于用户提供的 class
            ('CSS', 'p.xdj266r.x14z9mp', '基于class'),
            # 通用选择器
            ('CSS', 'div[contenteditable="true"]', 'contenteditable div'),
            ('CSS', 'p[contenteditable="true"]', 'contenteditable p'),
            ('XPATH', '//div[@role="textbox"]', 'role textbox'),
            ('XPATH', '//p[@contenteditable="true"]', 'p contenteditable'),
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
        input_box.click()
        time.sleep(0.5)
        input_box.send_keys(content)
        print(f"      ✅ 已输入评论: {content}")
        time.sleep(1)

        # 查找并点击发送按钮
        print(f"      🔍 查找发送按钮...")

        # 等待发送按钮激活（输入内容后按钮才会激活）
        time.sleep(1.5)

        # 策略1: 查找 data-visualcompletion="ignore" 的覆盖层，找其父元素
        try:
            overlays = driver.find_elements(By.CSS_SELECTOR, 'div[data-visualcompletion="ignore"][role="none"]')
            if overlays:
                print(f"      ✓ 找到 {len(overlays)} 个候选覆盖层")

                # 从后往前找（最新出现的）
                for overlay in reversed(overlays):
                    try:
                        if not overlay.is_displayed():
                            continue

                        # 找父元素（真正的按钮）
                        parent = overlay.find_element(By.XPATH, '..')

                        # 检查父元素的 aria-label 或 role
                        aria_label = parent.get_attribute('aria-label') or ''
                        role = parent.get_attribute('role') or ''

                        # 如果是按钮或可点击的
                        if role == 'button' or 'aria-label' in parent.get_attribute('outerHTML'):
                            # 尝试点击父元素
                            try:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", parent)
                                time.sleep(0.3)
                                driver.execute_script("arguments[0].click();", parent)
                                print(f"      ✅ 点击发送按钮成功（父元素）")
                                logging.info(f"评论成功: {content}")
                                time.sleep(2)
                                return True
                            except:
                                # 如果父元素点击失败，尝试点击覆盖层本身
                                driver.execute_script("arguments[0].click();", overlay)
                                print(f"      ✅ 点击发送按钮成功（覆盖层）")
                                logging.info(f"评论成功: {content}")
                                time.sleep(2)
                                return True
                    except:
                        continue
        except:
            pass

        # 策略2: 尝试按回车发送
        print("      ⚠️  未找到发送按钮，尝试按回车发送...")
        try:
            input_box.send_keys(Keys.ENTER)
            print(f"      ✅ 评论已发送（回车）")
            logging.info(f"评论成功（回车）: {content}")
            time.sleep(2)
            return True
        except Exception as e:
            print(f"      ❌ 回车发送失败: {e}")
            return False

    except Exception as e:
        print(f"      ❌ 评论失败: {e}")
        logging.error(f"评论异常: {e}")
        return False

def share_post(driver, post_element, share_templates):
    """分享帖子（Facebook 版本）"""
    try:
        print(f"      🔍 查找分享按钮...")

        # 查找分享按钮
        share_btn_selectors = [
            ('XPATH', './/span[contains(text(), "分享")]/../..', '文本"分享"'),
            ('XPATH', './/*[@aria-label="分享"]', 'aria-label 分享'),
            ('XPATH', './/*[@aria-label="Share"]', 'aria-label Share'),
        ]

        share_btn = None
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
        print("      ✅ 点击分享按钮，等待菜单...")
        time.sleep(2)

        # 查找"立即分享"或"分享到动态"选项
        share_option_selectors = [
            "//span[contains(text(), '立即分享')]",
            "//span[contains(text(), '分享到动态')]",
            "//span[contains(text(), 'Share now')]",
            "//span[contains(text(), 'Share to Feed')]",
        ]

        share_option = None
        for selector in share_option_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed():
                        share_option = elem
                        print(f"      ✓ 找到分享选项")
                        break
                if share_option:
                    break
            except:
                continue

        if share_option:
            driver.execute_script("arguments[0].click();", share_option)
            print("      ✅ 分享成功")
            logging.info("分享成功")
            time.sleep(2)
            return True
        else:
            print("      ⚠️  未找到分享选项，取消操作")
            # 按 ESC 关闭菜单
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(1)
            return False

    except Exception as e:
        print(f"      ❌ 分享失败: {e}")
        logging.error(f"分享异常: {e}")
        return False

def smart_browse_and_interact(driver, max_posts=10, mode='browse'):
    """智能浏览和互动

    Args:
        mode: 'browse' 仅浏览 | 'like' 浏览+点赞 | 'comment' 浏览+评论
    """
    mode_names = {
        'browse': '仅浏览',
        'like': '浏览+点赞',
        'comment': '浏览+评论'
    }

    print(f"\n🤖 开始智能浏览模式: {mode_names.get(mode, '未知')}...")
    print(f"   - 最多浏览 {max_posts} 条帖子")

    # 评论模板（丰富多样，60+条，中英文结合）
    comment_templates = [
        # 赞同认可类
        "说得好", "有道理", "赞同", "说到心坎里了", "深有同感", "确实如此",
        "太对了", "一针见血", "说得太好了", "非常认同", "完全赞同", "正解",
        "Exactly", "So true", "I agree", "Well said", "Couldn't agree more",

        # 学习收获类
        "学到了", "涨知识了", "长见识了", "受教了", "学习了", "get到了",
        "原来如此", "恍然大悟", "又学到新东西了", "受益匪浅",
        "Learned something new", "Good to know", "Thanks for sharing",

        # 表扬夸赞类
        "厉害厉害", "很棒", "太棒了", "优秀", "牛", "nb", "666", "绝了",
        "高手", "大神", "强", "真棒",
        "Amazing", "Awesome", "Great", "Brilliant", "Excellent", "Fantastic",
        "Love it", "Well done", "Impressive", "Outstanding",

        # 支持鼓励类
        "支持一下", "加油", "顶", "挺你", "支持", "给你点赞",
        "Keep it up", "You got this", "Good luck", "Cheers",

        # 情感表达类
        "哈哈哈", "笑死", "太真实了", "破防了", "绷不住了", "爱了爱了",
        "感动", "好暖", "治愈", "舒服了",
        "Haha", "LOL", "So funny", "Made my day", "This is gold",

        # 互动交流类
        "同问", "我也是", "同感", "求更新", "期待后续",
        "想知道更多", "能详细说说吗",
        "Same here", "Me too", "I feel you", "Tell me more",

        # 简短赞美类
        "赞", "火", "顶", "棒", "妙", "好", "强", "赞一个", "给力",
        "Nice", "Cool", "Wow", "Dope", "Fire", "Yes",

        # 感谢类
        "感谢分享", "谢谢", "多谢", "Thanks", "Thank you", "Appreciate it",
    ]

    browsed_count = 0
    interacted_count = 0
    interacted_posts = set()  # 记录已互动的帖子（通过ID或位置）

    for i in range(max_posts):
        try:
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
                driver.execute_script("window.scrollBy(0, 1200);")  # 增加滚动距离
                time.sleep(2)
                continue

            print(f"   ✅ 找到 {len(posts)} 个帖子")

            # 从中间靠后的位置选择帖子，跳过已互动的
            start_idx = min(2, len(posts) - 3)
            end_idx = min(start_idx + 5, len(posts))  # 扩大候选范围
            candidate_posts = posts[start_idx:end_idx]

            # 过滤已互动的帖子
            available_posts = []
            for post in candidate_posts:
                # 获取帖子唯一标识（使用帖子文本的哈希）
                try:
                    post_text = post.text[:100]  # 前100个字符作为标识
                    post_id = hash(post_text)

                    if post_id not in interacted_posts:
                        available_posts.append((post, post_id))
                except:
                    continue

            if not available_posts:
                print("   ⚠️  所有可见帖子已互动过，向下滚动加载新帖子...")
                driver.execute_script("window.scrollBy(0, 1500);")  # 大幅滚动
                time.sleep(3)
                continue

            # 随机选择一个未互动的帖子
            current_post, post_id = random.choice(available_posts)
            browsed_count += 1
            print(f"\n📄 浏览第 {browsed_count} 条帖子（候选: {len(available_posts)}）...")

            # 滚动到该帖子
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", current_post)
            simulate_reading(3, 7)

            # 根据模式执行操作
            if mode == 'browse':
                print("   👀 仅浏览，不互动")

            elif mode == 'like':
                print("   💬 执行点赞...")
                if like_post(driver, current_post):
                    interacted_count += 1
                    interacted_posts.add(post_id)  # 记录已互动
                    time.sleep(random.uniform(1, 2))

            elif mode == 'comment':
                print("   💬 执行评论...")
                if comment_post(driver, current_post, comment_templates):
                    interacted_count += 1
                    interacted_posts.add(post_id)  # 记录已互动
                    time.sleep(random.uniform(2, 3))

            # 随机暂停
            time.sleep(random.uniform(2, 5))

            # 向下滚动，确保加载新帖子
            scroll_distance = random.randint(800, 1200)  # 增加滚动距离
            driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            time.sleep(random.uniform(1, 2))

        except Exception as e:
            print(f"   ❌ 处理帖子时出错: {e}")
            continue

    print("\n" + "="*60)
    print(f"📊 浏览完成！")
    print(f"   - 浏览了 {browsed_count} 条帖子")
    print(f"   - 互动了 {interacted_count} 次")
    print("="*60)

    logging.info(f"浏览完成 - 浏览: {browsed_count}, 互动: {interacted_count}")

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

        # 选择浏览模式
        print("\n" + "="*60)
        print("请选择浏览模式:")
        print("1. 仅浏览（只看不互动）")
        print("2. 浏览+点赞")
        print("3. 浏览+评论")
        print("0. 退出")
        print("="*60)

        choice = input("请输入选项 (0-3): ").strip()

        if choice in ['1', '2', '3']:
            max_posts = int(input("浏览多少条帖子？(建议 10-20): ") or "10")

            # 根据选项确定模式
            mode_map = {
                '1': 'browse',
                '2': 'like',
                '3': 'comment'
            }
            mode = mode_map[choice]

            logging.info(f"开始智能浏览 - 模式: {mode}, 浏览数: {max_posts}")
            smart_browse_and_interact(driver, max_posts, mode)

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
