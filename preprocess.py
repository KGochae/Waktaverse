import pandas as pd
import streamlit as st
import datetime

now = datetime.datetime.now()
now_time = now.strftime('%Y-%m-%d') # 현재 시간을 문자열로 변환한 후 다시 datetime 객체로 변환
today = pd.to_datetime(now_time, format='%Y-%m-%d') # 현재 시간을 datetime 객체로 변환 

week = now - datetime.timedelta(days=now.weekday())
week_start = week.strftime('%m-%d')
month = str(now.strftime('%m'))
year = str(now.strftime('%Y'))


@st.cache_data
def data_diff (data):
    # data = pd.concat(dfs) if dfs else ''
    data = data.sort_values(by=['title', 'down_at'])

    # 날짜 데이터 형태가 'T19:39:21Z' 형식 이라 / 일단 '년월일' 형태의 문자열(str)로 바꾸고 다시 데이트타입으로 바꿔야한다.
    data['publishedAt'] = pd.to_datetime(data['publishedAt']).dt.strftime('%Y-%m-%d')
    data['publishedAt'] = pd.to_datetime(data['publishedAt'], format='%Y-%m-%d')

    data['down_at'] = pd.to_datetime(data['down_at']).dt.strftime('%Y-%m-%d')
    data['down_at'] = pd.to_datetime(data['down_at'], format='%Y-%m-%d')

    # year 과 month 를 구분해주자.
    data['year'] = data['publishedAt'].dt.year.astype(str)
    data['month'] = data['publishedAt'].dt.month.astype(str)

    # video_id가 error 생긴 경우가 있어서 제거
    data = data[data['video_id'] != '#NAME?']
    # data = data[data['playlistId'] != 'PLWTycz4el4t7ZCxkGYyekoP1iBxmOM4zZ'] # all music 은 제외 'PLWTycz4el4t7ZCxkGYyekoP1iBxmOM4zZ   
    data.loc[data['playlist_title'].str.contains('우왁굳'),'playlist_title'] = '우왁굳(연공전/똥겜 etc)' 

    # 전일 대비 조회수및 좋아요 컬럼
    data['prev_view_count'] = data.groupby(['playlist_title','video_id'])['view_count'].shift()
    data['prev_like_count'] = data.groupby(['playlist_title','video_id'])['like_count'].shift()

    # 하루전에 upload되고 조회수가 집계가 안된경우, 이전 조회수가 null값이 아닌 0으로 오게한다.  
    data.loc[(data['down_at'] - data['publishedAt'] ).dt.days == 1, 'prev_view_count'] = 0
    data.loc[(data['down_at'] - data['publishedAt'] ).dt.days == 1, 'prev_like_count'] = 0

    data['view_count_diff'] = data['view_count'] - data['prev_view_count']
    data['like_count_diff'] = data['like_count'] - data['prev_like_count']


    # 재생목록 제목들을 저장
    playlist_titles = data['playlist_title'].unique().tolist()
    playlist_titles.sort(reverse=True)

    # 구독자수 변화 (8월 2일 부터 측정 시작)
    subscribe = data[data['subscribe'].notna()][['subscribe','down_at']].drop_duplicates() 
    # subscribe['down_at'] = pd.to_datetime(subscribe['down_at']).dt.strftime('%Y-%m-%d')  # nivo 그래프에 표현하려면 date가 str 이어야한다.
    subscribe['down_at'] = pd.to_datetime(subscribe['down_at'], format='%Y-%m-%d')  

    subscribe['prev_subscribe'] = subscribe['subscribe'].shift()
    subscribe['subscribe_diff'] = subscribe['subscribe'] - subscribe['prev_subscribe']
    subscribe['week_start'] = subscribe['down_at'] - pd.to_timedelta(subscribe['down_at'].dt.dayofweek, unit='d')
    subscribe.groupby('week_start')['subscribe_diff'].sum().reset_index()    
    subscribe_week = subscribe.groupby('week_start').agg({'subscribe_diff': 'sum'}).reset_index()
    subscribe_week['week_start'] = pd.to_datetime(subscribe_week['week_start']).dt.strftime('%Y-%m-%d')
    
    return data, playlist_titles, subscribe, subscribe_week




def total_diff(merged_df,playlist_titles):
    # 재생목록별 조회수, 구독자
    total_diff = pd.DataFrame()    
    for playlist_title in playlist_titles:
        test_df = merged_df[merged_df['playlist_title'] == playlist_title].copy()
        total_diff = pd.concat([total_diff, test_df])

    total_diff.loc[total_diff['playlist_title'].str.contains('YOUTUBE|이세여고|OFFICIAL'), 'playlist_title'] = 'ISEGYE IDOL (예능)' # 이세돌 카테고리 통합
    total_diff.loc[total_diff['playlist_title'].str.contains('MIDDLE|GOMEM'),'playlist_title'] = 'WAKTAVERSE : GOMEM ' 
    total_diff.loc[total_diff['video_id'].isin(['JY-gJkMuJ94', 'fgSXAKsq-Vo']), 'playlist_title'] = 'ISEGYE IDOL : MUSIC'

    total_diff = total_diff[total_diff['playlist_title'] != 'ALL : MUSIC (최신순)']
    total_diff = total_diff.drop_duplicates(subset=['down_at', 'video_id'])

@st.cache_data
def hot_video(merged_df,playlist_titles, year, month): 

    total_diff = pd.DataFrame()    
    
    for playlist_title in playlist_titles:
        test_df = merged_df[merged_df['playlist_title'] == playlist_title].copy()
        total_diff = pd.concat([total_diff, test_df])

    total_diff.loc[total_diff['playlist_title'].str.contains('YOUTUBE|이세여고|OFFICIAL'), 'playlist_title'] = 'ISEGYE IDOL (예능)' # 이세돌 카테고리 통합
    total_diff.loc[total_diff['playlist_title'].str.contains('MIDDLE|GOMEM'),'playlist_title'] = 'WAKTAVERSE : GOMEM ' 
    total_diff.loc[total_diff['video_id'].isin(['JY-gJkMuJ94', 'fgSXAKsq-Vo']), 'playlist_title'] = 'ISEGYE IDOL : MUSIC'

    total_diff = total_diff[total_diff['playlist_title'] != 'ALL : MUSIC (최신순)']
    total_diff = total_diff.drop_duplicates(subset=['down_at', 'video_id'])

    hot_column = ['playlist_title','video_id', 'title','view_count_diff','like_count_diff','view_like_sum']
    # today
    total_diff = total_diff.drop_duplicates(subset=['down_at', 'video_id','playlist_title'], keep='first')  # 한영상에 재생목록이 두개 이상 들어간 경우가 있다.
    total_diff['view_like_sum'] = total_diff['view_count_diff'] + total_diff['like_count_diff']

    today_hot = total_diff[total_diff['down_at'] == total_diff['down_at'].max()] # 가장최근에 다운 받은 날짜   
    today_hot_enter = today_hot[today_hot['playlist_title'].isin(['WAKTAVERSE : GOMEM ', 'ISEGYE IDOL (예능)'])].drop_duplicates(subset='video_id')
    today_hot_music = today_hot[today_hot['playlist_title'].isin(["WAKTAVERSE : MUSIC", 'ISEGYE IDOL : MUSIC'])].drop_duplicates(subset='video_id')

    top3_videos = today_hot_enter.nlargest(3, 'view_like_sum')[hot_column]
    top3_music = today_hot_music.nlargest(3, 'view_like_sum')[hot_column]

    # week
    total_diff['down_at'] = pd.to_datetime(total_diff['down_at'], format='%Y-%m-%d') 
    total_diff['week_start'] = total_diff['down_at'] - pd.to_timedelta(total_diff['down_at'].dt.dayofweek, unit='d')

    weekly_df = total_diff.groupby(['playlist_title','video_id','title','week_start'])[['view_count_diff', 'like_count_diff','view_like_sum']].sum().reset_index()    
    weekly_df['week_start'] = pd.to_datetime(weekly_df['week_start']).dt.strftime('%m-%d')


    weekly_hot = weekly_df[weekly_df['week_start'] == weekly_df['week_start'].max()] # 이번주를 보고싶다면     
    weekly_hot_enter = weekly_hot[weekly_hot['playlist_title'].isin(['WAKTAVERSE : GOMEM ', 'ISEGYE IDOL (예능)'])]
    weekly_hot_music = weekly_hot[weekly_hot['playlist_title'].isin(["WAKTAVERSE : MUSIC", 'ISEGYE IDOL : MUSIC'])]

    top3_videos_week = weekly_hot_enter.nlargest(3, 'view_like_sum')[hot_column]
    top3_music_week = weekly_hot_music.nlargest(3, 'view_like_sum')[hot_column]

    # month

    monthly_df = total_diff.groupby(['playlist_title', 'video_id', 'title','year','month'])[['view_count_diff','like_count_diff','view_like_sum']].sum().reset_index()
    monthly_df = monthly_df[(monthly_df['year']== year) & (monthly_df['month']== month[1:2])] # 현재년도 현재 월

    monthly_hot_enter = monthly_df[monthly_df['playlist_title'].isin(['WAKTAVERSE : GOMEM ', 'ISEGYE IDOL (예능)'])].drop_duplicates(subset='video_id')
    monthly_hot_music = monthly_df[monthly_df['playlist_title'].isin(["WAKTAVERSE : MUSIC", 'ISEGYE IDOL : MUSIC'])].drop_duplicates(subset='video_id')

    top3_videos_month = monthly_hot_enter.nlargest(3, 'view_like_sum')[hot_column]
    top3_music_month = monthly_hot_music.nlargest(3, 'view_like_sum')[hot_column]

    return total_diff, top3_videos,top3_music, top3_videos_week, top3_music_week, top3_videos_month, top3_music_month


