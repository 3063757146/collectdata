#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram 智能自动化脚本 v1.0
模拟真实用户行为，随机浏览和互动
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium_stealth import stealth
import time
import random
import sys
import logging
import os
import shutil


# 检查是否通过环境变量禁用装饰器抓包
if os.getenv('DISABLE_DECORATOR_CAPTURE') == '1':
    CAPTURE_ENABLED = False
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
        def capture_traffic(*args, **kwargs):
            def decorator(func):
                return func
            return decorator


# === 模板数据 ===

def get_comment_templates():
    """获取评论模板"""
    return [
        # 简短赞美
        "Amazing! 🔥", "Love this! ❤️", "So beautiful!", "Stunning! 😍",
        "Goals! 💯", "Incredible!", "Wow! 😮", "Perfect! ✨", "Gorgeous!",
        # 鼓励类
        "Keep it up! 💪", "Love your content!", "This is everything! 👏",
        "So inspiring!", "Absolutely stunning!", "Obsessed! 🙌",
        # 情感表达
        "This made my day! 😊", "Can't get enough of this!",
        "This is gold! 🏆", "💯💯💯", "🔥🔥🔥", "👏👏👏",
        "❤️❤️❤️", "😍😍😍",
        # 互动类
        "So good!", "Amazing work!", "Totally in love with this! ❤️",
        "Wow, just wow!", "Absolutely love this!",
    ]


def get_post_templates():
    """获取发帖模板（文字帖）"""
    return [
        "Good vibes only! ✨", "Living my best life 😊",
        "Grateful for every moment 🙏", "Make today amazing! 💪",
        "Stay positive! 🌟", "Beautiful day! ☀️",
        "Life is good! ❤️", "Enjoying the journey 🚀",
    ]


def setup_logging():
    """配置日志系统"""
    log_filename = 'instagram_bot.log'
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

    logging.info("=" * 60)
    logging.info("新的运行会话开始")
    logging.info("=" * 60)

    return logging.getLogger(__name__)


def create_driver(use_proxy=True):
    """
    创建 Chrome 浏览器实例（保留登录状态）

    Args:
        use_proxy: 是否使用代理（Instagram在国内需要代理）
    """
    chrome_options = Options()

    sudo_user = os.getenv('SUDO_USER')
    if sudo_user and sudo_user != 'root':
        user_home = os.path.expanduser(f'~{sudo_user}')
    else:
        user_home = os.path.expanduser('~')

    user_data_dir = os.path.join(user_home, 'selenium_profiles', 'instagram')
    os.makedirs(user_data_dir, exist_ok=True)
    chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
    chrome_options.add_argument('--profile-directory=Default')
    print(f"💾 使用配置文件: {user_data_dir}")

    if use_proxy:
        chrome_options.add_argument('--proxy-server=socks5://127.0.0.1:10818')
        print("🌐 代理已启用")

    # 反检测设置
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')

    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')

    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--no-default-browser-check')
    chrome_options.add_argument('--disable-popup-blocking')

    # Linux 环境稳定参数（VM/无桌面环境）
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

    # 自动探测 chromedriver 路径
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
    if random.random() < 0.9:
        distance = random.randint(300, 700) if random.random() < 0.8 else random.randint(800, 1400)
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
        # Instagram登录后侧边栏有Home链接和个人资料入口
        home_links = driver.find_elements(By.CSS_SELECTOR, 'a[href="/"][role="link"]')
        if home_links:
            return True
        # 备用：头像图片（已登录用户的个人资料图片）
        avatars = driver.find_elements(By.CSS_SELECTOR, 'img[alt*="profile picture"]')
        if avatars:
            return True
        return False
    except:
        return False


def wait_for_login(driver):
    """等待用户登录"""
    print("\n" + "=" * 60)
    print("⚠️  检测到未登录状态")
    print("请在浏览器中完成登录后，按回车继续...")
    print("=" * 60)
    input()

    if not check_login(driver):
        print("⚠️  似乎还没有登录，请确认已登录后按回车...")
        input()


def _get_parent_button(driver, svg_element):
    """从 SVG 元素向上查找最近的可点击父元素（button 或 div[role='button']）"""
    elem = svg_element
    for _ in range(8):
        try:
            elem = elem.find_element(By.XPATH, '..')
            tag = elem.tag_name.lower()
            role = (elem.get_attribute('role') or '').lower()
            if tag == 'button' or role == 'button':
                return elem
        except:
            break
    return None


def _find_svg_in_viewport(driver, aria_labels: list):
    """
    在整页查找 aria-label 在给定列表中的 SVG，返回第一个在视口内可见的。
    Instagram 的按钮有时不在 article 的 DOM 子树内，需要全页查询。
    """
    selector = ', '.join(f'svg[aria-label="{lb}"]' for lb in aria_labels)
    svgs = driver.find_elements(By.CSS_SELECTOR, selector)
    for svg in svgs:
        try:
            if not svg.is_displayed():
                continue
            # 检查是否在视口内（y 坐标在 0~window.innerHeight 之间）
            rect = driver.execute_script(
                "var r = arguments[0].getBoundingClientRect();"
                "return {top: r.top, bottom: r.bottom};",
                svg
            )
            vh = driver.execute_script("return window.innerHeight;")
            if rect['top'] >= 0 and rect['bottom'] <= vh:
                return svg
        except:
            continue
    # 如果视口内没找到，退而返回第一个可见的
    for svg in svgs:
        try:
            if svg.is_displayed():
                return svg
        except:
            continue
    return None


def like_post(driver):
    """点赞帖子（全页查找视口内的点赞按钮）"""
    try:
        print("      🔍 查找点赞按钮...")

        # 已点赞则跳过（中文"取消赞" / 英文"Unlike"）
        already = _find_svg_in_viewport(driver, ["取消赞", "Unlike"])
        if already:
            print("      ⚠️  已经点赞，跳过")
            logging.info("点赞跳过：已点赞")
            return True

        # 找未点赞的按钮（中文"赞" / 英文"Like"）
        like_svg = _find_svg_in_viewport(driver, ["赞", "Like"])
        if not like_svg:
            print("      ❌ 未找到点赞按钮")
            logging.warning("点赞失败：未找到按钮")
            return False

        like_btn = _get_parent_button(driver, like_svg)
        if not like_btn:
            # 直接点击 SVG 的父 span/div
            like_btn = like_svg.find_element(By.XPATH, '..')

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", like_btn)
        time.sleep(random.uniform(0.3, 0.8))
        driver.execute_script("arguments[0].click();", like_btn)

        time.sleep(1.5)

        # 验证（变成"取消赞"/"Unlike"说明点赞成功）
        try:
            verified = _find_svg_in_viewport(driver, ["取消赞", "Unlike"])
            if verified:
                print("      ✅ 点赞成功（已验证）")
                logging.info("点赞成功")
            else:
                print("      ✅ 点赞已操作（假定成功）")
                logging.info("点赞已操作")
        except:
            print("      ✅ 点赞已操作")

        return True

    except Exception as e:
        print(f"      ❌ 点赞失败: {e}")
        logging.error(f"点赞异常: {e}")
        return False


def comment_post(driver, content_list):
    """评论帖子（全页查找视口内的评论按钮）"""
    try:
        print("      🔍 查找评论按钮...")

        comment_svg = _find_svg_in_viewport(driver, ["评论", "Comment"])
        if not comment_svg:
            print("      ❌ 未找到评论按钮")
            logging.warning("评论失败：未找到评论按钮")
            return False

        comment_btn = _get_parent_button(driver, comment_svg)
        if not comment_btn:
            comment_btn = comment_svg.find_element(By.XPATH, '..')

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", comment_btn)
        print("      ✅ 点击评论按钮，等待输入框...")
        time.sleep(1.5)

        # 查找评论输入框（中英文兼容）
        comment_input = None
        for selector in [
            'textarea[aria-label*="添加评论"]',
            'textarea[placeholder*="添加评论"]',
            'textarea[aria-label*="Add a comment"]',
            'textarea[placeholder*="Add a comment"]',
            'form textarea',
            'textarea',
        ]:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                visible_inputs = [e for e in elements if e.is_displayed()]
                if visible_inputs:
                    comment_input = visible_inputs[0]
                    print(f"      ✅ 找到输入框: {selector}")
                    break
            except:
                continue

        if not comment_input:
            print("      ❌ 未找到评论输入框")
            logging.warning("评论失败：未找到输入框")
            return False

        content = random.choice(content_list)
        print(f"      📝 准备输入评论: {content}")

        driver.execute_script("arguments[0].click();", comment_input)
        time.sleep(0.5)

        try:
            ActionChains(driver).move_to_element(comment_input).click().send_keys(content).perform()
        except:
            comment_input.send_keys(content)

        time.sleep(1.5)
        print(f"      ✅ 已输入评论: {content}")

        # 提交评论 —— 不复用 comment_input（Instagram 输入后会重渲染 DOM，引用会 stale）
        # 等待 Post 按钮从 aria-disabled="true" 变为激活状态
        time.sleep(1)
        submitted = False

        # 方法1：通过 span 文本找到 Post/发布 按钮（不依赖 aria-disabled 过滤）
        try:
            post_btns = driver.find_elements(
                By.XPATH, "//span[text()='Post' or text()='发布']/.."
            )
            visible_btns = [b for b in post_btns if b.is_displayed()]
            if visible_btns:
                driver.execute_script("arguments[0].click();", visible_btns[0])
                print("      ✅ 点击发布按钮")
                submitted = True
        except:
            pass

        # 方法2：重新查找 textarea 并按 Enter
        if not submitted:
            try:
                fresh_inputs = driver.find_elements(By.CSS_SELECTOR,
                    'textarea[aria-label*="添加评论"], textarea[aria-label*="Add a comment"], textarea'
                )
                fresh_visible = [e for e in fresh_inputs if e.is_displayed()]
                if fresh_visible:
                    fresh_visible[0].send_keys(Keys.RETURN)
                    print("      ✅ 按 Enter 提交")
                    submitted = True
            except:
                pass

        if not submitted:
            print("      ⚠️  提交失败，无法发送评论")
            logging.warning("评论提交失败")
            return False

        time.sleep(2)
        print(f"      ✅ 评论已发送")
        logging.info(f"评论成功: {content}")

        # 关闭评论输入框（按 ESC 或点击页面空白区域）
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.5)
        except:
            pass

        return True

    except Exception as e:
        print(f"      ❌ 评论失败: {e}")
        logging.error(f"评论异常: {e}")
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(1)
        except:
            pass
        return False


def share_post(driver):
    """转发帖子（全页查找视口内的转发按钮，不添加评论）"""
    try:
        print("      🔍 查找转发按钮...")

        share_svg = _find_svg_in_viewport(driver, ["转发", "Share Post", "Repost"])
        if not share_svg:
            print("      ❌ 未找到转发按钮")
            logging.warning("转发失败：未找到转发按钮")
            return False

        share_btn = _get_parent_button(driver, share_svg)
        if not share_btn:
            share_btn = share_svg.find_element(By.XPATH, '..')

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", share_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", share_btn)
        print("      ✅ 点击转发按钮")
        time.sleep(2)

        # 关闭可能弹出的面板
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(1)
        except:
            pass

        print("      ✅ 转发操作完成")
        logging.info("转发操作完成")
        return True

    except Exception as e:
        print(f"      ❌ 分享失败: {e}")
        logging.error(f"分享异常: {e}")
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(1)
        except:
            pass
        return False


def smart_browse_and_interact(
    driver,
    max_posts=3,
    enable_like=True,
    enable_comment=True,
    enable_share=True,
    comment_templates=None,
):
    """
    智能浏览和互动 - 确保模式

    每个启用的操作至少成功1次，最多尝试 max_posts*3 条帖子。
    Instagram所有操作均在Feed列表页内联完成，无需跳转详情页。
    """
    print("\n🤖 开始智能浏览模式（确保模式）...")
    print(f"   - 默认浏览 {max_posts} 条帖子")
    print(f"   - 点赞: {'启用（确保≥1次）' if enable_like else '禁用'}")
    print(f"   - 评论: {'启用（确保≥1次）' if enable_comment else '禁用'}")
    print(f"   - 转发: {'启用（确保≥1次）' if enable_share else '禁用'}")

    if comment_templates is None:
        comment_templates = get_comment_templates()

    browsed_count = 0
    interacted_count = 0
    interacted_post_ids = set()

    success_count = {'like': 0, 'comment': 0, 'share': 0}
    targets = {
        'like': 1 if enable_like else 0,
        'comment': 1 if enable_comment else 0,
        'share': 1 if enable_share else 0,
    }

    max_attempts = max_posts * 3
    i = 0

    while i < max_attempts:
        i += 1

        all_targets_met = all(success_count[a] >= targets[a] for a in success_count)

        if all_targets_met and browsed_count >= max_posts:
            print(f"\n✅ 已达成所有目标！")
            print(f"   - 点赞成功: {success_count['like']} 次")
            print(f"   - 评论成功: {success_count['comment']} 次")
            print(f"   - 转发成功: {success_count['share']} 次")
            break

        try:
            # 检查页面状态
            current_url = driver.current_url
            if 'instagram.com' not in current_url:
                print(f"   ⚠️  页面异常，返回首页...")
                driver.get('https://www.instagram.com/')
                time.sleep(3)

            # 随机滚动
            for _ in range(random.randint(1, 3)):
                random_scroll(driver)

            simulate_reading(2, 5)

            # 查找 Feed 中的帖子（article 标签）
            posts = driver.find_elements(By.TAG_NAME, 'article')
            if len(posts) < 2:
                print("   ⚠️  未找到足够帖子，继续滚动...")
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(2)
                continue

            print(f"   ✅ 找到 {len(posts)} 个帖子")

            # 从中间靠后位置选取，避免重复操作同一帖子
            start_idx = min(2, len(posts) - 3)
            end_idx = min(start_idx + 5, len(posts))
            candidates = posts[start_idx:end_idx]

            # 通过帖子内链接做去重
            post = None
            post_id = None
            for candidate in random.sample(candidates, len(candidates)):
                try:
                    links = candidate.find_elements(By.CSS_SELECTOR, 'a[href*="/p/"], a[href*="/reel/"]')
                    pid = links[0].get_attribute('href') if links else str(hash(candidate.id))
                    if pid not in interacted_post_ids:
                        post = candidate
                        post_id = pid
                        break
                except:
                    continue

            if not post:
                print("   ⚠️  候选帖子均已互动，继续滚动...")
                driver.execute_script("window.scrollBy(0, 600);")
                time.sleep(2)
                continue

            interacted_post_ids.add(post_id)
            browsed_count += 1
            print(f"\n📄 浏览第 {browsed_count} 条帖子...")

            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", post)
            simulate_reading(3, 7)

            # 决定要执行的操作（优先执行未达成目标的）
            actions = []
            if enable_like and success_count['like'] < targets['like']:
                actions.append('like')
            if enable_comment and success_count['comment'] < targets['comment']:
                actions.append('comment')
            if enable_share and success_count['share'] < targets['share']:
                actions.append('share')

            if not actions:
                print("   👀 目标已达成，只是浏览，不互动")
                continue

            print(f"   💬 决定互动: {', '.join(actions)}")
            print(f"      当前进度: 点赞{success_count['like']}/{targets['like']}, "
                  f"评论{success_count['comment']}/{targets['comment']}, "
                  f"转发{success_count['share']}/{targets['share']}")

            if 'like' in actions:
                if like_post(driver):
                    success_count['like'] += 1
                    interacted_count += 1
                time.sleep(random.uniform(1, 2))

            if 'comment' in actions:
                if comment_post(driver, comment_templates):
                    success_count['comment'] += 1
                    interacted_count += 1
                time.sleep(random.uniform(1, 2))

            if 'share' in actions:
                if share_post(driver):
                    success_count['share'] += 1
                    interacted_count += 1
                time.sleep(random.uniform(1, 2))

            time.sleep(random.uniform(2, 5))

            # 向下滚动确保下次加载新内容
            driver.execute_script(f"window.scrollBy(0, {random.randint(400, 800)});")
            time.sleep(random.uniform(1, 2))

        except Exception as e:
            print(f"   ❌ 处理帖子时出错: {e}")
            logging.error(f"处理帖子异常: {e}")
            continue

    print("\n" + "=" * 60)
    print(f"📊 浏览完成！")
    print(f"   - 浏览了 {browsed_count} 条帖子")
    print(f"   - 总互动次数: {interacted_count} 次")
    print(f"   - 成功点赞: {success_count['like']} 次")
    print(f"   - 成功评论: {success_count['comment']} 次")
    print(f"   - 成功转发: {success_count['share']} 次")
    print("=" * 60)

    logging.info(
        f"浏览完成 - 浏览: {browsed_count}, 互动: {interacted_count}, "
        f"点赞: {success_count['like']}, 评论: {success_count['comment']}, "
        f"转发: {success_count['share']}"
    )


def main():
    setup_logging()

    print("=" * 60)
    print("Instagram 智能自动化脚本 v1.0")
    print("=" * 60)
    logging.info("脚本启动")

    print("\n启动浏览器...")
    driver = create_driver(use_proxy=True)
    print("✅ 浏览器启动成功！")
    logging.info("浏览器启动成功")

    try:
        print("\n访问 Instagram 首页...")
        driver.get('https://www.instagram.com/')
        time.sleep(4)

        # 关闭可能出现的通知弹窗
        try:
            not_now = driver.find_element(
                By.XPATH,
                "//button[contains(text(), '以后再说') or contains(text(), 'Not Now') or contains(text(), 'Not now')]"
            )
            not_now.click()
            time.sleep(1)
        except:
            pass

        if not check_login(driver):
            logging.warning("检测到未登录状态，等待用户登录")
            wait_for_login(driver)
            logging.info("用户登录完成")
        else:
            print("✅ 已登录")
            logging.info("已登录状态")

        print("\n" + "=" * 60)
        print("请选择测试行为:")
        print("1. 纯浏览（不互动）")
        print("2. 点赞测试")
        print("3. 评论测试")
        print("4. 分享测试")
        print("5. 全部（点赞+评论+分享）")
        print("0. 退出")
        print("=" * 60)

        choice = input("请输入选项 (0-5): ").strip()

        if choice == '1':
            print("\n🔍 纯浏览模式（不互动）")
            logging.info("开始纯浏览测试")
            smart_browse_and_interact(
                driver, max_posts=3,
                enable_like=False, enable_comment=False, enable_share=False
            )

        elif choice == '2':
            print("\n👍 点赞测试模式（确保至少成功1次）")
            logging.info("开始点赞测试")
            smart_browse_and_interact(
                driver, max_posts=3,
                enable_like=True, enable_comment=False, enable_share=False
            )

        elif choice == '3':
            print("\n💬 评论测试模式（确保至少成功1次）")
            logging.info("开始评论测试")
            smart_browse_and_interact(
                driver, max_posts=3,
                enable_like=False, enable_comment=True, enable_share=False,
                comment_templates=get_comment_templates()
            )

        elif choice == '4':
            print("\n📤 分享测试模式（确保至少成功1次）")
            logging.info("开始分享测试")
            smart_browse_and_interact(
                driver, max_posts=3,
                enable_like=False, enable_comment=False, enable_share=True
            )

        elif choice == '5':
            print("\n🎯 全功能模式（点赞+评论+分享）")
            logging.info("开始全功能测试")
            smart_browse_and_interact(
                driver, max_posts=5,
                enable_like=True, enable_comment=True, enable_share=True,
                comment_templates=get_comment_templates()
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
        logging.info("=" * 60 + "\n")


if __name__ == "__main__":
    main()
