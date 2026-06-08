"""每日经营数据填报 — 主入口。

用法:
    python main.py              # 本地无头模式运行（不显示浏览器窗口）
    python main.py --visible    # 显示浏览器窗口，用于调试
"""

import argparse
import os
import sys
import yaml
from datetime import datetime
from pathlib import Path

from src.browser import Browser
from src.login import login, STATE_FILE
from src.reporter import fill_report
from src.notifier import send_notification


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="每日经营数据自动填报")
    parser.add_argument("--visible", action="store_true", help="显示浏览器窗口（调试用）")
    args = parser.parse_args()

    config = load_config()
    headless = not args.visible

    # 如果有保存的登录态，加载它
    state = str(STATE_FILE) if STATE_FILE.exists() else ""
    browser = Browser(headless=headless, storage_state=state)

    success = False
    message = ""

    try:
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 启动浏览器...")
        browser.start()

        print("执行登录...")
        if not login(browser, config):
            raise Exception("登录失败")

        print("执行填报...")
        if not fill_report(browser, config):
            raise Exception("填报失败")

        success = True
        message = "数据已成功提交。"
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 填报完成")

    except Exception as e:
        success = False
        message = f"错误：{e}"
        print(f"[失败] {e}")
        browser.screenshot("error")

    finally:
        send_notification(config, success, message)
        browser.close()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
