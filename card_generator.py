"""
卡片图片生成模块
基于 百炼 Qwen AI 总结 + Playwright 截图生成新闻卡片
"""

from pathlib import Path
import os
import json
import time
import asyncio
import re
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from jinja2 import Template
import datetime
import base64
from openai import OpenAI

# 加载环境变量
load_dotenv()
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

# 百炼 API 客户端（OpenAI 兼容模式）
qwen_client = None
if DASHSCOPE_API_KEY:
    qwen_client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )


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


def parse_json_output(text_content):
    """清理并解析 AI 返回的 JSON 字符串"""
    if not text_content:
        return None
    
    try:
        clean_text = text_content.replace("```json", "").replace("```", "").strip()
        clean_text = clean_text.replace('\u200b', '').replace('\u00ad', '')
        start = clean_text.find('{')
        end = clean_text.rfind('}')
        if start != -1 and end != -1:
            json_str = clean_text[start : end + 1]
            return json.loads(json_str)
        return json.loads(clean_text)
    except Exception as e:
        print(f"❌ JSON 解析失败: {e}")
        return None


def summarize_news_with_qwen(content, max_retries=2):
    """调用百炼 Qwen API 进行新闻总结（头条版，支持关键数据提取）"""
    
    if not qwen_client:
        print("❌ 错误：百炼 API 客户端未初始化")
        return None
    
    # 头条版提示词：内容总结 + 关键数据提取 + JSON 格式化
    prompt = f"""你是一位资深的法律科技资讯主编。你的任务是根据新闻内容，生成结构清晰的总结，并以 JSON 格式输出。

【新闻原文】
{content}

【核心决策逻辑：智能混合模式】
请根据新闻的**信息密度**和**信息独立性**来决定结构：

1. **情况 A：必须分点（高密度信息）**
   - 判定标准：新闻包含 2 个以上独立的数字、步骤、功能特性、理由或争议点
   - 融资新闻特例：如果包含"投资方"、"金额"、"用途"等多个细节，建议分点展示
   - 执行：总结段落写 30-50 字的简短引入，要点列表列出 1-3 个具体要点

2. **情况 B：保持叙事（低密度/单一事件）**
   - 判定标准：新闻只是讲述一件事，没有复杂的细节
   - 执行：总结段落写 60-90 字的完整段落，要点列表为空数组

【GO DEEPER - 关键数据提取】
如果新闻包含具体数据（金额、增长率、数量、时间节点等），请提取 1-3 个最核心的数据点填入 key_data。
如果没有具体数据，key_data 返回空数组 []。

【内容写作规范】
1. 标题：保留原标题（包含序号）
2. 要点列表：若启用，单点字数控制在 30-50 字

【输出格式】
必须且只能返回标准的 JSON 格式，不带任何 Markdown 标记：
{{
  "main_title": "[原标题序号和标题]",
  "abstract_summary": "[总结段落]",
  "key_data": [
    {{"label": "数据类别", "value": "数值", "unit": "单位"}}
  ],
  "bullet_points": ["要点一", "要点二"] 或 []
}}

【格式化规则】
1. 在字段值内部，严禁出现英文双引号 "，请使用中文引号 " " 或英文单引号 '
2. 如果不需要要点，bullet_points 必须返回空数组 []
3. 如果没有关键数据，key_data 必须返回空数组 []
4. key_data 中：label 是数据类别（如"融资金额"），value 是数值（如"500+"），unit 是单位（如"万美元"，无单位则为空字符串）
5. 严格只输出 JSON 字符串，前后严禁添加任何描述性文字"""

    for attempt in range(1, max_retries + 1):
        print(f"⏳ 正在请求百炼 AI 总结新闻 (尝试 {attempt}/{max_retries})...")
        try:
            response = qwen_client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            
            if not result_text:
                print(f"❌ 百炼返回内容为空 (Attempt {attempt})")
            else:
                result = parse_json_output(result_text)
                if result:
                    return result
                else:
                    print(f"⚠️ 解析失败，AI 原始返回内容如下:\n{result_text[:300]}...")

        except Exception as e:
            print(f"❌ 发生错误: {e}")

        if attempt < max_retries:
            print("🔄 准备重试...")
            time.sleep(1)

    print("❌ 所有重试均失败，跳过此条新闻。")
    return None


# 2-5 条新闻的提示词（极简风格）
CARD_NEWS_PROMPT = """# Role
你是一位深谙"极简主义"美学的 LegalTech 科技媒体主编。你的特长是将枯燥的法律科技新闻，改写为"高信噪比"的社交媒体短讯。

# Task
请阅读【新闻原文】，按照"小互日报"的风格，将其重写为一条**严格限制格式**的短讯。

# Style DNA (风格基因)
1. **Title (标题)**：采用"主体 + 动作：价值定性"的结构。标题必须包含一个吸引人的"钩子"或"行业判断"。
2. **Structure (结构)**：仅保留 **2 个** 核心要点。
   * Point 1: **硬事实 (Hard Fact)** —— 到底发布了什么？融了多少钱？判了什么？
   * Point 2: **软价值 (Soft Insight)** —— 对行业意味着什么？解决了什么痛点？用户体验如何？
3. **Tone (语调)**：客观、专业、但带有科技感的"冷峻"或"兴奋"。

# 新闻原文
{content}

# 输出格式
严格输出 JSON 格式，不带任何 Markdown 标记：
{{
  "main_title": "[标题核心]：[价值定性]",
  "bullet_points": [
    "[要点1：最核心的事实/功能/数据]",
    "[要点2：行业影响/应用场景/趋势判断]"
  ]
}}

# 格式规则
1. 严禁使用英文双引号 "，请用中文引号 " " 或单引号 '
2. bullet_points 必须且只有 2 个要点
3. 严格只输出 JSON 字符串"""


def summarize_card_news_with_qwen(content, max_retries=2):
    """调用百炼 Qwen API 进行新闻总结（极简卡片版，用于 2-5 条新闻）"""
    
    if not qwen_client:
        print("❌ 错误：百炼 API 客户端未初始化")
        return None
    
    prompt = CARD_NEWS_PROMPT.format(content=content)

    for attempt in range(1, max_retries + 1):
        print(f"⏳ 正在请求百炼 AI 总结新闻 [卡片版] (尝试 {attempt}/{max_retries})...")
        try:
            response = qwen_client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content
            
            if result_text:
                result = parse_json_output(result_text)
                if result:
                    return result
                else:
                    print(f"⚠️ 解析失败，AI 原始返回:\n{result_text[:300]}...")
            else:
                print(f"❌ 百炼返回内容为空 (Attempt {attempt})")

        except Exception as e:
            print(f"❌ 发生错误: {e}")

        if attempt < max_retries:
            print("🔄 准备重试...")
            time.sleep(1)

    print("❌ 所有重试均失败，跳过此条新闻。")
    return None


# HTML 模板 - 新拟态风格
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --bg-color: #E6E9EF;
            --text-primary: #333333;
            --text-secondary: #7D8592;
            --shadow-light: #FFFFFF;
            --shadow-dark: #D1D9E6;
            --theme-blue: #489CC1;
            --theme-red: #FF7272;
            --theme-green: #21A87D;
            --theme-purple: #6C63FF;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
            line-height: 1.8;
            -webkit-font-smoothing: antialiased;
            padding: 30px;
        }

        .container { max-width: 600px; margin: 0 auto; padding: 0 15px; }

        /* Hero Banner */
        .hero-banner {
            display: flex; flex-direction: column; text-align: center;
            align-items: center; gap: 20px;
            background: var(--bg-color); border-radius: 30px;
            padding: 30px 20px; margin-bottom: 30px;
            position: relative; overflow: hidden;
            box-shadow: 15px 15px 30px var(--shadow-dark), -15px -15px 30px var(--shadow-light);
        }
        .banner-content { z-index: 1; }
        .banner-subtitle {
            font-size: 0.9rem; color: var(--theme-blue); font-weight: 700;
            letter-spacing: 2px; text-transform: uppercase; margin-bottom: 5px;
        }
        .banner-title {
            font-size: 2.8rem; font-weight: 900; color: var(--text-primary);
            line-height: 1.1; margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        .banner-meta {
            display: inline-flex; align-items: center; justify-content: center;
            gap: 10px; color: var(--text-secondary); font-weight: 500; font-size: 0.9rem;
        }
        .banner-visual {
            position: relative; flex-shrink: 0; width: 80px; height: 80px;
            border-radius: 50%; background: var(--bg-color);
            display: flex; align-items: center; justify-content: center;
            box-shadow: inset 6px 6px 12px var(--shadow-dark), inset -6px -6px 12px var(--shadow-light);
        }
        .visual-icon { font-size: 2rem; filter: grayscale(100%) opacity(0.5); }
        .banner-glow {
            position: absolute; top: -50px; right: -50px; width: 200px; height: 200px;
            background: radial-gradient(circle, rgba(72,156,193,0.15) 0%, rgba(230,233,239,0) 70%);
            z-index: 0; pointer-events: none;
        }

        /* 插画区域 */
        .feature-illustration {
            width: 100%; height: 200px; margin-bottom: 40px;
            display: flex; align-items: center; justify-content: center;
        }
        .feature-illustration svg {
            width: 100%; height: 100%;
            filter: drop-shadow(8px 8px 16px var(--shadow-dark)) drop-shadow(-8px -8px 16px var(--shadow-light));
        }

        /* 头条区域 */
        .lead-story {
            margin-bottom: 50px; padding: 10px 15px 10px 20px; position: relative;
        }
        .lead-story::before {
            content: ''; position: absolute; left: 5px; top: 15px; bottom: 15px;
            width: 3px; border-radius: 2px; background: var(--theme-blue);
        }
        .lead-header {
            display: flex; flex-wrap: wrap; align-items: baseline;
            gap: 10px; margin-bottom: 15px;
        }
        .lead-number {
            font-size: 3rem; font-weight: 900; color: var(--theme-blue); line-height: 1;
            text-shadow: 2px 2px 5px rgba(255,255,255,0.8), -2px -2px 5px rgba(0,0,0,0.1);
        }
        .lead-title {
            font-size: 1.5rem; font-weight: 800; line-height: 1.4;
            color: var(--text-primary); flex: 1; min-width: 200px;
        }
        .lead-desc {
            font-size: 1rem; color: var(--text-secondary);
            margin-bottom: 25px; text-align: justify;
        }
        .lead-bullets { list-style: none; padding: 0; margin: 0; }
        .lead-bullets li {
            position: relative; 
            padding-left: 18px; 
            margin-bottom: 10px;
            color: var(--text-primary); 
            font-size: 0.95rem;
            line-height: 1.6;
            text-indent: -18px;
            margin-left: 18px;
        }
        .lead-bullets li::before {
            content: ''; 
            display: inline-block;
            width: 6px; height: 6px; 
            border-radius: 50%;
            background: var(--theme-blue);
            margin-right: 12px;
            vertical-align: middle;
        }

        /* 关键数据组件 */
        .key-data-container {
            display: flex;
            justify-content: flex-start;
            gap: 12px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        .key-data-card {
            background: rgba(255, 255, 255, 0.5);
            border-radius: 10px;
            padding: 12px 16px;
            min-width: 80px;
            text-align: center;
        }
        .key-data-label {
            display: block;
            font-size: 0.65rem;
            color: var(--text-secondary);
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        .key-data-value {
            display: block;
            font-size: 1.4rem;
            font-weight: 800;
            color: var(--theme-blue);
            line-height: 1.2;
        }
        .key-data-unit {
            font-size: 0.7rem;
            font-weight: 500;
            color: var(--text-secondary);
            margin-left: 1px;
        }

        .section-divider {
            height: 2px; background: var(--bg-color); margin: 0 auto 50px; width: 80%;
            border-radius: 2px;
            box-shadow: inset 1px 1px 2px var(--shadow-dark), inset -1px -1px 2px var(--shadow-light);
        }

        /* 普通新闻卡片 */
        .news-grid { display: grid; gap: 40px; padding: 0 10px; }
        .news-card {
            background: var(--bg-color); border-radius: 25px; padding: 35px;
            box-shadow: 15px 15px 30px var(--shadow-dark), -15px -15px 30px var(--shadow-light);
            position: relative; overflow: hidden;
        }
        .news-card::after {
            content: ''; position: absolute; top: 0; left: 0;
            width: 100%; height: 4px; background: var(--card-accent); opacity: 0.7;
        }
        .card-header {
            display: flex; align-items: center; gap: 15px; margin-bottom: 15px;
        }
        .card-number {
            flex-shrink: 0; width: 40px; height: 40px; border-radius: 10px;
            background: var(--bg-color); color: var(--card-accent);
            font-weight: 900; font-size: 1.1rem;
            display: flex; align-items: center; justify-content: center;
            box-shadow: inset 3px 3px 6px rgba(0,0,0,0.1), inset -3px -3px 6px var(--shadow-light);
        }
        .card-title {
            font-size: 1.15rem; font-weight: 700; color: var(--text-primary);
            line-height: 1.4; margin: 0;
        }
        .card-desc {
            color: #444444; font-size: 0.9rem; margin-bottom: 20px;
            text-align: justify; font-weight: 500;
        }
        .card-bullets {
            list-style: none; padding: 18px 20px; border-radius: 12px;
            background: rgba(255, 255, 255, 0.55);
            border: 1px solid rgba(255, 255, 255, 0.6);
            border-left: 3px solid var(--card-accent);
            margin: 0;
        }
        .card-bullets li {
            font-size: 0.85rem; 
            margin-bottom: 8px; 
            line-height: 1.6; 
            color: #666666;
            padding-left: 16px;
            text-indent: -16px;
        }
        .card-bullets li:last-child { margin-bottom: 0; }
        .card-bullets li::before {
            content: '•'; 
            display: inline;
            color: var(--card-accent); 
            font-size: 1.1em; 
            font-weight: bold;
            margin-right: 8px;
        }
        strong { color: #444; font-weight: 700; }

        /* 页脚 */
        footer {
            margin-top: 60px; text-align: center; padding: 30px 20px 10px;
            border-top: 1px solid rgba(0,0,0,0.05);
        }
        .footer-brand {
            font-size: 1.1rem; font-weight: 800; letter-spacing: 2px;
            color: var(--text-primary); margin-bottom: 10px;
        }
        .footer-slogan {
            font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 30px;
        }
        .qr-code-box {
            width: 100px; height: 100px; margin: 0 auto; border-radius: 20px;
            background: var(--bg-color); padding: 10px;
            display: flex; align-items: center; justify-content: center;
            box-shadow: 10px 10px 20px var(--shadow-dark), -10px -10px 20px var(--shadow-light);
        }
        .qr-img { width: 100%; height: 100%; border-radius: 10px; }
        .qr-text { margin-top: 15px; font-size: 0.8rem; color: #999; }
    </style>
</head>
<body>
    <div class="container">
        
        <div class="hero-banner">
            <div class="banner-glow"></div>
            <div class="banner-visual">
                <span class="visual-icon">⚖️</span>
            </div>
            <div class="banner-content">
                <div class="banner-subtitle">LAWGEEK 晚读</div>
                <h1 class="banner-title">DAILY NEWS</h1>
                <div class="banner-meta">
                    <span>📅 {{ date_str }}</span>
                    <span>|</span>
                    <span>{{ weekday_str }}</span>
                </div>
            </div>
        </div>

        <div class="feature-illustration">
            <svg viewBox="0 0 500 200" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <linearGradient id="opt1-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" style="stop-color:#489CC1;stop-opacity:0.8" />
                        <stop offset="100%" style="stop-color:#6C63FF;stop-opacity:0.8" />
                    </linearGradient>
                </defs>
                <g stroke="url(#opt1-grad)" stroke-width="1.5" opacity="0.3">
                    <line x1="150" y1="100" x2="250" y2="50" />
                    <line x1="250" y1="50" x2="350" y2="100" />
                    <line x1="150" y1="100" x2="250" y2="150" />
                    <line x1="250" y1="150" x2="350" y2="100" />
                    <line x1="250" y1="50" x2="250" y2="150" />
                    <line x1="150" y1="100" x2="100" y2="150" />
                    <line x1="350" y1="100" x2="400" y2="50" />
                </g>
                <g>
                    <circle cx="250" cy="50" r="12" fill="#E6E9EF" stroke="#489CC1" stroke-width="3" />
                    <circle cx="250" cy="150" r="12" fill="#E6E9EF" stroke="#6C63FF" stroke-width="3" />
                    <circle cx="150" cy="100" r="18" fill="#E6E9EF" stroke="#D1D9E6" stroke-width="1" />
                    <text x="150" y="105" text-anchor="middle" font-size="12" fill="#999">AI</text>
                    <circle cx="350" cy="100" r="18" fill="#E6E9EF" stroke="#D1D9E6" stroke-width="1" />
                    <text x="350" y="105" text-anchor="middle" font-size="12" fill="#999">LAW</text>
                </g>
            </svg>
        </div>

        {% if news_items %}
        {% set lead = news_items[0] %}
        <section class="lead-story">
            <div class="lead-header">
                <span class="lead-number">01</span>
                <h2 class="lead-title">{{ lead.main_title | regex_replace('^\\d+[.、]\\s*', '') }}</h2>
            </div>
            <p class="lead-desc">{{ lead.abstract_summary }}</p>
            
            {% if lead.key_data %}
            <div class="key-data-container">
                {% for item in lead.key_data %}
                <div class="key-data-card">
                    <span class="key-data-label">{{ item.label }}</span>
                    <span class="key-data-value">{{ item.value }}<span class="key-data-unit">{{ item.unit }}</span></span>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            {% if lead.bullet_points %}
            <ul class="lead-bullets">
                {% for point in lead.bullet_points %}
                <li>{{ point }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </section>

        <div class="section-divider"></div>

        {% if news_items | length > 1 %}
        <div class="news-grid">
            {% set accent_colors = ['#489CC1', '#FF7272', '#21A87D', '#6C63FF'] %}
            {% for news in news_items[1:] %}
            <article class="news-card" style="--card-accent: {{ accent_colors[loop.index0 % 4] }};">
                <div class="card-header">
                    <div class="card-number">{{ '%02d' | format(loop.index + 1) }}</div>
                    <h3 class="card-title">{{ news.main_title | regex_replace('^\\d+[.、]\\s*', '') }}</h3>
                </div>
                {% if news.abstract_summary %}
                <p class="card-desc">{{ news.abstract_summary }}</p>
                {% endif %}
                {% if news.bullet_points %}
                <ul class="card-bullets">
                    {% for point in news.bullet_points %}
                    <li>{{ point }}</li>
                    {% endfor %}
                </ul>
                {% endif %}
            </article>
            {% endfor %}
        </div>
        {% endif %}
        {% endif %}

        <footer>
            <div class="footer-brand">LAWGEEK | 法律极客</div>
            <p class="footer-slogan">Memene · 阅读即成长</p>
            <div class="qr-code-box">
                <img src="{{ qr_code_path }}" class="qr-img" alt="二维码">
            </div>
            <p class="qr-text">长按扫码 · 订阅接收每日推送</p>
        </footer>
    </div>
</body>
</html>
"""


def regex_replace_filter(value, pattern, replacement):
    """Jinja2 自定义过滤器：正则替换"""
    return re.sub(pattern, replacement, value)


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

    # 创建 Jinja2 环境并注册自定义过滤器
    from jinja2 import Environment
    env = Environment()
    env.filters['regex_replace'] = regex_replace_filter
    template = env.from_string(HTML_TEMPLATE)
    
    # 处理日期和星期
    now = datetime.datetime.now()
    if not date_str:
        date_str = now.strftime("%m月%d日")
    
    weekday_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday_str = weekday_map[now.weekday()]
    
    rendered_html = template.render(
        news_items=news_data_list, 
        date_str=date_str,
        weekday_str=weekday_str,
        qr_code_path=qr_code_base64
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(device_scale_factor=2)
        
        await page.set_content(rendered_html, wait_until="domcontentloaded")
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
    
    # 检查百炼 API Key
    if not DASHSCOPE_API_KEY:
        print("❌ 错误：未配置 DASHSCOPE_API_KEY，请在 .env 文件中设置")
        return None
    
    # 1. 加载新闻
    news_list = load_news_from_file(input_file)
    
    if not news_list:
        print("停止处理：没有新闻内容可供总结。")
        return None
    
    final_data = []
    print("🚀 开始调用百炼 AI 进行总结...")
    
    # 2. 处理第一条新闻（头条，用原版提示词）
    if news_list:
        print("📰 处理头条新闻...")
        lead_result = summarize_news_with_qwen(news_list[0])
        if lead_result:
            lead_result = clean_ai_result(lead_result)
            final_data.append(lead_result)
            print(f"✅ [头条] 已获取: {lead_result.get('main_title')}")
    
    # 3. 处理 2-5 条新闻（用极简卡片版提示词）
    for i, content in enumerate(news_list[1:], start=2):
        print(f"📰 处理第 {i} 条新闻...")
        result = summarize_card_news_with_qwen(content)
        if result:
            result = clean_ai_result(result)
            final_data.append(result)
            print(f"✅ [卡片] 已获取: {result.get('main_title')}")

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

