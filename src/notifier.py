"""通知模块：通过 Webhook 推送填报结果到手机。"""

import json
import requests
from datetime import datetime


def send_notification(config: dict, success: bool, message: str = ""):
    """
    通过 Webhook 发送通知。
    支持飞书、企业微信、钉钉机器人（Webhook 格式兼容）。
    """
    notify_config = config.get("notify", {})
    webhook_url = notify_config.get("webhook_url", "")

    if not webhook_url:
        print("[通知] 未配置 webhook_url，跳过通知")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    status = "成功" if success else "失败"

    payload = {
        "msgtype": "text",
        "text": {
            "content": (
                f"【经营数据填报】{status}\n"
                f"日期：{today}\n"
                f"{message}"
            )
        }
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        print(f"[通知] 已发送，状态码: {resp.status_code}")
    except Exception as e:
        print(f"[通知] 发送失败: {e}")
