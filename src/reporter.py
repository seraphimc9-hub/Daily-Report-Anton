"""填报模块：导航菜单 → 筛选条件 → 填写数据 → 提交。"""

from datetime import datetime
from src.browser import Browser


# ============================================================
# Element UI 组件交互辅助函数
# ============================================================

def _el_select(page, label_text: str, option_text: str):
    form_item = page.locator(f".el-form-item:has-text('{label_text}')")
    if not form_item.count():
        form_item = page.locator(f"*:has-text('{label_text}')").filter(
            has=page.locator(".el-select")
        ).first
    trigger = form_item.locator(".el-select .el-input__inner, .el-select input").first
    if not trigger.count():
        trigger = form_item.locator("input").first
    trigger.click()
    page.wait_for_timeout(500)
    page.wait_for_timeout(500)
    dropdown = page.locator(".el-select-dropdown").filter(
        has=page.locator(f".el-select-dropdown__item:has-text('{option_text}')")
    ).last
    dropdown.wait_for(state="attached", timeout=5000)
    option = dropdown.locator(f".el-select-dropdown__item:has-text('{option_text}')").last
    option.wait_for(state="visible", timeout=5000)
    option.click()
    page.wait_for_timeout(500)


def _el_autocomplete(page, input_label: str, search_text: str):
    form_item = page.locator(f".el-form-item:has-text('{input_label}')")
    if not form_item.count():
        form_item = page.locator(f"*:has-text('{input_label}')").filter(
            has=page.locator("input")
        ).first
    inp = form_item.locator("input").first
    inp.click()
    inp.fill("")
    page.wait_for_timeout(200)
    inp.type(search_text, delay=50)
    page.wait_for_timeout(1000)
    item = page.locator(f"li:has-text('{search_text}')").last
    item.wait_for(state="visible", timeout=8000)
    item.click()
    page.wait_for_timeout(500)


def _nav_dropdown_click(page, menu_title: str):
    toggle = page.locator(f".u-header__nav-link-toggle:has-text('{menu_title}')")
    if not toggle.count():
        toggle = page.locator(f"span:has-text('{menu_title}')").first
    box = toggle.first.bounding_box()
    if box:
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    else:
        toggle.first.hover()
    page.wait_for_timeout(1000)

    item = page.locator(f"a.u-header__sub-menu-nav-link:has-text('{menu_title}')")
    if not item.count():
        item = page.locator(f".dropdown-menu a:has-text('{menu_title}')")
    if not item.count():
        item = page.locator(f"a:has-text('{menu_title}')").last
    box = item.first.bounding_box()
    if box:
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.wait_for_timeout(300)
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    else:
        item.first.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)


# ============================================================
# 数据填充（elementFromPoint 坐标法）
# ============================================================

def _fill_table_data(page, report_data: dict):
    today = str(datetime.now().day)
    values = list(report_data.values())

    # 找 today 列头的 X 坐标
    ths = page.locator("th").all()
    col_x = None
    for th in ths:
        if th.inner_text().strip() == today:
            b = th.bounding_box()
            if b:
                col_x = b["x"] + b["width"] / 2
            break
    if col_x is None:
        raise Exception(f"未找到日期列: {today}")

    # 找「七、销售费用」下方 3 行的 Y 坐标
    result = page.evaluate("""() => {
        const allDivs = document.querySelectorAll('.paddingLeftRight10px');
        let sectionDiv = null;
        for (const d of allDivs) {
            if (d.textContent.trim().startsWith('七、销售费用')) {
                sectionDiv = d; break;
            }
        }
        if (!sectionDiv) return {error: 'section not found'};
        sectionDiv.scrollIntoView({block: 'center'});
        const sectionY = sectionDiv.getBoundingClientRect().y;

        const inputs = Array.from(document.querySelectorAll('input.el-input__inner'));
        const belowInputs = [];
        for (const inp of inputs) {
            const r = inp.getBoundingClientRect();
            if (r.y > sectionY + 5 && r.y < sectionY + 400)
                belowInputs.push({y: Math.round(r.y)});
        }
        const rows = [];
        for (const inp of belowInputs) {
            let found = false;
            for (const row of rows) { if (Math.abs(row.y - inp.y) < 40) { found = true; break; } }
            if (!found) rows.push(inp);
        }
        return {rowYs: rows.slice(0, 3).map(r => r.y)};
    }""")

    row_ys = result.get("rowYs", [])
    if len(row_ys) < 3:
        raise Exception(f"未找到足够的行: {result}")

    # 用 elementFromPoint 命中每个 input 并填值
    for i, ry in enumerate(row_ys):
        if i >= len(values):
            break
        val = str(values[i])
        r = page.evaluate("""([x, y, val]) => {
            let inp = document.elementFromPoint(x, y);
            if (!inp) return {error: 'no element'};
            if (inp.tagName !== 'INPUT') {
                const nearby = document.elementsFromPoint(x, y);
                for (const n of nearby) { if (n.tagName === 'INPUT') { inp = n; break; } }
            }
            if (!inp || inp.tagName !== 'INPUT') return {error: 'no input', tag: inp?.tagName};
            inp.focus();
            inp.value = '';
            inp.dispatchEvent(new Event('input', {bubbles: true}));
            inp.value = val;
            inp.dispatchEvent(new Event('input', {bubbles: true}));
            inp.dispatchEvent(new Event('change', {bubbles: true}));
            return {ok: true, val};
        }""", [col_x, ry, val])
        if "error" in r:
            raise Exception(f"填充第{i+1}行失败: {r}")


# ============================================================
# 主流程
# ============================================================

def fill_report(browser: Browser, config: dict) -> bool:
    page = browser.page

    # 等待页面完全加载（登录后 CAS 会重定向）
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    browser.screenshot("00_fill_start")

    # 1. 导航菜单 → 阿米巴数据填报
    _nav_dropdown_click(page, "阿米巴数据填报")

    # 2. 点击页面「填报」
    page.locator("span:text-is('填报')").first.click()
    page.wait_for_timeout(1500)

    # 3. 筛选条件
    f = config["filter"]
    _el_select(page, "填报层级", f["填报层级"])
    _el_select(page, "填报单位", f["填报单位"])
    _el_autocomplete(page, "阿米巴", f["阿米巴"])
    _el_autocomplete(page, "币种", f["币种"])

    # 4. 点击「修改」进入主数据页
    page.locator("button.el-button--primary:has-text('修改')").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    browser.screenshot("01_main_page")

    # 5. 填写表格数据
    _fill_table_data(page, config["report_data"])
    browser.screenshot("02_data_filled")

    # 6. 提交
    page.locator("button.el-button--danger:has-text('提交')").click()
    page.wait_for_timeout(3000)
    browser.screenshot("03_submitted")

    return True
