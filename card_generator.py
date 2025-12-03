"""
卡片图片生成模块
基于 Dify AI 总结 + Playwright 截图生成新闻卡片
"""

from pathlib import Path
import os
import requests
import json
import time
import asyncio
import re
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from jinja2 import Template
import datetime
import base64

# 加载环境变量
load_dotenv()
DIFY_API_KEY = os.getenv("DIFY_API_KEY")
DIFY_API_BASE_URL = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1")


def load_news_from_file(filepath="news_articles.txt"):
    """从文件中读取新闻列表，通过双换行符分割"""
    print(f"📄 正在从文件 {filepath} 中加载新闻内容...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            articles = [article.strip() for article in content.split('\n\n') if article.strip()]
            print(f"✅ 成功加载 {len(articles)} 条新闻。")
            return articles
    except FileNotFoundError:
        print(f"❌ 错误：未找到文件 {filepath}。")
        return []


def parse_dify_output_to_dict(text_content):
    """清理并解析 Dify 返回的 JSON 字符串"""
    if not text_content:
        return None
    
    try:
        clean_text = text_content.replace("```json", "").replace("```", "").strip()
        clean_text = clean_text.replace('\u200b', '').replace('\u00ad', '')
        start = clean_text.find('{')
        end = clean_text.rfind('}')
        if start != -1 and end != -1:
            json_str = clean_text[start : end + 1]
            json_str = json_str.replace('\n', '').replace('\t', '')
            return json.loads(json_str)
    except Exception as e:
        print(f"❌ JSON 解析失败: {e}")
        return None
    return None


def summarize_news_with_dify(content, max_retries=2):
    """调用 Dify API 进行新闻总结"""
    url = f"{DIFY_API_BASE_URL}/workflows/run"
    
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": {
            "news_text": content 
        },
        "response_mode": "blocking",
        "user": "LawGeekUser"
    }

    for attempt in range(1, max_retries + 1):
        print(f"⏳ 正在请求 AI 总结新闻 (尝试 {attempt}/{max_retries})...")
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            response.raise_for_status()

            json_response = response.json()
            outputs = json_response.get('data', {}).get('outputs', {})
            
            if not outputs:
                outputs = json_response.get('outputs', {})

            processed_text = outputs.get('text', '')
            if not processed_text:
                processed_text = outputs.get('final_summary_text', '')
            
            if not processed_text:
                print(f"❌ Dify 返回内容为空 (Attempt {attempt})")
            else:
                result = parse_dify_output_to_dict(processed_text)
                if result:
                    return result
                else:
                    print(f"⚠️ 解析失败，AI 原始返回内容如下:\n{processed_text[:200]}...")

        except requests.exceptions.Timeout:
            print(f"❌ 错误：请求超时。")
        except Exception as e:
            print(f"❌ 发生错误: {e}")

        if attempt < max_retries:
            print("🔄 准备重试...")
            time.sleep(2)

    print("❌ 所有重试均失败，跳过此条新闻。")
    return None


# HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
        body {
            margin: 0; padding: 0; background-color: #f0f2f5;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
            color: #333; -webkit-font-smoothing: antialiased;
            word-spacing: 1px;
        }
        .container {
            width: 450px; margin: 0 auto; background: white;
            padding: 0;
            overflow: hidden;
        }

        .header {
            background: linear-gradient(145deg, #020c1a 0%, #082a6d 100%);
            height: 450px; 
            padding: 35px 30px;
            position: relative;
            overflow: hidden;
            color: white;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            align-items: flex-start; 
        }

        .cover-top-info {
            position: relative;
            z-index: 10;
            margin-bottom: 20px;
            text-align: left; 
            max-width: 65%; 
        }

        .main-title {
            font-size: 48px;
            font-weight: 800;
            line-height: 1;
            font-family: "Georgia", serif;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            text-shadow: 0 5px 15px rgba(0,0,0,0.4);
        }

        .main-title span {
            display: block;
            width: 60px;
            height: 4px;
            background: rgba(255,255,255,0.8);
            margin: 15px 0; 
            border-radius: 2px;
        }

        .sub-title {
            font-size: 13px;
            font-weight: 500;
            color: rgba(255,255,255,0.8);
            letter-spacing: 2px;
            font-family: "Arial", sans-serif;
            text-transform: uppercase;
            margin-left: 0; 
        }
        
        .tech-elements {
            position: absolute;
            top: 0; right: 0; bottom: 0; width: 60%;
            pointer-events: none;
            opacity: 0.9;
            background: url('data:image/svg+xml;utf8,<svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg"><defs><pattern id="smallGrid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 L 0 10" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="0.5"/></pattern><pattern id="grid" width="100" height="100" patternUnits="userSpaceOnUse"><rect width="100" height="100" fill="url(%23smallGrid)"/><path d="M 100 0 L 0 0 L 0 100" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1"/></pattern></defs><rect width="100%" height="100%" fill="url(%23grid)"/></svg>') top left / 200px 200px repeat;
            -webkit-mask-image: linear-gradient(to right, transparent 0%, black 40%);
            mask-image: linear-gradient(to right, transparent 0%, black 40%);
        }

        .abstract-hand {
            position: absolute;
            bottom: -80px; 
            right: -40px;
            width: 350px; height: 350px;
            background: radial-gradient(circle at 55% 65%, rgba(135,206,250,0.1) 0%, transparent 80%);
            border-radius: 50%; transform: rotate(-10deg);
            opacity: 0.8; box-shadow: 0 0 100px rgba(43,126,255,0.2);
        }
        .abstract-hand::before {
            content: ''; position: absolute; top: 50%; left: 50%; width: 180px; height: 180px;
            background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="M50 0 L100 25 L75 100 L25 100 L0 25 Z" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.15)" stroke-width="1"/></svg>') center center / contain no-repeat;
            opacity: 0.7; transform: translate(-50%, -50%) rotate(25deg);
        }
        
        .touch-circle {
            position: absolute; 
            left: 0%; top: 18%; 
            transform: translate(0, -50%);
            width: 140px; height: 140px; border-radius: 50%;
            border: 2px solid rgba(135,206,250,0.5);
            box-shadow: 0 0 30px rgba(135,206,250,0.6), inset 0 0 15px rgba(135,206,250,0.3);
            animation: pulse-glow 2.5s infinite alternate; z-index: 5;
        }
        @keyframes pulse-glow {
            0% { transform: translate(0, -50%) scale(1); opacity: 1; }
            100% { transform: translate(0, -50%) scale(1.05); opacity: 0.9; }
        }

        .cover-slogan {
            position: absolute; 
            bottom: 30px; 
            left: 0; right: 0;
            text-align: center;
            font-size: 12px; color: rgba(255,255,255,0.6);
            letter-spacing: 1.5px; z-index: 10; text-transform: uppercase;
        }
        
        .content-area { 
            padding: 25px 35px 40px 35px; 
            background: white; 
        }
        .news-section { margin-bottom: 35px; }
        .news-section:last-child { margin-bottom: 0; }

        .news-title { 
            font-size: 18px; font-weight: 700; color: #1a1a1a; 
            line-height: 1.4; margin-bottom: 12px; 
            border-left: 4px solid #082a6d; padding-left: 12px; 
        }
        
        .news-summary { 
            font-size: 14px; color: #555; 
            line-height: 1.9; text-align: justify; margin-bottom: 12px;
            word-spacing: 1.5px; padding-left: 16px; 
        }

        .bullet-points { list-style: none; padding: 0; margin: 0; }
        
        .bullet-points li { 
            font-size: 13px; color: #444; margin-bottom: 8px; 
            line-height: 1.7; position: relative; padding-left: 16px;
            text-align: justify; 
        }
        
        .bullet-points li::before { 
            content: ''; position: absolute; left: 0; top: 9px; 
            width: 4px; height: 4px; background-color: #082a6d; 
        }

        .footer {
            background: linear-gradient(145deg, #020c1a 0%, #082a6d 100%);
            padding: 45px 35px; text-align: center; color: white; position: relative;
        }
        .footer-logo { font-size: 18px; font-weight: 800; letter-spacing: 2px; margin-bottom: 8px; display: block; color: white; font-family: "Georgia", serif; }
        .footer-info { font-size: 12px; color: rgba(255,255,255,0.6); margin-bottom: 25px; letter-spacing: 1px; }
        .qr-box { width: 110px; height: 110px; margin: 0 auto 15px auto; padding: 8px; background: white; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
        .qr-img { width: 100%; height: 100%; display: block; border-radius: 4px; }
        .qr-text { font-size: 12px; color: rgba(255,255,255,0.8); letter-spacing: 1px; font-weight: 500; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="cover-top-info">
                <div class="main-title">DAILY NEWS<span></span></div>
                <div class="sub-title">LawGeek 精选 | {{ date_str }}</div>
            </div>
            
            <div class="tech-elements">
                <div class="abstract-hand"></div>
                <div class="touch-circle"></div>
            </div>

            <div class="cover-slogan">每日法律科技动态 · 深度洞察与趋势解读</div>
        </div>
        
        <div class="content-area">
            {% for news in news_items %}
            <div class="news-section">
                <div class="news-title">{{ news.main_title }}</div>
                <div class="news-summary">{{ news.abstract_summary }}</div>
                {% if news.bullet_points %}
                <ul class="bullet-points">
                    {% for point in news.bullet_points %}
                    <li>{{ point }}</li>
                    {% endfor %}
                </ul>
                {% endif %}
            </div>
            {% endfor %}
        </div>

        <div class="footer">
            <span class="footer-logo">LAWGEEK | 法律极客</span>
            <div class="footer-info">Memene · 阅读即成长</div>
            
            <div class="qr-box">
                <img src="{{ qr_code_path }}" class="qr-img" alt="社群二维码">
            </div>
            <div class="qr-text">长按扫码 · 订阅接收每日推送</div>
        </div>
    </div>
</body>
</html>
"""


async def generate_news_card_from_data(news_data_list: list, output_path="daily_news_card.png", date_str=None):
    """从总结数据生成新闻卡片图片"""
    if not news_data_list:
        print("没有可用的总结数据，跳过图片生成。")
        return None

    print("🚀 开始生成新闻简报图片...")
    
    # 读取二维码图片转 Base64
    qr_code_base64 = ""
    qr_paths = ["qrcode.png", "card_assets/qrcode.png"]
    
    for qr_path in qr_paths:
        try:
            with open(qr_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                qr_code_base64 = f"data:image/png;base64,{encoded_string}"
                break
        except FileNotFoundError:
            continue
    
    if not qr_code_base64:
        print("⚠️ 未找到 qrcode.png，使用占位图片")
        qr_code_base64 = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

    template = Template(HTML_TEMPLATE)
    if not date_str:
        date_str = datetime.datetime.now().strftime("%m月%d日")
    
    rendered_html = template.render(
        news_items=news_data_list, 
        date_str=date_str,
        qr_code_path=qr_code_base64
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(device_scale_factor=2)
        
        await page.set_content(rendered_html)
        await page.locator(".container").screenshot(path=output_path, omit_background=True)
        
        await browser.close()
    
    print(f"🎉 图片已生成并保存到: {output_path}")
    return output_path


def clean_ai_result(result):
    """清洗 AI 返回结果，去除多余符号"""
    if 'main_title' in result:
        result['main_title'] = result['main_title'].replace('**', '').replace('##', '').strip()
    
    if 'abstract_summary' in result:
        result['abstract_summary'] = result['abstract_summary'].replace('**', '').replace('##', '').strip()
    
    if 'bullet_points' in result and isinstance(result['bullet_points'], list):
        clean_points = []
        for point in result['bullet_points']:
            clean_p = re.sub(r'^[\*\-\d\.]+\s*', '', point)
            clean_p = clean_p.replace('**', '').strip()
            clean_points.append(clean_p)
        result['bullet_points'] = clean_points
    
    return result


async def generate_card_from_file(input_file="news_articles.txt", output_file="daily_news_card.png", skip_review=False):
    """从文本文件生成卡片图片（完整流程，含人工确认环节）"""
    
    # 检查 Dify API Key
    if not DIFY_API_KEY:
        print("❌ 错误：未配置 DIFY_API_KEY，请在 .env 文件中设置")
        return None
    
    # 1. 加载新闻
    news_list = load_news_from_file(input_file)
    
    if not news_list:
        print("停止处理：没有新闻内容可供总结。")
        return None
    
    final_data = []
    print("🚀 开始调用 AI 进行总结...")
    
    # 2. 循环处理每一条新闻
    for content in news_list:
        result = summarize_news_with_dify(content)
        if result:
            result = clean_ai_result(result)
            final_data.append(result)
            print(f"✅ 已获取并清洗: {result.get('main_title')}")

    if not final_data:
        print("⚠️ 警告：所有新闻总结失败，未生成图片。")
        return None

    # ==========================================
    # 🛑 人工介入环节 (Human-in-the-Loop)
    # ==========================================
    review_filename = "news_edit_review.json"
    
    # 保存中间结果供人工编辑
    with open(review_filename, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    
    if not skip_review:
        print("\n" + "=" * 50)
        print(f"✋ 程序已暂停！中间结果已保存到: {review_filename}")
        print("👉 请打开 'news_edit_review.json' 文件进行编辑")
        print("👉 你可以修改标题、摘要、要点，删除不需要的内容")
        print("👉 修改完记得按 Ctrl+S 保存文件！")
        print("=" * 50)
        
        # 等待用户按回车
        input("⌨️  修改完成并保存后，请按 [回车键] 继续生成图片...")
        
        # 重新读取修改后的文件
        print("🔄 正在读取你修改后的内容...")
        try:
            with open(review_filename, "r", encoding="utf-8") as f:
                final_data = json.load(f)
            print("✅ 读取成功！开始制作卡片...")
        except Exception as e:
            print(f"❌ 读取文件出错，可能是 JSON 格式有误: {e}")
            return None
    else:
        print(f"📝 中间结果已保存到: {review_filename}")
    # ==========================================

    # 3. 生成图片
    return await generate_news_card_from_data(final_data, output_file)


async def generate_card_from_review(review_file="news_edit_review.json", output_file="daily_news_card.png", date_str=None):
    """从已编辑的 review JSON 文件直接生成卡片（跳过 AI 总结）"""
    
    print(f"🔄 正在读取 {review_file}...")
    try:
        with open(review_file, "r", encoding="utf-8") as f:
            final_data = json.load(f)
        print(f"✅ 读取成功，共 {len(final_data)} 条内容")
    except FileNotFoundError:
        print(f"❌ 错误：未找到文件 {review_file}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON 格式错误: {e}")
        return None
    
    if not final_data:
        print("⚠️ 文件内容为空")
        return None
    
    return await generate_news_card_from_data(final_data, output_file, date_str)


def run_card_generation(input_file="news_articles.txt", output_file="daily_news_card.png", skip_review=False):
    """同步接口：生成卡片图片（完整流程，含人工确认）"""
    return asyncio.run(generate_card_from_file(input_file, output_file, skip_review))


def run_from_review(review_file="news_edit_review.json", output_file="daily_news_card.png", date_str=None):
    """同步接口：从已编辑的 JSON 直接生成卡片"""
    return asyncio.run(generate_card_from_review(review_file, output_file, date_str))


if __name__ == "__main__":
    import sys
    
    # 支持命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--from-review":
        # 从已编辑的 JSON 生成：python card_generator.py --from-review
        print("📄 从 news_edit_review.json 生成卡片...")
        run_from_review()
    elif len(sys.argv) > 1 and sys.argv[1] == "--skip-review":
        # 跳过人工确认：python card_generator.py --skip-review
        print("⚡ 跳过人工确认，直接生成...")
        run_card_generation(skip_review=True)
    else:
        # 默认完整流程（含人工确认）
        run_card_generation()

