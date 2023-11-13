import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly as plt

import seaborn as sns
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from statsmodels.formula.api import ols

from yout import get_all_playlist_videos_wak, get_channel_id, get_playlist, get_all_playlist_videos, video_duration
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



uploaded_file = pd.read_csv('csv_data/waktaverse_benefit.csv')

if uploaded_file is not None:
    df = benfit_cal(uploaded_file)
    df = df.sort_values(by='benefit', ascending = False).reset_index()
   
    # 재생목록 전처리
    df.loc[df['playlist_title'].str.contains('연공전|먹방|캠방|핫클립|합방'), 'playlist_title'] = '합방기타컨텐츠'      
    df.loc[df['playlist_title'].str.contains('vr'),'playlist_title'] = 'vrchat'  
    df.loc[df['playlist_title'].str.contains('YOUTUBE|이세여고|OFFICIAL'), 'playlist_title'] = 'ISEGYE_IDOL_예능' # 이세돌 카테고리 통합
    df.loc[df['playlist_title'].str.contains('GOMEM|MIDDLE'), 'playlist_title'] = 'WAKTAVERSE_예능'    
    df.loc[df['playlist_title'].str.contains('MUSIC'), 'playlist_title'] ='WAKTAVERSE_MUSIC'

    df = df[df['playlist_title'].str.contains('MUSIC|마크|똥겜|컨텐츠|노가리|예능|WAKTAVERSE|shorts|vrchat|시리즈')]


    df['publishedAt'] = pd.to_datetime(df['publishedAt'])
    df['date'] = df['publishedAt'].dt.date
    df['year'] = df['publishedAt'].dt.year
    df['hour'] = df['publishedAt'].dt.hour

    df = df[df['year'] > 2020]
    df = df.drop(df[df['playlist_title'].isin(['Shorts', '리그오브레전드', '왁튜브 처음 추천'])].index)

    df = df[df['video_id'] !="#NAME?"]
    df['reaction'] = df['like_count'] + df['comment_count']
    df['react_per_view'] = round(df['view_count'] * 0.02,0)
    df['diff_react_per_view'] = df['reaction'] - df['react_per_view']


    video_ids = df['video_id'].tolist()

    with st.container():
        col1, col2= st.columns([1,1])
        with col1:
            st.markdown('''
                        ### 💻 분석과제
                        ### 1.목적
                        **유튜브의 수익모델의 핵심은 '광고' 입니다.** 업로드된 영상에 붙은 광고가 시청자들에게 많이 노출 된 만큼 수익이 들어오는데요! 
                        즉, **조회수가 높다**는 것은 **광고에 노출된 횟수가 높다**는 말이므로 **수익과 큰 상관성**이 있다고 볼 수 있습니다.👀 

                        > 그렇다면 채널을 운영하는 입장에서 **어떤 컨텐츠들이 수익이 좋고 시청자 반응(댓글,좋아요)이 활발한지** 분석이 꼭 필요할 것 이라고 생각했습니다. 

                        ''')
  
        with col2:
            st.markdown('''
                        ### 2.과제 
                        > " 지금 보다 채널을 성장시키고 싶습니다. 현재 운영하고있는 채널의 컨텐츠들중에서 어떤 컨텐츠들의 영상들을 중점으로 공략해야 할까요? "                        
                        
                        ### 3.가설
                        > 채널을 성장을 위한 가장 큰 두개의 핵심은 **조회수와 시청자들의 참여도** 
                        > 이를 위해 세워본 가설은 다음과 같습니다!                        
                        * ✔️시청자 참여(좋아요, 댓글)가 높은 컨텐츠들이 수익도 높을 것 이다.
                        * ✔️오전,오후 업로드 시간에 따라 수익에 차이가 있지 않을까?
                        ''' ) 
    st.divider()

    # 업로드 시간, 상관분석 등 시각화 
    with st.container():
        st.header('데이터 탐색')
        col1,_,col2 = st.columns([1.5,0.2,1.5])
        with col1:
            st.subheader('💻업로드 시간') 
            st.caption(''' 주로 업로드 하는 시간은?''')      

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


            tab1, tab2 = st.tabs(['Chart','Correlation Heatmap'])
            with tab1:
                fig = px.scatter(filtered_df, x='view_count', y='like_count', size='comment_count', color='playlist_title', hover_name='title', log_x=True, log_y=True, size_max=60)

                st.plotly_chart(fig, theme="streamlit", use_container_width=True)

            with tab2:
                st.caption(f'''
                            Correlation Heatmap 결과입니다.
                            ''')
        
                mask = ['view_count','seconds','ad_count','ad_benefit','cost','benefit','comment_count','like_count','reaction']
                df_col= df[mask]

                fig = plt.figure(figsize=(10, 8))
                sns.heatmap(df_col.corr(), annot=True)
                plt.title('Correlation Heatmap')
                plt.xlabel('Features')
                plt.ylabel('Features')

                st.pyplot(fig)


    # 컨텐츠별 조회수/이익/좋아요 비율 시각화    
    with st.container():
        col1,col2 = st.columns([1.5,1.5])
        with col1:
            # st.header('2020년 Point ✔️')
            st.subheader('📊 컨텐츠별 조회수/이익/좋아요 비율')
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


            pivot_df = all_df.pivot(index="year", columns="playlist_title", values=values).reset_index()
            pivot_nivo = pivot_df.to_dict(orient="records")

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
              

            with st.expander("See DATA"):
                st.write(grouped_year)

        with col2:
            with st.container():
                tab1, tab2 = st.tabs(['추정수익',' '])
            with tab1:
                st.markdown('''##### 📝 추정수익 정의''')
                st.caption('추정 수익의 경우 아래와 같은 공식으로 계산 되었습니다. 말그대로 예상 수익입니다. 정확한 편집 비용, 광고 종류/노출횟수를 알 수 없기 때문에 오차가 있습니다.')
                # with st.expander('계산공식'):
                st.markdown('''                     
                                > 수익과 비용은 아래의 가정하에 산출하였습니다.
 
                                > * CPM = 2022년 기준 3500원
                                > * Shorts CPM = 2023년 기준 120원
 
                                > * 10명중 6명이 광고를 봤다.
                                > * 유튜브 광고 수익 = 3500 * (조회수 * 0.6) / 1000) * 0.55(수수료)
                                > * 편집비용 = 분당 30,000원  (쇼츠의 경우 영상 1개당 15,000원)                
                                > * 비용은 편집비용만 고려하였으며 30분이상인 경우 풀영상으로 파악하여 비용을 100,000원으로 고정                                                                                                       
                                ''')
                

    st.divider()

    # 전처리
    with st.container():
        st.subheader('데이터 전처리')
        st.caption('대부분 오른쪽으로 치우쳐있는 왜도값을 갖고있습니다. "-2~+2" 를 벗어나는 변수에 log화를 해주었습니다.')
        col1,col2 = st.columns([2,1])
        with col1:
            code ='''
                # 범주형 변수 인코딩
                df_encoded = pd.get_dummies(df, columns=['playlist_title'], prefix=['pli'])
                variables_to_normalize = ['seconds', 'view_count', 'like_count', 'comment_count', 'benefit','reaction','diff_react_per_view']

                # 표준화 (Standardization)
                scaler = StandardScaler()
                df_encoded[variables_to_normalize] = scaler.fit_transform(df_encoded[variables_to_normalize])

                # 로그화
                var = ['seconds', 'view_count', 'like_count', 'comment_count', 'benefit','reaction','diff_react_per_view']
                df_encoded[var] = np.log1p(df_encoded[var])
                '''

            st.code(code, language='python')
        with col2:        
            # 범주형 변수 인코딩
            df_encoded = pd.get_dummies(df, columns=['playlist_title'], prefix=['pli'])        
            variables_to_normalize = ['seconds', 'view_count', 'like_count', 'comment_count', 'benefit','reaction','diff_react_per_view']

            # 표준화 (Standardization)
            scaler = StandardScaler()
            df_encoded[variables_to_normalize] = scaler.fit_transform(df_encoded[variables_to_normalize])

            # 연속형 변수에 로그 변환 적용
            var = ['seconds', 'view_count', 'like_count', 'comment_count', 'benefit','reaction','diff_react_per_view']

            # 로그 전
            before_log = pd.DataFrame(df_encoded[var].skew())
            before_log = before_log.rename(columns={0: 'skew_before'})

            # 로그후
            df_encoded[var] = np.log1p(df_encoded[var])
            after_log = pd.DataFrame(df_encoded[var].skew())
            after_log = after_log.rename(columns={0: 'skew_after'})

            # 둘 비교
            result = pd.concat([before_log, after_log], axis=1)
            st.write(result)

    st.divider()

    # 회귀분석 결과
    with st.container():
        st.subheader('수익이 높은 컨텐츠라고 해서 시청자들의 반응도 높을까?🤔?')
        
        summary_benefit = ols('benefit ~ seconds + reaction  + pli_ISEGYE_IDOL_예능 + pli_WAKTAVERSE_예능 + pli_shorts + pli_vrchat + pli_노가리 + pli_똥겜 + pli_마크 + pli_합방기타컨텐츠', df_encoded).fit().summary()
        summary_reaction= ols('reaction ~ seconds + benefit  + pli_ISEGYE_IDOL_예능 + pli_WAKTAVERSE_MUSIC + pli_WAKTAVERSE_예능 + pli_shorts + pli_똥겜 + pli_노가리', df_encoded).fit().summary()
        # summary_react_perview= ols('diff_react_per_view ~ seconds + benefit  + pli_WAKTAVERSE_MUSIC + pli_WAKTAVERSE_예능 + pli_shorts + pli_합방기타컨텐츠 + pli_vrchat + pli_마크', df_encoded).fit().summary()


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
        # d_statistic_df, d_summary_df, d_r_squared = reg(summary_react_perview)


        st.markdown(f'''
                ## 1. benefit
                > 수익차원에서 상대적으로 높은 컨텐츠 :blue[노가리, 마인크래프트, 합방 컨텐츠]
                * 서브채널 컨텐츠보다 :blue[본채널의 컨텐츠]가 수익측면에서 상대적으로 높은 추정치(coef)를 갖고 있습니다.
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
            st.caption('(2021~2023) 연도별로 추정이익이 가장 높은 영상 입니다.')
        
            result_df = pd.DataFrame(columns=df.columns)
            for year in ['2021', '2022', '2023']:
                mark_df = df[(df['playlist_title'] == '마크') & (df['year'] == year)].nlargest(1, 'benefit')
                nogari_df = df[(df['playlist_title'] == '노가리') & (df['year'] == year)].nlargest(1,'benefit')
                habang_df = df[(df['playlist_title'] == '합방기타컨텐츠')&(df['year'] == year)].nlargest(1,'benefit')
                # vrchat_df = df[(df['playlist_title'] == 'vrchat')&(df['year'] == year)].nlargest(1,'benefit')
                result_df = pd.concat([result_df,mark_df,nogari_df,habang_df], ignore_index=True).sort_values(by='playlist_title')


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
                        * 추가로 :red[WAKTAVERSE : MUSIC]의 경우 댓글수를 목표변수(Y)로 봤을 때 전체 컨텐츠중에서 :red[댓글수를 높히는데 가장 큰 영향력]을 갖고 있었습니다.
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
            st.subheader('요약')
            st.markdown('''
                        > ##### 수익과 시청자 반응간의 상관성이 높은 편이지만 컨텐츠 별로 보았을 때는 다르다.
                        * (수익) 본채널 컨텐츠의 '마인크래프트', '합방 시리즈', 'vrchat'의 비중이 상대적으로 🔥
                        * (시청자 반응) 영상 길이가 짧은 'Shorts' 와 서브채널의 'WAKTAVERSE : MUSIC (이세계아이돌 MUSIC 포함)' 🔥
                        * 👉 수익이 높은 컨텐츠라고해서 시청자의 반응(좋아요+댓글)도 높다고 볼 수 없었다.

                        > #####  WAKTAVERSE : MUSIC 의 경우 댓글반응을 높히는데 가장 영향력이 있다.
                        * 댓글까지 남긴다는건 하트를 누르는것에 비해 시청자의 수고가 조금 더 들어가기 때문에 확실히 현재 시청자들의 참여도가 가장 높은 컨텐츠라 볼 수 있다.
                        ''')

