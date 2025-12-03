from pathlib import Path
import os
import requests
import json
import time
import asyncio
import re  # 新增：用于正则处理
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from jinja2 import Template
import datetime
import base64

# 1. 加载钥匙
load_dotenv()
DIFY_API_KEY = os.getenv("DIFY_API_KEY")
# 注意：这里修正了变量名，确保代码里用的一致
DIFY_API_BASE_URL = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1") 

print("Dify API KEY Loaded:", DIFY_API_KEY[:5] + "...") # 只打印前几位，安全

# --- 2. 新闻输入部分：从文件读取 ---
def load_news_from_file(filepath="news_articles.txt"):
    """从文件中读取新闻列表，通过双换行符 (\n\n) 分割"""
    print(f"📄 正在从文件 {filepath} 中加载新闻内容...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # 使用双换行符分隔，并过滤掉空字符串
            articles = [article.strip() for article in content.split('\n\n') if article.strip()]
            print(f"✅ 成功加载 {len(articles)} 条新闻。")
            return articles
    except FileNotFoundError:
        print(f"❌ 错误：未找到文件 {filepath}。请确保文件已创建。")
        return []

# --- 辅助函数：解析 Dify 返回的 JSON 文本 (新增) ---
def parse_dify_output_to_dict(text_content):
    """清理并解析 Dify 返回的 JSON 字符串"""
    if not text_content:
        return None
    
    try:
        # 1. 移除 Markdown 标记
        clean_text = text_content.replace("```json", "").replace("```", "").strip()
        # 2. 移除零宽空格
        clean_text = clean_text.replace('\u200b', '').replace('\u00ad', '')
        # 3. 截取 JSON
        start = clean_text.find('{')
        end = clean_text.rfind('}')
        if start != -1 and end != -1:
            json_str = clean_text[start : end + 1]
            # 4. 清除换行符 (防止破坏 JSON)
            json_str = json_str.replace('\n', '').replace('\t', '')
            return json.loads(json_str)
    except Exception as e:
        print(f"❌ JSON 解析失败: {e}")
        return None
    return None
# --- 3. Dify 总结函数 (路径修正版) ---
def summarize_news_with_dify(content, max_retries=2):
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
            # 设置 90 秒超时
            response = requests.post(url, headers=headers, json=payload, timeout=90) 
            response.raise_for_status()

            # 获取响应 JSON
            json_response = response.json()
            
            # 🚨 关键修复：正确的提取路径
            # Dify 的返回结构通常是 { "data": { "outputs": { "text": "..." } } }
            # 我们先尝试从 data.outputs 里拿
            outputs = json_response.get('data', {}).get('outputs', {})
            
            # 如果没拿到，再试试直接从 outputs 拿 (兼容不同版本)
            if not outputs:
                outputs = json_response.get('outputs', {})

            # 获取文本内容 (尝试 'text' 或 'final_summary_text')
            processed_text = outputs.get('text', '')
            if not processed_text:
                processed_text = outputs.get('final_summary_text', '')
            
            # 🔍 检查结果
            if not processed_text:
                # 如果还是空的，打印出整个结构看看是啥情况
                print(f"❌ Dify 返回内容为空 (Attempt {attempt})")
                # 只有在调试时才打印下面这行，防止刷屏
                # print(f"DEBUG: Dify 原始返回: {json_response}") 
            else:
                # 尝试解析
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
# --- 5.9版 HTML/CSS 模板 (复刻经典头图 + 完美正文排版 + 1:1 方形) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
        /* --- 全局设置 --- */
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
            ;
        }

        /* --- 1. 头部设计 (1:1 方形 & 左对齐布局) --- */
        .header {
            background: linear-gradient(145deg, #020c1a 0%, #082a6d 100%);
            height: 450px; 
            padding: 35px 30px;
            position: relative;
            overflow: hidden;
            color: white;
            display: flex;
            flex-direction: column;
            /* 核心改动：整体左对齐，内容靠上 */
            justify-content: flex-start;
            align-items: flex-start; 
        }

        /* 封面顶部文字区 (左对齐) */
        .cover-top-info {
            position: relative;
            z-index: 10;
            margin-bottom: 20px;
            text-align: left; 
            /* 给右侧圆圈留出空间 */
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
            /* 下划线左对齐 */
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
        
        /* --- 核心视觉元素 (移回右侧) --- */
        .tech-elements {
            position: absolute;
            /* 核心改动：定位到右侧 */
            top: 0; right: 0; bottom: 0; width: 60%;
            pointer-events: none;
            opacity: 0.9;
            /* 仅在右侧区域显示网格 */
            background: url('data:image/svg+xml;utf8,<svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg"><defs><pattern id="smallGrid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 L 0 10" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="0.5"/></pattern><pattern id="grid" width="100" height="100" patternUnits="userSpaceOnUse"><rect width="100" height="100" fill="url(%23smallGrid)"/><path d="M 100 0 L 0 0 L 0 100" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1"/></pattern></defs><rect width="100%" height="100%" fill="url(%23grid)"/></svg>') top left / 200px 200px repeat;
            /* 加一个左侧的遮罩，让网格自然过渡 */
            -webkit-mask-image: linear-gradient(to right, transparent 0%, black 40%);
            mask-image: linear-gradient(to right, transparent 0%, black 40%);
        }
/* 抽象手 (移回靠近中心的位置) */
        .abstract-hand {
            position: absolute;
            bottom: -80px; 
            right: -40px; /* 往左移回来 */
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
        
        /* 触控圆圈 (移到右手位置) */
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
/* 封面底部的 Slogan (核心改动：居中) */
        .cover-slogan {
            position: absolute; 
            bottom: 30px; 
            left: 0; right: 0; /* 撑满宽度 */
            text-align: center; /* 文字居中 */
            font-size: 12px; color: rgba(255,255,255,0.6);
            letter-spacing: 1.5px; z-index: 10; text-transform: uppercase;
        }
        
        /* --- 2. 内容列表区 (保持完美排版) --- */
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

        /* --- 3. 底部设计 (深蓝底色) --- */
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
                <div class="sub-title">LawGeek 精选 | 11月28日</div>
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
# --- 5. 截图生成函数 (最稳健版本：Base64嵌入 + 标准截图) ---
async def generate_news_card_from_data(news_data_list: list, output_path="daily_news_card.png"):
    if not news_data_list:
        print("没有可用的总结数据，跳过图片生成。")
        return

    print("🚀 开始生成新闻简报图片...")
    
    # 1. 读取图片转 Base64
    qr_code_base64 = ""
    try:
        with open("qrcode.png", "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            qr_code_base64 = f"data:image/png;base64,{encoded_string}"
    except FileNotFoundError:
        print("❌ 错误：未找到 qrcode.png")
        qr_code_base64 = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

    template = Template(HTML_TEMPLATE)
    today_str = datetime.datetime.now().strftime("%m/%d")
    
    rendered_html = template.render(
        news_items=news_data_list, 
        date_str=today_str,
        qr_code_path=qr_code_base64
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(device_scale_factor=2) # 高清渲染
        
        await page.set_content(rendered_html)
        
        # 🚨 核心改回：使用标准截图，加上 omit_background 即可完美去白边
        await page.locator(".container").screenshot(path=output_path, omit_background=True)
        
        await browser.close()
    
    print(f"🎉 图片已生成并保存到: {output_path}")
    
# --- 6. 主程序 (含自动清洗 + 人工编辑功能) ---
async def main():
    # 1. 加载新闻
    MOCK_NEWS_INPUT = load_news_from_file() 
    
    if not MOCK_NEWS_INPUT:
        print("停止处理：没有新闻内容可供总结。")
        return 
    
    final_data = []
    print("🚀 开始调用 AI 进行总结...") 
    
    # 2. 循环处理每一条新闻
    for content in MOCK_NEWS_INPUT:
        result = summarize_news_with_dify(content) 
        if result:
            # --- 自动清洗功能：去除 AI 喜欢乱加的符号 ---
            # 清洗标题
            if 'main_title' in result:
                result['main_title'] = result['main_title'].replace('**', '').replace('##', '').strip()
            
            # 清洗摘要
            if 'abstract_summary' in result:
                result['abstract_summary'] = result['abstract_summary'].replace('**', '').replace('##', '').strip()
            
            # 清洗要点
            if 'bullet_points' in result and isinstance(result['bullet_points'], list):
                # 遍历每个要点，去掉星号、减号等
                clean_points = []
                for point in result['bullet_points']:
                    # 去掉开头的 * 或 - 或 数字. 
                    clean_p = re.sub(r'^[\*\-\d\.]+\s*', '', point) 
                    # 去掉中间的粗体符号
                    clean_p = clean_p.replace('**', '').strip()
                    clean_points.append(clean_p)
                result['bullet_points'] = clean_points
            # -------------------------------------------

            final_data.append(result)
            print(f"✅ 已获取并清洗: {result.get('main_title')}")
        
        # time.sleep(1) 

    if not final_data:
        print("⚠️ 警告：所有新闻总结失败，未生成图片。")
        return

    # ==========================================
    # 🛑 人工介入环节 (Human-in-the-Loop)
    # ==========================================
    
    # 1. 把 AI 总结好的内容，存到一个临时文件里
    review_filename = "news_edit_review.json"
    with open(review_filename, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    
    print("\n" + "="*50)
    print(f"✋ 程序已暂停！中间结果已保存到文件: {review_filename}")
    print("👉 请在 VS Code 左侧打开 'news_edit_review.json' 文件。")
    print("👉 你可以手动修改里面的文字、删除怪符号、调整顺序。")
    print("👉 修改完记得按 Ctrl+S (Command+S) 保存文件！")
    print("="*50)
    
    # 2. 等待你按回车
    input("⌨️  修改完成并保存后，请在这里按 [回车键] 继续生成图片...")

    # 3. 重新读取你修改后的文件
    print("🔄 正在读取你修改后的内容...")
    try:
        with open(review_filename, "r", encoding="utf-8") as f:
            final_data = json.load(f)
        print("✅ 读取成功！开始制作卡片...")
    except Exception as e:
        print(f"❌ 读取文件出错，可能是 JSON 格式改错了: {e}")
        return
    # ==========================================

    # 3. 生成图片
    await generate_news_card_from_data(final_data)


if __name__ == "__main__":
    asyncio.run(main())