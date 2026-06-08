"""CAS 两步登录：输入用户名 → 下一步 → 输入密码 → 登录。"""

from pathlib import Path
from src.browser import Browser

STATE_FILE = Path(__file__).parent.parent / "auth_state.json"


def login(browser: Browser, config: dict) -> bool:
    page = browser.page

    # 如果已经加载了登录态（Browser 构造函数传入），直接验证
    if browser.storage_state and STATE_FILE.exists():
        page.goto(config["target"]["url"])
        page.wait_for_load_state("networkidle")
        if page.query_selector("text=阿米巴经营管理平台"):
            return True
        # 登录态失效，重新登录

    # 导航到 CAS 登录页
    page.goto(config["target"]["login_url"])
    page.wait_for_load_state("networkidle")

    # 第一步：输入用户名，点击「下一步」
    page.fill("#username", config["credentials"]["username"])
    page.click("input.c-usr-next")

    # 等待密码框出现
    page.wait_for_selector("#password", state="visible", timeout=10000)

    # 第二步：输入密码，点击「登录」
    page.fill("#password", config["credentials"]["password"])
    page.click("input.btn-submit")

    # 等待登录成功（国外服务器访问国内网站较慢，给 30 秒）
    try:
        page.wait_for_selector("text=阿米巴经营管理平台", timeout=30000)
    except Exception:
        # 失败时截图帮助排查
        browser.screenshot("login_failed")
        # 检查是否有错误提示
        err = page.query_selector(".error, .alert-danger, [class*=error]")
        if err:
            raise Exception(f"登录失败: {err.inner_text()}")
        # 检查当前 URL 是否还在登录页
        if "login" in page.url:
            raise Exception("登录失败: 仍在登录页面，请检查账号密码或网络")
        raise Exception(f"登录超时: 当前URL={page.url}")

    # 保存登录态
    page.context.storage_state(path=str(STATE_FILE))
    browser.storage_state = str(STATE_FILE)
    return True
