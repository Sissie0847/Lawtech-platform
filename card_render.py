"""
卡片渲染模块 - 从模板 + JSON 数据生成 PNG
支持快速迭代：美术修改 HTML 模板，开发填充数据生成图片

用法:
    python card_render.py                           # 默认模板 + 默认数据
    python card_render.py --template xxx.html       # 指定模板
    python card_render.py -t card_template_v2.html
    python card_render.py --data xxx.json           # 指定数据
    python card_render.py --output xxx.png          # 指定输出
    python card_render.py --date 12月17日           # 指定日期
"""

import asyncio
import json
import re
import base64
import datetime
import argparse
from pathlib import Path
from playwright.async_api import async_playwright
from jinja2 import Environment


def load_json_data(json_file="news_edit_review.json"):
    """读取 JSON 数据"""
    print(f"[数据] 读取数据: {json_file}")
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"   [OK] 共 {len(data)} 条新闻")
    return data


def load_html_template(html_file):
    """读取 HTML 模板"""
    print(f"[模板] 读取模板: {html_file}")
    with open(html_file, "r", encoding="utf-8") as f:
        return f.read()


def regex_replace_filter(value, pattern, replacement):
    """Jinja2 正则替换过滤器"""
    return re.sub(pattern, replacement, str(value))


def load_image_base64(paths, name="图片"):
    """读取图片转 Base64"""
    for img_path in paths:
        try:
            with open(img_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
                print(f"   [OK] 已加载{name}: {img_path}")
                return f"data:image/png;base64,{encoded}"
        except FileNotFoundError:
            continue
    print(f"   [警告] 未找到{name}，使用占位图")
    return "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"


def get_qr_code_base64():
    """读取二维码转 Base64"""
    return load_image_base64(["qrcode.png", "card_assets/qrcode.png"], "二维码")


def get_scale_icon_base64():
    """读取天平图标转 Base64"""
    return load_image_base64(["scale_icon.png", "card_assets/scale_icon.png"], "天平图标")


def get_calendar_icon_base64():
    """读取日历图标转 Base64"""
    return load_image_base64(["calendar_icon.png", "card_assets/calendar_icon.png"], "日历图标")


def render_template(template_content, news_items, date_str=None, weekday_str=None):
    """使用 Jinja2 渲染模板"""
    # 设置 Jinja2 环境
    env = Environment()
    env.filters['regex_replace'] = regex_replace_filter
    template = env.from_string(template_content)
    
    # 准备日期
    now = datetime.datetime.now()
    if not date_str:
        date_str = now.strftime("%m月%d日")
    if not weekday_str:
        weekday_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday_str = weekday_map[now.weekday()]
    
    # 渲染
    rendered = template.render(
        news_items=news_items,
        date_str=date_str,
        weekday_str=weekday_str,
        qr_code_path=get_qr_code_base64(),
        scale_icon=get_scale_icon_base64(),
        calendar_icon=get_calendar_icon_base64()
    )
    
    return rendered


async def generate_png(html_content, output_path="daily_news_card.png", padding_top=50, padding_bottom=80):
    """用 Playwright 截图生成 PNG
    
    Args:
        html_content: 渲染后的 HTML 内容
        output_path: 输出图片路径
        padding_top: 顶部额外边距 (像素)
        padding_bottom: 底部额外边距 (像素)
    """
    print(f"[图片] 生成图片: {output_path}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(device_scale_factor=2)
        await page.set_content(html_content, wait_until="domcontentloaded")
        
        # 添加额外的上下边距
        await page.evaluate(f"""
            const container = document.querySelector('.container');
            container.style.paddingTop = '{padding_top}px';
            container.style.paddingBottom = '{padding_bottom}px';
        """)
        
        await page.locator(".container").screenshot(path=output_path, omit_background=True)
        await browser.close()
    
    print(f"[完成] 已保存到: {output_path}")
    return output_path


async def render_card(
    template_file="card_template_v2.html",
    json_file="news_edit_review.json", 
    output_file="daily_news_card.png",
    date_str=None,
    weekday_str=None,
    padding_top=50,
    padding_bottom=80
):
    """主渲染函数"""
    print("\n" + "="*50)
    print("开始渲染卡片")
    print("="*50)
    
    # 1. 读取数据
    news_items = load_json_data(json_file)
    
    # 2. 读取模板
    template_content = load_html_template(template_file)
    
    # 3. 渲染 HTML
    rendered_html = render_template(template_content, news_items, date_str, weekday_str)
    
    # 4. 生成 PNG
    result = await generate_png(rendered_html, output_file, padding_top, padding_bottom)
    
    print("="*50 + "\n")
    return result


def run(template="card_template_v2.html", data="news_edit_review.json", output="daily_news_card.png", date=None, weekday=None, padding_top=50, padding_bottom=80):
    """同步入口"""
    return asyncio.run(render_card(template, data, output, date, weekday, padding_top, padding_bottom))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='从模板 + JSON 数据生成卡片 PNG')
    parser.add_argument(
        '-t', '--template',
        type=str,
        default="card_template_v2.html",
        help='HTML 模板文件路径 (默认: card_template_v2.html)'
    )
    parser.add_argument(
        '-d', '--data',
        type=str,
        default="news_edit_review.json",
        help='JSON 数据文件路径 (默认: news_edit_review.json)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default="daily_news_card.png",
        help='输出 PNG 文件路径 (默认: daily_news_card.png)'
    )
    parser.add_argument(
        '--date',
        type=str,
        help='自定义日期显示 (例如: 12月17日)'
    )
    parser.add_argument(
        '--weekday',
        type=str,
        help='自定义星期显示 (例如: 星期二)'
    )
    parser.add_argument(
        '--padding-top',
        type=int,
        default=50,
        help='顶部边距像素 (默认: 50)'
    )
    parser.add_argument(
        '--padding-bottom',
        type=int,
        default=80,
        help='底部边距像素 (默认: 80)'
    )
    
    args = parser.parse_args()
    
    run(
        template=args.template,
        data=args.data,
        output=args.output,
        date=args.date,
        weekday=args.weekday,
        padding_top=args.padding_top,
        padding_bottom=args.padding_bottom
    )

