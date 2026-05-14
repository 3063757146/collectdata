#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博调试脚本 - 查找页面元素
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

def create_driver():
    options = Options()
    options.add_argument('--proxy-server=socks5://127.0.0.1:10818')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-extensions')

    return webdriver.Chrome(options=options)

print("启动浏览器（可能需要几分钟）...")
driver = create_driver()

try:
    print("访问微博...")
    weibo_url = input("请输入微博链接: ")
    driver.get(weibo_url)

    print("\n等待页面加载...")
    time.sleep(5)

    print("\n" + "="*60)
    print("查找页面上的所有按钮和输入框")
    print("="*60)

    # 查找所有按钮
    print("\n【按钮列表】")
    buttons = driver.find_elements(By.TAG_NAME, 'button')
    for i, btn in enumerate(buttons[:20], 1):  # 只显示前20个
        try:
            text = btn.text.strip()
            aria_label = btn.get_attribute('aria-label')
            class_name = btn.get_attribute('class')

            if text or aria_label:
                print(f"{i}. 文本: {text or '无'} | aria-label: {aria_label or '无'}")
                print(f"   class: {class_name}")
        except:
            pass

    # 查找所有输入框
    print("\n【输入框列表】")
    inputs = driver.find_elements(By.TAG_NAME, 'textarea')
    for i, inp in enumerate(inputs, 1):
        try:
            placeholder = inp.get_attribute('placeholder')
            class_name = inp.get_attribute('class')
            node_type = inp.get_attribute('node-type')

            print(f"{i}. placeholder: {placeholder or '无'}")
            print(f"   class: {class_name}")
            print(f"   node-type: {node_type or '无'}")
        except:
            pass

    # 查找所有 a 标签（可能是点赞、转发链接）
    print("\n【链接列表（可能的操作按钮）】")
    links = driver.find_elements(By.TAG_NAME, 'a')
    for i, link in enumerate(links[:30], 1):  # 只显示前30个
        try:
            text = link.text.strip()
            action_type = link.get_attribute('action-type')

            if action_type:
                print(f"{i}. 文本: {text or '无'} | action-type: {action_type}")
        except:
            pass

    # 查找包含"转发"和"评论"的所有元素
    print("\n【包含'转发'的元素】")
    repost_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '转发')]")
    for i, elem in enumerate(repost_elements[:10], 1):
        try:
            tag = elem.tag_name
            text = elem.text.strip()
            class_name = elem.get_attribute('class')
            print(f"{i}. 标签: {tag} | 文本: {text} | class: {class_name}")
        except:
            pass

    print("\n【包含'评论'的元素】")
    comment_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '评论')]")
    for i, elem in enumerate(comment_elements[:10], 1):
        try:
            tag = elem.tag_name
            text = elem.text.strip()
            class_name = elem.get_attribute('class')
            print(f"{i}. 标签: {tag} | 文本: {text} | class: {class_name}")
        except:
            pass

    print("\n" + "="*60)
    print("调试完成！现在尝试点击转发按钮...")
    print("="*60)

    # 尝试点击转发按钮
    try:
        repost_btn = driver.find_elements(By.XPATH, "//*[contains(text(), '转发')]")[0]
        driver.execute_script("arguments[0].scrollIntoView(true);", repost_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", repost_btn)
        print("✅ 转发按钮点击成功！")
        time.sleep(3)

        # 查看弹窗内容
        print("\n【转发弹窗中的元素】")
        textareas = driver.find_elements(By.TAG_NAME, 'textarea')
        for i, ta in enumerate(textareas, 1):
            placeholder = ta.get_attribute('placeholder')
            print(f"{i}. textarea placeholder: {placeholder}")

        buttons_in_modal = driver.find_elements(By.TAG_NAME, 'button')
        for i, btn in enumerate(buttons_in_modal[:20], 1):
            text = btn.text.strip()
            if text:
                print(f"{i}. 弹窗按钮: {text}")
    except Exception as e:
        print(f"❌ 点击转发失败: {e}")

    input("\n按回车关闭浏览器...")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

finally:
    driver.quit()
