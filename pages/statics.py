import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly as plt


from sklearn.preprocessing import StandardScaler
from statsmodels.formula.api import ols

from yout import get_all_playlist_videos_wak,get_channel_id,get_playlist,get_all_playlist_videos,video_duration
from googleapiclient.discovery import build
import plotly.express as px

import isodate
from yout import benfit_cal
from streamlit_elements import dashboard
from streamlit_elements import nivo, elements, mui
from PIL import Image



st.header(" Waktaverse Statics ")
pd.set_option('mode.chained_assignment',  None)
css='''
    <style>
        section.main > div {max-width:90rem;
                            padding-top: 5rem;
                            padding-bottom: 0rem;
                                }
                            
    </style>
    '''
st.markdown(css, unsafe_allow_html=True)


# ------------------- 각 영상의 playlist_title를 추가하기 위해서 playlist 별 영상과 최근 영상 두개의 방법으로 가져와야함 

# with st.form(key='searchform_channel'):
#     st.caption('''최근영상순 혹은 재생목록 별로 영상을 가져올 수 있습니다.''')
#     sort_option_side = st.selectbox("select", ["재생목록별"], key='side_sort_option')
#     submit_search = st.form_submit_button("검색")

# # ------------------ 재생목록별로 영상을 수집할 때 (최근 재생목록이 아님, 50개까지 가능)

# if submit_search and sort_option_side == "재생목록별": 
#     channel_name = 'waktaverse'
#     channel_Id= get_channel_id(api_key, channel_name)
#     playlist, playlist_ids = get_playlist(channel_Id, api_key)
#     video_df, video_ids = get_all_playlist_videos(playlist_ids, api_key)

#     st.session_state.video_df = video_df
#     st.session_state.playlist = playlist

# if hasattr(st.session_state, 'video_df'):
#     video_df = st.session_state.video_df

#     video_df = video_df[video_df['playlistId'] != 'PLWTycz4el4t7ZCxkGYyekoP1iBxmOM4zZ']    
#     video_df = video_df.drop_duplicates(subset='video_id', keep='first')
#     st.write(video_df)

# if hasattr(st.session_state, 'playlist'):
#     playlist = st.session_state.playlist 
#     wakta_pli = video_df.merge(playlist, on='playlistId', how='left')
#     wakta_pli.to_csv('wakta_pli.csv', index=False)

#     st.write(wakta_pli)




# CSV 파일 업로드
uploaded_file = st.sidebar.file_uploader('CSV 파일을 업로드하세요.', type=['csv'])


# 업로드된 파일이 있을 경우에만 처리
if uploaded_file is not None:
    # 업로드된 CSV 파일을 pandas DataFrame으로 읽기
    df = pd.read_csv(uploaded_file)
    df = benfit_cal(df)
    df = df.sort_values(by='benefit', ascending = False).reset_index()
    # df = df[~df['playlist_title'].str.contains('MUSIC')]
    # df = df[df['channel'] == 'waktaverse']

    df.loc[df['playlist_title'].str.contains('연공전|먹방|캠방|핫클립'), 'playlist_title'] = '합방기타컨텐츠'      
    df.loc[df['playlist_title'].str.contains('vr'),'playlist_title'] = 'vrchat'  
    df.loc[df['playlist_title'].str.contains('YOUTUBE|이세여고|OFFICIAL'), 'playlist_title'] = 'ISEGYE_IDOL_예능' # 이세돌 카테고리 통합
    df.loc[df['playlist_title'].str.contains('GOMEM|MIDDLE'), 'playlist_title'] = 'WAKTAVERSE_예능'    
    df.loc[df['playlist_title'].str.contains('MUSIC'), 'playlist_title'] ='WAKTAVERSE_MUSIC'

    df = df[df['playlist_title'].str.contains('MUSIC|마크|똥겜|컨텐츠|노가리|예능|WAKTAVERSE|shorts|vrchat|시리즈')]


    # df = df.drop('id',axis=1)
    df['publishedAt'] = pd.to_datetime(df['publishedAt'])
    df['date'] = df['publishedAt'].dt.date
    df['year'] = df['publishedAt'].dt.year
    df['hour'] = df['publishedAt'].dt.hour

    df = df[df['year'] > 2020]
    df = df.drop(df[df['playlist_title'].isin(['Shorts', '리그오브레전드', '왁튜브 처음 추천'])].index)

    df = df[df['video_id'] !="#NAME?"]
    df['reaction'] = df['like_count'] + df['comment_count']
    
    video_ids = df['video_id'].tolist()

    with st.container():
        col1, col2= st.columns([1,1])
        with col1:
            st.markdown('''
                        ### 💻 분석과제
                        * 좋아요가 많은 영상, 조회수가 많은 영상, 댓글이 많은 영상 특징이뭘까
                        * 조회수가 높으면 그 영상들은 모두 좋아요가 높을까? 
                        * 어떤 재생목록이 인기가 많을까? 
                        * 지금 트렌드는?
                        ''')
  
        with col2:
            st.subheader('업로드별 조회수 차이가 있을까?')
            st.markdown('''
                        * 주업로드 시간은 **15시부터 19시** 하교 시간, 퇴근 타임에 업로드 되고 있다. 
                        * ###### 그렇다면 업로드시간에 따라 조회수 차이가 있을까? 물론, 유투브 영상 특성상 오래된 영상일 수록 누적조회수가 쌓여서 차이를 찾기 어려울 수 있다.
                        * 그래서 모든 데이터를 하지않고 최소한 년도별로 나눠서 두변수간의 차이가 있는지 실험해보자.
                        ''' ) 
    st.divider()

    with st.container():
        col1,_,col2 = st.columns([1.5,0.2,1.5])
        with col1:
            st.subheader('💻업로드 시간') 
            st.caption(''' 형 주로 언제 업로드해?''')      

            year_option = st.selectbox('Select year', ['2023','2022','2021', '2020','ALL'], key='year_option')

            channel_option = st.selectbox('Select channel', ['waktaverse', '우왁굳의게임방송','ALL'],key='channel_option')

            df['year'] = df['publishedAt'].dt.strftime('%Y')
            # filtered_df = df[(df['channel'] == channel_option) & (df['year'] == year_option)]


            if channel_option == 'ALL' and year_option == 'ALL':
                # channel_option과 year_option 모두 'ALL'인 경우, 모든 데이터를 그대로 사용
                filtered_df = df
            elif channel_option == 'ALL':
                # channel_option이 'ALL'인 경우 year_option으로 데이터 필터링
                filtered_df = df[df['year'] == year_option]
            elif year_option == 'ALL':
                # year_option이 'ALL'인 경우 channel_option으로 데이터 필터링
                filtered_df = df[df['channel'] == channel_option]
            else:
                # channel_option과 year_option 모두 특정한 값인 경우, 둘 다 조건으로 데이터 필터링
                filtered_df = df[(df['channel'] == channel_option) & (df['year'] == year_option)]


            grouped = filtered_df.groupby('playlist_title').agg({
                'view_count': ['sum', 'mean'],
                'like_count': ['sum', 'mean'],
                'comment_count': ['sum', 'mean'],
                'cost':['sum','mean'],
                'benefit':['sum','mean'],
                'seconds':'mean',
                'title': 'count'
            }).round(0).reset_index()
            grouped.columns = ['재생목록', '조회수(합)', '조회수(평균)', '좋아요(합)', '좋아요(평균)', '댓글수(합)', '댓글수(평균)',
                               '편집비용(합)','비용(평균)','추정수익(합)','추정수익(평균)','영상길이(평균)', '영상개수']
            grouped = grouped[grouped['영상개수'] > 1]

            hour_counts_by_year = filtered_df.pivot_table(index='hour', columns='year', aggfunc='size', fill_value=0)
            top_100 = filtered_df.nlargest(100, 'view_count')

            st.area_chart(hour_counts_by_year)



 
        with col2:
            
            st.subheader('''
                        🤔카테고리별 조회수, 좋아요, 댓글수의 상관성
                        ''')
            st.caption('x축 조회수 / y축 좋아요수 / 원의 크기는 댓글수를 의미합니다.')
            st.markdown(''' 원하는 재생목록 범주를 더블클릭하면 해당 차트만 보실 수 있습니다. ''' )


            tab1, tab2 = st.tabs(['Chart','Table'])
            with tab1:
                fig = px.scatter(filtered_df, x='view_count', y='like_count', size='comment_count', color='playlist_title', hover_name='title', log_x=True, log_y=True, size_max=60)

                st.plotly_chart(fig, theme="streamlit", use_container_width=True)

            with tab2:
                st.caption(f'''
                            ({year_option} - {channel_option}채널)  Playlist 별 누적 조회수, 좋아요, 댓글수 입니다. 
                            ''')
        
                st.dataframe(grouped)

    # # view_count 열의 데이터를 리스트로 변환
    # view_counts = filtered_df['view_count'].tolist()

    # # 히스토그램 그리기
    # fig = px.histogram(filtered_df, x='view_count', nbins=100, labels={'view_count': 'View Count'},
    #                 title='Distribution of View Count')

    # # 그래프를 streamlit에 표시
    # st.plotly_chart(fig)
    # nivo 차트를 위한 데이터 가공

        
    # st.write(nivo_pie[0])
        


    with st.container():
        col1,col2 = st.columns([1.5,1.5])
        with col1:
            # st.header('2020년 Point ✔️')
            st.subheader('📊 컨텐츠별 조회수/이익/좋아요 비율')
            st.caption('추정이익 = 편집비용 - (CPM * ')
            with st.container():
                col0, col1_1, col2_1, = st.columns([1,2,2])

                with col0:
                    select_option = st.selectbox('year',['2021','2022','2023','all'], key='select_year')
                    if select_option == '2021':
                        years = ['2021']
                    elif select_option == '2022':
                        years = ['2022']
                    elif select_option == '2023':
                        years = ['2023']
                    elif select_option == 'all':
                        years = ['all']

                with col1_1:
                    select_option = st.selectbox('channel' , ['우왁굳의게임방송','waktaverse'], key='select_channel')                                
                    if select_option == '우왁굳의게임방송':
                        channel = '우왁굳의게임방송'
                    elif select_option == 'waktaverse':
                        channel = 'waktaverse'

                with col2_1:
                    static_option = st.selectbox('statics' , ['영상개수','조회수(합)','조회수(평균)','추정이익(합)','추정이익(평균)','시청자반응(합)','시청자반응(평균)'], key='select_stat')
                    # st.caption('* 시청자반응은 좋아요와 댓글수를 합친 값 입니다.')

                    if static_option == '조회수(합)':
                        values = 'view_sum_ratio' 
                    elif static_option == '조회수(평균)':
                        values = 'view_mean_ratio'
                    elif static_option == '추정이익(합)':
                        values = 'benefit_sum_ratio'
                    elif static_option == '추정이익(평균)':
                        values = 'benefit_mean_ratio'            
                    elif static_option == '시청자반응(합)':
                        values = 'reaction_sum_ratio'
                    elif static_option == '시청자반응(평균)':
                        values = 'reaction_mean_ratio'
                    elif static_option == '영상개수':
                        values = 'count'
                


            nivo_pie = []
            for year in years:
                if year == 'all':
                    df_year = df[df['channel'] == channel]
                else:
                    df_year = df[(df['year'] == year) & (df['channel'] == channel)]

                grouped_year = df_year.groupby('playlist_title').agg({
                    'view_count': ['sum', 'mean'],
                    'like_count': ['sum', 'mean'],
                    'comment_count': ['sum', 'mean'],
                    'cost': ['sum', 'mean'],
                    'benefit': ['sum', 'mean'],
                    'reaction': ['sum','mean'],
                    'seconds': 'mean',
                    'title': 'count'
                }).round(0).reset_index()
                grouped_year.columns = ['playlist_title', 'view_sum', 'view_mean', 'like_sum', 'like_mean', 'comment_sum', 'comment_mean',
                                        'cost_sum', 'cost_mean', 'benefit_sum', 'benefit_mean', 'reaction_sum','reaction_mean', 'seconds_mean', 'count']

                grouped_year = grouped_year[grouped_year['count']>5]
                cols = ['view_sum', 'view_mean', 'like_sum', 'like_mean', 'comment_sum', 'comment_mean',
                        'cost_sum', 'cost_mean', 'benefit_sum', 'benefit_mean', 'reaction_sum','reaction_mean', 'seconds_mean', 'count']

                for column in cols:
                    new_column_name = f"{column}_ratio"
                    grouped_year[new_column_name] = round((grouped_year[column] / grouped_year[column].sum()) * 100, 0)

                grouped_year = grouped_year.sort_values(by=values, ascending=False)

                result_list = []
                grouped_year = grouped_year.sort_values(by=values)
                for index, row in grouped_year.iterrows():
                    result_list.append({
                        'id': row['playlist_title'],
                        'value': row[values],
                    })

                nivo_pie.append(result_list)

# --------------------------------------------------------------------------------------------------------------- #

            all_df = df.groupby(['year','playlist_title']).agg({
                'view_count': ['sum', 'mean'],
                'like_count': ['sum', 'mean'],
                'comment_count': ['sum', 'mean'],
                'cost': ['sum', 'mean'],
                'benefit': ['sum', 'mean'],
                'reaction': ['sum','mean'],
                'seconds': 'mean',
                'title': 'count'
            }).round(0).reset_index()
            all_df.columns = ['year', 'playlist_title','view_sum', 'view_mean', 'like_sum', 'like_mean', 'comment_sum', 'comment_mean',
                                    'cost_sum', 'cost_mean', 'benefit_sum', 'benefit_mean', 'reaction_sum','reaction_mean', 'seconds_mean', 'count']

            cols = ['view_sum', 'view_mean', 'like_sum', 'like_mean', 'comment_sum', 'comment_mean',
                    'cost_sum', 'cost_mean', 'benefit_sum', 'benefit_mean', 'reaction_sum','reaction_mean', 'seconds_mean', 'count']

            for column in cols:
                new_column_name = f"{column}_ratio"
                all_df[new_column_name] = round((all_df[column] / all_df[column].sum()) * 100, 0)


            # 데이터프레임을 피벗하여 원하는 형식으로 변환
            pivot_df = all_df.pivot(index="year", columns="playlist_title", values=values).reset_index()
            # 결과를 리스트 형식으로 변환
            pivot_nivo = pivot_df.to_dict(orient="records")

            # 결과 출력
            for item in pivot_nivo:
                item["year"] = int(item["year"])


            with elements("pli_veiw_ration"):
                layout = [
                    dashboard.Item("items1", 0, 0, 4, 2 ),
                    dashboard.Item("items2", 0, 2, 4, 3 )
                ]
                with dashboard.Grid(layout):
                    mui.Box(
                            mui.Typography(f'({year}){select_option} - {static_option}'
                                        if static_option == '영상개수' else f'({year}){select_option} - {static_option} %'
                                        ,variant="h2"
                                        ,sx={'text-align':'center','font-size':'24px','fontWeight': '500'}
                                        ),
                            nivo.Pie(
                                data=nivo_pie[0],
                                margin={"top": 50, "right": 20, "bottom": 50, "left": 80 },
                                sortByValue=True,
                                innerRadius={0.5},
                                padAngle={2},
                                colors= { 'scheme': 'pastel1' }, # pastel1
                                borderWidth={1},
                                borderColor={
                                    "from": 'color',
                                    "modifiers": [
                                        [
                                            'opacity',
                                            0.2
                                        ]
                                    ]
                                },
                                enableArcLinkLabels=True,
                                # arcLabel="id",
                                arcLabelsRadiusOffset={0.5},
                                arcLinkLabelsSkipAngle={3},
                                arcLinkLabelsThickness={1},
                                arcLabelsTextColor="black",
                                arcLabelsSkipAngle={10},
                            legends=[
                                    {
                                    'anchor': 'top-left',
                                    'direction': 'column',
                                    'justify': False,
                                    'translateX': -70,
                                    # 'translateY': -200,
                                    'itemsSpacing': 0,
                                    'itemDirection': 'left-to-right',
                                    'itemWidth': 80,
                                    'itemHeight': 15,
                                    'itemOpacity': 0.75,
                                    'symbolSize': 12,
                                    'symbolShape': 'circle',
                                    'symbolBorderColor': 'rgba(0, 0, 0, .5)',
                                    'effects': [
                                            {
                                            'on': 'hover',
                                            'style': {
                                                'itemBackground': 'rgba(0, 0, 0, .03)',
                                                'itemOpacity': 1
                                                }
                                            }
                                        ]
                                    }
                                ],                                                     
                                theme={
                                    # "background": "#141414",
                                    "textColor": "white",
                                    "tooltip": {
                                        "container": {
                                            "background": "#3a3c4a",
                                            "color": "white",
                                        }
                                    }
                                }
                            ),key="items1" 
                        )
              
                    # mui.Box(                            
                    #         children=[
                    #         mui.Typography(f' 연도별 {static_option}',
                    #                        variant="h2",
                    #                        sx={'font-size':'24px','text-align':'center','fontWeight': '500'}),
                    #         nivo.Bar(
                    #             data=pivot_nivo,
                    #             keys=[
                    #                 "ISEGYE IDOL : 예능",
                    #                 "WAKTAVERSE : MUSIC",
                    #                 "WAKTAVERSE : 예능",
                    #                 "shorts",
                    #                 "vrchat",
                    #                 "노가리",
                    #                 "똥겜",
                    #                 "마크",
                    #                 "합방,시리즈,기타 컨텐츠",
                    #                 ],# 막대 그래프의 그룹을 구분하는 속성
                    #             indexBy="year",  # x축에 표시할 속성

                    #             margin={"top": 20, "right": 30, "bottom": 80, "left": 100},
                    #             padding={0.5},
                    #             innerPadding={2},
                    #             layout="horizontal",
                    #             sortByValue=True,
                    #             valueScale={ "type" : 'linear' },
                    #             indexScale={ "type": 'band', "round": 'true'},
                    #             borderRadius={0},
                    #             colors={ 'scheme': 'pastel1' },
                    #             innerRadius=0,
                    #             padAngle=0.1,
                    #             activeOuterRadiusOffset=8,
                    #             enableGridX= True,
                    #             axisLeft=True,  # Y축 단위 
                        
                    #             labelSkipWidth={40},
                    #             labelSkipHeight={20},

                    #             legends=[
                    #                 {
                    #                 'anchor': 'top-right',
                    #                 'direction': 'column',
                    #                 'justify': False,
                    #                 'translateX': -70,
                    #                 # 'translateY': -200,
                    #                 'itemsSpacing': 0,
                    #                 'itemDirection': 'left-to-right',
                    #                 'itemWidth': 80,
                    #                 'itemHeight': 15,
                    #                 'itemOpacity': 0.75,
                    #                 'symbolSize': 12,
                    #                 'symbolShape': 'circle',
                    #                 # 'symbolBorderColor': 'rgba(0, 0, 0, .5)',
                    #                 'effects': [
                    #                         {
                    #                         'on': 'hover',
                    #                         'style': {
                    #                             'itemBackground': 'rgba(0, 0, 0, .03)',
                    #                             'itemOpacity': 1
                    #                             }
                    #                         }
                    #                     ]
                    #                 }
                    #             ],    
                    #             theme={
                    #                     # "background": "white",
                    #                     "textColor": "white",
                    #                     "tooltip": {
                    #                         "container": {
                    #                             "background": "#3a3c4a",
                    #                             "color": "white",
                    #                         }
                    #                     }
                    #                 }                         
                    #             )
                    #         ] 
                    #     ,key = 'items2',sx={'background-color':'#3a3c4a','borderRadius':'5%'})
                        

                    # st.subheader('컨텐츠별 시청자 반응 비율(좋아요,댓글)')
                    # st.subheader('컨텐츠별 예상이익 비율')

            with st.expander("See DATA"):
                st.write(grouped_year)

        with col2:
            with st.container():
                tab1, tab2 = st.tabs(['추정수익 정의','EDA 요약'])
            with tab1:
                st.subheader('📝 예상수익이 높은 컨텐츠 top3')
                st.caption('예상 수익의 경우 아래와 같은 공식으로 계산 되었습니다. 말그대로 예상 수익입니다. 정확한 편집 비용, 광고 종류/노출횟수를 알 수 없기 때문에 오차가 있습니다.')
                # with st.expander('계산공식'):
                st.markdown('''                     
                                > 수익과 비용은 아래의 가정하에 산출하였습니다.
                                > * 10명중 6명이 광고를 봤다.
                                > * CPM = 2022년 기준 3500원
                                > * 유튜브 광고 수익 = 3500 * (조회수 * 0.6) / 1000) * 0.55(수수료)
                                > * 편집비용 = 분당 30,000원                    
                                > * 비용은 편집비용만 고려하였으며 30분이상인 경우 풀영상으로 파악하여 비용을 100,000원으로 고정                                                                                                       
                                ''')
                
                # st.markdown('''
                # ## 2020년 Point ✔️  
                #     - 수익면, 시청자반응, 조회수 총3개의 주제로 측정해 보았습니다.
                # ----
                # ##### 혜자 컨텐츠 - 합방,시리즈,기타 컨텐츠  + VRchat
                # > 시청자반응(좋아요+댓글) 

                # * 과거 왁카데미에 더나아가, 컨셉을 갖고있는 '멤버'를 본격적으로 뽑기 시작함으로써 `합방` 시너지가 굉장히 높아졌다. (물론, 컨셉이 없어도된다.)
                # * 사실상 `본캐와 부캐`라는 컨텐츠를 2020년 부터 시작한것이다. 이 사람들이 실제 뭐하는 사람인지 몰라서 더 재밌다. 그래서 컨텐츠에 몰입하게 만드는 효과가 있다.
                # * 주로 `Vrchat` 을 이용한 컨텐츠이며 대표적으로 '상황극'이 있다.
                            
                                        
                # ----
                # ##### 가성비 부분 - 먹방/캠방 
                # * `먹방/캠방` 의 경우 주컨텐츠인 `마크, vrchat, 노가리`와 비교했을 때  모두 :blue[상위권]에 속한다.
                # * 평균 조회수를 비교했을 때  
                #             \
                # vrchat 👉 먹방/캠방 👉 노가리 👉 마크 순으로 무려 :blue[2위]이며
                # * 평균 좋아요(16,298) :blue[2위], 평균 댓글수(2,153)는 :blue[1위] 이다.
                # * 일단 보이지 않던게 실제 화면에 보이니 반응이 좋을 수 밖에 없다. \
                #     (우왁굳이 캠을켜? 맛있다.
                            

                # ---- ''')
            with tab2:
                st.caption('수익에 가장 영향을주는 컨텐츠 다중회귀분석')


    st.divider()

    with st.container():
        st.header('수익이 높은 컨텐츠라고 해서 시청자들의 반응도 높을까?🤔?')

        
        df_encoded = pd.get_dummies(df, columns=['playlist_title'], prefix=['pli'])
        variables_to_normalize = ['seconds', 'view_count', 'like_count', 'comment_count', 'benefit','reaction']

        # 표준화 (Standardization)
        scaler = StandardScaler()
        df_encoded[variables_to_normalize] = scaler.fit_transform(df_encoded[variables_to_normalize])

        var = ['seconds', 'view_count', 'like_count', 'comment_count', 'benefit','reaction']

        # 연속형 변수에 로그 변환 적용
        df_encoded[var] = np.log1p(df_encoded[var])

        summary_benefit = ols('benefit ~ seconds + reaction  + pli_ISEGYE_IDOL_예능 + pli_WAKTAVERSE_예능 + pli_shorts + pli_vrchat + pli_노가리 + pli_똥겜 + pli_마크 + pli_합방기타컨텐츠', df_encoded).fit().summary()
        summary_reaction= ols('reaction ~ seconds + benefit  + pli_ISEGYE_IDOL_예능 + pli_WAKTAVERSE_MUSIC + pli_WAKTAVERSE_예능 + pli_shorts + pli_똥겜 + pli_노가리', df_encoded).fit().summary()

        def reg(summary_df):
            r_squared = summary_df.tables[0].data[1][3]
            adj_r_squared = summary_df.tables[0].data[2][3]
            f_statistic = summary_df.tables[1].data[0][3]

            summary_data = {
                "Statistic": ["R-squared", "Adj. R-squared", "F-statistic"],
                "Value": [r_squared, adj_r_squared, f_statistic]
            }
            statistic_df = pd.DataFrame(summary_data)

            table = summary_df.tables[1]
            summary_df = pd.DataFrame(table.data[1:], columns=table.data[0])

            return statistic_df, summary_df, r_squared
        
        b_statistic_df, b_summary_df, b_r_squared = reg(summary_benefit)
        r_statistic_df, r_summary_df, r_r_squared = reg(summary_reaction)


        st.markdown(f'''
                ## 1. benefit
                > 수익차원에서 상대적으로 높은 컨텐츠 :blue[마인크래프트, 노가리, 합방]
                * 서브채널 컨텐츠보다 :green[본채널의 컨텐츠]가 수익측면에서 상대적으로 높은 추정치(coef)를 갖고 있습니다.
                * Shorts 의 경우 수익측면에서 좋진 않습니다. 영상의 길이가 짧기 때문에 들어가는 비용이 낮지만, cpm 도 낮기 때문입니다.
                * 설명력(R-Sqaure) : {b_r_squared}
                * 다중공선성 문제 없음
                ''' )

        col1,col2 = st.columns([1,1])
        with col1:
            st.markdown('''#### ① summary table''')
            # 'coef' 컬럼에서 nlargest(3)를 사용하여 상위 3개 값을 하이라이트
            b_summary_df['coef'] = b_summary_df['coef'].astype(float)

            top_3_values = b_summary_df['coef'].nlargest(3).values

            def highlight_high_values(value):
                if value in top_3_values:
                    return 'background-color: yellow'
                else:
                    return ''
            styled_df = b_summary_df.style.applymap(highlight_high_values, subset=['coef'])

            # 스크립트에 표시
            st.dataframe(styled_df)


        with col2:
            st.markdown('''#### ② 컨텐츠 대표 영상''')
            st.caption('(2021~2023) 연도별로 조회수가 가장 높은 영상 입니다.')
        
            result_df = pd.DataFrame(columns=df.columns)
            for year in ['2021', '2022', '2023']:
                mark_df = df[(df['playlist_title'] == '마크') & (df['year'] == year)].nlargest(1, 'view_count')
                nogari_df = df[(df['playlist_title'] == '노가리') & (df['year'] == year)].nlargest(1,'view_count')
                habang_df = df[(df['playlist_title'] == '합방기타컨텐츠')&(df['year'] == year)].nlargest(1,'view_count')
                vrchat_df = df[(df['playlist_title'] == 'vrchat')&(df['year'] == year)].nlargest(1,'view_count')
                result_df = pd.concat([result_df,mark_df,nogari_df,habang_df,vrchat_df], ignore_index=True).sort_values(by='playlist_title')

            with elements("content"):
                layout=[
                    dashboard.Item(f"item_1", 0, 0, 1.3, 1.5, isDraggable=False, isResizable=True ),                    
                    dashboard.Item(f"item_2", 1.3, 0, 1.3, 1.5, isDraggable=False, isResizable=True ),                    
                    dashboard.Item(f"item_3", 2.6, 0, 1.3, 1.5, isDraggable=False, isResizable=True ),                    
                    dashboard.Item(f"item_4", 0, 1, 1.3, 1.5, isDraggable=False, isResizable=True ),                    
                    dashboard.Item(f"item_5", 1.3, 1, 1.3, 1.5, isDraggable=False, isResizable=True ),                    
                    dashboard.Item(f"item_6", 2.6, 1, 1.3, 1.5, isDraggable=False, isResizable=True ),                    

                    ]
                with dashboard.Grid(layout):
                    for i in range(6):
                        mui.Box(
                            children = [
                                mui.Typography(f'# {result_df["playlist_title"].iloc[i]}',
                                            component="div", 
                                            sx={
                                                "font-size" : "14px",
                                                "fontWeight":"bold",
                                                }),                     
              
                                mui.CardMedia( # 썸네일 이미지
                                    sx={ "height": 120, #h_dGGxhH6YQ
                                        # "ovjectFit":"contain",
                                        "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{result_df['video_id'].iloc[i]}/sddefault.jpg)","borderRadius": "15px",
                                    }                            
                                ),
                                mui.Typography(f'{result_df["title"].iloc[i]}', variant="body2",sx={"pt":"5px"})                                
                                ]                                                      
                                , key=f'item_{i+1}',sx={'borderRadius':'15px', "max-height": "100%","overflow": "hidden",})                            
 
            




        st.markdown(f'''
                        ## 2. reaction (comment_count + like_count)
                        > 영상의 길이가 짧을 수록 reaction이 높을 확률이 크다?
                        * :red[Shorts 와 WAKTAVERSE : MUSIC] 컨텐츠의 공통점을 뽑자면 먼저 :red[영상의 길이]가 상대적으로 짧다는 것입니다. 그 만큼 보는데 부담이 적은 컨텐츠라고 할 수 있습니다.
                        * 추가로 WAKTAVERSE : MUSIC의 경우 댓글수를 목표변수(Y)로 봤을 때 전체 컨텐츠중에서 댓글수를 높히는데 가장 큰 영향력을 갖고 있었습니다.
                        * 반면에 유의미한 변수중 똥겜, 노가리, 예능 클립의 경우 시청자 반응이 상대적으로 낮은편에 속합니다.
                        * 설명력(R-Sqaure) : {r_r_squared}
                        * 다중공선성 문제 없음
                        ''' )
        col1,col2 = st.columns([1,1])
        with col1:
            st.markdown('''#### ① summary table''')
            # 'coef' 컬럼에서 nlargest(3)를 사용하여 상위 3개 값을 하이라이트
            r_summary_df['coef'] = r_summary_df['coef'].astype(float)

            top_3_values = r_summary_df['coef'].nlargest(3).values

            def highlight_high_values(value):
                if value in top_3_values:
                    return 'background-color: red'
                else:
                    return ''
            styled_df = r_summary_df.style.applymap(highlight_high_values, subset=['coef'])

            # 스크립트에 표시
            st.dataframe(styled_df)

        with col2:
            st.markdown('''#### ② 컨텐츠 대표 영상''')

            # music_df = df[(df['playlist_title'] == 'WAKTAVERSE_MUSIC') & (df['year'] == '2021')].nlargest(1,'reaction')
            # music_df = df[(df['playlist_title'] == 'WAKTAVERSE_MUSIC') & (df['year'] == '2022')].nlargest(1,'reaction')
            # music_df = df[(df['playlist_title'] == 'WAKTAVERSE_MUSIC') & (df['year'] == '2023')].nlargest(1,'reaction')
           
           
            result_df = pd.DataFrame(columns=df.columns)
            for year in ['2021', '2022', '2023']:
                music_df = df[(df['playlist_title'] == 'WAKTAVERSE_MUSIC') & (df['year'] == year)].nlargest(1, 'reaction')
                shorts_df = df[(df['playlist_title'] == 'shorts') & (df['year'] == year)].nlargest(1,'reaction')
                result_df = pd.concat([result_df,music_df,shorts_df], ignore_index=True).sort_values(by='playlist_title')

            with elements("content_reaction"):
                layout=[
              
                    dashboard.Item(f"item_1", 0, 0, 1.3, 1.5, isDraggable=False, isResizable=True ),                    
                    dashboard.Item(f"item_2", 1.3, 0, 1.3, 1.5, isDraggable=False, isResizable=True ),                    
                    dashboard.Item(f"item_3", 2.6, 0, 1.3, 1.5, isDraggable=False, isResizable=True ),                    
                    dashboard.Item(f"item_4", 0, 1, 1.3, 1.5, isDraggable=False, isResizable=True ),                    
                    dashboard.Item(f"item_5", 1.3, 1, 1.3, 1.5, isDraggable=False, isResizable=True ),                    
                    dashboard.Item(f"item_6", 2.6, 1, 1.3, 1.5, isDraggable=False, isResizable=True ),                    

                    ]
                with dashboard.Grid(layout):
                    for i in range(6):
                        mui.Box(
                            children = [
                                mui.Typography(f'# {result_df["playlist_title"].iloc[i]}',
                                            component="div", 
                                            sx={
                                                "font-size" : "14px",
                                                "fontWeight":"bold",
                                                }),                     
              
                                mui.CardMedia( # 썸네일 이미지
                                    sx={ "height": 120, #h_dGGxhH6YQ
                                        # "ovjectFit":"contain",
                                        "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{result_df['video_id'].iloc[i]}/sddefault.jpg)","borderRadius": "15px",
                                    }                            
                                ),
                                mui.Typography(f'{result_df["title"].iloc[i]}', variant="body2",sx={"pt":"5px"})                                
                                ]                                                      
                                , key=f'item_{i+1}',sx={'borderRadius':'15px', "max-height": "100%","overflow": "hidden",})                 

    with st.container():
        col1, col2 = st.columns([1,1])
        with col1:
            st.subheader('요약시치')
            st.markdown('''
                        > ##### 수익과 시청자의 반응의 상관성이 높은 편이지만 컨텐츠 별로 보았을 때는 다르다.
                        * (수익) 본채널 컨텐츠의 '마인크래프트', '합방 시리즈', 'vrchat'의 비중이 상대적으로 🔥
                        * (시청자 반응) 영상 길이가 짧은 'Shorts' 와 서브채널의 'WAKTAVERSE : MUSIC (이세계아이돌 MUSIC 포함)' 🔥
                        > ##### 특히, WAKTAVERSE : MUSIC 의 경우 댓글반응을 높히는데 가장 영향력이 있다.
                        * 댓글까지 남긴다는건 하트를 누르는것에 비해 시청자의 수고가 조금 더 들어가기 때문에 확실히 현재 시청자들의 참여도가 가장 높은 컨텐츠라 볼 수 있습니다.
                        ''')

    #     st.write(df)

    #     # df = df[df['playlist_title'].isin(['ISEGYE IDOL : 예능','WAKTAVERSE : 예능','shorts'])]

    #     group_1 = df[df['seconds'] < 600].reset_index() # 15분 미만
    #     group_2 = df[df['seconds'] >= 600].reset_index() # 15분 이상
    #     group_3 = df[df['seconds'] >= 1800].reset_index() # 30분 이상
    #     group_4 = df[df['seconds'] > 0 ].reset_index()

    #     group_wakta = df[df['playlist_title'].str.contains('WAKTA')].reset_index()
    #     group_idol = df[df['playlist_title'].str.contains('IDOL')].reset_index()

    #     col1,col2= st.columns([1,1])           
    #     with col1:
    #         c1,c2 = st.columns([1,3])
    #         with c1:
    #             year_option = st.selectbox('년도', [2023, 2022, 2021,'all'], key='group_video_year')

    #         with c2:
    #             option = st.selectbox('정렬기준', ['15분 미만','15분 이상','30분 이상','all'], key='group_video_seconds')

    #         if option == '15분 미만':
    #             df = group_1[group_1['year'] == year_option]
    #         elif option == '15분 이상':
    #             df = group_2[group_2['year'] == year_option]
    #         elif  option == '30분 이상':
    #             df = group_3[group_2['year'] == year_option]
    #         elif year_option == 'all':
    #             df = group_4

        
    #         # df = df[df['year'] == year_option]  # 년도에 따라 필터링

    #         grouped = df.groupby('playlist_title').agg({
    #             'view_count':  'mean',
    #             'like_count' : 'mean',
    #             'comment_count': 'mean',
    #             'cost':'mean',
    #             'benefit':'mean',
    #             'seconds':'mean',
    #             'title': 'count'
    #         }).round(0).reset_index()

    #         st.markdown('''##### 영상길이별 통계값(평균) ''')
    #         st.dataframe(grouped)

    #         # st.dataframe(df[['playlist_title','publishedAt','title','view_count','like_count','seconds','ad_count','cost','benefit']])   

    #     with col2:

    #         from scipy.stats import *

    #         # st.subheader('영상의 타이틀(고멤,이세돌)에 따라 평균 수익, 조회수, 좋아요, 댓글수에 차이가 있을까?')

    #         option = st.selectbox('변수', ['view_count','like_count','comment_count','benefit','cost'], key='t-test')                

    #         group_w = group_wakta[option]
    #         group_i = group_idol[option]

    #         st.subheader(f'{option}')

    #         st.markdown('''##### 왜도''')
    #         st.markdown(f''' 
    #                     * 고정멤버:{round(skew(group_w),3)}
    #                     * 이세돌:{round(skew(group_i),3)}
    #                     ''')


    #         # 등분산성
    #         statistic_l, pvalue_l = levene(group_w, group_i)
    #         if pvalue_l < 0.05:
    #             statistic_m, pvalue_m = mannwhitneyu(group_w, group_i)                    
    #             st.markdown(f''' 
    #                         ##### levene
    #                         * statistic : {round(statistic_l,3)} , p-value: {round(pvalue_l,3)}
    #                         * 등분산성이 가정되지 않아 비모수적인 방법을 이용합니다(mannwhitneyu)
    #                         ''')
    #             if pvalue_m < 0.05:
    #                 st.markdown(f'''
    #                         ##### t-test
    #                         * statistic : {round(statistic_m,3)} , p-value : {round(pvalue_m,3)}
    #                         * t-test 결과 평균 {option} 의 차이가 통계적으로 유의미합니다.
    #                             ''')
    #             else:
    #                 st.markdown(f'''mannwhitneyu 결과 두 그룹간 {option}은 통계적으로 큰 차이가 없습니다.
    #                             (* p-value : {round(pvalue_m,3)})
    #                             ''')

    #         else :
    #             # t-검정 실행
    #             statistic_t, pvalue_t = ttest_ind(group_w, group_i)
    #             st.markdown(f'''
    #                         ##### levene
    #                         * statistic : {round(statistic_l,3)} , p-value: {round(pvalue_l,3)}
    #                         * 등분산성을 만족합니다 
    #                         ''')
    #             if pvalue_t < 0.05:
    #                 st.markdown(f'''
    #                         ##### t-test
    #                         * statistic : {round(statistic_t,3)} , p-value : {round(pvalue_t,3)}
    #                         * t-test 결과 평균 {option} 의 차이가 통계적으로 유의미합니다.
    #                             ''')
    #             else:
    #                 st.markdown(f'''t-test 결과 두 그룹간 {option}은 통계적으로 큰 차이가 없습니다.
    #                             (* p-value : {round(pvalue_t,3)})
    #                             ''')







    # with tab2:
    #     st.write('gs')
 
    # with tab3:
    #     st.write('ㅎㅇ')



                # st.markdown('''
                # ## 2020년 Point ✔️  
                #     - vrchat, 고정멤버, 마인크래프트

                # ----
                # ##### 사랑받은 타이틀 - 합방,시리즈,기타 컨텐츠  + VRchat
                # * 과거 왁카데미에 더나아가, 컨셉을 갖고있는 '멤버'를 본격적으로 뽑기 시작함으로써 `합방` 시너지가 굉장히 높아졌다. (물론, 컨셉이 없어도된다.)
                # * 사실상 `본캐와 부캐`라는 컨텐츠를 2020년 부터 시작한것이다. 이 사람들이 실제 뭐하는 사람인지 몰라서 더 재밌다. 그래서 컨텐츠에 몰입하게 만드는 효과가 있다.
                # * 주로 `Vrchat` 을 이용한 컨텐츠이며 대표적으로 '상황극'이 있다.
                # * 당시, Vrchat자체가 굉장히 신선했다. 이를 컨텐츠로 성공시킨 유투버는 우왁굳이 유일무이하다.                     
                # ----
                # ##### 가성비 부분 - 먹방/캠방 
                # * `먹방/캠방` 의 경우 주컨텐츠인 `마크, vrchat, 노가리`와 비교했을 때  모두 :blue[상위권]에 속한다.
                # * 평균 조회수를 비교했을 때  
                #             \
                # vrchat 👉 먹방/캠방 👉 노가리 👉 마크 순으로 무려 :blue[2위]이며
                # * 평균 좋아요(16,298) :blue[2위], 평균 댓글수(2,153)는 :blue[1위] 이다.
                # * 일단 보이지 않던게 실제 화면에 보이니 반응이 좋을 수 밖에 없다. \
                #     (우왁굳이 캠을켜? 맛있다.)
                # ----  
                                                                                                                        
                # ##### 꾸준하게 먹여주는, 연금복권 철밥통 컨텐츠
                # * " `마인크래프트`, `노가리` "   
                # * `노가리`  그냥 맛있다. 편집까지 더해 더 맛있다. 그냥 말을 맛있게 잘한다.                      
                # * `마인크래프트` , 건축형 장기 컨텐츠, 콘테스트형 컨텐츠 
                # * (+) 당시 `똥겜`의 경우, 총 42번 업로드, 마인크래프트보다 두배나 많지만 평균 조회수가 약 :red[1.8배] 정도 낮다. 
                # * 똥겜 풀업로드 영상 까지 합친다면 더 낮을것이지만, 편집본과 풀영상의 경우 성격이 다르기 때문에 패스했다.
                # * 그렇다고 모든 똥겜의 조회수와 반응이 저조하다는것이 아니다. 2020년 조회수 top100 을 보면 14개가 똥겜이다.
                # * 단지, 많이 올린것에 비해 낮은 편이다. 근데 이 점이 굉장히 크다.

                # ''')


 


                #     st.subheader('대표영상')
                #     with elements("layout_1"):
                #         layout = [
                #             dashboard.Item("items0", 0, 1, 6, 1 ), # x,y
                #             dashboard.Item("items1",0, 2, 2, 1.2 ),
                #             dashboard.Item("items2",2, 2, 2, 1.2 ),
                #             dashboard.Item("items3",4, 2, 2, 1.2 ),
                #         ]
                #         with dashboard.Grid(layout):
                #             # mui.Card('test', key='items0')
                #             mui.Card('test',key='items1')
                #             mui.Card('test',key='items2')
                #             mui.Card('test',key='items3')

                # with st.container():
                #     with elements("tete"):
                #         with st.container():
                #             with elements("layout_2"):
                #                 layout = [
                #                     dashboard.Item("items0", 0, 1, 6, 1 ), # x,y
                #                     dashboard.Item("items1",0, 2, 2, 1.2 ),
                #                     dashboard.Item("items2",2, 2, 2, 1.2 ),
                #                     dashboard.Item("items3",4, 2, 2, 1.2 ),
                #                 ]
                #                 with dashboard.Grid(layout):
                #                     # mui.Card('test', key='items0')
                #                     mui.Card('test',key='items1')
                #                     mui.Card('test',key='items2')
                #                     mui.Card('test',key='items3')
 
 

# def iso_to_seconds(iso_duration):
#     time_delta = isodate.parse_duration(iso_duration)
#     return int(time_delta.total_seconds())

# # 'Duration' 컬럼 값을 초로 변환하여 새로운 컬럼에 저장
# df_2['seconds'] = df_2['Duration'].apply(iso_to_seconds)
# unique_df = df_2.drop_duplicates(subset=['video_id', 'playlist_title'])

# st.write(unique_df)



# def convert_df(unique_df):
#     # IMPORTANT: Cache the conversion to prevent computation on every rerun
#     return unique_df.to_csv().encode('utf-8-sig')

# csv = convert_df(unique_df)

# st.download_button(
#     label="Download data as CSV",
#     data=csv,
#     file_name='real_df.csv',
#     mime='text/csv',
# )


# merged_df = pd.merge(df, video_df, on='video_id', how = 'left')
# merged_df['playlistId'] = merged_df.apply(lambda row: 'PLshorts' if '#Shorts' in row['title_x'] else row['playlistId'], axis=1)
# merged_df2 = merged_df.merge(wakgood, on='playlistId', how='left').drop(columns=['playlistId'])

# st.write(merged_df2)

