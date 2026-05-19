#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顶层抓包运行脚本

提供 run(platform, action, num) 接口，执行完整的抓包流程：
1. 启动抓包
2. 启动浏览器 → 登录 → 执行行为 → 退出
3. 停止抓包并保存
4. 重复num次，每次生成独立的pcap文件

使用示例：
    python3 run_capture.py --platform weibo --action like --num 5
    # 执行5次微博点赞，每次生成一对pcap文件

快速模式（提速50-70%）：
    FAST_MODE=1 python3 run_capture.py --platform weibo --action browse --num 1
"""

import sys
import os
import time
import logging
import argparse
import random
from capture import CaptureManager, CaptureConfig
from capture.label import generate_label

# 检查是否启用快速模式（环境变量）
FAST_MODE = os.getenv('FAST_MODE', '0') == '1'


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def run_weibo_action(action: str, iteration: int) -> bool:
    """
    运行一次微博行为（登录 → 访问 → 执行 → 退出）

    Args:
        action: 行为类型（like/comment/repost/post/browse）
        iteration: 当前迭代次数（用于日志）

    Returns:
        是否成功
    """
    logger.info(f"[Iteration {iteration}] Starting Weibo bot for action: {action}")

    try:
        # 导入微博bot模块
        import weibo_bot_smart

        # 创建driver（使用快速模式如果已启用）
        driver = weibo_bot_smart.create_driver(use_proxy=True, fast_mode=FAST_MODE)

        try:
            # 打开微博首页
            driver.get("https://weibo.com")
            time.sleep(3)

            # 检查登录状态
            if not weibo_bot_smart.check_login(driver):
                logger.info("[Iteration {iteration}] Not logged in, waiting for manual login...")
                weibo_bot_smart.wait_for_login(driver)

            logger.info(f"[Iteration {iteration}] Logged in successfully")

            # 根据action执行不同的行为
            if action == "like":
                # 浏览并点赞1次
                weibo_bot_smart.smart_browse_and_interact(
                    driver,
                    max_weibos=2,
                    interaction_rate=0.3,
                    enable_like=True,
                    enable_comment=False,
                    enable_repost=False
                )

            elif action == "comment":
                # 浏览并评论1次
                comment_templates = weibo_bot_smart.get_comment_templates()
                weibo_bot_smart.smart_browse_and_interact(
                    driver,
                    max_weibos=2,
                    interaction_rate=0.3,
                    enable_like=False,
                    enable_comment=True,
                    enable_repost=False,
                    comment_templates=comment_templates
                )

            elif action == "repost":
                # 浏览并转发1次
                repost_templates = weibo_bot_smart.get_repost_templates()
                weibo_bot_smart.smart_browse_and_interact(
                    driver,
                    max_weibos=2,
                    interaction_rate=0.3,
                    enable_like=False,
                    enable_comment=False,
                    enable_repost=True,
                    repost_templates=repost_templates
                )

            elif action == "post":
                # 发布一条新微博（使用统一的 smart_browse_and_interact 接口）
                post_templates = weibo_bot_smart.get_post_templates()
                weibo_bot_smart.smart_browse_and_interact(
                    driver,
                    max_weibos=3,  # 只需要发1条微博
                    interaction_rate=0.0,  # 不需要额外互动
                    enable_like=False,
                    enable_comment=False,
                    enable_repost=False,
                    enable_post=True,  # 启用发帖（确保至少成功1次）
                    post_templates=post_templates
                )

            elif action == "browse":
                # 纯浏览，不互动
                weibo_bot_smart.smart_browse_and_interact(
                    driver,
                    max_weibos=3,
                    interaction_rate=0.0,
                    enable_like=False,
                    enable_comment=False,
                    enable_repost=False
                )

            else:
                logger.error(f"Unknown action: {action}")
                return False

            logger.info(f"[Iteration {iteration}] Action completed successfully")
            return True

        finally:
            # 总是关闭浏览器
            driver.quit()
            logger.info(f"[Iteration {iteration}] Browser closed")

    except Exception as e:
        logger.error(f"[Iteration {iteration}] Error: {e}", exc_info=True)
        return False


def run_facebook_action(action: str, iteration: int) -> bool:
    """
    运行一次Facebook行为（登录 → 访问 → 执行 → 退出）

    Args:
        action: 行为类型（like/comment/share/post/browse）
        iteration: 当前迭代次数

    Returns:
        是否成功
    """
    logger.info(f"[Iteration {iteration}] Starting Facebook bot for action: {action}")

    try:
        import facebook_bot_smart

        driver = facebook_bot_smart.create_driver(use_proxy=True)

        try:
            driver.get("https://www.facebook.com")
            time.sleep(3)

            if not facebook_bot_smart.check_login(driver):
                logger.info(f"[Iteration {iteration}] Not logged in, waiting for manual login...")
                facebook_bot_smart.wait_for_login(driver)

            logger.info(f"[Iteration {iteration}] Logged in successfully")

            # 根据action执行行为
            if action == "like":
                # 浏览并点赞1次
                facebook_bot_smart.smart_browse_and_interact(
                    driver,
                    max_posts=2,
                    interaction_rate=0.3,
                    enable_like=True,
                    enable_comment=False,
                    enable_share=False
                )

            elif action == "comment":
                # 浏览并评论1次（comment_templates内置在函数中）
                facebook_bot_smart.smart_browse_and_interact(
                    driver,
                    max_posts=2,
                    interaction_rate=0.3,
                    enable_like=False,
                    enable_comment=True,
                    enable_share=False
                )

            elif action == "share":
                # 浏览并分享1次（share_templates内置在函数中）
                facebook_bot_smart.smart_browse_and_interact(
                    driver,
                    max_posts=2,
                    interaction_rate=0.3,
                    enable_like=False,
                    enable_comment=False,
                    enable_share=True
                )

            elif action == "post":
                # 发布一条新帖子
                post_templates = [
                    "Just finished an amazing workout session! Feeling energized and ready to take on the day! 💪",
                    "Grateful for all the wonderful people in my life. Sometimes it's the little things that matter most. ❤️",
                    "Beautiful sunset today! Nature never fails to amaze me. 🌅",
                    "Coffee and good vibes - that's all I need to start the day right! ☕",
                    "Excited to share that I've reached a personal milestone today. Hard work really does pay off! 🎉",
                    "Taking time to appreciate the present moment. Life moves fast, so it's important to slow down sometimes. 🧘",
                    "Just discovered a new favorite spot in the city. Can't wait to go back! 📍",
                    "Finished reading an incredible book today. Highly recommend it to anyone looking for inspiration! 📚",
                    "Sometimes you just need to step back and appreciate how far you've come. Proud of the progress! 🌟",
                    "Weekend plans: relaxation and recharging. Self-care isn't selfish! 🛀",
                ]
                content = random.choice(post_templates)

                # 执行发帖
                if not facebook_bot_smart.create_post(driver, content):
                    logger.warning(f"[Iteration {iteration}] Post action failed")
                    return False

                # 发帖后浏览3条帖子
                facebook_bot_smart.smart_browse_and_interact(
                    driver,
                    max_posts=3,
                    interaction_rate=0.0,
                    enable_like=False,
                    enable_comment=False,
                    enable_share=False
                )

            elif action == "browse":
                # 纯浏览，不互动
                facebook_bot_smart.smart_browse_and_interact(
                    driver,
                    max_posts=3,
                    interaction_rate=0.0,
                    enable_like=False,
                    enable_comment=False,
                    enable_share=False
                )

            else:
                logger.error(f"Unknown action: {action}")
                return False

            logger.info(f"[Iteration {iteration}] Action completed successfully")
            return True

        finally:
            driver.quit()
            logger.info(f"[Iteration {iteration}] Browser closed")

    except Exception as e:
        logger.error(f"[Iteration {iteration}] Error: {e}", exc_info=True)
        return False


def run_tiktok_action(action: str, iteration: int) -> bool:
    """
    运行一次TikTok行为（登录 → 访问 → 执行 → 退出）

    Args:
        action: 行为类型（like/comment/share/browse）
        iteration: 当前迭代次数

    Returns:
        是否成功
    """
    logger.info(f"[Iteration {iteration}] Starting TikTok bot for action: {action}")

    try:
        import tiktok_bot

        driver = tiktok_bot.create_driver(use_proxy=True)

        try:
            driver.get("https://www.tiktok.com")
            time.sleep(3)

            if not tiktok_bot.check_login(driver):
                logger.info(f"[Iteration {iteration}] Not logged in, waiting for manual login...")
                tiktok_bot.wait_for_login(driver)

            logger.info(f"[Iteration {iteration}] Logged in successfully")

            # 根据action执行行为
            if action == "like":
                # 浏览并点赞1次
                tiktok_bot.smart_browse_and_interact(
                    driver,
                    max_videos=2,
                    interaction_rate=0.3,
                    enable_like=True,
                    enable_comment=False
                )

            elif action == "comment":
                # 浏览并评论1次
                comment_templates = tiktok_bot.get_comment_templates()
                tiktok_bot.smart_browse_and_interact(
                    driver,
                    max_videos=2,
                    interaction_rate=0.3,
                    enable_like=False,
                    enable_comment=True,
                    comment_templates=comment_templates
                )

            elif action == "share":
                # TikTok 暂不支持 share 功能
                logger.warning(f"[Iteration {iteration}] TikTok share not yet implemented, fallback to browse")
                tiktok_bot.smart_browse_and_interact(
                    driver,
                    max_videos=2,
                    interaction_rate=0.0,
                    enable_like=False,
                    enable_comment=False
                )

            elif action == "browse":
                # 纯浏览，不互动
                tiktok_bot.smart_browse_and_interact(
                    driver,
                    max_videos=3,
                    interaction_rate=0.0,
                    enable_like=False,
                    enable_comment=False
                )

            else:
                logger.error(f"Unknown action: {action}")
                return False

            logger.info(f"[Iteration {iteration}] Action completed successfully")
            return True

        finally:
            driver.quit()
            logger.info(f"[Iteration {iteration}] Browser closed")

    except Exception as e:
        logger.error(f"[Iteration {iteration}] Error: {e}", exc_info=True)
        return False


def run_twitter_action(action: str, iteration: int) -> bool:
    """
    运行一次Twitter行为（登录 → 访问 → 执行 → 退出）

    Args:
        action: 行为类型（like/comment/retweet/post/browse）
        iteration: 当前迭代次数

    Returns:
        是否成功
    """
    logger.info(f"[Iteration {iteration}] Starting Twitter bot for action: {action}")

    try:
        import twitter_bot_smart

        driver = twitter_bot_smart.create_driver(use_proxy=True)

        try:
            driver.get("https://x.com/home")
            time.sleep(3)

            if not twitter_bot_smart.check_login(driver):
                logger.info(f"[Iteration {iteration}] Not logged in, waiting for manual login...")
                twitter_bot_smart.wait_for_login(driver)

            logger.info(f"[Iteration {iteration}] Logged in successfully")

            # 根据action执行行为
            if action == "like":
                # 浏览并点赞1次
                twitter_bot_smart.smart_browse_and_interact(
                    driver,
                    max_tweets=2,
                    interaction_rate=0.3,
                    enable_like=True,
                    enable_comment=False,
                    enable_retweet=False,
                    enable_post=False
                )

            elif action == "comment":
                # 浏览并评论1次
                comment_templates = twitter_bot_smart.get_comment_templates()
                twitter_bot_smart.smart_browse_and_interact(
                    driver,
                    max_tweets=2,
                    interaction_rate=0.3,
                    enable_like=False,
                    enable_comment=True,
                    enable_retweet=False,
                    enable_post=False,
                    comment_templates=comment_templates
                )

            elif action == "retweet":
                # 浏览并转发1次
                retweet_templates = twitter_bot_smart.get_retweet_templates()
                twitter_bot_smart.smart_browse_and_interact(
                    driver,
                    max_tweets=2,
                    interaction_rate=0.3,
                    enable_like=False,
                    enable_comment=False,
                    enable_retweet=True,
                    enable_post=False,
                    retweet_templates=retweet_templates
                )

            elif action == "post":
                # 发布一条新推文
                post_templates = twitter_bot_smart.get_post_templates()
                twitter_bot_smart.smart_browse_and_interact(
                    driver,
                    max_tweets=2,
                    interaction_rate=0.0,
                    enable_like=False,
                    enable_comment=False,
                    enable_retweet=False,
                    enable_post=True,
                    post_templates=post_templates
                )

            elif action == "browse":
                # 纯浏览，不互动
                twitter_bot_smart.smart_browse_and_interact(
                    driver,
                    max_tweets=3,
                    interaction_rate=0.0,
                    enable_like=False,
                    enable_comment=False,
                    enable_retweet=False,
                    enable_post=False
                )

            else:
                logger.error(f"Unknown action: {action}")
                return False

            logger.info(f"[Iteration {iteration}] Action completed successfully")
            return True

        finally:
            driver.quit()
            logger.info(f"[Iteration {iteration}] Browser closed")

    except Exception as e:
        logger.error(f"[Iteration {iteration}] Error: {e}", exc_info=True)
        return False


def run_zhihu_action(action: str, iteration: int) -> bool:
    """
    运行一次知乎行为（登录 → 访问 → 执行 → 退出）

    Args:
        action: 行为类型（like/comment/share/post/browse）
        iteration: 当前迭代次数

    Returns:
        是否成功
    """
    logger.info(f"[Iteration {iteration}] Starting Zhihu bot for action: {action}")

    try:
        import zhihu_bot_smart

        driver = zhihu_bot_smart.create_driver(use_proxy=True)

        try:
            driver.get("https://www.zhihu.com")
            time.sleep(3)

            if not zhihu_bot_smart.check_login(driver):
                logger.info(f"[Iteration {iteration}] Not logged in, waiting for manual login...")
                zhihu_bot_smart.wait_for_login(driver)

            logger.info(f"[Iteration {iteration}] Logged in successfully")

            # 根据action执行行为
            if action == "like":
                # 浏览并点赞1次
                zhihu_bot_smart.smart_browse_and_interact(
                    driver,
                    max_items=2,
                    interaction_rate=0.3,
                    enable_like=True,
                    enable_comment=False,
                    enable_share=False,
                    enable_post=False
                )

            elif action == "comment":
                # 浏览并评论1次
                comment_templates = zhihu_bot_smart.get_comment_templates()
                zhihu_bot_smart.smart_browse_and_interact(
                    driver,
                    max_items=2,
                    interaction_rate=0.3,
                    enable_like=False,
                    enable_comment=True,
                    enable_share=False,
                    enable_post=False,
                    comment_templates=comment_templates
                )

            elif action == "share":
                # 浏览并分享1次（转发到想法）
                share_templates = zhihu_bot_smart.get_share_templates()
                zhihu_bot_smart.smart_browse_and_interact(
                    driver,
                    max_items=2,
                    interaction_rate=0.3,
                    enable_like=False,
                    enable_comment=False,
                    enable_share=True,
                    enable_post=False,
                    share_templates=share_templates
                )

            elif action == "post":
                # 发布一条新想法
                post_templates = zhihu_bot_smart.get_post_templates()
                zhihu_bot_smart.smart_browse_and_interact(
                    driver,
                    max_items=2,
                    interaction_rate=0.0,
                    enable_like=False,
                    enable_comment=False,
                    enable_share=False,
                    enable_post=True,
                    post_templates=post_templates
                )

            elif action == "browse":
                # 纯浏览，不互动
                zhihu_bot_smart.smart_browse_and_interact(
                    driver,
                    max_items=3,
                    interaction_rate=0.0,
                    enable_like=False,
                    enable_comment=False,
                    enable_share=False,
                    enable_post=False
                )

            else:
                logger.error(f"Unknown action: {action}")
                return False

            logger.info(f"[Iteration {iteration}] Action completed successfully")
            return True

        finally:
            driver.quit()
            logger.info(f"[Iteration {iteration}] Browser closed")

    except Exception as e:
        logger.error(f"[Iteration {iteration}] Error: {e}", exc_info=True)
        return False


def run(platform: str, action: str, num: int, timeout: int = 300) -> int:
    """
    顶层接口：执行num次指定平台的指定行为，每次抓包

    Args:
        platform: 平台名称（weibo/facebook/tiktok）
        action: 行为类型（like/comment/repost/share/post/browse）
        num: 执行次数
        timeout: 单次抓包超时（秒），默认300秒（5分钟）

    Returns:
        成功执行的次数

    流程：
        对于每次迭代（i = 1 to num）：
        1. 生成label：platform_action_i
        2. 启动抓包（macOS + VPS）
        3. 运行bot：登录 → 执行行为 → 退出
        4. 停止抓包并保存
        5. 等待间隔（避免被检测）
    """
    logger.info("="*70)
    logger.info(f"Starting capture run: platform={platform}, action={action}, num={num}")
    logger.info("="*70)

    success_count = 0

    # 根据平台创建专属输出目录
    platform_output_dir = f"output/captures/{platform}"
    os.makedirs(platform_output_dir, exist_ok=True)

    # 创建自定义配置，指定平台专属输出目录
    config = CaptureConfig()
    config.local_output_dir = platform_output_dir

    # 使用自定义配置创建 CaptureManager
    manager = CaptureManager(config=config)

    # 选择bot执行函数
    if platform == "weibo":
        bot_func = run_weibo_action
    elif platform == "facebook":
        bot_func = run_facebook_action
    elif platform == "tiktok":
        bot_func = run_tiktok_action
    elif platform == "twitter":
        bot_func = run_twitter_action
    elif platform == "zhihu":
        bot_func = run_zhihu_action
    else:
        logger.error(f"Unknown platform: {platform}")
        return 0

    for i in range(1, num + 1):
        logger.info("\n" + "="*70)
        logger.info(f"Iteration {i}/{num}")
        logger.info("="*70)

        # 生成label（格式：platform_action_序号）
        label = f"{platform}_{action}_{i}"

        try:
            # === 第1步：启动抓包 ===
            logger.info(f"[{i}/{num}] Starting capture: {label}")
            manager.start(label, timeout=timeout)

            # === 第2步：执行bot行为 ===
            bot_success = bot_func(action, i)

            # === 第3步：停止抓包 ===
            logger.info(f"[{i}/{num}] Stopping capture...")
            result = manager.stop()

            # === 第4步：记录结果 ===
            if bot_success:
                success_count += 1
                logger.info(f"[{i}/{num}] ✅ Success!")
                logger.info(f"  Duration: {result['duration']:.1f}s")
                logger.info(f"  Local pcap: {result['local_pcap']}")
                if result['vps_pcap']:
                    logger.info(f"  VPS pcap: {result['vps_pcap']}")
            else:
                logger.warning(f"[{i}/{num}] ⚠️  Bot action failed, but capture saved")

        except KeyboardInterrupt:
            logger.warning("\n\n⚠️  User interrupted")
            # 尝试停止当前抓包
            try:
                if manager._running:
                    manager.stop()
            except Exception:
                pass
            break

        except Exception as e:
            logger.error(f"[{i}/{num}] ❌ Error: {e}", exc_info=True)
            # 尝试停止抓包（即使出错也要保存）
            try:
                if manager._running:
                    manager.stop()
            except Exception:
                pass

        # === 第5步：迭代间隔 ===
        if i < num:
            interval = 30  # 30秒间隔，避免被检测
            logger.info(f"\nWaiting {interval}s before next iteration...")
            time.sleep(interval)

    # === 总结 ===
    logger.info("\n" + "="*70)
    logger.info("Capture run completed")
    logger.info("="*70)
    logger.info(f"Total iterations: {num}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {num - success_count}")
    logger.info(f"Success rate: {success_count/num*100:.1f}%")
    logger.info("="*70)

    # 断开SSH连接
    try:
        manager._ssh.disconnect()
    except Exception:
        pass

    return success_count


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='会话级抓包运行脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 微博点赞5次
  %(prog)s --platform weibo --action like --num 5

  # Facebook评论3次
  %(prog)s --platform facebook --action comment --num 3

  # TikTok浏览10次
  %(prog)s --platform tiktok --action browse --num 10

  # 自定义超时（10分钟）
  %(prog)s --platform weibo --action post --num 2 --timeout 600

支持的平台:
  weibo, facebook, tiktok, twitter, zhihu

支持的行为:
  - weibo: like, comment, repost, post, browse
  - facebook: like, comment, share, post, browse
  - tiktok: like, comment, share, browse
  - twitter: like, comment, retweet, post, browse
  - zhihu: like, comment, share, post, browse
        """
    )

    parser.add_argument(
        '--platform', '-p',
        required=True,
        choices=['weibo', 'facebook', 'tiktok', 'twitter', 'zhihu'],
        help='平台名称'
    )

    parser.add_argument(
        '--action', '-a',
        required=True,
        help='行为类型（like/comment/repost/share/post/browse）'
    )

    parser.add_argument(
        '--num', '-n',
        type=int,
        required=True,
        help='执行次数'
    )

    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=300,
        help='单次抓包超时（秒），默认300秒'
    )

    args = parser.parse_args()

    # 验证action对于当前platform是否有效
    valid_actions = {
        'weibo': ['like', 'comment', 'repost', 'post', 'browse'],
        'facebook': ['like', 'comment', 'share', 'post', 'browse'],
        'tiktok': ['like', 'comment', 'share', 'browse'],
        'twitter': ['like', 'comment', 'retweet', 'post', 'browse'],
        'zhihu': ['like', 'comment', 'share', 'post', 'browse'],
    }

    if args.action not in valid_actions[args.platform]:
        logger.error(
            f"Invalid action '{args.action}' for platform '{args.platform}'. "
            f"Valid actions: {', '.join(valid_actions[args.platform])}"
        )
        return 1

    # 执行
    success_count = run(args.platform, args.action, args.num, args.timeout)

    # 返回码：全部成功返回0，否则返回1
    return 0 if success_count == args.num else 1


if __name__ == '__main__':
    sys.exit(main())
