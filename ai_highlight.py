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
        
        prompt = """# Role
你是一位 LegalTech 资讯主编。你的目标是保证阅读体验的“高信噪比”，同时避免页面枯燥无重点。
# Task
阅读【新闻原文】，采用 **“分级召回 (Tiered Recall)”** 策略进行局部高亮。
# ⚡ Core Logic: Tiered Strategy (分级策略)
请在内心按顺序执行以下逻辑判断（不要输出判断过程，只输出最终结果）：
1.  **第一轮扫描 (Tier 1 - 核弹级)**
    * 寻找：**具体金额/交易价**、**生效/截止日期**、**定性结论**、**具体效率数据**。
    * 👉 判定：如果发现了 Tier 1，**只标红 Tier 1**，严格忽略 Tier 2。
2.  **第二轮召回 (Tier 2 - 保底级)**
    * *仅当第一轮扫描结果为空时启动。*
    * 寻找：**增长率**、**市场地位**、**里程碑动作**、**积极情绪引用**。
    * 👉 判定：如果没发现 Tier 1，则标红 Tier 2 以防页面空白。
# Constraints (格式铁律)
1.  **Output Format**: 直接输出处理后的文本，**不要**输<Logic_Analysis>的内容。
2.  **Length**: 标红长度控制在 **4-10 个汉字**。
3.  **No Hallucination**: 绝不修改原文。
# Few-Shot Examples (逻辑演示)
---
### Case 1: 资源丰富 (Hit Tier 1 -> Ignore Tier 2)
<Input>
Elite 平台订阅用户激增 125%，过去 12 个月处理账单交易额达 720 亿美元。原生集成的 Payments 功能将付款周期缩短 40%。
</Input>
<Logic_Analysis>
扫描发现 Tier 1 信息："720 亿美元" (Money) 和 "缩短 40%" (Efficiency)。
策略：命中 Tier 1，忽略 "增长 125%" (Tier 2)。
</Logic_Analysis>
<Output>
Elite 平台订阅用户激增 125%，过去 12 个月处理账单交易额达 **720 亿美元**。原生集成的 Payments 功能将付款周期 **缩短 40%**。
</Output>
---
### Case 2: 资源贫瘠 (No Tier 1 -> Recall Tier 2)
<Input>
Clarra 推出了业界首个全球案件管理平台，订阅用户量同比激增 125％，持续引领数字化转型。
</Input>
<Logic_Analysis>
扫描 Tier 1：无金额，无截止日，无具体效率数据。
策略：启动 Tier 2 召回。标红 "业界首个..." (Status) 和 "激增 125%" (Growth)。
</Logic_Analysis>
<Output>
Clarra 推出了 **业界首个全球案件管理平台**，订阅用户量 **同比激增 125％**，持续引领数字化转型。
</Output>
---
### Case 3: 纯营销空话 (No Tier 1 & No Tier 2 -> Empty)
<Input>
我们致力于构建开放的生态系统，赋能每一位律师实现价值飞跃，共创美好未来。
</Input>
<Logic_Analysis>
扫描 Tier 1：无。
扫描 Tier 2：无具体增长，无里程碑，全是愿景空话。
策略：保持空白。
</Logic_Analysis>
<Output>
我们致力于构建开放的生态系统，赋能每一位律师实现价值飞跃，共创美好未来。
</Output>
---
原文内容：
""" + content
        
        result = self._call_api(prompt, max_tokens=4000)
        if not result:
            return content

        result_stripped = result.strip()

        # 安全兜底：如果 AI 返回内容过短，或者相对原文缩短过多，则认为标红失败，直接回退到原文
        original_len = len(content) if content is not None else 0
        if original_len > 0:
            if len(result_stripped) < 50 or len(result_stripped) < 0.5 * original_len:
                return content

        return result_stripped
    
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

