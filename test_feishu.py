"""测试飞书 API - 测试加粗功能"""
from publish_feishu import FeishuPublisher, parse_markdown_bold

# 先测试解析函数
print("测试 parse_markdown_bold 函数:")
test_text = "这是普通文本，**这是加粗文本**，这又是普通文本。"
elements = parse_markdown_bold(test_text)
print(f"输入: {test_text}")
print(f"输出: {elements}")
print()

publisher = FeishuPublisher()

# 模拟文章数据（带加粗格式）
test_articles = [
    {
        "标题": "测试加粗功能",
        "原文内容": "Norm AI 宣布获得黑石集团旗下基金 5000 万美元投资。**这是 Norm AI 首次从法律合规平台向直接提供法律服务的领域拓展。** 创始人 John Nay 强调这种整合模式的独特性。**Norm AI 此前主要为金融机构内部团队提供合规 AI 平台。**",
        "链接": "https://example.com/test",
        "来源名称": "测试来源"
    }
]

try:
    print("测试加粗功能...")
    doc_id, doc_url = publisher.publish_weekly_report("加粗测试", test_articles)
    print(f"发布成功!")
    print(f"文档链接: {doc_url}")
    print("请打开文档查看加粗效果！")
except Exception as e:
    print(f"发布失败: {e}")

