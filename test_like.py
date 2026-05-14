#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
点赞功能诊断工具
测试点赞按钮并输出详细调试信息
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

def create_driver():
    """创建浏览器"""
    chrome_options = Options()
    chrome_options.add_argument('--proxy-server=socks5://127.0.0.1:10818')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    return webdriver.Chrome(options=chrome_options)

def diagnose_like_button(driver):
    """诊断点赞按钮"""
    print("\n" + "="*60)
    print("点赞按钮诊断工具")
    print("="*60)

    # 获取所有微博卡片
    try:
        articles = driver.find_elements(By.TAG_NAME, 'article')
        print(f"\n✅ 找到 {len(articles)} 个微博卡片")

        if not articles:
            print("❌ 未找到微博卡片，可能页面还没加载完成")
            return

        # 诊断第一个微博
        weibo = articles[0]
        print(f"\n📋 诊断第一个微博卡片...")

        # 查找所有按钮
        print("\n🔍 查找所有按钮...")
        all_buttons = weibo.find_elements(By.TAG_NAME, 'button')
        print(f"   找到 {len(all_buttons)} 个按钮\n")

        for i, btn in enumerate(all_buttons, 1):
            try:
                text = btn.text.strip()
                class_name = btn.get_attribute('class') or '(无)'
                aria_label = btn.get_attribute('aria-label') or '(无)'
                title = btn.get_attribute('title') or '(无)'
                is_visible = btn.is_displayed()

                print(f"   按钮 {i}:")
                print(f"     - 文本: {text[:30] if text else '(空)'}")
                print(f"     - class: {class_name[:60]}")
                print(f"     - aria-label: {aria_label[:30]}")
                print(f"     - title: {title[:30]}")
                print(f"     - 是否可见: {is_visible}")

                # 检查是否是点赞按钮
                is_like_button = (
                    'like' in class_name.lower() or
                    'like' in aria_label.lower() or
                    '赞' in text or
                    '赞' in aria_label or
                    '赞' in title
                )

                if is_like_button:
                    print(f"     ⭐ 【可能是点赞按钮】")

                    # 尝试点击
                    print(f"\n   🖱️  尝试点击这个按钮...")

                    # 记录点击前状态
                    class_before = btn.get_attribute('class')

                    # 滚动到元素
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(1)

                    # 点击
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        print(f"   ✅ 点击成功")

                        # 等待状态更新
                        time.sleep(2)

                        # 检查状态变化
                        class_after = btn.get_attribute('class')

                        print(f"\n   📊 状态对比:")
                        print(f"     - 点击前: {class_before[:80]}")
                        print(f"     - 点击后: {class_after[:80]}")

                        if class_before != class_after:
                            print(f"   ✅ 状态已改变，点赞可能成功！")
                        else:
                            print(f"   ⚠️  状态未改变，点赞可能失败")

                        # 询问用户确认
                        print(f"\n   ❓ 请在浏览器中查看，这个微博是否已经点赞？")
                        result = input("   已点赞？(y/n): ").strip().lower()

                        if result == 'y':
                            print(f"\n   ✅ 找到正确的点赞按钮！")
                            print(f"   推荐选择器：")
                            print(f"     - CSS: button[class*=\"{class_name.split()[0]}\"]")
                            print(f"     - XPATH: .//button[@aria-label=\"{aria_label}\"]" if aria_label != '(无)' else "")
                        else:
                            print(f"\n   ❌ 这不是正确的点赞按钮，继续查找...")

                    except Exception as e:
                        print(f"   ❌ 点击失败: {e}")

                print()

            except Exception as e:
                print(f"   ⚠️  读取按钮 {i} 失败: {e}\n")
                continue

        # 查找所有图标
        print("\n🔍 查找所有图标元素（i 标签）...")
        all_icons = weibo.find_elements(By.TAG_NAME, 'i')
        print(f"   找到 {len(all_icons)} 个图标\n")

        for i, icon in enumerate(all_icons[:10], 1):  # 只显示前10个
            try:
                class_name = icon.get_attribute('class') or '(无)'
                parent = icon.find_element(By.XPATH, '..')
                parent_tag = parent.tag_name

                print(f"   图标 {i}:")
                print(f"     - class: {class_name[:60]}")
                print(f"     - 父元素: {parent_tag}")

                if 'like' in class_name.lower() or 'heart' in class_name.lower():
                    print(f"     ⭐ 【可能是点赞图标】")
                    print(f"     - 建议点击父元素: {parent_tag}")

                print()

            except Exception as e:
                print(f"   ⚠️  读取图标 {i} 失败: {e}\n")
                continue

    except Exception as e:
        print(f"\n❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("启动浏览器...")
    driver = create_driver()

    try:
        # 获取微博链接
        print("\n请输入微博详情页链接（或直接按回车访问首页）:")
        url = input("> ").strip()

        if not url:
            url = "https://weibo.com"

        print(f"\n访问: {url}")
        driver.get(url)

        print("\n等待页面加载...")
        time.sleep(5)

        # 开始诊断
        diagnose_like_button(driver)

        print("\n" + "="*60)
        print("诊断完成！")
        print("="*60)

        input("\n按回车关闭浏览器...")

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("✅ 浏览器已关闭")

if __name__ == "__main__":
    main()
