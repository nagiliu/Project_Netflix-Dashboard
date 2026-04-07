import streamlit as st
import pandas as pd
import plotly.express as px
import tmdbsimple as tmdb
import time

# 初始化 API (建議改用 st.secrets)
tmdb.API_KEY = '4939ea562d668d06c3a45cfe5c71c620'

@st.cache_data(show_spinner="正在從 TMDb 獲取影視資訊...")
def get_content_details(title):
    try:
        search = tmdb.Search()
        # 搜尋電影
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
            
            # 修正：實例化物件後再取得資訊
            if is_tv:
                target_obj = tmdb.TV(item_id)
                credits = target_obj.credits()
                date = item.get('first_air_date', '未知')[:4]
            else:
                target_obj = tmdb.Movies(item_id)
                credits = target_obj.credits()
                date = item.get('release_date', '未知')[:4]
            
            cast = [p['name'] for p in credits.get('cast', [])[:3]]
            return {
                'name_tw': item.get('title') or item.get('name'),
                'poster': f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get('poster_path') else None,
                'year': date,
                'cast': "、".join(cast) if cast else "暫無資料"
            }
    except Exception as e:
        # 記錄錯誤但不要讓程式中斷
        print(f"Error fetching {title}: {e}")
    
    return {'name_tw': title, 'poster': None, 'year': '未知', 'cast': '暫無資料'}

@st.cache_data
def load_and_process_data():
    # 建議加上 try-except 確保檔案存在
    try:
        df = pd.read_excel("netflix_data.xlsx")
    except FileNotFoundError:
        st.error("找不到 netflix_data.xlsx，請確認檔案路徑。")
        st.stop()

    latest_week = df['week'].max()
    df_now = df[df['week'] == latest_week].copy()
    
    # 抓取最高週數
    df_max = df.groupby('show_title')['cumulative_weeks_in_top_10'].max().reset_index()
    plot_data = pd.merge(df_now[['show_title', 'weekly_rank', 'category']], df_max, on='show_title')
    
    # 這裡可以加入一個進度條，提升 UX
    unique_titles = plot_data['show_title'].unique()
    details_list = []
    
    # 批次獲取，這裡若資料量大建議優化
    for t in unique_titles:
        details_list.append(get_content_details(t))
    
    details_df = pd.DataFrame(details_list)
    details_df['search_title'] = unique_titles # 建立 Mapping 用的 key
    
    # 合併資料
    final_df = plot_data.merge(details_df, left_on='show_title', right_on='search_title', how='left')
    return final_df, latest_week

# --- 以下介面程式碼保持大致不變 ---