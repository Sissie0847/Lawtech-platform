import streamlit as st
import pandas as pd
import os
from publish_feishu import FeishuPublisher, test_connection
from wechat_format import generate_wechat_html
from card_export import generate_card_txt

# 页面设置
st.set_page_config(page_title="法律科技运营台", layout="wide")
st.title("⚖️ 法律科技资讯 · 智能运营台")

CSV_FILE = "news_database.csv"

# === 加载数据函数 ===
def load_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        return pd.DataFrame()

# === 保存数据函数 ===
def save_data(df):
    df.to_csv(CSV_FILE, index=False)
    st.toast("✅ 数据已保存！", icon="💾")

# === 主界面：编辑表格 ===
st.subheader("📝 今日资讯审阅")

if not os.path.exists(CSV_FILE):
    st.warning("⚠️ 还没有数据，请先运行 fetch.py 进行进货！")
    st.stop()

# 读取数据
df = load_data()

# 修复历史数据中的空值问题
if "人工审核" in df.columns:
    df["人工审核"] = df["人工审核"].fillna("待审核")
    df["人工审核"] = df["人工审核"].replace("", "待审核")

# --- 核心：可编辑的超级表格 ---
edited_df = st.data_editor(
    df,
    column_config={
        "人工审核": st.column_config.SelectboxColumn(
            "✅ 人工审核", 
            options=["入库", "垃圾", "待审核"], 
            default="待审核",
            required=True,
            width="small"
        ),
        "发布顺序": st.column_config.NumberColumn(
            "📋 顺序",
            help="填写数字决定发布顺序，不填则按评分排序",
            min_value=1,
            max_value=99,
            step=1,
            width="small"
        ),
        "AI分类": st.column_config.SelectboxColumn(
            "🤖 AI推荐", 
            options=["强烈推荐", "推荐", "一般", "不推荐"], 
            width="small"
        ),
        "AI理由": st.column_config.TextColumn("💡 AI理由", width="medium"),
        "标题": st.column_config.TextColumn("标题", width="medium"),
        "原文内容": st.column_config.TextColumn("内容预览", width="large"),
        "链接": st.column_config.LinkColumn("原文"),
    },
    hide_index=True,
    num_rows="dynamic",
    height=600
)

# === 操作按钮区 ===
col1, col2, col3 = st.columns([1, 1, 4])

with col1:
    if st.button("💾 保存所有修改", type="primary"):
        save_data(edited_df)
        st.rerun()  # 刷新页面以更新侧边栏

with col2:
    if st.button("🗑️ 清理垃圾数据"):
        cleaned_df = edited_df[edited_df["人工审核"] != "垃圾"]
        deleted_count = len(edited_df) - len(cleaned_df)
        if deleted_count > 0:
            save_data(cleaned_df)
            st.toast(f"✅ 已删除 {deleted_count} 条垃圾数据！", icon="🗑️")
            st.rerun()
        else:
            st.toast("没有标记为「垃圾」的数据", icon="ℹ️")

# === 侧边栏：导出功能 ===
with st.sidebar:
    st.header("📤 发布周报")
    
    st.caption("💡 修改审核状态后，请先点击「保存所有修改」")
    
    # 期号输入
    vol_number = st.text_input("📌 期号", placeholder="例如: 12", help="输入本期周报的期号")
    
    # 获取入库文章（从已保存的 CSV 读取）
    saved_df = load_data()
    if not saved_df.empty and "人工审核" in saved_df.columns:
        selected_articles = saved_df[saved_df["人工审核"] == "入库"].copy()
        article_count = len(selected_articles)
        
        # 排序逻辑：手动顺序优先，评分兜底
        if article_count > 0:
            # AI分类转换为数字用于排序（强烈推荐=1, 推荐=2, 一般=3, 不推荐=4）
            ai_order = {"强烈推荐": 1, "推荐": 2, "一般": 3, "不推荐": 4}
            selected_articles["_ai_order"] = selected_articles["AI分类"].map(ai_order).fillna(3)
            
            # 发布顺序：有值的排在前面，没值的按评分和AI分类排序
            selected_articles["_sort_order"] = selected_articles["发布顺序"].fillna(999)
            selected_articles = selected_articles.sort_values(
                by=["_sort_order", "_ai_order", "评分"],
                ascending=[True, True, False]
            )
            # 删除临时排序列
            selected_articles = selected_articles.drop(columns=["_sort_order", "_ai_order"])
    else:
        selected_articles = pd.DataFrame()
        article_count = 0
    
    st.info(f"📊 已选择 **{article_count}** 篇文章待发布")
    
    # 预览按钮
    if st.button("👁️ 预览周报内容"):
        if article_count == 0:
            st.error("⚠️ 还没有标记为「入库」的文章！")
        else:
            st.markdown("---")
            st.markdown(f"### vol.{vol_number or 'X'}｜LawGeek法律科技周报")
            st.caption("💡 提示：填写「顺序」列可手动调整文章排序")
            st.markdown("---")
            for i, (_, row) in enumerate(selected_articles.iterrows(), 1):
                order_info = f" (手动排序: {int(row['发布顺序'])})" if pd.notna(row.get('发布顺序')) else ""
                st.markdown(f"**{i:02d} {row['标题']}**{order_info}")
                content = row.get('原文内容', '') or row.get('AI总结', '')
                if content:
                    st.markdown(str(content)[:200] + "..." if len(str(content)) > 200 else str(content))
                if row.get('链接'):
                    st.markdown(f"[来源链接]({row['链接']})")
                st.markdown("---")
    
    st.markdown("---")
    
    # 发布按钮区
    col_feishu, col_wechat, col_card = st.columns(3)
    
    with col_feishu:
        if st.button("🚀 发布到飞书", type="primary", use_container_width=True):
            if not vol_number:
                st.error("⚠️ 请输入期号！")
            elif article_count == 0:
                st.error("⚠️ 还没有标记为「入库」的文章！")
            else:
                with st.spinner("正在发布到飞书..."):
                    try:
                        publisher = FeishuPublisher()
                        articles = selected_articles.to_dict('records')
                        doc_id, doc_url = publisher.publish_weekly_report(vol_number, articles)
                        
                        st.success("🎉 发布成功！")
                        st.markdown(f"📄 [点击查看文档]({doc_url})")
                        st.code(doc_url, language=None)
                        st.balloons()
                    except Exception as e:
                        st.error(f"❌ 发布失败: {str(e)}")
    
    with col_wechat:
        if st.button("📱 生成公众号", use_container_width=True):
            if article_count == 0:
                st.error("⚠️ 还没有标记为「入库」的文章！")
            else:
                st.session_state['show_wechat_html'] = True
                st.session_state['show_card_txt'] = False
    
    with col_card:
        if st.button("🃏 导出卡片", use_container_width=True):
            if article_count == 0:
                st.error("⚠️ 还没有标记为「入库」的文章！")
            else:
                st.session_state['show_card_txt'] = True
                st.session_state['show_wechat_html'] = False
    
    # 公众号 HTML 展示区
    if st.session_state.get('show_wechat_html', False):
        st.markdown("---")
        st.subheader("📱 公众号排版内容")
        st.caption("复制下方 HTML 代码，粘贴到公众号编辑器即可")
        
        articles = selected_articles.to_dict('records')
        html_content = generate_wechat_html(articles, vol_number or "X")
        
        # 显示 HTML 代码（可复制）
        st.code(html_content, language="html")
        
        # 预览效果
        with st.expander("👁️ 预览效果（大致样式）"):
            st.markdown(html_content, unsafe_allow_html=True)
        
        if st.button("✅ 关闭公众号内容"):
            st.session_state['show_wechat_html'] = False
            st.rerun()
    
    # 卡片 TXT 展示区
    if st.session_state.get('show_card_txt', False):
        st.markdown("---")
        st.subheader("🃏 卡片内容（前5条）")
        st.caption("复制下方内容用于卡片自动化")
        
        articles = selected_articles.to_dict('records')
        txt_content = generate_card_txt(articles, max_count=5)
        
        # 显示 TXT 内容（可复制）
        st.code(txt_content, language=None)
        
        # 显示导出数量
        export_count = min(5, len(articles))
        st.info(f"📊 已导出 {export_count} 条文章")
        
        if st.button("✅ 关闭卡片内容"):
            st.session_state['show_card_txt'] = False
            st.rerun()
    
    # 测试连接
    st.markdown("---")
    with st.expander("🔧 飞书连接测试"):
        if st.button("测试连接"):
            success, message = test_connection()
            if success:
                st.success(message)
            else:
                st.error(message)

