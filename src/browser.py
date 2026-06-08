"""Playwright 浏览器封装：启动、截图、关闭。"""

import os
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser


class Browser:
    """封装 Playwright 浏览器实例，统一管理生命周期。"""

    def __init__(self, headless: bool = True, storage_state: str = ""):
        self.headless = headless
        self.storage_state = storage_state
        self._playwright = None
        self._browser: Browser | None = None
        self._context = None
        self._page: Page | None = None
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def start(self) -> Page:
        """启动浏览器并返回 page 对象。"""
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)

        # 如果有登录态文件，恢复 cookies / localStorage
        ctx_kwargs = {}
        if self.storage_state and os.path.exists(self.storage_state):
            ctx_kwargs["storage_state"] = self.storage_state
        self._context = self._browser.new_context(**ctx_kwargs)
        self._page = self._context.new_page()
        return self._page

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("浏览器未启动，请先调用 start()")
        return self._page

    def screenshot(self, name: str) -> str:
        """截图并保存到 screenshots/ 目录。返回文件路径。"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.screenshot_dir, f"{ts}_{name}.png")
        self.page.screenshot(path=path, full_page=True)
        return path

    def close(self):
        """关闭浏览器和 Playwright。"""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
