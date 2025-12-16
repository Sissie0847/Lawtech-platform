import pandas as pd
import requests
import datetime
import os
import argparse
from ai_highlight import AIHighlighter

# ================= 配置区 =================
BASE_URL = "https://apis.memenews.cn"
PLAN_ID = "cmh1eis5n0002pjq9g6ck6t8c"
CSV_FILE = "news_database.csv"

def get_timestamp_for_date(date_str=None):
    """
    将日期字符串转换为毫秒级时间戳
    如果不传参数，则返回今天的时间戳
    date_str 格式: YYYY-MM-DD
    """
    if date_str:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    else:
        dt = datetime.datetime.now()
    # 返回毫秒级时间戳
    return int(dt.timestamp() * 1000)

def get_data_from_backend(date_str=None, verbose=False):
    """
    从 Meme 业务系统获取指定日期的数据
    date_str: 可选，格式 YYYY-MM-DD，不传则获取今天的数据
    verbose: 是否打印详细的 API 原始数据
    """
    print(f"正在从 Meme 系统获取数据...")
    
    url = f"{BASE_URL}/api/summary/detailsSummary/{PLAN_ID}"
    
    params = {}
    if date_str:
        params['date'] = get_timestamp_for_date(date_str)
        print(f"📅 目标日期: {date_str}")
    else:
        today = datetime.date.today().strftime("%Y-%m-%d")
        params['date'] = get_timestamp_for_date(today)
        print(f"📅 目标日期: {today} (今天)")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # 仅在 verbose 模式下打印 API 原始返回
        if verbose:
            import json
            print("\n" + "="*60)
            print("📡 API 原始返回数据:")
            print("="*60)
            print(json.dumps(data, ensure_ascii=False, indent=2))
            print("="*60 + "\n")
        
        if data.get('statusCode') != 200:
            print(f"❌ API 返回错误: {data.get('statusText', '未知错误')}")
            return []
        
        api_data = data.get('data', {})
        content_list = api_data.get('content', [])
        
        if not content_list:
            print("⚠️ 该日期暂无数据")
            return []
        
        print(f"✅ 成功获取 {len(content_list)} 条新闻")
        
        # 转换为统一格式
        news_list = []
        for idx, item in enumerate(content_list, 1):
            # 仅在 verbose 模式下打印每条新闻的原始字段
            if verbose:
                print(f"\n📰 第 {idx} 条新闻原始字段:")
                print(f"   - title: {item.get('title', '')[:50]}...")
                print(f"   - referenceLinks: {item.get('referenceLinks', '')}")
                print(f"   - reference: {item.get('reference', '')}")
                print(f"   - remakeIndex: {item.get('remakeIndex', 0)}")
                print(f"   - score: {item.get('score', 0)}")
                print(f"   - content 长度: {len(item.get('content', ''))} 字符")
                print(f"   - 所有字段: {list(item.keys())}")
            
            news_list.append({
                "title": item.get('title', ''),
                "url": item.get('referenceLinks', ''),
                "reference": item.get('reference', ''),  # 来源名称
                "content": item.get('content', ''),
                "rank": item.get('remakeIndex', 0),
                "score": item.get('score', 0),
            })
        
        # 按 rank 排序
        news_list.sort(key=lambda x: x['rank'])
        
        return news_list
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时，请稍后重试")
        return []
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        return []
    except Exception as e:
        print(f"❌ 数据解析失败: {e}")
        return []

# ================= 主逻辑 =================
def main(date_str=None, enable_highlight=True, verbose=False):
    """
    主函数，支持指定日期获取数据
    date_str: 可选，格式 YYYY-MM-DD
    enable_highlight: 是否启用 AI 标红功能
    verbose: 是否打印详细的 API 原始数据
    """
    # 1. 获取新数据
    raw_news_list = get_data_from_backend(date_str, verbose=verbose)
    
    if not raw_news_list:
        print("没有获取到数据，退出")
        return
    
    # 初始化 AI 处理器
    ai_processor = None
    if enable_highlight:
        print("🤖 AI 处理功能已启用（标红 + 分类）")
        ai_processor = AIHighlighter()
    
    new_rows = []
    # 使用传入的日期或今天的日期
    record_date = date_str if date_str else datetime.date.today().strftime("%Y-%m-%d")
    
    total = len(raw_news_list)
    for idx, news in enumerate(raw_news_list, 1):
        content = news['content']
        title = news['title']
        ai_classification = "推荐"
        ai_reason = ""
        
        # AI 处理（标红 + 分类）
        if ai_processor and content:
            print(f"📝 正在处理 ({idx}/{total}): {title[:30]}...")
            result = ai_processor.process_article(title, content)
            content = result['content']
            ai_classification = result['classification']
            ai_reason = result['reason']
            print(f"   → {ai_classification}: {ai_reason}")
        
        new_rows.append({
            "收录日期": record_date,
            "每日排名": news['rank'],
            "评分": news.get('score', 0),
            "标题": title,
            "链接": news['url'],
            "来源名称": news.get('reference', ''),  # 来源名称
            "原文内容": content,  # 标红后的内容
            "AI分类": ai_classification,  # 强烈推荐/推荐/一般/不推荐
            "AI理由": ai_reason,  # AI 分类理由
            "人工审核": "待审核",  # 入库 / 垃圾 / 待审核
            "发布顺序": "",  # 手动填写，用于发布时排序
        })
    
    # 2. 保存到 CSV
    new_df = pd.DataFrame(new_rows)
    
    if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
        # 如果文件已存在且不为空，就读取旧的，把新的拼接到后面
        try:
            old_df = pd.read_csv(CSV_FILE)
            # 简单去重：如果标题已经有了就不加了 (防止你点两次 fetch 重复进货)
            new_df = new_df[~new_df['标题'].isin(old_df['标题'])]
            if new_df.empty:
                print("⚠️ 所有新闻都已存在，没有新增数据")
                return
            final_df = pd.concat([old_df, new_df], ignore_index=True)
        except pd.errors.EmptyDataError:
            # CSV 文件为空或损坏，直接用新数据
            final_df = new_df
    else:
        final_df = new_df
        
    final_df.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
    print(f"✅ 进货成功！新增 {len(new_df)} 条，共存有 {len(final_df)} 条数据。现在去运行 app.py 吧！")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='从 Meme 系统获取新闻数据')
    parser.add_argument(
        '-d', '--date',
        type=str,
        help='指定获取数据的日期，格式: YYYY-MM-DD (例如: 2025-12-01)，不指定则获取今天的数据'
    )
    parser.add_argument(
        '--start',
        type=str,
        help='日期范围开始，格式: YYYY-MM-DD'
    )
    parser.add_argument(
        '--end',
        type=str,
        help='日期范围结束，格式: YYYY-MM-DD'
    )
    parser.add_argument(
        '--no-highlight',
        action='store_true',
        help='禁用 AI 标红功能（默认启用）'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='打印详细的 API 原始数据（调试用）'
    )
    
    args = parser.parse_args()
    enable_highlight = not args.no_highlight
    verbose = args.verbose
    
    # 日期范围模式
    if args.start and args.end:
        try:
            start_dt = datetime.datetime.strptime(args.start, "%Y-%m-%d")
            end_dt = datetime.datetime.strptime(args.end, "%Y-%m-%d")
        except ValueError:
            print("❌ 日期格式错误！请使用 YYYY-MM-DD 格式")
            exit(1)
        
        current = start_dt
        while current <= end_dt:
            date_str = current.strftime("%Y-%m-%d")
            print(f"\n{'='*50}")
            print(f"📆 正在处理: {date_str}")
            print('='*50)
            main(date_str, enable_highlight, verbose)
            current += datetime.timedelta(days=1)
    # 单日期模式
    elif args.date:
        try:
            datetime.datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print("❌ 日期格式错误！请使用 YYYY-MM-DD 格式，例如: 2025-12-01")
            exit(1)
        main(args.date, enable_highlight, verbose)
    else:
        main(None, enable_highlight, verbose)
