"""
微信公众号排版模块
生成适合公众号编辑器的 HTML 格式内容
"""

import re


def generate_wechat_html(articles: list, vol: str = "") -> str:
    """
    生成公众号格式的 HTML 内容
    
    样式规范：
    - 字体大小: 15px
    - 两端对齐: text-align: justify
    - 两端缩进: padding: 0 8px
    - 标题加粗
    - 来源链接使用公众号蓝色 #576b95
    
    articles: [{"标题": "", "原文内容": "", "链接": "", "来源名称": ""}, ...]
    vol: 期号
    """
    
    # 公众号样式常量
    FONT_SIZE = "15px"
    LINE_HEIGHT = "1.8"
    PADDING = "0 8px"
    TEXT_ALIGN = "justify"
    LINK_COLOR = "#576b95"
    TITLE_COLOR = "#0336CB"  # 蓝色标题
    BADGE_COLOR = "#0336CB"  # 序号圆标背景色
    DIVIDER_COLOR = "#e5e5e5"
    
    html_parts = []
    
    # 周报标题
    if vol:
        html_parts.append(f'''
<section style="padding: 16px 8px; text-align: center;">
  <p style="font-size: 20px; font-weight: bold; color: {TITLE_COLOR}; margin: 0;">
    vol.{vol}｜LawGeek法律科技周报
  </p>
</section>
''')
    
    # 文章内容
    for i, article in enumerate(articles, 1):
        title = article.get("标题", "无标题")
        content = article.get("原文内容", "") or article.get("AI总结", "")
        link = article.get("链接", "")
        reference = article.get("来源名称", "")
        
        # 处理 Markdown 加粗格式 **text** -> <strong>text</strong>
        content = convert_markdown_bold(content)
        
        # 分段处理
        paragraphs = content.split('\n\n') if content else []
        content_html = ""
        for para in paragraphs:
            para = para.strip()
            if para:
                # 处理单个换行
                para = para.replace('\n', '<br/>')
                content_html += f'''
  <p style="font-size: {FONT_SIZE}; line-height: {LINE_HEIGHT}; text-align: {TEXT_ALIGN}; padding: {PADDING}; margin: 0 0 12px 0; color: #333;">
    {para}
  </p>'''
        
        # 来源
        source_html = ""
        if reference:
            if link:
                source_html = f'''
  <p style="font-size: 14px; padding: {PADDING}; margin: 8px 0 0 0;">
    <span style="color: #999;">来源：</span><a href="{link}" style="color: {LINK_COLOR}; text-decoration: none;">{reference}</a>
  </p>'''
            else:
                source_html = f'''
  <p style="font-size: 14px; padding: {PADDING}; margin: 8px 0 0 0; color: #999;">
    来源：{reference}
  </p>'''
        
        # 分隔线（不是最后一篇）
        divider = ""
        if i < len(articles):
            divider = f'''
<section style="padding: 12px 8px;">
  <hr style="border: none; border-top: 1px solid {DIVIDER_COLOR}; margin: 0;"/>
</section>'''
        
        # 序号圆标样式
        badge_html = f'''<span style="display: inline-block; width: 22px; height: 22px; line-height: 22px; text-align: center; background-color: {BADGE_COLOR}; color: white; border-radius: 50%; font-size: 13px; font-weight: bold; margin-right: 8px; vertical-align: middle;">{i}</span>'''
        
        # 组装单篇文章
        article_html = f'''
<section style="padding: 8px 0;">
  <p style="font-size: 17px; font-weight: bold; color: {TITLE_COLOR}; padding: {PADDING}; margin: 0 0 12px 0;">
    {badge_html}<span style="vertical-align: middle;">{title}</span>
  </p>
{content_html}
{source_html}
</section>
{divider}'''
        
        html_parts.append(article_html)
    
    # 尾部署名
    html_parts.append(f'''
<section style="padding: 24px 8px; text-align: center;">
  <p style="font-size: 14px; color: #999; margin: 0;">
    ———— END ————
  </p>
  <p style="font-size: 14px; color: #999; margin: 8px 0 0 0;">
    📮 LawGeek法律科技周报 | 每周精选法律科技前沿资讯
  </p>
</section>
''')
    
    return '\n'.join(html_parts)


def convert_markdown_bold(text: str) -> str:
    """将 Markdown 加粗格式 **text** 转换为 HTML <strong>text</strong>"""
    if not text:
        return text
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)


def test_generate():
    """测试生成功能"""
    test_articles = [
        {
            "标题": "Norm AI 获黑石 5000 万美元投资",
            "原文内容": "Norm AI 宣布**获得黑石集团旗下基金 5000 万美元投资**，同时成立 AI 原生律所 Norm Law LLP。\n\n这是 Norm AI 首次从法律合规平台向直接提供法律服务的领域拓展。",
            "链接": "https://example.com/1",
            "来源名称": "微信公众号"
        },
        {
            "标题": "法律科技趋势分析",
            "原文内容": "2025年法律科技领域呈现**三大趋势**：AI合规、智能合同、法律服务自动化。",
            "链接": "https://example.com/2",
            "来源名称": "Reddit 法律科技社区"
        }
    ]
    
    html = generate_wechat_html(test_articles, "12")
    print(html)


if __name__ == "__main__":
    test_generate()

