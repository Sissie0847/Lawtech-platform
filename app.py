import streamlit as st
import pandas as pd
import os
import time
import datetime
from streamlit_sortables import sort_items
from publish_feishu import FeishuPublisher, test_connection
from wechat_format import generate_wechat_html
from card_export import generate_card_txt, save_card_txt
from community_copy import generate_community_copy

# 导入 fetch.py 的功能
from fetch import get_data_from_backend
from ai_highlight import AIHighlighter

# 页面设置
st.set_page_config(
    page_title="LawGeek 运营台", 
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="⚖️"
)

# === 自定义 CSS 主题 ===
st.markdown("""
<style>
    /* ===== 全局样式 ===== */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');
    
    /* 隐藏默认的 Streamlit 元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 主容器背景 */
    .stApp {
        background: linear-gradient(145deg, #faf8f5 0%, #f5f0e8 50%, #f0ebe3 100%);
        font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* 主内容区域 - 减少顶部空白 */
    .main .block-container {
        padding: 0.5rem 2rem 3rem 2rem;
        max-width: 1400px;
    }
    
    /* 隐藏 Streamlit 默认的顶部空白 */
    .stApp > header {
        display: none;
    }
    
    .block-container {
        padding-top: 1rem !important;
    }
    
    /* ===== 顶部品牌栏（居中无背景） ===== */
    .top-header {
        text-align: center;
        padding: 0 0 16px 0;
        margin-top: -0.5rem;
    }
    
    .top-header h1 {
        margin: 0;
        font-size: 22px;
        font-weight: 700;
        color: #2d2d2d;
        letter-spacing: -0.5px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
    }
    
    .top-header h1 .icon {
        width: 36px;
        height: 36px;
        background: linear-gradient(145deg, #b85c38 0%, #9b4d30 100%);
        border-radius: 10px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        box-shadow: 0 4px 12px rgba(184, 92, 56, 0.2);
    }
    
    .top-header p {
        margin: 6px 0 0 0;
        font-size: 13px;
        color: #999;
        letter-spacing: 1px;
    }
    
    /* ===== Tab 样式 - 简洁风格 ===== */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255,255,255,0.6);
        border-radius: 12px;
        padding: 5px;
        gap: 4px;
        border: 1px solid rgba(139, 90, 60, 0.08);
        justify-content: center;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        border-radius: 10px;
        padding: 0 28px;
        font-weight: 500;
        font-size: 14px;
        color: #777;
        background: transparent;
        border: none;
        transition: all 0.2s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: #faf8f5;
        color: #b85c38;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #b85c38 0%, #c96b44 100%) !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(184, 92, 56, 0.25);
    }
    
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 20px;
    }
    
    /* 隐藏 tab 下划线 */
    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }
    
    .stTabs [data-baseweb="tab-border"] {
        display: none;
    }
    
    /* ===== 统计卡片样式（简洁版） ===== */
    .stat-card {
        background: rgba(255,255,255,0.5);
        border-radius: 14px;
        padding: 16px 20px;
        border: 1px solid rgba(139, 90, 60, 0.06);
        text-align: center;
    }
    
    .stat-icon {
        font-size: 24px;
        margin-bottom: 8px;
    }
    
    .stat-number {
        font-size: 32px;
        font-weight: 700;
        color: #b85c38;
        margin: 0;
        line-height: 1;
    }
    
    .stat-label {
        font-size: 13px;
        color: #8a8a8a;
        margin-top: 4px;
    }
    
    /* ===== 按钮样式 ===== */
    .stButton > button {
        border-radius: 12px;
        padding: 10px 24px;
        font-weight: 500;
        transition: all 0.2s ease;
        border: none;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #b85c38 0%, #c96b44 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(184, 92, 56, 0.25);
    }
    
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #a85230 0%, #b8603c 100%);
        box-shadow: 0 6px 16px rgba(184, 92, 56, 0.35);
        transform: translateY(-1px);
    }
    
    /* ===== 选择框样式 ===== */
    .stSelectbox > div > div {
        border-radius: 12px;
        border-color: rgba(139, 90, 60, 0.15);
        background: white;
    }
    
    /* ===== 输入框样式 ===== */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        border-radius: 12px;
        border-color: rgba(139, 90, 60, 0.15);
        background: white;
        padding: 10px 16px;
    }
    
    /* ===== 空状态提示 ===== */
    .empty-state {
        text-align: center;
        padding: 60px 40px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 2px 12px rgba(139, 90, 60, 0.06);
    }
    
    .empty-state-icon {
        font-size: 48px;
        margin-bottom: 16px;
    }
    
    .empty-state-title {
        font-size: 18px;
        font-weight: 600;
        color: #2d2d2d;
        margin-bottom: 8px;
    }
    
    .empty-state-desc {
        font-size: 14px;
        color: #8a8a8a;
    }
    
    /* ===== 紧凑按钮布局 ===== */
    .stHorizontalBlock, 
    [data-testid="stHorizontalBlock"],
    [data-testid="column"] > div {
        gap: 0.5rem !important;
    }
    
    [data-testid="column"] {
        padding-left: 0.25rem !important;
        padding-right: 0.25rem !important;
    }
    
    [data-testid="column"]:first-child {
        padding-left: 0 !important;
    }
    
    [data-testid="column"]:last-child {
        padding-right: 0 !important;
    }
    
    .stButton > button {
        min-height: 38px;
        padding: 8px 16px;
        font-size: 13px;
    }
    
    .stButton {
        width: auto !important;
    }
    
    /* ===== 拖拽排序卡片样式 ===== */
    .sortable-item,
    .sortable-item:hover {
        background-color: rgba(255, 255, 255, 0.9) !important;
        color: #333 !important;
        border: 1px solid #e0d6cc !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        margin: 4px 0 !important;
        font-size: 14px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
    }
    
    .sortable-item:hover {
        background-color: #fff !important;
        border-color: #b85c38 !important;
        box-shadow: 0 2px 8px rgba(184, 92, 56, 0.15) !important;
    }
    
    .sortable-item:active {
        background-color: #faf6f2 !important;
    }
    
    .sortable-container-body {
        background-color: transparent !important;
        padding: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

CSV_FILE = "news_database.csv"


def load_data():
    """加载数据"""
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame()


def save_data(df):
    """保存数据"""
    df.to_csv(CSV_FILE, index=False)
    st.toast("✅ 数据已保存！", icon="💾")


def archive_articles(full_df, published_df, vol_number):
    """
    发布后存档
    1. 入库文章 → archive/vol_{vol_number}.csv，状态改为「已发布 vol.X」
    2. 垃圾文章 → archive/trash_vol_{vol_number}.csv，从数据库删除
    """
    archive_dir = "archive"
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
    
    # 1. 归档入库文章
    archive_file = f"{archive_dir}/vol_{vol_number}.csv"
    published_df.to_csv(archive_file, index=False)
    
    # 2. 归档垃圾文章（单独存档）
    trash_df = full_df[full_df["人工审核"] == "垃圾"].copy()
    trash_count = len(trash_df)
    if trash_count > 0:
        trash_file = f"{archive_dir}/trash_vol_{vol_number}.csv"
        trash_df.to_csv(trash_file, index=False)
    
    # 3. 更新入库文章状态
    published_titles = published_df["标题"].tolist()
    for title in published_titles:
        mask = full_df["标题"] == title
        full_df.loc[mask, "人工审核"] = f"已发布 vol.{vol_number}"
    
    # 4. 从数据库删除垃圾文章
    full_df = full_df[full_df["人工审核"] != "垃圾"].copy()
    
    full_df.to_csv(CSV_FILE, index=False)
    
    return trash_count


@st.dialog("📖 使用指南", width="large")
def show_help_dialog():
    """帮助文档弹窗"""
    st.markdown("### 🔄 工作流程")
    
    col0, col1, col2, col3, col4 = st.columns(5)
    col0.metric("📥", "数据导入")
    col1.success("📊 数据总览")
    col2.info("📋 资讯审阅")
    col3.warning("🚀 内容发布")
    col4.error("📦 归档")
    
    st.markdown("---")
    
    st.markdown("#### 📥 前置工作：数据导入")
    st.write("在项目目录下运行命令获取新闻数据：")
    st.code("python fetch.py", language="bash")
    st.write("如需指定日期范围：")
    st.code("python fetch.py --start 2024-12-01 --end 2024-12-03", language="bash")
    st.write("启动运营台：")
    st.code("python -m streamlit run app.py", language="bash")
    
    st.markdown("---")
    
    st.markdown("#### 📊 第一步：数据总览")
    st.write("查看导入的全部资讯数量，心中有数后开始审阅。")
    
    st.markdown("#### 📋 第二步：资讯审阅")
    st.write("AI 已预分类（🔥强烈推荐 / 👍推荐 / 📄一般）。")
    st.write("你只需决定：**入库**（发布）或 **垃圾**（跳过）。")
    
    st.markdown("#### 🚀 第三步：内容发布")
    st.write("入库文章会显示在这里，可拖拽调整发布顺序。")
    st.write("填写期号，点击「发布飞书」生成文档。")
    st.write("点击「公众号」生成公众号html格式排版，复制打开公众号后台，复制进壹伴的编辑源代码保存即可")
    st.write("点击「卡片」保存前5条新闻的txt，在项目中运行card_export.py文件，即可调用dify进行短总结，人工审核生成卡片的文本，保存生成卡片")
    st.write("点击「文案」，生成社群文案，复制即可使用")



    st.markdown("#### 📦 第四步：归档")
    st.write("所有运营物料出完后，点击「归档」。")
    st.warning("⚠️ 归档后无法撤销")
    


def render_top_header():
    """渲染顶部品牌栏"""
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        st.markdown("""
        <div class="top-header">
            <h1><span class="icon">⚖️</span> LawGeek 运营台</h1>
            <p>数据获取 → 资讯审阅 → 内容发布 → 归档，一站式完成</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        btn1, btn2 = st.columns(2)
        with btn1:
            if st.button("🔌 测试", key="test_conn_btn", help="测试飞书连接"):
                success, message = test_connection()
                if success:
                    st.toast(message)
                else:
                    st.toast(message, icon="❌")
        with btn2:
            if st.button("❓ 帮助", key="help_btn"):
                show_help_dialog()


def fetch_news_data(date_str=None, start_date=None, end_date=None, progress_callback=None, status_callback=None):
    """
    获取新闻数据并保存到 CSV
    date_str: 单个日期，格式 YYYY-MM-DD
    start_date, end_date: 日期范围
    progress_callback: 进度回调函数 (current, total)
    status_callback: 状态回调函数 (message)
    """
    try:
        # 初始化 AI 处理器
        if status_callback:
            status_callback("正在初始化 AI 处理器...")
        ai_processor = AIHighlighter()
        
        # 确定要处理的日期列表
        dates_to_process = []
        if start_date and end_date:
            # 日期范围模式
            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            current = start_dt
            while current <= end_dt:
                dates_to_process.append(current.strftime("%Y-%m-%d"))
                current += datetime.timedelta(days=1)
        elif date_str:
            # 单日期模式
            dates_to_process = [date_str]
        else:
            # 默认今天
            dates_to_process = [datetime.date.today().strftime("%Y-%m-%d")]
        
        new_rows = []
        total_dates = len(dates_to_process)
        processed_news_count = 0
        
        # 缓存：存储每个日期获取的新闻数据，避免重复调用 API
        news_cache = {}
        total_news_count = 0
        
        # 一次性获取所有日期的数据并缓存（用于统计和后续处理）
        if status_callback:
            status_callback("正在获取新闻数据...")
        for date_idx, date in enumerate(dates_to_process, 1):
            if status_callback:
                status_callback(f"📡 正在获取日期 {date} 的数据 ({date_idx}/{total_dates})...")
            
            raw_news_list = get_data_from_backend(date, verbose=False)
            if raw_news_list:
                news_cache[date] = raw_news_list
                total_news_count += len(raw_news_list)
        
        if total_news_count == 0:
            return False, "没有获取到新数据"
        
        # 估算时间：每条新闻约 3-5 秒（AI处理，API已调用完成）
        estimated_seconds = total_news_count * 4
        estimated_minutes = estimated_seconds // 60
        estimated_secs = estimated_seconds % 60
        if status_callback:
            if estimated_minutes > 0:
                status_callback(f"预计需要 {estimated_minutes} 分 {estimated_secs} 秒（共 {total_news_count} 条新闻，每条约 3-5 秒）")
            else:
                status_callback(f"预计需要 {estimated_secs} 秒（共 {total_news_count} 条新闻，每条约 3-5 秒）")
        
        # 处理每个日期（使用缓存的数据，不再重复调用 API）
        for date_idx, date in enumerate(dates_to_process, 1):
            if date not in news_cache:
                continue
                
            if status_callback:
                status_callback(f"📅 正在处理日期 {date} ({date_idx}/{total_dates})...")
            
            # 使用缓存的数据，避免重复调用 API
            raw_news_list = news_cache[date]
            
            # 处理每条新闻
            for news_idx, news in enumerate(raw_news_list, 1):
                processed_news_count += 1
                
                if status_callback:
                    status_callback(f"📰 正在处理: {news['title'][:30]}... ({processed_news_count}/{total_news_count})")
                
                # 更新进度
                if progress_callback:
                    progress = processed_news_count / total_news_count
                    progress_callback(progress)
                
                content = news['content']
                title = news['title']
                ai_classification = "推荐"
                ai_reason = ""
                
                # AI 处理（标红 + 分类）
                if ai_processor and content:
                    result = ai_processor.process_article(title, content)
                    content = result['content']
                    ai_classification = result['classification']
                    ai_reason = result['reason']
                
                new_rows.append({
                    "收录日期": date,
                    "每日排名": news['rank'],
                    "评分": news.get('score', 0),
                    "标题": title,
                    "链接": news['url'],
                    "来源名称": news.get('reference', ''),
                    "原文内容": content,
                    "AI分类": ai_classification,
                    "AI理由": ai_reason,
                    "人工审核": "待审核",
                    "发布顺序": "",
                })
        
        if not new_rows:
            return False, "没有获取到新数据"
        
        # 保存到 CSV
        if status_callback:
            status_callback("💾 正在保存数据...")
        new_df = pd.DataFrame(new_rows)
        
        if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
            # 如果文件已存在，读取旧的，去重后拼接
            try:
                old_df = pd.read_csv(CSV_FILE)
                # 去重：如果标题已经有了就不加了
                new_df = new_df[~new_df['标题'].isin(old_df['标题'])]
                if new_df.empty:
                    return False, "所有新闻都已存在，没有新增数据"
                final_df = pd.concat([old_df, new_df], ignore_index=True)
            except pd.errors.EmptyDataError:
                final_df = new_df
        else:
            final_df = new_df
        
        final_df.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
        
        if progress_callback:
            progress_callback(1.0)  # 完成
        
        return True, f"成功获取 {len(new_df)} 条新数据，共 {len(final_df)} 条"
        
    except Exception as e:
        return False, f"获取数据失败: {str(e)}"


def render_fetch_data_section():
    """渲染获取数据区域"""
    # st.markdown("---")  # 删除分割线
    
    # 显示标题
    st.markdown("#### 📥 获取数据")
    
    # 直接显示，不使用折叠按钮
    # 单日期获取功能（暂时注释）
    # col1, col2 = st.columns([1, 1])
    # 
    # with col1:
    #     st.markdown("#### 单日期获取")
    #     date_input = st.date_input(
    #         "选择日期",
    #         value=datetime.date.today(),
    #         key="fetch_single_date"
    #     )
    #     if st.button("📥 获取该日期数据", key="fetch_single_btn", type="primary"):
    #         date_str = date_input.strftime("%Y-%m-%d")
    #         
    #         # 创建进度条和状态容器
    #         progress_bar = st.progress(0)
    #         status_text = st.empty()
    #         
    #         def update_progress(progress):
    #             progress_bar.progress(progress)
    #         
    #         def update_status(message):
    #             status_text.info(f"⏳ {message}")
    #         
    #         # 执行获取数据
    #         success, message = fetch_news_data(
    #             date_str=date_str,
    #             progress_callback=update_progress,
    #             status_callback=update_status
    #         )
    #         
    #         # 清除进度条和状态
    #         progress_bar.empty()
    #         status_text.empty()
    #         
    #         if success:
    #             st.success(f"✅ {message}")
    #             time.sleep(1)  # 短暂延迟让用户看到成功消息
    #             st.rerun()  # 刷新页面
    #         else:
    #             st.error(f"❌ {message}")
    
    # 日期范围获取功能（保留）
    # st.markdown("#### 日期范围获取")  # 隐藏标题
    st.caption("前置工作，数据导入")
    col_start, col_end, col_btn = st.columns([2, 2, 1.5])
    with col_start:
        start_date = st.date_input(
            "开始日期",
            value=datetime.date.today(),
            key="fetch_start_date"
        )
    with col_end:
        end_date = st.date_input(
            "结束日期",
            value=datetime.date.today(),
            key="fetch_end_date"
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)  # 垂直对齐按钮
        fetch_btn_clicked = st.button("📥 获取数据", key="fetch_range_btn", type="primary", use_container_width=True)
    
    if fetch_btn_clicked:
            if start_date > end_date:
                st.error("❌ 开始日期不能晚于结束日期")
            else:
                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")
                
                # 创建进度条和状态容器
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(progress):
                    progress_bar.progress(progress)
                
                def update_status(message):
                    status_text.info(f"⏳ {message}")
                
                # 执行获取数据
                success, message = fetch_news_data(
                    start_date=start_str,
                    end_date=end_str,
                    progress_callback=update_progress,
                    status_callback=update_status
                )
                
                # 清除进度条和状态
                progress_bar.empty()
                status_text.empty()
                
                if success:
                    st.success(f"✅ {message}")
                    time.sleep(1)  # 短暂延迟让用户看到成功消息
                    st.rerun()  # 刷新页面
                else:
                    st.error(f"❌ {message}")


def render_stats_cards(df):
    """渲染统计卡片"""
    total = len(df)
    入库数 = len(df[df["人工审核"] == "入库"]) if "人工审核" in df.columns else 0
    待审核数 = len(df[df["人工审核"] == "待审核"]) if "人工审核" in df.columns else total
    垃圾数 = len(df[df["人工审核"] == "垃圾"]) if "人工审核" in df.columns else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">📰</div>
            <div class="stat-number">{total}</div>
            <div class="stat-label">全部</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">✅</div>
            <div class="stat-number">{入库数}</div>
            <div class="stat-label">入库</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">⏳</div>
            <div class="stat-number">{待审核数}</div>
            <div class="stat-label">待审</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">🗑️</div>
            <div class="stat-number">{垃圾数}</div>
            <div class="stat-label">垃圾</div>
        </div>
        """, unsafe_allow_html=True)


def get_ai_badge_class(ai_tag):
    """获取 AI 标签的样式类"""
    badge_map = {
        "强烈推荐": ("hot", "🔥 强烈推荐"),
        "推荐": ("recommend", "👍 推荐"),
        "一般": ("normal", "📄 一般"),
        "不推荐": ("skip", "👎 不推荐")
    }
    return badge_map.get(ai_tag, ("normal", "📄 一般"))


def convert_markdown_highlights(text: str) -> str:
    """
    将 Markdown 的 **加粗** 标记转换为 HTML 高亮样式
    """
    import re
    if not text:
        return text
    # 将 **文字** 转换为带高亮样式的 <strong> 标签
    pattern = r'\*\*(.+?)\*\*'
    replacement = r'<strong style="color: #b85c38; background: linear-gradient(180deg, transparent 60%, rgba(184, 92, 56, 0.15) 60%); padding: 0 2px;">\1</strong>'
    return re.sub(pattern, replacement, text)


def render_news_card(row, idx, df):
    """渲染单个新闻卡片"""
    ai_tag = row.get('AI分类', '一般')
    badge_class, badge_text = get_ai_badge_class(ai_tag)
    title = row.get('标题', '无标题')
    link = row.get('链接', '')
    ai_reason = row.get('AI理由', '')
    date_str = row.get('收录日期', '')
    score = row.get('评分', 0)
    source = row.get('来源名称', '未知来源')
    
    content_raw = row.get('原文内容', '')
    if pd.isna(content_raw):
        content_raw = ''
    content = str(content_raw).strip() if content_raw else ''
    # 将 Markdown 标记转换为 HTML 高亮
    content = convert_markdown_highlights(content)
    
    with st.container():
        col_content, col_action = st.columns([5, 1])
        
        with col_content:
            st.markdown(f"""
            <div style="display: flex; align-items: flex-start; gap: 12px; margin-bottom: 8px;">
                <span style="
                    padding: 4px 10px;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                    white-space: nowrap;
                    background: {'linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%)' if badge_class == 'hot' else 'linear-gradient(135deg, #b85c38 0%, #c96b44 100%)' if badge_class == 'recommend' else '#f5f0e8' if badge_class == 'normal' else '#e8e8e8'};
                    color: {'white' if badge_class in ['hot', 'recommend'] else '#8a8a8a'};
                ">{badge_text}</span>
                <span style="font-size: 16px; font-weight: 600; color: #2d2d2d; line-height: 1.5;">{title}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col_action:
            current_status = row.get('人工审核', '待审核')
            if pd.isna(current_status) or current_status == '':
                current_status = '待审核'
            status_options = ["入库", "垃圾", "待审核"]
            current_index = status_options.index(current_status) if current_status in status_options else 2
            
            key = f"status_{idx}"
            new_status = st.selectbox(
                "状态",
                status_options,
                index=current_index,
                key=key,
                label_visibility="collapsed"
            )
            
            if new_status != current_status:
                df.at[idx, "人工审核"] = new_status
                df.to_csv(CSV_FILE, index=False)
                st.toast(f"✅ 已保存：{title[:20]}... → {new_status}", icon="💾")
        
        meta_parts = [f"📅 {date_str}", f"📊 评分 {score}", f"🏷️ {source}"]
        if link:
            meta_parts.append(f"[🔗 原文链接]({link})")
        st.caption(" · ".join(meta_parts))
        
        ai_reason_str = str(ai_reason) if not pd.isna(ai_reason) else ''
        if ai_reason_str.strip():
            st.info(f"🤖 **AI 分析：** {ai_reason_str}")
        
        if content:
            st.markdown(f"""
            <div style="
                background: #fdfbf9;
                padding: 14px 18px;
                border-radius: 10px;
                font-size: 14px;
                color: #555;
                line-height: 1.8;
                margin-top: 8px;
                border: 1px solid #f0ebe3;
                max-height: 400px;
                overflow-y: auto;
            ">{content}</div>
            """, unsafe_allow_html=True)
        else:
            st.caption("📭 暂无原文内容")
        
        st.markdown("---")


def render_empty_state(icon, title, desc):
    """渲染空状态"""
    st.markdown(f"""
    <div class="empty-state">
        <div class="empty-state-icon">{icon}</div>
        <div class="empty-state-title">{title}</div>
        <div class="empty-state-desc">{desc}</div>
    </div>
    """, unsafe_allow_html=True)


# === 主程序 ===

render_top_header()

if not os.path.exists(CSV_FILE):
    render_empty_state(
        "📭",
        "还没有数据",
        "请使用上方的「获取数据」功能获取新闻"
    )
    st.stop()

df = load_data()

if "人工审核" in df.columns:
    df["人工审核"] = df["人工审核"].fillna("待审核")
    df["人工审核"] = df["人工审核"].replace("", "待审核")

tab_data, tab_review, tab_publish = st.tabs(["📊 数据总览", "📋 资讯审阅", "🚀 内容发布"])

# ==================== TAB 1: 数据总览 ====================
with tab_data:
    # 获取数据功能
    render_fetch_data_section()
   
    st.markdown("### 📊 数据总览")
    st.caption("第一步：查看导入的资讯数量，了解今天有多少新闻等待审阅（已归档的不显示）")
    
    # 过滤掉已归档的数据（人工审核字段包含 "已发布" 的记录）
    df_active = df[~df["人工审核"].str.contains("已发布", na=False)].copy() if "人工审核" in df.columns else df.copy()
    
    render_stats_cards(df_active)
    
    st.markdown("---")
    
    st.dataframe(
        df_active,
        column_config={
            "标题": st.column_config.TextColumn("📰 标题", width="medium"),
            "原文内容": st.column_config.TextColumn("📄 内容", width="large"),
            "链接": st.column_config.LinkColumn("🔗 链接"),
            "人工审核": st.column_config.TextColumn("✅ 状态", width="small"),
            "AI分类": st.column_config.TextColumn("🤖 AI推荐", width="small"),
            "评分": st.column_config.NumberColumn("📊 评分", width="small"),
            "来源名称": st.column_config.TextColumn("🏷️ 来源", width="small"),
            "收录日期": st.column_config.TextColumn("📅 日期", width="small"),
        },
        hide_index=True,
        width='stretch',
        height=500
    )

# ==================== TAB 2: 资讯审阅 ====================
with tab_review:
    入库数 = len(df[df["人工审核"] == "入库"]) if "人工审核" in df.columns else 0
    待审核数 = len(df[df["人工审核"] == "待审核"]) if "人工审核" in df.columns else 0
    
    title_col, spacer, filter_col, stat_col = st.columns([2, 3, 1.2, 0.8])
    
    with title_col:
        st.markdown("### 📋 资讯审阅")
        st.caption("第二步：AI 已预分类，选择「入库」或「垃圾」，状态自动保存 ✨")
    
    with filter_col:
        filter_option = st.selectbox(
            "筛选",
            ["待审核", "入库", "垃圾", "已发布", "全部"],
            index=0,
            label_visibility="collapsed"
        )
    
    with stat_col:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #b85c38 0%, #c96b44 100%);
            color: white;
            padding: 8px 12px;
            border-radius: 10px;
            text-align: center;
            font-size: 13px;
        ">
            <div style="font-size: 18px; font-weight: 700;">{入库数}</div>
            <div style="font-size: 11px; opacity: 0.9;">已入库</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.caption(f"待审核 {待审核数} 篇 · 修改状态后自动保存")
    
    st.markdown("---")
    
    if filter_option == "待审核":
        display_df = df[df["人工审核"] == "待审核"].copy()
    elif filter_option == "入库":
        display_df = df[df["人工审核"] == "入库"].copy()
    elif filter_option == "垃圾":
        display_df = df[df["人工审核"] == "垃圾"].copy()
    elif filter_option == "已发布":
        display_df = df[df["人工审核"].str.startswith("已发布", na=False)].copy()
    else:
        display_df = df.copy()
    
    if display_df.empty:
        render_empty_state(
            "📭",
            "当前筛选条件下没有数据",
            "尝试切换筛选条件查看更多内容"
        )
    else:
        for idx, row in display_df.iterrows():
            render_news_card(row, idx, df)
        
        st.session_state['edited_df'] = df

# ==================== TAB 3: 内容发布 ====================
with tab_publish:
    st.caption("第三步：调整顺序 → 发布飞书预览 → 确认无误后点「归档」完成")
    
    saved_df = load_data()
    if not saved_df.empty and "人工审核" in saved_df.columns:
        selected_articles = saved_df[saved_df["人工审核"] == "入库"].copy()
        article_count = len(selected_articles)
        
        if article_count > 0:
            ai_order = {"强烈推荐": 1, "推荐": 2, "一般": 3, "不推荐": 4}
            selected_articles["_ai_order"] = selected_articles["AI分类"].map(ai_order).fillna(3)
            selected_articles["_sort_order"] = selected_articles["发布顺序"].fillna(999)
            selected_articles = selected_articles.sort_values(
                by=["_sort_order", "_ai_order", "评分"],
                ascending=[True, True, False]
            )
            selected_articles = selected_articles.drop(columns=["_sort_order", "_ai_order"])
    else:
        selected_articles = pd.DataFrame()
        article_count = 0
    
    if article_count == 0:
        render_empty_state(
            "📝",
            "暂无待发布文章",
            "请先在「资讯审阅」中将文章标记为「入库」"
        )
    else:
        edit_col, preview_col = st.columns([1.2, 1])
        
        with edit_col:
            st.markdown("#### ✏️ 调整发布顺序")
            st.caption("↕️ 上下拖拽卡片调整顺序，松手自动保存")
            
            drag_items = []
            for i, (idx, row) in enumerate(selected_articles.iterrows()):
                title = row.get('标题', '无标题')
                display_text = f"{title[:50]}{'...' if len(title) > 50 else ''}"
                drag_items.append(display_text)
            
            sorted_items = sort_items(drag_items, direction="vertical")
            
            if sorted_items != drag_items:
                for new_idx, display_text in enumerate(sorted_items, 1):
                    title_part = display_text
                    if title_part.endswith('...'):
                        title_part = title_part[:-3]
                    
                    for _, row in selected_articles.iterrows():
                        original_title = row.get('标题', '')
                        if original_title.startswith(title_part) or title_part in original_title[:50]:
                            mask = saved_df["标题"] == original_title
                            if mask.any():
                                saved_df.loc[mask, "发布顺序"] = new_idx
                            break
                
                saved_df.to_csv(CSV_FILE, index=False)
                st.toast("✅ 顺序已更新！", icon="🔄")
                time.sleep(0.3)
                st.rerun()
        
        with preview_col:
            st.markdown("#### 📋 发布顺序预览")
            st.caption("保存后将按此顺序发布")
            
            for i, (_, row) in enumerate(selected_articles.iterrows(), 1):
                title = row.get('标题', '无标题')
                ai_tag = row.get('AI分类', '一般')
                badge_class, _ = get_ai_badge_class(ai_tag)
                border_color = '#ff6b6b' if badge_class == 'hot' else '#b85c38' if badge_class == 'recommend' else '#d4c8bc'
                
                st.markdown(f"""
                <div style="
                    background: rgba(255,255,255,0.5);
                    border-radius: 8px;
                    padding: 10px 14px;
                    margin-bottom: 8px;
                    border-left: 3px solid {border_color};
                    display: flex;
                    align-items: center;
                    gap: 10px;
                ">
                    <span style="
                        min-width: 24px;
                        height: 24px;
                        background: #b85c38;
                        border-radius: 6px;
                        display: inline-flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 11px;
                        font-weight: 600;
                        color: white;
                    ">{i:02d}</span>
                    <span style="font-size: 13px; color: #444;">{title[:35]}{'...' if len(title) > 35 else ''}</span>
                </div>
                """, unsafe_allow_html=True)
    
    if article_count > 0:
        st.markdown("---")
        left_col, right_col = st.columns([1, 1])
        
        with left_col:
            sub1, sub2, sub3 = st.columns([1.2, 0.8, 1.5])
            with sub1:
                vol_number = st.text_input("期号", placeholder="期号，如 12", label_visibility="collapsed")
            with sub2:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #b85c38 0%, #c96b44 100%);
                    border-radius: 8px;
                    padding: 7px 12px;
                    color: white;
                    text-align: center;
                    font-size: 13px;
                    margin-top: 1px;
                "><b>{article_count}</b> 篇</div>
                """, unsafe_allow_html=True)
        
        with right_col:
            # 检查是否已有生成的文档（同一期号）
            cached_doc = st.session_state.get('feishu_doc', {})
            cached_vol = cached_doc.get('vol')
            cached_url = cached_doc.get('url')
            has_cached_doc = cached_vol == vol_number and cached_url and vol_number
            
            if has_cached_doc:
                # 已有文档：查看文档 | 重新生成 | 公众号 | 卡片 | 文案 | 归档
                b1, b2, b3, b4, b5, b6 = st.columns([1, 1, 1, 1, 1, 1])
                with b1:
                    view_doc_clicked = st.button("📄 查看文档")
                    publish_clicked = False
                with b2:
                    regenerate_clicked = st.button("🔄 重新生成")
                with b3:
                    wechat_clicked = st.button("📱 公众号")
                with b4:
                    card_clicked = st.button("🃏 卡片")
                with b5:
                    copy_clicked = st.button("💬 文案")
                with b6:
                    archive_clicked = st.button("📦 归档", type="primary")
            else:
                # 无缓存：发布飞书 | 公众号 | 卡片 | 文案 | 归档
                b1, b2, b3, b4, b5 = st.columns([1, 1, 1, 1, 1])
                view_doc_clicked = False
                regenerate_clicked = False
                with b1:
                    publish_clicked = st.button("📤 发布飞书")
                with b2:
                    wechat_clicked = st.button("📱 公众号")
                with b3:
                    card_clicked = st.button("🃏 卡片")
                with b4:
                    copy_clicked = st.button("💬 文案")
                with b5:
                    archive_clicked = st.button("📦 归档", type="primary")
    else:
        vol_number = ""
        publish_clicked = False
        regenerate_clicked = False
        view_doc_clicked = False
        wechat_clicked = False
        card_clicked = False
        copy_clicked = False
        archive_clicked = False
    
    # 处理查看已生成文档
    if view_doc_clicked:
        cached_doc = st.session_state.get('feishu_doc', {})
        if cached_doc.get('url'):
            st.success(f"📄 Vol.{cached_doc.get('vol')} 文档已生成")
            st.markdown(f"👉 [点击查看文档]({cached_doc.get('url')})")
            st.info("💡 如需重新生成，请点击「🔄 重新生成」按钮")
    
    # 处理发布或重新生成
    if publish_clicked or regenerate_clicked:
        # 清除展示状态
        st.session_state['show_wechat'] = False
        st.session_state['show_card'] = False
        st.session_state['show_copy'] = False
        
        if not vol_number:
            st.error("⚠️ 请输入期号！")
        elif article_count == 0:
            st.error("⚠️ 还没有标记为「入库」的文章！")
        else:
            with st.spinner("正在发布到飞书（预览）..."):
                try:
                    publisher = FeishuPublisher()
                    articles = selected_articles.to_dict('records')
                    doc_id, doc_url = publisher.publish_weekly_report(vol_number, articles)
                    
                    # 缓存文档信息，避免重复生成
                    st.session_state['feishu_doc'] = {
                        'vol': vol_number,
                        'url': doc_url,
                        'doc_id': doc_id
                    }
                    
                    st.success("🎉 发布成功！")
                    st.markdown(f"📄 [点击查看文档]({doc_url})")
                    st.info("💡 确认无误后，点击「📦 归档」按钮完成归档")
                except Exception as e:
                    st.error(f"❌ 发布失败: {str(e)}")
    
    if archive_clicked:
        # 清除展示状态
        st.session_state['show_wechat'] = False
        st.session_state['show_card'] = False
        st.session_state['show_copy'] = False
        
        if not vol_number:
            st.error("⚠️ 请输入期号！")
        elif article_count == 0:
            st.error("⚠️ 还没有标记为「入库」的文章！")
        else:
            trash_count = archive_articles(saved_df, selected_articles, vol_number)
            
            # 归档成功后清除文档缓存
            if 'feishu_doc' in st.session_state:
                del st.session_state['feishu_doc']
            
            st.success(f"🎉 已归档！文章已标记为「已发布 vol.{vol_number}」")
            st.info(f"📦 入库存档：archive/vol_{vol_number}.csv")
            if trash_count > 0:
                st.info(f"🗑️ 垃圾存档：archive/trash_vol_{vol_number}.csv（{trash_count} 条已清理）")
            st.balloons()
            st.rerun()
    
    if wechat_clicked:
        st.session_state['show_wechat'] = True
        st.session_state['show_card'] = False
        st.session_state['show_copy'] = False
    
    if card_clicked:
        st.session_state['show_card'] = True
        st.session_state['show_wechat'] = False
        st.session_state['show_copy'] = False
    
    if copy_clicked:
        st.session_state['show_copy'] = True
        st.session_state['show_wechat'] = False
        st.session_state['show_card'] = False
    
    if st.session_state.get('show_wechat', False) or st.session_state.get('show_card', False) or st.session_state.get('show_copy', False):
        st.markdown("---")
        
        if st.session_state.get('show_wechat', False):
            st.markdown("#### 📱 公众号 HTML")
            articles = selected_articles.to_dict('records')
            html_content = generate_wechat_html(articles, vol_number or "X")
            
            code_col, preview_col = st.columns(2)
            with code_col:
                st.caption("复制下方代码")
                st.code(html_content, language="html")
            with preview_col:
                st.caption("预览效果")
                st.markdown(f"""
                <div style="
                    background: white;
                    border-radius: 12px;
                    padding: 16px;
                    max-height: 400px;
                    overflow-y: auto;
                    border: 1px solid #eee;
                ">{html_content}</div>
                """, unsafe_allow_html=True)
        
        if st.session_state.get('show_card', False):
            st.markdown("#### 🃏 卡片文本（前5条）")
            articles = selected_articles.to_dict('records')
            txt_content = generate_card_txt(articles, max_count=5)
            st.code(txt_content, language=None)
            if st.button("💾 保存为 news_articles.txt"):
                save_card_txt(articles, "news_articles.txt", max_count=5)
                st.success("✅ 已保存！运行 `python card_generator.py` 生成图片")
        
        if st.session_state.get('show_copy', False):
            st.markdown("#### 💬 社群早报文案")
            with st.spinner("🤖 AI 正在生成文案..."):
                articles = selected_articles.to_dict('records')
                other_df = saved_df[saved_df["人工审核"] != "入库"]
                other_titles = other_df["标题"].tolist() if not other_df.empty else []
                result = generate_community_copy(articles[:5], other_titles)
            
            if result.get("success"):
                full_copy = result.get("copy", "")
                copy_only = result.get("copy_only", "")
                
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #fdfaf7 0%, #faf6f2 100%);
                    border-radius: 16px;
                    padding: 20px 24px;
                    border-left: 4px solid #b85c38;
                    margin-bottom: 16px;
                ">
                    <p style="font-size: 15px; line-height: 1.8; color: #444; margin: 0;">{copy_only}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"> {result.get('guide', '')}")
                st.text_area("复制完整文案", full_copy, height=100)
                st.caption(f"📊 正文 {len(copy_only)} 字")
                
                with st.expander("🔍 AI 分析"):
                    st.markdown(result.get("analysis", ""))
            else:
                st.error(f"❌ {result.get('error', '生成失败')}")
