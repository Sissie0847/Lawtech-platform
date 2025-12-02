"""
卡片内容导出模块
生成前5条文章的 TXT 格式内容，用于卡片自动化
"""

import re


def generate_card_txt(articles: list, max_count: int = 5) -> str:
    """
    生成卡片格式的 TXT 内容
    
    格式：
    01 标题
    内容...
    
    02 标题
    内容...
    
    articles: [{"标题": "", "原文内容": "", ...}, ...]
    max_count: 最多导出几条，默认5条
    """
    
    lines = []
    
    # 只取前 max_count 条
    articles_to_export = articles[:max_count]
    
    for i, article in enumerate(articles_to_export, 1):
        title = article.get("标题", "无标题")
        content = article.get("原文内容", "") or article.get("AI总结", "")
        
        # 移除 Markdown 加粗格式 **text** -> text
        content = remove_markdown_bold(content)
        
        # 清理多余空行
        content = clean_content(content)
        
        # 添加序号和标题
        lines.append(f"{i:02d} {title}")
        
        # 添加内容
        if content:
            lines.append(content)
        
        # 文章之间空一行
        if i < len(articles_to_export):
            lines.append("")
    
    return '\n'.join(lines)


def remove_markdown_bold(text: str) -> str:
    """移除 Markdown 加粗格式 **text** -> text"""
    if not text:
        return text
    return re.sub(r'\*\*(.+?)\*\*', r'\1', text)


def clean_content(text: str) -> str:
    """清理内容，合并多余空行"""
    if not text:
        return text
    # 将多个换行合并为一个
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def test_generate():
    """测试生成功能"""
    test_articles = [
        {
            "标题": "企业法务 AI 应用场景成熟度榜单即将发布",
            "原文内容": "法务 AI 大会即将发布《2025 法务 AI 应用场景成熟度榜单》，这份报告基于对数百家企业法务团队的深度调研，覆盖多行业、多发展阶段的企业，对 80 个典型 AI 场景进行了价值度与成熟度调研发现。\n\n一些看似基础的场景反而获得较高评分，表明稳定可靠、重复可用的特性更受重视。"
        },
        {
            "标题": "全国律协动态周报：上海发布企业法律顾问指引",
            "原文内容": "上海律协发布了《律师办理企业法律顾问业务操作指引（2025）（试行）》，旨在为律师提供企业法律顾问服务的参考框架。\n\n北京律协发布《北京市律师行业网络推广合规倡议书》，呼吁律师行业在网络推广中坚持正确政治方向。"
        },
        {
            "标题": "全球 AI 治理的风险识别与透明度义务",
            "原文内容": "人工智能技术在突破能力上限的同时，也带来了版权侵权、深度伪造等多方面风险。**如何在有效防范风险的同时促进技术发展，避免过度进行干预阻碍技术进步，成为各国人工智能治理的关键课题**"
        },
        {
            "标题": "人工智能软硬件数据跨境合规指南起草人申报",
            "原文内容": "由公安部第三研究所等机构指导、智合标准中心牵头制定的《人工智能软硬件数据跨境合规指南》已完成专家论证，进入草案编制阶段。"
        },
        {
            "标题": "法律人如何通过知识库提升大模型的专业表现",
            "原文内容": "法律 AI 应用中常遇到大模型输出不够精准的问题，核心原因在于缺乏专业知识的支撑。知识库作为存储定领域数据的核心组件，通过 RAG 技术实现与大模型的联动。"
        }
    ]
    
    txt = generate_card_txt(test_articles)
    print(txt)


if __name__ == "__main__":
    test_generate()

