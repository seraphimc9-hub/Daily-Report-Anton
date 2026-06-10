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

    # 一次 JS 调用完成所有操作：定位列 → 找行 → 按 X 坐标匹配 → 填值
    result = page.evaluate("""([today, values]) => {
        // 1. 找 today 列头的 X 坐标
        const ths = document.querySelectorAll('th');
        let colX = null;
        for (const th of ths) {
            if (th.textContent.trim() === today) {
                const r = th.getBoundingClientRect();
                colX = r.x + r.width / 2;
                break;
            }
        }
        if (colX === null) return {error: 'column not found: ' + today};

        // 2. 找「七、销售费用」并滚动到可见区域
        const divs = document.querySelectorAll('.paddingLeftRight10px');
        let sectionDiv = null;
        for (const d of divs) {
            if (d.textContent.trim().startsWith('七、销售费用')) { sectionDiv = d; break; }
        }
        if (!sectionDiv) return {error: 'section not found'};
        sectionDiv.scrollIntoView({block: 'center'});

        // 3. 找 section 下方所有 input，按 Y 聚类成行
        const sectionY = sectionDiv.getBoundingClientRect().y;
        const allInputs = Array.from(document.querySelectorAll('input.el-input__inner'));
        const rows = [];
        for (const inp of allInputs) {
            const r = inp.getBoundingClientRect();
            if (r.y <= sectionY + 5 || r.y >= sectionY + 400) continue;
            let found = false;
            for (const row of rows) {
                if (Math.abs(row.y - r.y) < 40) { row.inputs.push(inp); found = true; break; }
            }
            if (!found) rows.push({y: r.y, inputs: [inp]});
        }
        rows.sort((a, b) => a.y - b.y);
        const targetRows = rows.slice(0, values.length);

        // 4. 逐行找 X 坐标最接近 colX 的 input 并填值
        const filled = [];
        const nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
        ).set;
        for (let i = 0; i < targetRows.length; i++) {
            let bestInp = null, bestDist = Infinity;
            for (const inp of targetRows[i].inputs) {
                const dist = Math.abs(inp.getBoundingClientRect().x - colX);
                if (dist < bestDist) { bestDist = dist; bestInp = inp; }
            }
            if (!bestInp) {
                filled.push({row: i, error: 'no input in row'});
                continue;
            }
            bestInp.focus();
            nativeSetter.call(bestInp, String(values[i]));
            bestInp.dispatchEvent(new Event('input', {bubbles: true}));
            bestInp.dispatchEvent(new Event('change', {bubbles: true}));
            filled.push({row: i, ok: true});
        }
        return {filled};
    }""", [today, values])

    if "error" in result:
        raise Exception(f"填充失败: {result['error']}")
    for f in result.get("filled", []):
        if "error" in f:
            raise Exception(f"填充第{f['row']+1}行失败: {f}")


# ============================================================
# 主流程
# ============================================================

def fill_report(browser: Browser, config: dict) -> bool:
    page = browser.page

    # 0. 切换中文界面（GitHub Actions 默认英文）
    lang_btn = page.locator("button:has-text('English')")
    if lang_btn.count():
        lang_btn.first.click()
        page.wait_for_timeout(1500)

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
