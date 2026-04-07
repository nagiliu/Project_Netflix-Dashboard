import streamlit as st
import pandas as pd
import plotly.express as px
import tmdbsimple as tmdb

# 1. API 與基礎設定
tmdb.API_KEY = '4939ea562d668d06c3a45cfe5c71c620'

st.set_page_config(
    page_title="Netflix 台灣市場深度洞察儀表板",
    page_icon="🎬",
    layout="wide"
)

# 2. 詳情獲取函數 (恢復抓取年份與演員，並加上快取提升載入速度)
@st.cache_data(ttl=3600)
def get_content_details(title):
    try:
        search = tmdb.Search()
        search.movie(query=title, language='zh-TW')
        res = search.results
        is_tv = False
        if not res:
            search.tv(query=title, language='zh-TW')
            res = search.results
            is_tv = True
            
        if res:
            item = res[0]
            item_id = item['id']
            if is_tv:
                detail = tmdb.TV(item_id).credits()
                date = item.get('first_air_date', '未知')[:4]
            else:
                detail = tmdb.Movies(item_id).credits()
                date = item.get('release_date', '未知')[:4]
            
            cast = [person['name'] for person in detail.get('cast', [])[:3]]
            return {
                'name_tw': item.get('title') or item.get('name'),
                'poster': f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get('poster_path') else None,
                'year': date,
                'cast': "、".join(cast) if cast else "資料載入中"
            }
    except:
        pass
    return {'name_tw': title, 'poster': None, 'year': '未知', 'cast': '暫無資料'}

# 3. 資料處理 (確保變數定義正確)
@st.cache_data
def load_and_process_data():
    try:
        df = pd.read_excel("netflix_data.xlsx").tail(100000)
        latest_week = df['week'].max()
        df_now = df[df['week'] == latest_week].copy()
        
        # 取得歷史最高累積週數
        df_max = df.groupby('show_title')['cumulative_weeks_in_top_10'].max().reset_index()
        plot_data = pd.merge(df_now[['show_title', 'weekly_rank', 'category']], df_max, on='show_title')
        
        # 只針對當週前 20 名做 API 抓取，提升效能
        unique_titles = plot_data['show_title'].unique()
        details_list = [get_content_details(t) for t in unique_titles]
        details_df = pd.DataFrame(details_list)
        details_df['search_key'] = unique_titles
        
        return plot_data.merge(details_df, left_on='show_title', right_on='search_key', how='left'), latest_week
    except Exception as e:
        st.error(f"資料處理失敗：{e}")
        return None, None

# 4. 介面呈現 (恢復原本的三頁籤設計)
try:
    data, week = load_and_process_data()
    
    st.title("🎬 Netflix 台灣市場深度洞察儀表板")
    st.caption(f"數據最後更新日期：{week}")

    tab1, tab2, tab3 = st.tabs(["🎯 ROI 價值矩陣", "📊 內容組合分析", "🚀 潛力黑馬預測"])

    # --- Tab 1: 核心矩陣 ---
    with tab1:
        col_main, col_side = st.columns([3, 1])
        with col_main:
            st.subheader("內容價值象限圖")
            fig = px.scatter(
                data, x="weekly_rank", y="cumulative_weeks_in_top_10",
                size="cumulative_weeks_in_top_10", color="category",
                hover_name="name_tw",
                labels={"weekly_rank": "當週排名", "cumulative_weeks_in_top_10": "累積進榜週數"},
                template="plotly_white", height=550
            )
            fig.update_xaxes(autorange="reversed", tickmode='linear', dtick=1)
            st.plotly_chart(fig, use_container_width=True)
            
        with col_side:
            st.subheader("📺 作品詳情")
            selected_show = st.selectbox("搜尋或選擇作品", options=data['name_tw'].unique())
            target = data[data['name_tw'] == selected_show].iloc[0]
            
            if target['poster']:
                st.image(target['poster'], use_container_width=True)
            st.markdown(f"**📅 出版年份：** {target['year']}")
            st.markdown(f"**🎭 主要演員：** {target['cast']}")
            st.markdown(f"**🏆 目前排名：** 第 {target['weekly_rank']} 名")
            st.markdown(f"**⏳ 累積週數：** {target['cumulative_weeks_in_top_10']} 週")

    # --- Tab 2: 結構分析 ---
    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("內容佔比 (Films vs TV)")
            st.plotly_chart(px.pie(data, names='category', hole=0.4), use_container_width=True)
        with c2:
            st.subheader("各類別平均續航力 (週數)")
            res_data = data.groupby('category')['cumulative_weeks_in_top_10'].mean().reset_index()
            st.plotly_chart(px.bar(res_data, x='category', y='cumulative_weeks_in_top_10', color='category'), use_container_width=True)

    # --- Tab 3: 黑馬預測 ---
    with tab3:
        st.subheader("🔥 本週空降新進榜作品")
        new_items = data[data['cumulative_weeks_in_top_10'] == 1].sort_values('weekly_rank')
        if not new_items.empty:
            st.dataframe(new_items[['name_tw', 'weekly_rank', 'category', 'year', 'cast']], use_container_width=True)
            st.success("這些是剛進榜的新面孔，若排名靠前，極具成為未來明星作品的潛力。")
        else:
            st.info("本週無新進榜作品，榜單結構相對穩定。")

except Exception as e:
    st.error(f"發生錯誤：{e}")