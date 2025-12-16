"""
飞书文档发布模块
用于自动创建飞书云文档并写入周报内容
"""

import requests
import json
import re
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, WEEKLY_REPORT_TITLE_TEMPLATE


def parse_markdown_bold(text: str) -> list:
    """
    解析 Markdown 加粗格式 (**text**)，转换为飞书 elements 数组
    返回: [{"text_run": {"content": "普通文本"}}, {"text_run": {"content": "加粗文本", "text_element_style": {"bold": True}}}, ...]
    """
    elements = []
    
    # 使用正则表达式匹配 **text** 格式
    pattern = r'\*\*(.+?)\*\*'
    last_end = 0
    
    for match in re.finditer(pattern, text):
        # 添加匹配之前的普通文本
        if match.start() > last_end:
            normal_text = text[last_end:match.start()]
            if normal_text:
                elements.append({
                    "text_run": {
                        "content": normal_text
                    }
                })
        
        # 添加加粗文本
        bold_text = match.group(1)
        if bold_text:
            elements.append({
                "text_run": {
                    "content": bold_text,
                    "text_element_style": {
                        "bold": True
                    }
                }
            })
        
        last_end = match.end()
    
    # 添加最后剩余的普通文本
    if last_end < len(text):
        remaining_text = text[last_end:]
        if remaining_text:
            elements.append({
                "text_run": {
                    "content": remaining_text
                }
            })
    
    # 如果没有匹配到任何加粗格式，返回整个文本作为普通文本
    if not elements:
        elements.append({
            "text_run": {
                "content": text
            }
        })
    
    return elements


class FeishuPublisher:
    """飞书文档发布器"""
    
    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.base_url = "https://open.feishu.cn/open-apis"
        self._tenant_access_token = None
    
    def get_tenant_access_token(self):
        """获取 tenant_access_token"""
        if self._tenant_access_token:
            return self._tenant_access_token
        
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        response = requests.post(url, json=payload)
        data = response.json()
        
        if data.get("code") == 0:
            self._tenant_access_token = data.get("tenant_access_token")
            return self._tenant_access_token
        else:
            raise Exception(f"获取 token 失败: {data.get('msg')}")
    
    def create_document(self, title: str, folder_token: str = None):
        """
        创建飞书文档
        返回文档的 document_id
        """
        token = self.get_tenant_access_token()
        url = f"{self.base_url}/docx/v1/documents"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {"title": title}
        if folder_token:
            payload["folder_token"] = folder_token
        
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        
        if data.get("code") == 0:
            doc_data = data.get("data", {}).get("document", {})
            return doc_data.get("document_id")
        else:
            raise Exception(f"创建文档失败: {data.get('msg')}")
    
    def get_document_blocks(self, document_id: str):
        """获取文档的根 block_id"""
        token = self.get_tenant_access_token()
        url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{document_id}"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data.get("code") == 0:
            return data.get("data", {}).get("block", {})
        else:
            raise Exception(f"获取文档块失败: {data.get('msg')}")
    
    def create_blocks(self, document_id: str, block_id: str, blocks: list, index: int = 0):
        """在文档中创建内容块"""
        token = self.get_tenant_access_token()
        url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{block_id}/children"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "children": blocks,
            "index": index
        }
        
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        
        if data.get("code") == 0:
            return data.get("data")
        else:
            # 打印详细错误信息用于调试
            error_detail = f"code: {data.get('code')}, msg: {data.get('msg')}"
            if data.get('error'):
                error_detail += f", error: {data.get('error')}"
            print(f"[DEBUG] 飞书API响应: {data}")
            raise Exception(f"写入内容失败: {error_detail}")
    
    def set_public_edit(self, document_id: str):
        """设置文档为「获得链接的人可编辑」"""
        token = self.get_tenant_access_token()
        url = f"{self.base_url}/drive/v1/permissions/{document_id}/public?type=docx"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "external_access_entity": "open",
            "security_entity": "anyone_can_edit",
            "comment_entity": "anyone_can_view",
            "share_entity": "anyone",
            "link_share_entity": "anyone_editable"
        }
        
        response = requests.patch(url, headers=headers, json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            print(f"[WARN] 设置权限失败: {data.get('msg')}, error: {data}")
        else:
            print(f"[INFO] 文档权限已设置为「链接可编辑」")
        
        return data
    
    def build_weekly_report_blocks(self, articles: list):
        """
        根据文章列表构建飞书文档块
        articles: [{"标题": "", "原文内容": "", "链接": "", "来源名称": "", "每日排名": 1}, ...]
        """
        blocks = []
        
        for i, article in enumerate(articles, 1):
            title = article.get("标题", "无标题")
            content = article.get("原文内容", "") or article.get("AI总结", "")
            link = article.get("链接", "")
            reference = article.get("来源名称", "") or self._extract_source_name(link)
            
            # 标题块 (Heading2)
            heading_block = {
                "block_type": 4,  # heading2
                "heading2": {
                    "style": {},
                    "elements": [
                        {
                            "text_run": {
                                "content": f"{i:02d} {title}"
                            }
                        }
                    ]
                }
            }
            blocks.append(heading_block)
            
            # 正文块 (Text) - 支持 **加粗** 格式
            if content:
                # 分段处理长文本，每段不超过 2000 字符
                paragraphs = content.split('\n\n')
                for para in paragraphs:
                    para_text = para.strip()
                    if para_text:
                        # 限制单段长度
                        if len(para_text) > 2000:
                            para_text = para_text[:2000] + "..."
                        
                        # 解析 Markdown 加粗格式
                        elements = parse_markdown_bold(para_text)
                        
                        text_block = {
                            "block_type": 2,  # text
                            "text": {
                                "style": {},
                                "elements": elements
                            }
                        }
                        blocks.append(text_block)
            
            # 来源链接块（带超链接）
            if link and reference:
                link_block = {
                    "block_type": 2,  # text
                    "text": {
                        "style": {},
                        "elements": [
                            {
                                "text_run": {
                                    "content": "来源："
                                }
                            },
                            {
                                "text_run": {
                                    "content": reference,
                                    "text_element_style": {
                                        "link": {
                                            "url": link
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
                blocks.append(link_block)
            elif reference:
                # 只有来源名称，没有链接
                link_block = {
                    "block_type": 2,
                    "text": {
                        "style": {},
                        "elements": [
                            {
                                "text_run": {
                                    "content": f"来源：{reference}"
                                }
                            }
                        ]
                    }
                }
                blocks.append(link_block)
            
            # 空行分隔（除了最后一篇）
            if i < len(articles):
                empty_block = {
                    "block_type": 2,
                    "text": {
                        "style": {},
                        "elements": [{
                            "text_run": {
                                "content": "———————————————————"
                            }
                        }]
                    }
                }
                blocks.append(empty_block)
        
        return blocks
    
    def _extract_source_name(self, url: str) -> str:
        """从 URL 提取来源名称"""
        if "mp.weixin.qq.com" in url:
            return "微信公众号"
        elif "weibo.com" in url or "weibo.cn" in url:
            return "微博"
        elif "twitter.com" in url or "x.com" in url:
            return "Twitter/X"
        elif "reddit.com" in url:
            return "Reddit"
        elif "ft.com" in url:
            return "金融时报"
        elif "github.com" in url:
            return "GitHub"
        else:
            # 提取域名
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                return parsed.netloc or "链接"
            except:
                return "链接"
    
    def _clean_articles(self, articles: list) -> list:
        """
        清洗文章数据，移除 NaN/inf 等非法 JSON 值
        """
        import math
        cleaned = []
        for article in articles:
            clean_article = {}
            for key, value in article.items():
                # 处理 float 类型的 NaN 和 inf
                if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                    clean_article[key] = ""
                # 处理 None
                elif value is None:
                    clean_article[key] = ""
                else:
                    clean_article[key] = value
            cleaned.append(clean_article)
        return cleaned

    def publish_weekly_report(self, vol: str, articles: list, folder_token: str = None):
        """
        发布周报
        vol: 期号，如 "12"
        articles: 文章列表
        folder_token: 可选，指定存放的文件夹
        
        返回: (document_id, document_url)
        """
        # 0. 清洗数据，移除 NaN/inf 等非法值
        articles = self._clean_articles(articles)

        # 1. 创建文档
        title = WEEKLY_REPORT_TITLE_TEMPLATE.format(vol=vol)
        document_id = self.create_document(title, folder_token)
        
        # 2. 设置文档权限为「链接可编辑」
        self.set_public_edit(document_id)
        
        # 3. 构建内容块
        blocks = self.build_weekly_report_blocks(articles)
        
        # 4. 分批写入内容（飞书 API 限制每次最多 50 个 children）
        BATCH_SIZE = 50
        current_index = 0
        
        for i in range(0, len(blocks), BATCH_SIZE):
            batch = blocks[i:i + BATCH_SIZE]
            if batch:
                self.create_blocks(document_id, document_id, batch, index=current_index)
                current_index += len(batch)
        
        # 5. 返回文档链接
        doc_url = f"https://bytedance.larkoffice.com/docx/{document_id}"
        
        return document_id, doc_url


def test_connection():
    """测试飞书连接是否正常"""
    try:
        publisher = FeishuPublisher()
        token = publisher.get_tenant_access_token()
        if token:
            return True, "✅ 飞书连接成功！"
    except Exception as e:
        return False, f"❌ 连接失败: {str(e)}"
    return False, "❌ 未知错误"


if __name__ == "__main__":
    # 测试连接
    success, message = test_connection()
    print(message)

