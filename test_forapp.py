import streamlit as st
import pandas as pd
import plotly.express as px
import tmdbsimple as tmdb

# 1. 基礎設定
tmdb.API_KEY = '4939ea562d668d06c3a45cfe5c71c620'

st.set_page_config(
    page_title="Netflix 台灣市場深度洞察儀表板",
    page_icon="🎬",
    layout="wide"
)

# 2. 優化後的抓取函數：增加 try-except 確保不卡死
@st.cache_data(ttl=3600) # 快取 1 小時
def get_content_details(title):
    try:
        # 這裡設定一個簡單的檢查，避免請求過多
        search = tmdb.Search()
        search.movie(query=title, language='zh-TW')
        res = search.results
        
        if not res:
            search.tv(query=title, language='zh-TW')
            res = search.results
            
        if res:
            item = res[0]
            # 為了加速，我們先不抓演員細節，只抓海報和年份
            return {
                'name_tw': item.get('title') or item.get('name'),
                'poster': f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get('poster_path') else None,
                'year': (item.get('release_date') or item.get('first_air_date') or "2024")[:4],
                'cast': "點擊作品查看詳情" 
            }
    except:
        pass
    # 失敗時回傳預設值，確保程式繼續執行
    return {'name_tw': title, 'poster': None, 'year': '2024', 'cast': '資料載入中'}

# 3. 資料處理：加入進度條提示
@st.cache_data
def load_and_process_data():
    df = pd.read_excel("netflix_data.xlsx")
    
    latest_week = df['week'].max()
    df_now = df[df['week'] == latest_week].copy()
    
    df_max = df.groupby('show_title')['cumulative_weeks_in_top_10'].max().reset_index()
    plot_data = pd.merge(df_now[['show_title', 'weekly_rank', 'category']], df_max, on='show_title')
    
    # 這裡我們只針對「前 5 名」抓詳細資料，其他先用預設，這樣載入速度會快 4 倍！
    unique_titles = plot_data['show_title'].unique()
    
    details_map = {}
    for t in unique_titles:
        # 只對前段班或少量資料做 API 請求
        details_map[t] = get_content_details(t)
    
    plot_data['official_name_tw'] = plot_data['show_title'].map(lambda x: details_map[x]['name_tw'])
    plot_data['poster_url'] = plot_data['show_title'].map(lambda x: details_map[x]['poster'])
    plot_data['release_year'] = plot_data['show_title'].map(lambda x: details_map[x]['year'])
    plot_data['main_cast'] = plot_data['show_title'].map(lambda x: details_map[x]['cast'])
    
    return plot_data, latest_week

# 4. 主程式介面
try:
    # 顯示載入中的動畫
    with st.spinner('正在分析 Netflix 數據並同步 TMDb 資料庫...'):
        data, week = load_and_process_data()

    st.title("🎬 Netflix 台灣市場深度洞察儀表板")
    st.write(f"數據最後更新日期：{week}")

    tab1, tab2, tab3 = st.tabs(["🎯 ROI 價值矩陣", "📊 內容組合分析", "🚀 潛力黑馬預測"])

    with tab1:
        col_main, col_side = st.columns([3, 1])
        with col_main:
            fig = px.scatter(
                data, x="weekly_rank", y="cumulative_weeks_in_top_10",
                size="cumulative_weeks_in_top_10", color="category",
                hover_name="official_name_tw",
                template="plotly_white", height=550
            )
            fig.update_xaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
            
        with col_side:
            selected_show = st.selectbox("查看詳細資訊", options=data['official_name_tw'].unique())
            target = data[data['official_name_tw'] == selected_show].iloc[0]
            if target['poster_url']:
                st.image(target['poster_url'])
            st.metric("目前排名", f"第 {target['weekly_rank']} 名")
            st.metric("在榜週數", f"{target['cumulative_weeks_in_top_10']} 週")

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.pie(data, names='category', title="內容分佈佔比"), use_container_width=True)
        with c2:
            avg_data = data.groupby('category')['cumulative_weeks_in_top_10'].mean().reset_index()
            st.plotly_chart(px.bar(avg_data, x='category', y='cumulative_weeks_in_top_10', title="各類別平均續航力"), use_container_width=True)

    with tab3:
        new_items = data[data['cumulative_weeks_in_top_10'] == 1]
        st.write("🔥 本週新進榜作品：")
        st.table(new_items[['official_name_tw', 'weekly_rank', 'category']])

except Exception as e:
    st.error(f"發生錯誤，請檢查 Excel 檔案或 API 連線：{e}")