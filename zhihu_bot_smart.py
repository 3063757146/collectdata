#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知乎智能自动化脚本 v1.0
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
from selenium_stealth import stealth  # 反检测库
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
    """获取评论模板（中文为主）"""
    return [
        # 简短赞同类
        "说得好！", "很有道理", "赞同", "支持", "学习了",
        "有见地", "深有同感", "确实如此", "太对了", "说到点子上了",

        # 表扬类
        "优秀！", "精彩！", "写得好！", "分析得很透彻", "总结得很到位",
        "这个回答太棒了", "受教了", "高见", "见解独到",

        # 感谢分享类
        "感谢分享！", "谢谢", "多谢科普", "涨知识了",
        "感谢，很有帮助", "受益匪浅",

        # 学习类
        "学到了", "长见识了", "很有启发", "醍醐灌顶",
        "值得深思", "这个角度很新颖",

        # 情感表达类
        "👍", "💯", "🔥", "哈哈哈", "笑死",
        "有意思", "有内味了", "绝了",

        # 互动类
        "同问", "同感", "我也是", "一样的想法",
        "说得太好了", "不能更赞同",
    ]


def get_share_templates():
    """获取分享/转发模板"""
    return [
        # 转发标记
        "", "👀", "📌", "🔥", "💯", "🎯", "⬆️", "转",

        # 推荐类
        "值得一看", "推荐阅读", "好文推荐", "强烈推荐",
        "不要错过", "必看", "精彩",

        # 认同类
        "说得太对了", "深有同感", "确实如此",
        "不能更赞同", "说到心坎里了",

        # 感悟类
        "很有启发", "受益匪浅", "值得深思",
        "这个角度很新颖", "分享给大家",

        # 学习类
        "学到了", "涨知识了", "干货满满",
        "很有价值", "深度好文",
    ]


def get_post_templates():
    """获取发帖/想法模板"""
    return [
        # 日常分享
        "今天学到一个新东西...", "随便说说", "今日感悟",
        "分享一下最近的思考", "记录一下",

        # 学习分享
        "每天学习一点点", "今日学习笔记",
        "突然想明白了一件事", "小小的感悟",

        # 励志正能量
        "加油！💪", "坚持就是胜利",
        "保持学习", "进步的一天",
        "每天都要有收获", "持续成长",

        # 生活态度
        "生活很美好", "今天天气不错",
        "活在当下", "小确幸",

        # 简短感悟
        "有时候少即是多", "质量比数量重要",
        "专注当下", "每天都是新的开始",
    ]


def setup_logging():
    """配置日志系统"""
    # 日志文件名（固定，追加模式）
    log_filename = 'zhihu_bot.log'

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
        use_proxy: 是否使用代理（知乎通常不需要）
    """
    chrome_options = Options()

    # 📂 设置用户数据目录（保存登录状态）
    # 在 sudo 场景下优先使用真实用户目录，避免落到 /root 导致 Chromium 会话异常。
    import os
    sudo_user = os.getenv('SUDO_USER')
    if sudo_user and sudo_user != 'root':
        user_home = os.path.expanduser(f'~{sudo_user}')
    else:
        user_home = os.path.expanduser('~')
    user_data_dir = os.path.join(user_home, 'selenium_profiles', 'zhihu')
    os.makedirs(user_data_dir, exist_ok=True)
    chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
    chrome_options.add_argument('--profile-directory=Default')
    print(f"💾 使用配置文件: {user_data_dir}")

    if use_proxy:
        # 根据需要修改代理端口
        chrome_options.add_argument('--proxy-server=socks5://127.0.0.1:10818')
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

    # Linux 环境常见稳定参数（VM/无桌面环境）
    if sys.platform.startswith('linux'):
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-zygote')
        chrome_options.add_argument('--remote-debugging-port=9222')

        # 没有图形会话时自动切换 headless，避免 Chrome instance exited
        if not os.getenv('DISPLAY'):
            chrome_options.add_argument('--headless=new')
            print("🖥️ 未检测到 DISPLAY，自动启用 headless 模式")

    # 自动探测浏览器可执行文件（Ubuntu arm64 常用 chromium）
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

        # 应用 selenium-stealth 反检测（自动隐藏所有自动化特征）
        print("🛡️  应用 Stealth 反检测模式...")
        stealth(driver,
            languages=["zh-CN", "zh"],
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
    """随机滚动页面，模拟人类浏览（只向下）"""
    # 只向下滚动，不向上
    if random.random() < 0.8:
        distance = random.randint(300, 600)  # 小幅滚动
    else:
        distance = random.randint(800, 1200)  # 大幅滚动
    driver.execute_script(f"window.scrollBy(0, {distance});")

    time.sleep(random.uniform(0.5, 1.5))


def simulate_reading(min_sec=3, max_sec=8):
    """模拟阅读时间"""
    reading_time = random.uniform(min_sec, max_sec)
    print(f"   📖 模拟阅读 {reading_time:.1f} 秒...")
    time.sleep(reading_time)


def expand_content(driver, content_element):
    """点击"阅读全文"按钮展开内容"""
    try:
        # 查找"阅读全文"按钮
        expand_selectors = [
            'button.ContentItem-more',
            'button.Button.ContentItem-more',
            '//button[contains(text(), "阅读全文")]',
        ]

        for selector in expand_selectors:
            try:
                if selector.startswith('//'):
                    buttons = content_element.find_elements(By.XPATH, selector)
                else:
                    buttons = content_element.find_elements(By.CSS_SELECTOR, selector)

                if buttons:
                    for btn in buttons:
                        if btn.is_displayed():
                            # 滚动到按钮位置
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                            time.sleep(0.3)

                            # 点击展开
                            try:
                                driver.execute_script("arguments[0].click();", btn)
                            except:
                                btn.click()

                            print("      📖 已展开全文")
                            time.sleep(0.5)
                            return True
            except:
                continue

        # 没有找到"阅读全文"按钮（内容可能本身就是完整的）
        return False
    except Exception:
        # 忽略展开失败的情况
        return False


def check_login(driver):
    """检查是否已登录"""
    try:
        # 知乎登录状态检查：查找用户头像
        user_elements = driver.find_elements(By.CSS_SELECTOR, '.Avatar')
        if len(user_elements) > 0:
            return True

        # 备用检查：查找登录按钮
        login_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), '登录') or contains(text(), '注册')]")
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


def like_content(driver, content_element):
    """点赞内容（回答/文章/想法）"""
    try:
        print(f"      🔍 查找点赞按钮...")

        # 信息流会重绘，避免持有 Selenium 老元素，使用 JS 即时查找和点击。
        like_result = None

        # 优先在当前内容容器内查找
        try:
            like_result = driver.execute_script("""
                const root = arguments[0];

                function isVisible(el) {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none' && style.visibility !== 'hidden' &&
                           rect.width > 0 && rect.height > 0;
                }

                function getState(btn) {
                    const aria = (btn.getAttribute('aria-label') || '').trim();
                    const cls = btn.className || '';
                    const text = (btn.innerText || '').trim();
                    const isLiked = /已赞同|取消赞同/.test(aria) || cls.includes('is-active') || cls.includes('VoteButton--up');
                    return { aria, cls, text, isLiked };
                }

                function pickVoteButton(scope) {
                    if (!scope) return null;
                    const buttons = Array.from(scope.querySelectorAll('button.VoteButton, button[aria-label*="赞同"], button'));
                    const candidates = buttons.filter(btn => {
                        if (!isVisible(btn)) return false;
                        const aria = (btn.getAttribute('aria-label') || '').trim();
                        const cls = btn.className || '';
                        const text = (btn.innerText || '').trim();
                        return /赞同/.test(aria) || /赞同/.test(text) || cls.includes('VoteButton');
                    });
                    if (!candidates.length) return null;

                    // 优先明确“赞同xx”按钮
                    let target = candidates.find(btn => /赞同/.test((btn.getAttribute('aria-label') || '') + ' ' + (btn.innerText || '')));
                    if (!target) target = candidates[0];
                    return target;
                }

                const btn = pickVoteButton(root);
                if (!btn) return { status: 'not_found' };

                const before = getState(btn);
                if (before.isLiked) {
                    return { status: 'already_liked', text: before.text || before.aria };
                }

                btn.scrollIntoView({ block: 'center' });
                btn.click();

                const after = getState(btn);
                if (after.isLiked) {
                    return { status: 'clicked_verified', text: after.text || after.aria };
                }
                return { status: 'clicked_unverified', text: after.text || after.aria };
            """, content_element)
        except Exception as e:
            if 'stale' in str(e).lower():
                print("      ⚠️  当前内容元素已刷新，改用全局查找点赞按钮...")

        # 失败时退化到全局视口可见区域
        if not like_result or like_result.get('status') == 'not_found':
            try:
                like_result = driver.execute_script("""
                    function isVisible(el) {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style.display !== 'none' && style.visibility !== 'hidden' &&
                               rect.width > 0 && rect.height > 0 &&
                               rect.bottom >= 0 && rect.top <= window.innerHeight;
                    }

                    function getState(btn) {
                        const aria = (btn.getAttribute('aria-label') || '').trim();
                        const cls = btn.className || '';
                        const text = (btn.innerText || '').trim();
                        const isLiked = /已赞同|取消赞同/.test(aria) || cls.includes('is-active') || cls.includes('VoteButton--up');
                        return { aria, cls, text, isLiked };
                    }

                    const buttons = Array.from(document.querySelectorAll('button.VoteButton, button[aria-label*="赞同"], button'));
                    const candidates = buttons.filter(btn => {
                        if (!isVisible(btn)) return false;
                        const aria = (btn.getAttribute('aria-label') || '').trim();
                        const cls = btn.className || '';
                        const text = (btn.innerText || '').trim();
                        return /赞同/.test(aria) || /赞同/.test(text) || cls.includes('VoteButton');
                    });
                    if (!candidates.length) return { status: 'not_found' };

                    let btn = candidates.find(b => /赞同/.test((b.getAttribute('aria-label') || '') + ' ' + (b.innerText || '')));
                    if (!btn) btn = candidates[0];

                    const before = getState(btn);
                    if (before.isLiked) {
                        return { status: 'already_liked', text: before.text || before.aria };
                    }

                    btn.scrollIntoView({ block: 'center' });
                    btn.click();

                    const after = getState(btn);
                    if (after.isLiked) return { status: 'clicked_verified', text: after.text || after.aria };
                    return { status: 'clicked_unverified', text: after.text || after.aria };
                """)
            except Exception:
                pass

        if not like_result:
            print("      ❌ 未找到点赞按钮")
            logging.warning("点赞失败：未找到点赞按钮")
            return False

        status = like_result.get('status')
        btn_text = like_result.get('text', '')

        if status == 'already_liked':
            print("      ⚠️  已经点赞过了，跳过")
            logging.info("点赞跳过：已点赞")
            return True

        if status == 'clicked_verified':
            print(f"      ✅ 点赞成功（已验证）{f' - {btn_text}' if btn_text else ''}")
            logging.info("点赞成功")
            return True

        if status == 'clicked_unverified':
            # 给前端状态一点时间再复查一次，避免“其实成功但瞬时未更新”被误判。
            time.sleep(1.0)
            recheck = driver.execute_script("""
                const buttons = Array.from(document.querySelectorAll('button.VoteButton, button[aria-label*="赞同"]'));
                for (const btn of buttons) {
                    const aria = (btn.getAttribute('aria-label') || '').trim();
                    const cls = btn.className || '';
                    if (/已赞同|取消赞同/.test(aria) || cls.includes('is-active') || cls.includes('VoteButton--up')) {
                        return true;
                    }
                }
                return false;
            """)
            if recheck:
                print("      ✅ 点赞成功（延迟复查确认）")
                logging.info("点赞成功（延迟复查）")
                return True

            print("      ⚠️  点击了但状态未变化")
            logging.warning("点赞状态未确认")
            return False

        print("      ❌ 未找到点赞按钮")
        logging.warning("点赞失败：未找到点赞按钮")
        return False

    except Exception as e:
        print(f"      ❌ 点赞异常: {e}")
        logging.error(f"点赞异常: {e}")
        return False


def close_comment_modal(driver):
    """关闭评论弹窗"""
    try:
        print("      🔍 尝试关闭评论弹窗...")
        # 查找关闭按钮（排除编辑弹窗的关闭按钮 Modal-closeButton）
        # 优先查找发布成功后的关闭按钮（不包含 Modal-closeButton 类）

        close_button = None

        # 方法1：查找所有关闭按钮，排除 Modal-closeButton
        try:
            close_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="关闭"]')
            for elem in close_buttons:
                if elem.is_displayed():
                    # 检查是否包含 Modal-closeButton 类
                    class_name = elem.get_attribute('class') or ''
                    if 'Modal-closeButton' not in class_name:
                        # 这是发布成功后的关闭按钮
                        close_button = elem
                        print(f"      ✅ 找到发布成功后的关闭按钮")
                        break
        except:
            pass

        # 方法2：如果没找到，尝试查找包含特定CSS类的关闭按钮
        if not close_button:
            try:
                # 发布成功后的关闭按钮通常有 css-xxxxx 类
                close_buttons = driver.find_elements(By.XPATH, '//button[@aria-label="关闭" and contains(@class, "css-")]')
                for elem in close_buttons:
                    if elem.is_displayed():
                        close_button = elem
                        print(f"      ✅ 找到关闭按钮（css-类）")
                        break
            except:
                pass

        if close_button:
            driver.execute_script("arguments[0].click();", close_button)
            print("      ✅ 已点击关闭按钮")
            time.sleep(1)

            # 检查是否弹出了确认弹窗（"是否放弃本次编辑"）
            # 如果有，点击"放弃"按钮
            try:
                abandon_button_selectors = [
                    '//button[contains(@class, "Button--primary") and contains(@class, "Button--blue") and contains(text(), "放弃")]',
                    '//button[contains(text(), "放弃")]',
                ]

                for selector in abandon_button_selectors:
                    try:
                        abandon_buttons = driver.find_elements(By.XPATH, selector)
                        for btn in abandon_buttons:
                            if btn.is_displayed():
                                driver.execute_script("arguments[0].click();", btn)
                                print("      ✅ 已点击'放弃'按钮（确认关闭）")
                                time.sleep(1)
                                return True
                    except:
                        continue
            except:
                pass

            return True
        else:
            # 备用：按 ESC 键
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            print("      ✅ 已按 ESC 关闭弹窗")
            time.sleep(1)

            # 同样检查是否需要点击"放弃"
            try:
                abandon_buttons = driver.find_elements(By.XPATH, '//button[contains(text(), "放弃")]')
                for btn in abandon_buttons:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        print("      ✅ 已点击'放弃'按钮（确认关闭）")
                        time.sleep(1)
                        break
            except:
                pass

            return True
    except Exception as e:
        print(f"      ⚠️  关闭弹窗失败: {e}")
        return False


def comment_content(driver, content_element, content_list):
    """评论内容（回答/文章/想法）"""
    try:
        print(f"      🔍 查找评论按钮...")

        # 知乎信息流会频繁重绘，Selenium 缓存元素容易 stale。
        # 这里改为 JS 即时查找+点击，优先在当前 content_element 内，失败再退到全局可见区域。
        click_msg = None

        # 先尝试在当前内容容器内点击
        try:
            click_msg = driver.execute_script("""
                const root = arguments[0];
                function isVisible(el) {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none' && style.visibility !== 'hidden' &&
                           rect.width > 0 && rect.height > 0;
                }

                function pickAndClick(scope) {
                    if (!scope) return null;
                    const buttons = Array.from(scope.querySelectorAll('button'));
                    const candidates = buttons.filter(btn => {
                        if (!isVisible(btn)) return false;
                        const text = (btn.innerText || '').trim();
                        const aria = (btn.getAttribute('aria-label') || '').trim();
                        const cls = btn.className || '';
                        const hasButtonClass = cls.includes('Button');
                        const hasActionClass = cls.includes('ContentItem-action') || cls.includes('action');
                        const hasCommentText = /条评论|评论/i.test(text);
                        const hasCommentAria = /评论|comment/i.test(aria);
                        return hasCommentText || hasCommentAria ||
                               (hasActionClass && hasCommentText) ||
                               (hasButtonClass && (hasCommentText || hasCommentAria));
                    });
                    if (!candidates.length) return null;

                    let target = candidates.find(btn => /\\d+\\s*条评论/.test((btn.innerText || '').trim()));
                    if (!target) target = candidates.find(btn => /条评论|评论/i.test((btn.innerText || '').trim()));
                    if (!target) target = candidates.find(btn => /评论|comment/i.test((btn.getAttribute('aria-label') || '')));
                    if (!target) target = candidates[0];

                    target.scrollIntoView({ block: 'center' });
                    target.click();
                    return (target.innerText || target.getAttribute('aria-label') || '评论按钮').trim();
                }

                return pickAndClick(root);
            """, content_element)
        except Exception as e:
            if 'stale' in str(e).lower():
                print("      ⚠️  当前内容元素已刷新，改用全局查找评论按钮...")

        # 失败时退化到全局查找（仅取视口中可见按钮）
        if not click_msg:
            try:
                click_msg = driver.execute_script("""
                    function isVisible(el) {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style.display !== 'none' && style.visibility !== 'hidden' &&
                               rect.width > 0 && rect.height > 0 &&
                               rect.bottom >= 0 && rect.top <= window.innerHeight;
                    }

                    const buttons = Array.from(document.querySelectorAll('button.ContentItem-action, button.Button--plain, button'));
                    const candidates = buttons.filter(btn => {
                        if (!isVisible(btn)) return false;
                        const text = (btn.innerText || '').trim();
                        const aria = (btn.getAttribute('aria-label') || '').trim();
                        const cls = btn.className || '';
                        const hasButtonClass = cls.includes('Button');
                        const hasActionClass = cls.includes('ContentItem-action') || cls.includes('action');
                        const hasCommentText = /条评论|评论/i.test(text);
                        const hasCommentAria = /评论|comment/i.test(aria);
                        return hasCommentText || hasCommentAria ||
                               (hasActionClass && hasCommentText) ||
                               (hasButtonClass && (hasCommentText || hasCommentAria));
                    });

                    if (!candidates.length) return null;
                    let target = candidates.find(btn => /\\d+\\s*条评论/.test((btn.innerText || '').trim()));
                    if (!target) target = candidates.find(btn => /条评论|评论/i.test((btn.innerText || '').trim()));
                    if (!target) target = candidates[0];

                    target.scrollIntoView({ block: 'center' });
                    target.click();
                    return (target.innerText || target.getAttribute('aria-label') || '评论按钮').trim();
                """)
            except Exception:
                pass

        if not click_msg:
            print("      ❌ 未找到评论按钮")
            logging.warning("评论失败：未找到评论按钮")
            return False

        print(f"      ✅ 已点击评论按钮（{click_msg}），等待输入框...")
        time.sleep(2)

        # 查找评论输入框（Draft.js 编辑器）
        print("      🔍 查找评论输入框（Draft.js）...")
        input_selectors = [
            'div.public-DraftEditor-content[contenteditable="true"]',
            'div[contenteditable="true"]',
        ]

        comment_input = None
        for selector in input_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        # 检查元素大小（过滤隐藏元素）
                        rect = elem.rect
                        if rect['height'] > 10 and rect['width'] > 100:
                            comment_input = elem
                            print(f"      ✅ 找到输入框: {selector}")
                            break
                if comment_input:
                    break
            except:
                continue

        if not comment_input:
            print("      ❌ 未找到输入框（可能此内容不支持评论）")
            logging.warning("评论失败：未找到输入框")
            # 关闭评论弹窗
            close_comment_modal(driver)
            return False

        # 输入评论内容
        content = random.choice(content_list)
        print(f"      📝 准备输入评论: {content}")

        # ⚠️ Draft.js 需要点击两次：第一次展开，第二次获得焦点
        print("      🔍 点击输入框（第1次）...")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_input)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", comment_input)
        time.sleep(0.5)

        print("      🔍 点击输入框（第2次，获得焦点）...")
        driver.execute_script("arguments[0].click();", comment_input)
        time.sleep(0.5)

        # 使用 ActionChains 输入（Draft.js 必须用这种方式）
        print(f"      ⌨️  使用 ActionChains 输入...")
        try:
            actions = ActionChains(driver)
            actions.move_to_element(comment_input).click().send_keys(content).perform()
            time.sleep(1.5)
            print(f"      ✅ 已输入评论: {content}")
        except Exception as e:
            print(f"      ⚠️  ActionChains 失败，尝试备用方式: {e}")
            # 备用方案：直接send_keys
            comment_input.send_keys(content)
            time.sleep(1.5)
            print(f"      ✅ 已输入评论（备用方式）: {content}")

        # 查找发送按钮（Button--primary Button--blue，文本为"发布"）
        print("      🔍 查找发送按钮...")
        time.sleep(1)

        send_button_selectors = [
            # 精确匹配：同时满足 class 和文本内容
            '//button[contains(@class, "Button--primary") and contains(@class, "Button--blue") and contains(text(), "发布")]',
            '//button[contains(@class, "Button--primary") and text()="发布"]',
            '//button[contains(text(), "发布")]',
            'button.Button--primary.Button--blue',
            'button.Button--primary',
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
                        # 额外检查：确保按钮文本确实是"发布"
                        btn_text = elem.text.strip()
                        if '发布' in btn_text:
                            send_button = elem
                            print(f"      ✅ 找到发送按钮: {selector}")
                            break
                if send_button:
                    break
            except:
                continue

        if send_button:
            # 等待按钮变成可点击状态（最多等待8秒）
            print("      ⏳ 等待发送按钮变成可点击...")
            max_wait = 8
            waited = 0
            while waited < max_wait:
                is_disabled = send_button.get_attribute('disabled')
                if not is_disabled:
                    print("      ✅ 发送按钮已可用")
                    break
                print(f"      ⚠️  按钮禁用中，等待... ({waited + 1}s)")
                time.sleep(1)
                waited += 1

            # 如果按钮还是禁用，尝试重新输入
            is_disabled = send_button.get_attribute('disabled')
            if is_disabled:
                print("      ⚠️  按钮仍然禁用，尝试重新输入...")
                # 全选并删除
                actions = ActionChains(driver)
                actions.move_to_element(comment_input).click().perform()
                time.sleep(0.3)
                actions.key_down(Keys.COMMAND).send_keys('a').key_up(Keys.COMMAND).perform()
                time.sleep(0.2)
                actions.send_keys(Keys.BACKSPACE).perform()
                time.sleep(0.3)
                # 重新输入
                actions.send_keys(content).perform()
                time.sleep(2)

                # 再次检查
                is_disabled = send_button.get_attribute('disabled')
                if is_disabled:
                    print("      ❌ 按钮始终禁用，放弃评论")
                    logging.warning("评论失败：发送按钮始终禁用")
                    # 关闭弹窗
                    try:
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(1)
                    except:
                        pass
                    return False

            # 滚动到按钮位置，确保完全可见
            print("      📍 滚动到发送按钮位置...")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", send_button)
            time.sleep(1)

            # 确认按钮信息
            btn_class = send_button.get_attribute('class')
            btn_text = send_button.text.strip()
            print(f"      ℹ️  按钮信息: class='{btn_class}', text='{btn_text}'")

            # 点击发送（尝试多种方式）
            click_success = False

            # 方式1: JavaScript 点击
            try:
                print(f"      🖱️  方式1: JavaScript 点击...")
                driver.execute_script("arguments[0].click();", send_button)
                print(f"      ✅ JavaScript 点击成功")
                click_success = True
            except Exception as e:
                print(f"      ⚠️  JavaScript 点击失败: {str(e)[:50]}")

            # 方式2: 直接点击
            if not click_success:
                try:
                    print(f"      🖱️  方式2: 直接点击...")
                    send_button.click()
                    print(f"      ✅ 直接点击成功")
                    click_success = True
                except Exception as e:
                    print(f"      ⚠️  直接点击失败: {str(e)[:50]}")

            # 方式3: ActionChains 点击
            if not click_success:
                try:
                    print(f"      🖱️  方式3: ActionChains 点击...")
                    actions = ActionChains(driver)
                    actions.move_to_element(send_button).pause(0.5).click().perform()
                    print(f"      ✅ ActionChains 点击成功")
                    click_success = True
                except Exception as e:
                    print(f"      ⚠️  ActionChains 点击失败: {str(e)[:50]}")

            # 方式4: JavaScript 强制触发事件
            if not click_success:
                try:
                    print(f"      🖱️  方式4: 强制触发点击事件...")
                    driver.execute_script("""
                        var evt = new MouseEvent('click', {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        });
                        arguments[0].dispatchEvent(evt);
                    """, send_button)
                    print(f"      ✅ 事件触发成功")
                    click_success = True
                except Exception as e:
                    print(f"      ⚠️  事件触发失败: {str(e)[:50]}")

            if not click_success:
                print(f"      ❌ 所有点击方式都失败了")
                logging.warning("评论失败：无法点击发送按钮")
                close_comment_modal(driver)
                return False

            # 等待发布完成
            print("      ⏳ 等待评论发布完成...")
            time.sleep(5)

            print(f"      ✅ 评论已发送")
            logging.info(f"评论成功: {content}")

            # 等待弹窗自动消失（最多等待5秒）
            print("      🔍 等待弹窗自动消失...")
            for _ in range(5):
                try:
                    close_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="关闭"]')
                    visible_close = [btn for btn in close_buttons if btn.is_displayed()]
                    if not visible_close:
                        print("      ✅ 弹窗已自动关闭")
                        break
                    time.sleep(1)
                except:
                    break
            else:
                # 如果5秒后弹窗还在，手动关闭
                print("      🔍 弹窗未自动关闭，尝试手动关闭...")
                close_comment_modal(driver)

            return True
        else:
            print("      ❌ 未找到发送按钮")
            logging.warning("评论失败：未找到发送按钮")
            # 关闭评论弹窗
            close_comment_modal(driver)
            return False

    except Exception as e:
        print(f"      ❌ 评论失败: {e}")
        logging.error(f"评论异常: {e}")
        # 关闭评论弹窗
        close_comment_modal(driver)
        return False


def share_content(driver, content_element, share_templates):
    """分享内容（转发到想法）"""
    try:
        print(f"      🔍 查找分享按钮...")

        # 信息流频繁重绘，分享按钮和菜单项都不能依赖缓存的 Selenium 元素。
        share_click_msg = None

        try:
            share_click_msg = driver.execute_script("""
                const root = arguments[0];

                function isVisible(el) {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none' && style.visibility !== 'hidden' &&
                           rect.width > 0 && rect.height > 0;
                }

                function pickButton(scope) {
                    if (!scope) return null;
                    const buttons = Array.from(scope.querySelectorAll('button'));
                    const candidates = buttons.filter(btn => {
                        if (!isVisible(btn)) return false;
                        const text = (btn.innerText || '').trim();
                        const aria = (btn.getAttribute('aria-label') || '').trim();
                        const cls = btn.className || '';
                        const hasButtonClass = cls.includes('Button');
                        const hasShareText = /分享/.test(text);
                        const hasShareAria = /分享|share/i.test(aria);
                        return hasShareText || hasShareAria ||
                               (hasButtonClass && (hasShareText || hasShareAria));
                    });
                    if (!candidates.length) return null;
                    return candidates.find(btn => /^分享$/.test((btn.innerText || '').trim()) || /分享/.test((btn.innerText || '').trim())) || 
                           candidates.find(btn => /分享|share/i.test((btn.getAttribute('aria-label') || ''))) || candidates[0];
                }

                const btn = pickButton(root);
                if (!btn) return null;
                btn.scrollIntoView({ block: 'center' });
                btn.click();
                return (btn.innerText || btn.getAttribute('aria-label') || '分享按钮').trim();
            """, content_element)
        except Exception as e:
            if 'stale' in str(e).lower():
                print("      ⚠️  当前内容元素已刷新，改用全局查找分享按钮...")

        if not share_click_msg:
            try:
                share_click_msg = driver.execute_script("""
                    function isVisible(el) {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style.display !== 'none' && style.visibility !== 'hidden' &&
                               rect.width > 0 && rect.height > 0 &&
                               rect.bottom >= 0 && rect.top <= window.innerHeight;
                    }

                    const buttons = Array.from(document.querySelectorAll('button'));
                    const candidates = buttons.filter(btn => {
                        if (!isVisible(btn)) return false;
                        const text = (btn.innerText || '').trim();
                        const aria = (btn.getAttribute('aria-label') || '').trim();
                        const cls = btn.className || '';
                        const hasButtonClass = cls.includes('Button');
                        const hasShareText = /分享/.test(text);
                        const hasShareAria = /分享|share/i.test(aria);
                        return hasShareText || hasShareAria ||
                               (hasButtonClass && (hasShareText || hasShareAria));
                    });
                    if (!candidates.length) return null;
                    const btn = candidates.find(b => /^分享$/.test((b.innerText || '').trim()) || /分享/.test((b.innerText || '').trim())) || 
                               candidates.find(b => /分享|share/i.test((b.getAttribute('aria-label') || ''))) || candidates[0];
                    btn.scrollIntoView({ block: 'center' });
                    btn.click();
                    return (btn.innerText || btn.getAttribute('aria-label') || '分享按钮').trim();
                """)
            except Exception:
                pass

        if not share_click_msg:
            print("      ❌ 未找到分享按钮")
            logging.warning("分享失败：未找到分享按钮")
            return False

        print("      ✅ 点击分享按钮，等待菜单...")
        time.sleep(2)

        # 查找"转发到想法"选项
        print("      🔍 查找转发到想法选项...")
        share_to_pin_msg = None
        try:
            share_to_pin_msg = driver.execute_script("""
                function isVisible(el) {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none' && style.visibility !== 'hidden' &&
                           rect.width > 0 && rect.height > 0;
                }

                const buttons = Array.from(document.querySelectorAll('button.ShareMenu-button, button'));
                const candidates = buttons.filter(btn => {
                    if (!isVisible(btn)) return false;
                    const text = (btn.innerText || '').trim();
                    const cls = btn.className || '';
                    return /转发到想法|想法/.test(text) || cls.includes('ShareMenu-button');
                });
                if (!candidates.length) return null;

                const btn = candidates.find(b => /转发到想法/.test((b.innerText || '').trim())) ||
                            candidates.find(b => /想法/.test((b.innerText || '').trim())) ||
                            candidates[0];
                btn.click();
                return (btn.innerText || '转发到想法').trim();
            """)
        except Exception:
            pass

        if not share_to_pin_msg:
            print("      ⚠️  未找到转发到想法选项")
            logging.warning("分享失败：未找到转发到想法选项")
            # 关闭菜单
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(1)
            except:
                pass
            return False

        print("      ✅ 点击转发到想法")
        time.sleep(2)

        # 查找想法输入框（textarea）
        print("      🔍 查找想法输入框...")
        pin_input = None
        input_selectors = [
            'textarea[placeholder="标题"]',
            'textarea[name="title"]',
            'textarea',
        ]

        for selector in input_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        # 检查元素大小
                        rect = elem.rect
                        if rect['height'] > 10 and rect['width'] > 100:
                            pin_input = elem
                            print(f"      ✅ 找到想法输入框: {selector}")
                            break
                if pin_input:
                    break
            except:
                continue

        if not pin_input:
            print("      ❌ 未找到想法输入框")
            logging.warning("分享失败：未找到想法输入框")
            # 关闭弹窗
            close_comment_modal(driver)
            return False

        # 准备分享内容（标题和正文）
        title = random.choice(share_templates)
        content = None  # 正文内容（如果有的话）

        print(f"      📝 准备输入分享标题: {title}")

        # 点击标题输入框获得焦点
        driver.execute_script("arguments[0].focus();", pin_input)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", pin_input)
        time.sleep(0.5)

        # 输入标题（textarea 可以直接用 send_keys）
        try:
            pin_input.send_keys(title)
            time.sleep(1)
            print(f"      ✅ 已输入分享标题: {title}")
        except Exception as e:
            print(f"      ⚠️  输入标题失败: {e}")
            # 备用方案：使用 ActionChains
            try:
                actions = ActionChains(driver)
                actions.move_to_element(pin_input).click().send_keys(title).perform()
                time.sleep(1)
                print(f"      ✅ 已输入分享标题（ActionChains）: {title}")
            except Exception as e2:
                print(f"      ❌ ActionChains 也失败: {e2}")
                close_comment_modal(driver)
                return False

        # 查找正文输入框（Draft.js 编辑器）
        print("      🔍 查找正文输入框（Draft.js）...")
        content_input = None
        content_selectors = [
            'div.public-DraftEditor-content[contenteditable="true"]',
            'div[contenteditable="true"][role="textbox"]',
        ]

        for selector in content_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        # 检查元素大小
                        rect = elem.rect
                        if rect['height'] > 10 and rect['width'] > 100:
                            content_input = elem
                            print(f"      ✅ 找到正文输入框: {selector}")
                            break
                if content_input:
                    break
            except:
                continue

        if not content_input:
            print("      ⚠️  未找到正文输入框（仅填写标题）")
            # 不算失败，继续发布
        else:
            # 输入正文内容
            content = random.choice(share_templates)
            print(f"      📝 准备输入正文: {content}")

            # 点击正文输入框获得焦点
            driver.execute_script("arguments[0].focus();", content_input)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", content_input)
            time.sleep(0.5)

            # 使用 ActionChains 输入（Draft.js 必须用这种方式）
            print(f"      ⌨️  使用 ActionChains 输入正文...")
            try:
                actions = ActionChains(driver)
                actions.move_to_element(content_input).click().send_keys(content).perform()
                time.sleep(1.5)
                print(f"      ✅ 已输入正文: {content}")
            except Exception as e:
                print(f"      ⚠️  ActionChains 输入正文失败: {e}")
                # 备用方案：直接 send_keys
                try:
                    content_input.send_keys(content)
                    time.sleep(1.5)
                    print(f"      ✅ 已输入正文（备用方式）: {content}")
                except Exception as e2:
                    print(f"      ⚠️  备用方式也失败，仅保留标题: {e2}")

        # 查找发布按钮（Button--secondary Button--blue）
        print("      🔍 查找发布按钮...")
        time.sleep(1)

        publish_msg = None
        try:
            publish_msg = driver.execute_script("""
                function isVisible(el) {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none' && style.visibility !== 'hidden' &&
                           rect.width > 0 && rect.height > 0;
                }

                const buttons = Array.from(document.querySelectorAll('button.Button--secondary.Button--blue, button.Button--secondary, button'));
                const candidates = buttons.filter(btn => {
                    if (!isVisible(btn)) return false;
                    const text = (btn.innerText || '').trim();
                    return /发布/.test(text);
                });
                if (!candidates.length) return null;
                const btn = candidates[0];
                btn.scrollIntoView({ block: 'center' });
                btn.click();
                return (btn.innerText || '发布').trim();
            """)
        except Exception:
            pass

        if not publish_msg:
            print("      ❌ 未找到发布按钮")
            logging.warning("分享失败：未找到发布按钮")
            # 关闭弹窗
            close_comment_modal(driver)
            return False

        print("      ✅ 点击发布按钮")

        # 等待发布完成（增加等待时间，确保服务器处理完成）
        print("      ⏳ 等待发布完成...")
        time.sleep(5)

        print("      ✅ 分享成功")
        if content:
            logging.info(f"分享成功 - 标题: {title}, 正文: {content}")
        else:
            logging.info(f"分享成功 - 标题: {title}")

        # 等待弹窗自动消失（最多等待5秒）
        print("      🔍 等待弹窗自动消失...")
        for _ in range(5):
            try:
                # 检查弹窗是否还存在
                close_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="关闭"]')
                visible_close = [btn for btn in close_buttons if btn.is_displayed()]
                if not visible_close:
                    print("      ✅ 弹窗已自动关闭")
                    break
                time.sleep(1)
            except:
                break
        else:
            # 如果5秒后弹窗还在，手动关闭
            print("      🔍 弹窗未自动关闭，尝试手动关闭...")
            close_comment_modal(driver)

        return True

    except Exception as e:
        print(f"      ❌ 分享失败: {e}")
        logging.error(f"分享异常: {e}")
        # 关闭弹窗
        close_comment_modal(driver)
        return False


def post_pin(driver, post_templates):
    """发布想法"""
    try:
        print("\n📝 准备发布想法...")

        # 查找发布想法入口（"分享此刻的想法..."）
        print("   🔍 查找发布想法入口...")

        entry_selectors = [
            '//div[contains(text(), "分享此刻的想法")]',
            '//div[contains(@class, "css-") and contains(text(), "分享")]',
            '//button[contains(text(), "发布")]',
            '//button[contains(text(), "写想法")]',
            '//button[contains(@class, "Button") and contains(text(), "发布")]',
            '//button[contains(@class, "Button") and contains(text(), "想法")]',
            '//div[contains(@class, "css-")]',
        ]

        entry_button = None
        for selector in entry_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed():
                        text = elem.text.strip()
                        if '分享' in text or '发布' in text or '想法' in text:
                            entry_button = elem
                            print(f"   ✅ 找到发布想法入口: {text[:20]}")
                            break
                if entry_button:
                    break
            except:
                continue

        if not entry_button:
            print("   ❌ 未找到发布想法入口")
            logging.warning("发布想法失败：未找到发布入口")
            return False

        # 点击入口
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", entry_button)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", entry_button)
        print("   ✅ 点击发布想法入口，等待弹窗...")
        time.sleep(2)

        # 查找标题输入框
        print("   🔍 查找标题输入框...")
        title_input = None
        title_selectors = [
            'textarea[placeholder="标题"]',
            'textarea[name="title"]',
        ]

        for selector in title_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        title_input = elem
                        print(f"   ✅ 找到标题输入框: {selector}")
                        break
                if title_input:
                    break
            except:
                continue

        if not title_input:
            print("   ❌ 未找到标题输入框")
            logging.warning("发布想法失败：未找到标题输入框")
            close_comment_modal(driver)
            return False

        # 输入标题
        title = random.choice(post_templates)
        print(f"   📝 准备输入标题: {title}")

        # 点击标题输入框获得焦点
        driver.execute_script("arguments[0].focus();", title_input)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", title_input)
        time.sleep(0.5)

        # 输入标题（textarea 可以直接用 send_keys）
        try:
            title_input.send_keys(title)
            time.sleep(1)
            print(f"   ✅ 已输入标题: {title}")
        except Exception as e:
            print(f"   ⚠️  输入标题失败: {e}")
            close_comment_modal(driver)
            return False

        # 查找正文输入框（Draft.js 编辑器）
        print("   🔍 查找正文输入框...")
        content_input = None
        content_selectors = [
            'div.public-DraftEditor-content[contenteditable="true"]',
            'div[contenteditable="true"][role="textbox"]',
        ]

        for selector in content_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        # 检查元素大小
                        rect = elem.rect
                        if rect['height'] > 10 and rect['width'] > 100:
                            content_input = elem
                            print(f"   ✅ 找到正文输入框: {selector}")
                            break
                if content_input:
                    break
            except:
                continue

        if not content_input:
            print("   ❌ 未找到正文输入框")
            logging.warning("发布想法失败：未找到正文输入框")
            close_comment_modal(driver)
            return False

        # 输入正文内容
        content = random.choice(post_templates)
        print(f"   📝 准备输入正文: {content}")

        # 点击正文输入框获得焦点
        driver.execute_script("arguments[0].focus();", content_input)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", content_input)
        time.sleep(0.5)

        # 使用 ActionChains 输入（Draft.js 必须用这种方式）
        print(f"   ⌨️  使用 ActionChains 输入正文...")
        try:
            actions = ActionChains(driver)
            actions.move_to_element(content_input).click().send_keys(content).perform()
            time.sleep(1.5)
            print(f"   ✅ 已输入正文: {content}")
        except Exception as e:
            print(f"   ⚠️  ActionChains 输入失败: {e}")
            # 备用方案：直接 send_keys
            try:
                content_input.send_keys(content)
                time.sleep(1.5)
                print(f"   ✅ 已输入正文（备用方式）: {content}")
            except Exception as e2:
                print(f"   ❌ 备用方式也失败: {e2}")
                close_comment_modal(driver)
                return False

        # 查找发布按钮（Button--secondary Button--blue）
        print("   🔍 查找发布按钮...")
        time.sleep(1)

        publish_button_selectors = [
            '//button[contains(@class, "Button--secondary") and contains(@class, "Button--blue") and contains(text(), "发布")]',
            'button.Button--secondary.Button--blue',
            '//button[contains(text(), "发布")]',
        ]

        publish_button = None
        for selector in publish_button_selectors:
            try:
                if selector.startswith('//'):
                    elements = driver.find_elements(By.XPATH, selector)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)

                for elem in elements:
                    if elem.is_displayed():
                        # 确认按钮文本是"发布"
                        btn_text = elem.text.strip()
                        if '发布' in btn_text:
                            publish_button = elem
                            print(f"   ✅ 找到发布按钮")
                            break
                if publish_button:
                    break
            except:
                continue

        if not publish_button:
            print("   ❌ 未找到发布按钮")
            logging.warning("发布想法失败：未找到发布按钮")
            close_comment_modal(driver)
            return False

        # 滚动到发布按钮位置
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", publish_button)
        time.sleep(0.5)

        # 点击发布
        try:
            driver.execute_script("arguments[0].click();", publish_button)
            print("   ✅ 点击发布按钮")
        except:
            publish_button.click()
            print("   ✅ 点击发布按钮（直接点击）")

        # 等待发布完成
        print("   ⏳ 等待发布完成...")
        time.sleep(5)

        print(f"   ✅ 发布想法成功！")
        logging.info(f"发布想法成功 - 标题: {title}, 正文: {content}")

        # 等待弹窗自动消失（最多等待5秒）
        print("   🔍 等待弹窗自动消失...")
        for _ in range(5):
            try:
                close_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="关闭"]')
                visible_close = [btn for btn in close_buttons if btn.is_displayed()]
                if not visible_close:
                    print("   ✅ 弹窗已自动关闭")
                    break
                time.sleep(1)
            except:
                break
        else:
            # 如果5秒后弹窗还在，手动关闭
            print("   🔍 弹窗未自动关闭，尝试手动关闭...")
            close_comment_modal(driver)

        return True

    except Exception as e:
        print(f"   ❌ 发布想法失败: {e}")
        logging.error(f"发布想法异常: {e}")
        import traceback
        traceback.print_exc()
        # 关闭弹窗
        close_comment_modal(driver)
        return False


def smart_browse_and_interact(
    driver,
    max_items=3,
    interaction_rate=0.3,
    enable_like=True,
    enable_comment=True,
    enable_share=True,
    enable_post=False,
    comment_templates=None,
    share_templates=None,
    post_templates=None
):
    """
    智能浏览和互动 - 确保模式

    参数:
        max_items: 默认浏览多少条内容（默认3条）
        interaction_rate: 额外互动概率（达成目标后的额外互动概率）
        enable_like: 是否启用点赞（True则确保至少成功1次）
        enable_comment: 是否启用评论（True则确保至少成功1次）
        enable_share: 是否启用分享（True则确保至少成功1次）
        enable_post: 是否启用发布想法（True则确保至少成功1次）
        comment_templates: 评论模板列表（None则使用默认）
        share_templates: 分享模板列表（None则使用默认）
        post_templates: 发布想法模板列表（None则使用默认）

    新逻辑：
        - 如果 enable_like=True，确保至少成功点赞1次
        - 如果 enable_comment=True，确保至少成功评论1次
        - 如果 enable_share=True，确保至少成功分享1次
        - 如果 enable_post=True，确保至少成功发布想法1次
        - 最多尝试 max_items*3 条内容（避免无限循环）
    """
    print("\n🤖 开始智能浏览模式（确保模式）...")
    print(f"   - 默认浏览 {max_items} 条内容")
    print(f"   - 点赞: {'启用（确保≥1次）' if enable_like else '禁用'}")
    print(f"   - 评论: {'启用（确保≥1次）' if enable_comment else '禁用'}")
    print(f"   - 分享: {'启用（确保≥1次）' if enable_share else '禁用'}")
    print(f"   - 发布想法: {'启用（确保≥1次）' if enable_post else '禁用'}")

    # 使用默认模板（如果未提供）
    if comment_templates is None:
        comment_templates = get_comment_templates()
    if share_templates is None:
        share_templates = get_share_templates()
    if post_templates is None:
        post_templates = get_post_templates()

    browsed_count = 0
    interacted_count = 0

    # 成功计数器
    success_count = {
        'like': 0,
        'comment': 0,
        'share': 0,
        'post': 0,
    }

    # 目标：每个启用的操作至少成功1次
    targets = {
        'like': 1 if enable_like else 0,
        'comment': 1 if enable_comment else 0,
        'share': 1 if enable_share else 0,
        'post': 1 if enable_post else 0,
    }

    max_attempts = max_items * 3
    i = 0

    while i < max_attempts:
        i += 1

        # 检查是否达成所有目标
        all_targets_met = all(
            success_count[action] >= targets[action]
            for action in ['like', 'comment', 'share', 'post']
        )

        # 如果已达成所有目标且浏览数达到默认值，退出
        if all_targets_met and browsed_count >= max_items:
            print(f"\n✅ 已达成所有目标！")
            print(f"   - 点赞成功: {success_count['like']} 次")
            print(f"   - 评论成功: {success_count['comment']} 次")
            print(f"   - 分享成功: {success_count['share']} 次")
            if enable_post:
                print(f"   - 发布想法成功: {success_count['post']} 次")
            break

        try:
            # 如果启用发布想法且还没发够，则发布想法
            if enable_post and success_count['post'] < targets['post']:
                print(f"\n📝 [循环 {i}] 准备发布想法（确保至少1次）...")
                logging.info(f"触发自动发布想法（第 {i} 次循环）")

                if post_pin(driver, post_templates):
                    success_count['post'] += 1
                    print("   ✅ 发布想法成功！")
                    time.sleep(random.uniform(5, 10))

                    # 发布想法后刷新页面
                    print("   🔄 刷新页面继续浏览...")
                    driver.refresh()
                    time.sleep(random.uniform(3, 5))
                else:
                    print("   ⚠️  发布想法失败，继续尝试")
                    time.sleep(random.uniform(2, 4))

            # 随机滚动
            scroll_times = random.randint(1, 3)
            for _ in range(scroll_times):
                random_scroll(driver)

            # 模拟阅读
            simulate_reading(2, 5)

            # 查找当前可见的内容（回答/文章/想法）
            # 知乎的内容通常在 .List-item 或 .ContentItem 中，支持新的动态类名
            content_items = driver.find_elements(By.CSS_SELECTOR, '.List-item, .ContentItem, .Card, [class*="List-item"], [class*="ContentItem"], [class*="Card"]')

            if not content_items or len(content_items) < 2:
                print("   ⚠️  未找到足够的内容，继续滚动...")
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(2)
                continue

            print(f"   ✅ 找到 {len(content_items)} 条内容")

            # 从中间位置选择内容（避免重复选前几个）
            start_idx = min(2, len(content_items) - 3)
            end_idx = min(start_idx + 5, len(content_items))
            candidate_items = content_items[start_idx:end_idx]

            # 随机选择一条内容
            current_item = random.choice(candidate_items)

            browsed_count += 1
            print(f"\n📄 浏览第 {browsed_count} 条内容...")

            # 滚动到该内容位置
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", current_item)
            time.sleep(0.5)

            # 尝试展开"阅读全文"
            expand_content(driver, current_item)

            # 模拟阅读
            simulate_reading(3, 7)

            # 智能决定互动操作
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
                if not all_targets_met:
                    print("   ⚠️  本条内容未选择互动，继续寻找...")
                else:
                    print("   👀 目标已达成，只是浏览，不互动")
                continue

            # 显示选择的操作和目标进度
            print(f"   💬 决定互动: {', '.join(actions)}")
            progress = (f"      当前进度: 点赞{success_count['like']}/{targets['like']}, "
                       f"评论{success_count['comment']}/{targets['comment']}, "
                       f"分享{success_count['share']}/{targets['share']}")
            if enable_post:
                progress += f", 发布想法{success_count['post']}/{targets['post']}"
            print(progress)

            # 执行操作
            if 'like' in actions:
                if like_content(driver, current_item):
                    success_count['like'] += 1
                    interacted_count += 1
                    time.sleep(random.uniform(1, 2))

            if 'comment' in actions:
                if comment_content(driver, current_item, comment_templates):
                    success_count['comment'] += 1
                    interacted_count += 1
                    time.sleep(random.uniform(1, 2))

            if 'share' in actions:
                if share_content(driver, current_item, share_templates):
                    success_count['share'] += 1
                    interacted_count += 1
                    time.sleep(random.uniform(1, 2))

            # 随机暂停
            time.sleep(random.uniform(2, 5))

            # 向下滚动
            scroll_distance = random.randint(400, 800)
            driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            time.sleep(random.uniform(1, 2))

        except Exception as e:
            print(f"   ❌ 处理内容时出错: {e}")
            logging.error(f"处理内容异常: {e}")
            continue

    print("\n" + "="*60)
    print(f"📊 浏览完成！")
    print(f"   - 浏览了 {browsed_count} 条内容")
    print(f"   - 总互动次数: {interacted_count} 次")
    print(f"   - 成功点赞: {success_count['like']} 次")
    print(f"   - 成功评论: {success_count['comment']} 次")
    print(f"   - 成功分享: {success_count['share']} 次")
    if enable_post:
        print(f"   - 成功发布想法: {success_count['post']} 次")
    print("="*60)

    # 记录统计信息到日志
    summary = (f"浏览完成 - 浏览: {browsed_count}, 互动: {interacted_count}, "
               f"点赞: {success_count['like']}, 评论: {success_count['comment']}, "
               f"分享: {success_count['share']}")
    if enable_post:
        summary += f", 发布想法: {success_count['post']}"
    logging.info(summary)


def main():
    # 初始化日志系统
    setup_logging()

    print("="*60)
    print("知乎智能自动化脚本 v1.0")
    print("="*60)
    logging.info("脚本启动")

    # 询问是否使用代理
    print("\n是否使用代理？")
    print("1. 是")
    print("2. 否（默认）")
    proxy_choice = input("请选择 (1/2，默认2): ").strip()
    use_proxy = (proxy_choice == '1')

    print("\n启动浏览器...")
    driver = create_driver(use_proxy=use_proxy)
    print("✅ 浏览器启动成功！")
    logging.info("浏览器启动成功")

    try:
        # 访问知乎首页
        print("\n访问知乎首页...")
        driver.get('https://www.zhihu.com')
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
        print("5. 发布想法测试")
        print("0. 退出")
        print("="*60)

        choice = input("请输入选项 (0-5): ").strip()

        if choice == '1':
            # 纯浏览
            print("\n🔍 纯浏览模式（不互动）")
            logging.info("开始纯浏览测试")
            smart_browse_and_interact(
                driver,
                max_items=3,
                interaction_rate=0.0,
                enable_like=False,
                enable_comment=False,
                enable_share=False,
                enable_post=False
            )

        elif choice == '2':
            # 点赞测试
            print("\n👍 点赞测试模式（确保至少成功1次）")
            logging.info("开始点赞测试")
            smart_browse_and_interact(
                driver,
                max_items=3,
                interaction_rate=0.3,
                enable_like=True,
                enable_comment=False,
                enable_share=False,
                enable_post=False
            )

        elif choice == '3':
            # 评论测试
            print("\n💬 评论测试模式（确保至少成功1次）")
            logging.info("开始评论测试")
            comment_templates = get_comment_templates()
            smart_browse_and_interact(
                driver,
                max_items=3,
                interaction_rate=0.3,
                enable_like=False,
                enable_comment=True,
                enable_share=False,
                enable_post=False,
                comment_templates=comment_templates
            )

        elif choice == '4':
            # 分享测试
            print("\n🔄 分享测试模式（确保至少成功1次）")
            logging.info("开始分享测试")
            share_templates = get_share_templates()
            smart_browse_and_interact(
                driver,
                max_items=3,
                interaction_rate=0.3,
                enable_like=False,
                enable_comment=False,
                enable_share=True,
                enable_post=False,
                share_templates=share_templates
            )

        elif choice == '5':
            # 发布想法测试
            print("\n📝 发布想法测试模式")
            logging.info("开始发布想法测试")
            post_templates = get_post_templates()
            smart_browse_and_interact(
                driver,
                max_items=3,
                interaction_rate=0.0,
                enable_like=False,
                enable_comment=False,
                enable_share=False,
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
