"""
百炼大模型 AI 处理模块
- 标红：自动标记文章中的重要观点
- 分类：判断文章是否值得入库
"""

import requests
import json
from config import BAILIAN_API_KEY, BAILIAN_MODEL


class AIHighlighter:
    """AI 处理器（标红 + 分类）"""
    
    def __init__(self):
        self.api_key = BAILIAN_API_KEY
        self.model = BAILIAN_MODEL
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    
    def _call_api(self, prompt: str, max_tokens: int = 4000) -> str:
        """调用百炼 API 的通用方法"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"].strip()
            else:
                return ""
                
        except Exception as e:
            print(f"[AI] API 调用失败: {e}")
            return ""
    
    def classify_content(self, title: str, content: str) -> tuple:
        """
        对文章进行分类判断
        返回: (分类等级, 推荐理由)
        分类等级: 强烈推荐 / 推荐 / 一般 / 不推荐
        """
        if not content or len(content.strip()) < 20:
            return "一般", "内容过短，无法判断"
        
        prompt = f"""你是一个专业的法律科技领域编辑。请根据以下文章的标题和内容，判断这篇文章是否值得收录到「法律科技周报」中。

判断标准：
1. 法律科技相关性：是否与法律科技、法律AI、合规科技、法律服务创新等领域相关
2. 内容质量：信息价值、深度、时效性、可读性
3. 目标读者：法律从业者、法律科技从业者、对法律科技感兴趣的人

请按以下格式返回（只返回这两行，不要其他内容）：
分类：[强烈推荐/推荐/一般/不推荐]
理由：[一句话说明理由，不超过50字]

文章标题：{title}

文章内容：
{content[:1500]}
"""
        
        result = self._call_api(prompt, max_tokens=200)
        
        if not result:
            return "一般", "AI 分析失败"
        
        # 解析结果
        classification = "一般"
        reason = "无"
        
        for line in result.split('\n'):
            line = line.strip()
            if line.startswith('分类：') or line.startswith('分类:'):
                classification = line.split('：')[-1].split(':')[-1].strip()
            elif line.startswith('理由：') or line.startswith('理由:'):
                reason = line.split('：', 1)[-1].split(':', 1)[-1].strip()
        
        # 验证分类值
        valid_classifications = ["强烈推荐", "推荐", "一般", "不推荐"]
        if classification not in valid_classifications:
            classification = "一般"
        
        return classification, reason
    
    def highlight_content(self, content: str) -> str:
        """
        对文章内容进行标红处理
        返回处理后的内容，重要观点用 **加粗** 标记
        """
        if not content or len(content.strip()) < 10:
            return content
        
        prompt = """你是一个专业的法律科技领域编辑。请阅读以下文章内容，找出其中最重要的2-4个核心观点或关键信息，用 **双星号** 将它们标记出来。

要求：
1. 只标记真正重要的核心观点，不要过度标记
2. 标记的内容应该是完整的句子或短语
3. 保持原文的其他部分不变
4. 直接返回处理后的全文，不要添加任何解释

原文内容：
""" + content
        
        result = self._call_api(prompt, max_tokens=4000)
        return result if result else content
    
    def process_article(self, title: str, content: str) -> dict:
        """
        一次性处理文章：标红 + 分类
        返回: {"content": 标红后的内容, "classification": 分类, "reason": 理由}
        """
        # 先进行分类
        classification, reason = self.classify_content(title, content)
        
        # 再进行标红
        highlighted_content = self.highlight_content(content)
        
        return {
            "content": highlighted_content,
            "classification": classification,
            "reason": reason
        }


def test_all():
    """测试标红和分类功能"""
    highlighter = AIHighlighter()
    
    test_title = "Norm AI 获黑石 5000 万美元投资并成立 AI 原生律所"
    test_content = """Norm AI 宣布获得黑石集团旗下基金 5000 万美元投资，同时成立 AI 原生律所 Norm Law LLP。这是 Norm AI 首次从法律合规平台向直接提供法律服务的领域拓展，初期将专注于为金融机构客户提供服务。创始人 John Nay 强调这种整合模式的独特性。Norm AI 此前主要为金融机构内部团队提供合规 AI 平台，客户包括管理超 30 万亿美元资产的全球银行、对冲基金等。"""
    
    print("=" * 50)
    print("测试文章标题:", test_title)
    print("=" * 50)
    print("\n原文:")
    print(test_content)
    
    print("\n" + "=" * 50)
    print("AI 处理中...")
    print("=" * 50)
    
    result = highlighter.process_article(test_title, test_content)
    
    print(f"\n📊 AI 分类: {result['classification']}")
    print(f"💡 AI 理由: {result['reason']}")
    print(f"\n📝 标红后内容:")
    print(result['content'])


if __name__ == "__main__":
    test_all()

