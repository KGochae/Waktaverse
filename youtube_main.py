import io
import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from collections import Counter

from googleapiclient.discovery import build
from google.cloud import storage, bigquery
from google.oauth2 import service_account

from streamlit_elements import dashboard
from streamlit_elements import nivo, elements, mui, media

# 문자열을 파이썬 리스트로 변환하기 위한 모듈
import ast 

# 일부 전처리 및 댓글 수집
from preprocess import data_diff, hot_video

# keyword 분석
from NLP import get_comment, nivo_pie, wordCount, get_member_images, gomem_video, gomem_comment, monthly_gomem

# 일부 css 적용
with open( "font.css" ) as css:
    st.markdown( f'<style>{css.read()}</style>' , unsafe_allow_html= True)
pd.set_option('mode.chained_assignment',  None)


now = datetime.datetime.now()
now_time = now.strftime('%Y-%m-%d') # 현재 시간을 문자열로 변환한 후 다시 datetime 객체로 변환
today = pd.to_datetime(now_time, format='%Y-%m-%d') # 현재 시간을 datetime 객체로 변환 

week = now - datetime.timedelta(days=now.weekday())
week_start = week.strftime('%m-%d')
month = str(now.strftime('%m'))
year = str(now.strftime('%Y'))

min_date = datetime.date(2023, 8, 2)
max_date = datetime.date(now.year, now.month, now.day)
befor_7 = datetime.date(2023, 12, 1) 


# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials)


# ------------------------------GOOGLE CLOUD STORAGE------------------------------------------------ #

main_bucket = 'waktaverse'
comment_bucket = 'waktaverse_comment'


def load_maindata():
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(main_bucket)
    blobs = bucket.list_blobs()

    # CSV 파일만 필터링합니다.
    csv_blobs = [blob for blob in blobs if blob.name.endswith('.csv') and blob.name.startswith('waktaverse_playlist_2023')]


    # CSV files to DataFrames
    dfs = []
    for blob in csv_blobs:
        csv_data = blob.download_as_string()
        df = pd.read_csv(io.StringIO(csv_data.decode('utf-8')))
        dfs.append(df)

    # Merge all DataFrames
    data = pd.concat(dfs)
    return data

def load_comment():
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(comment_bucket)
    blob = bucket.blob('gomem_tmp_20231130.csv')

    csv_data = blob.download_as_string()
    df = pd.read_csv(io.StringIO(csv_data.decode('utf-8')))

    df['tmp'] = df['tmp'].apply(ast.literal_eval) # 토큰화된 값들 이 [] 안에있는데, csv 로 불러오면 '[' , ']' 또한 문자열로 바뀌어버린다(?). 리스트로 변환해야함

    return df


@st.cache_data() # ttl ?  
def load_data():
    data = load_maindata() 
    comment_data = load_comment()
    isaedol = pd.read_csv('csv_data/이세계아이돌_video_2312.csv')
    return data, comment_data, isaedol

data, comment_data, isaedol = load_data()


with st.container():
    st.markdown(''' 

                # WATKAVERSE DASHBOARD

                ''')

if not data.empty:
    # 일부 전처리
    merged_df, playlist_titles, subscribe, subscribe_week = data_diff(data)
    total_diff, top3_videos,top3_music, top3_videos_week, top3_music_week, top3_videos_month, top3_music_month = hot_video(merged_df,playlist_titles, year, month)

    # -------------------------------------------------------- MAIN CONTENTS(재생목록, 구독자, hot_video) ------------------------------------------------------------- #

    with st.container():  ### 📊 재생목록 조회수 증가량
        col1,col2,_= st.columns([4,2,7])
        with col1:
                st.markdown('''
                    ### 📊 재생목록 조회수/ 구독자수 증가량
                    ''')
        with col2:
            # 재생목록별 조회수 option (일별)
            d = st.date_input(
                "date",
                (befor_7, datetime.date(now.year, now.month, now.day)),
                min_date, # 최소 날짜
                max_date, # 최대 날짜
                format="YYYY.MM.DD",
            ) 
            if len(d) >= 2: 
                start_d = str(d[0])
                end_d = str(d[1])
            else:
                start_d = str(d[0])
                end_d = str(max_date)


            playlist_diff = total_diff.groupby(['playlist_title', 'down_at']).agg({'view_count_diff': 'sum'}).reset_index()
            date_mask = (playlist_diff['down_at'] >= start_d) & (playlist_diff['down_at'] <= end_d) # date로 지정된 값들만 
            pli_day_diff = playlist_diff.loc[date_mask]
            pli_day_diff['down_at'] = pd.to_datetime(playlist_diff['down_at']).dt.strftime('%m-%d')


            # 재생목록별 조회수(주간)
            copy_df = total_diff.groupby(['playlist_title', 'down_at']).agg({'view_count_diff': 'sum'}).reset_index() 
            copy_df['down_at'] = pd.to_datetime(copy_df['down_at'], format='%Y-%m-%d') 
            copy_df['week_start'] = copy_df['down_at'] - pd.to_timedelta(copy_df['down_at'].dt.dayofweek, unit='d')
            copy_df.groupby(['playlist_title','week_start'])['view_count_diff'].sum().reset_index()    
            pli_weekly_diff = copy_df.groupby(['playlist_title', 'week_start']).agg({'view_count_diff': 'sum'}).reset_index()
            pli_weekly_diff['week_start'] = pd.to_datetime(pli_weekly_diff['week_start']).dt.strftime('%m-%d')

            
            # 월간


            # nivo 차트를 위한 데이터 가공
            diff = []
            for playlist_title, group in pli_day_diff.groupby('playlist_title'):
                if len(group) > 0:
                    
                    playlist_title = group.iloc[0]['playlist_title']
                    view_count_diff = group.iloc[-1]['view_count_diff']

                    diff.append({
                        'id': playlist_title,
                        'value' : view_count_diff,
                        'data' : [{'x': down_at, 'y': view_count_diff} for down_at, view_count_diff in zip(group['down_at'], group['view_count_diff'])][1:],
                    })

            # 구독 변화
            subscribe_n = [
                {
                    'id': 'subscribe',
                    'data': [
                        {'x': week_start, 'y': subscribe_diff}
                        for week_start, subscribe_diff in zip(subscribe_week['week_start'], subscribe_week['subscribe_diff'])
                    ]
                }
            ]

            today_total = sum(item['value'] for item in diff) # 가장 최근 전체 조회수


            weekly_diff = []
            for playlist_title, group in pli_weekly_diff.groupby('playlist_title'):
                if len(group) > 0:
                    
                    playlist_title = group.iloc[0]['playlist_title']

                    weekly_diff.append({
                        'id': playlist_title,
                        'data' : [{'x': week_start, 'y': view_count_diff} for week_start, view_count_diff in zip(group['week_start'], group['view_count_diff'])][1:],

                    })



    with st.container(): ### 재생목록별 조회수 증가량
        with st.container():       
                with elements("playlist_line_chart"):
                    layout = [
                        dashboard.Item("item_1", 0, 0, 8, 2),
                        dashboard.Item("item_2", 8, 0, 2, 2),
                        dashboard.Item("item_3", 10, 0, 1.5, 2)

                    ]

                    with dashboard.Grid(layout):
                                                        
                            mui.Box( # 재생목록별 전체 조회수 증가량
                                    nivo.Line(
                                        data= diff,
                                        margin={'top': 50, 'right': 15, 'bottom': 20, 'left': 55},
                                        xScale={'type': 'point',
                                                },

                                        curve="cardinal",
                                        axisTop=None,
                                        axisRight=None,
                                        axisBottom=None,

                                        # axisLeft={
                                        #     'tickSize': 4,
                                        #     'tickPadding': 10,
                                        #     'tickRotation': 0,
                                        #     'legend': '조회수',
                                        #     'legendOffset': -70,
                                        #     'legendPosition': 'middle'
                                        # },
                                        colors= {'scheme': 'accent'},
                                        enableGridX = False,
                                        enableGridY = False,
                                        enableArea = True,
                                        areaOpacity = 0.5   ,
                                        lineWidth=2,
                                        pointSize=1,
                                        pointColor='white',
                                        pointBorderWidth=0.5,
                                        pointBorderColor={'from': 'serieColor'},
                                        pointLabelYOffset=-12,
                                        useMesh=True,
                                        legends=[
                                                    {
                                                    'anchor': 'top-left',
                                                    'direction': 'column',
                                                    'justify': False,
                                                    # 'translateX': -30,
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
                                                # "background-color": "rgba(158, 60, 74, 0.2)",
                                                "textColor": "white",
                                                "tooltip": {
                                                    "container": {
                                                        "background": "#3a3c4a",
                                                        "color": "white",
                                                    }
                                                }
                                            },
                                        animate= False)
                                        ,key="item_1",sx={"borderRadius":"15px", "borderRadius":"15px","outline": "1px solid #31323b"}) # "background-color":"rgb(49 50 59)"

                            mui.Box( # today view count
                                children = [
                                    mui.Typography(
                                        " Today View Count",
                                        variant="body2",
                                        sx={ # "fontFamily":"Pretendard Variable",
                                            "font-size": "24px",
                                            "pt":2} ,
                                    ),

                                    mui.Typography(
                                        f"{round(today_total)}",
                                        variant="body2",
                                        sx={
                                            "font-size": "32px",
                                            "fontWeight":"bold",
                                            "padding-top": 0
                                            } ,
                                        
                                    ),
                                    mui.Divider(),

                                    nivo.Pie(
                                            data=diff,
                                            margin={"top": 30, "right": 20, "bottom": 110, "left": 20 },
                                            sortByValue=True,
                                            innerRadius={0.5},
                                            padAngle={2},
                                            colors= { 'scheme': 'accent' }, # pastel1
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
                                            enableArcLinkLabels=False,
                                            arcLabel='id',
                                            arcLabelsRadiusOffset={1.3},
                                            arcLinkLabelsSkipAngle={5},
                                            arcLinkLabelsThickness={5},
                                            # arcLabelsTextColor={ "from": 'white', "modifiers": [['brighter',0.5]] },
                                            arcLabelsTextColor="white",
                                            arcLabelsSkipAngle={10},
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
                                        )
                                
                                ]
                                ,key='item_2', sx={"text-align":"center", "borderRadius":"15px", "outline": "1px solid #31323b"}) # rgb(49 50 59)

                            mui.Box( # subscribe
                                children = [
                                    mui.Typography(
                                        " Subscribe ",
                                        variant="body2",
                                        sx={"fontFamily":"Pretendard Variable",
                                            "font-size": "24px",
                                            "pt":2} ,
                                    ),

                                    mui.Typography(
                                        f"{round(subscribe['subscribe'].max())}",
                                        variant="body2",
                                        sx={
                                            "font-size": "32px",
                                            "fontWeight":"bold",
                                            "padding-top": 0
                                            } ,
                                        
                                    ),
                                    mui.Divider(),

                                    mui.Typography(
                                        '전일 대비 증가량',
                                         variant="body2",
                                         color="text.secondary",
                                         sx={'pt':2}
                                    ),
                                    
                                    nivo.Line(
                                        data =subscribe_n,
                                        margin={'top': 20, 'right': 20, 'bottom': 150, 'left': 20},
                                        xScale={'type': 'point'},
                                        yScale={
                                            'type': 'linear',
                                            'min': 'auto',
                                            'max': 'auto',
                                            'stacked': True,
                                            'reverse': False
                                        },
                                        curve="cardinal",
                                        axisRight=None,
                                        axisBottom=None,
                                        # {
                                        #     'tickCount': 5,
                                        #     'tickValues': tickValues,  # X축 값들 사이에 구분선을 그리기 위해 설정
                                        #     'tickSize': 0,
                                        #     'tickPadding': 5,
                                        #     'tickRotation': 0,
                                        #     'legendOffset': 36,
                                        #     'legendPosition': 'middle',
                                        # },
                                        axisLeft=None,

                                        colors=  {'scheme': 'accent'},
                                        enableGridX = False,
                                        enableGridY = False,
                                        lineWidth=3,
                                        pointSize=0,
                                        pointColor='white',
                                        pointBorderWidth=1,
                                        pointBorderColor={'from': 'serieColor'},
                                        pointLabelYOffset=-10,
                                        # enableArea=True,
                                        # areaOpacity='0.15',
                                        useMesh=True,                
                                        theme={
                                                # "background": "#100F0F", # #262730 #100F0F
                                                "textColor": "white",
                                                "tooltip": {
                                                    "container": {
                                                        "background": "#3a3c4a",
                                                        "color": "white",
                                                    }
                                                }
                                            },
                                        animate= False
                                    )
                                        ]                                
                                    ,key="item_3",sx={"text-align":"center", "borderRadius":"15px","outline": "1px solid #31323b"})



    with st.container(): ### 뜨는 컨텐츠, 영상반응요약
        col1,_,col2 = st.columns([1.8,0.01,1])

        with col1: # HOT_VIDEO
            with st.container():  # HOT_VIDEO 
                
                col1_1,col2_1,_ = st.columns([6, 1.2, 0.15])
                with col1_1:
                    st.markdown('''
                        ### 🔥뜨는 컨텐츠 TOP3 (예능/노래)
                        ''')
                    # st.caption('몇주동안, 몇일동안 상위권 등수를 유지했는지 기록해보자')
                with col2_1:
                        sort_option_count = st.selectbox('__' , ['Today',f'주간 ({week_start})',f'월간 ({month}월)'], key='sort_option_hot')

                        if sort_option_count == 'Today':
                            top3_data_enter = top3_videos
                            top3_data_music = top3_music

                        elif sort_option_count == f'주간 ({week_start})':
                            top3_data_enter = top3_videos_week 
                            top3_data_music = top3_music_week

                        elif sort_option_count == f'월간 ({month}월)':
                            top3_data_enter = top3_videos_month 
                            top3_data_music = top3_music_month                            

            st.caption(f'''
                        * {sort_option_count} 조회수/좋아요 증가량 TOP3를 가져옵니다.                              
                        ''')

            with st.container(): # HOT_VIDEO   
                with elements("hot_videos"):
                    layout=[
                           dashboard.Item("item_1", 0, 0, 2, 1.5, isDraggable=True, isResizable=False ),
                            dashboard.Item("item_2", 2, 0, 2, 1.5, isDraggable=True, isResizable=False),
                            dashboard.Item("item_3", 4, 0, 2, 1.5, isDraggable=True, isResizable=False),
                            dashboard.Item("item_4", 0, 2, 2, 1.5, isDraggable=True, isResizable=False),
                            dashboard.Item("item_5", 2, 2, 2, 1.5, isDraggable=True, isResizable=False),
                            dashboard.Item("item_6", 4, 2, 2, 1.5, isDraggable=True, isResizable=False),

                         ]
                    hot_video_card_sx = { #  타이틀 조회수증가량 css
                                        "display": "flex",
                                        "item-align":"center",
                                        "gap":"10px",
                                        "justify-content":"center",
                                        "height": "50px",
                                        "width" : "240px",
                                        "padding-bottom": "5px", 
                                        "padding-top": "5px",  
                                        }

                    title_sx = {"font-size":"12px",
                                "align-self": "center",
                                "max-height": "100%",
                                "overflow": "hidden",
                                "width" : "160px",
                                "item-align":"center",
                                # "fontFamily":"Pretendard Variable"                                            
                                }   
                    
                    # mui.Box('hi')
                    with dashboard.Grid(layout):
                        mui.Card(
                                mui.CardContent( # 재생목록/링크
                                    sx={'display':'flex',
                                        'padding': '2px 0 0 0'
                                        },
                                    children=[
                                        mui.Typography(
                                                    f"🥇{top3_data_enter['playlist_title'].iloc[0]}",
                                                    component="div",
                                                    sx={"font-size":"12px",
                                                        "padding-left": 10,
                                                        "padding-right": 10}                            
                                                ),
                                        mui.Link(
                                            "🔗",
                                            href=f"https://www.youtube.com/watch?v={top3_data_enter['video_id'].iloc[0]}",
                                            target="_blank",
                                            sx={"font-size": "12px",
                                                "font-weight": "bold"}
                                                )                                                                                       
                                            ]                            
                                        ),


                                mui.CardMedia( # 썸네일 이미지
                                sx={ "height": 140,
                                    "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{top3_data_enter['video_id'].iloc[0]}/sddefault.jpg)",
                                    # "mt": 0.5
                                    },
                                ),

                                mui.CardContent( # 타이틀 조회수증가량
                                    sx = hot_video_card_sx,
                                    children=[
                                        mui.Typography( # 타이틀
                                            f"{top3_data_enter['title'].iloc[0]}",
                                            component="div",
                                            sx=title_sx                           
                                        ),
                                    
                                        mui.Divider(orientation="vertical",sx={"border-width":"1px"}), # divider 추가
                                     
                                        mui.Box(
                                            mui.Typography(
                                                f"{int(top3_data_enter['view_count_diff'].iloc[0])}",
                                                    variant='body2', 
                                                sx={
                                                    "font-size" : "25px",
                                                    "fontWeight":"bold",
                                                    "text-align":"center",
                                                    "height":"30px"
                                                    },     
                                                ),   
                                            mui.Typography(
                                                f"❤️{int(top3_data_enter['like_count_diff'].iloc[0])} +",
                                                    variant='body2', 
                                                sx={
                                                    "font-size" : "14px",
                                                    "fontWeight":"bold",
                                                    "text-align":"center"
                                                    },     
                                                ),    
                                            ),
                                        ]
                                    )                       
                                ,key='item_1',sx={"borderRadius": '23px',
                                                #   "background-color":"white",
                                                #   "background": "linear-gradient(rgba(19, 129, 155, 0.8), rgba(39, 185, 142, 0.8))"
                                                #     if "WAKTA" in f"{top3_data_enter['playlist_title'].iloc[0]}" else "linear-gradient(#e66465, #9198e5)"
                                                    })
                                                                    
                        mui.Card(                            
                                mui.CardContent(
                                    sx={'display':'flex',
                                        'padding': '2px 0 0 0'
                                        },
                                    children=[
                                        mui.Typography( # 재생목록
                                                    f"🥈{top3_data_enter['playlist_title'].iloc[1]}",
                                                    component="div",
                                                    sx={"font-size":"12px",
                                                        "padding-left": 10,
                                                        "padding-right": 10}                            
                                                ),
                                        mui.Link(
                                            "🔗",
                                            href=f"https://www.youtube.com/watch?v={top3_data_enter['video_id'].iloc[1]}",
                                            target="_blank",
                                            sx={"font-size": "12px",
                                                "font-weight": "bold"}
                                                )                                                                                       
                                            ]                            
                                        ),
                            mui.CardMedia( # 썸네일 이미지
                                sx={ "height": 140,
                                    "ovjectFit":"cover",
                                    "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{top3_data_enter['video_id'].iloc[1]}/sddefault.jpg)",
                                    }                            
                            ),
                            mui.CardContent( # 타이틀 조회수 증가량
                                    sx = hot_video_card_sx,
                                    children=[
                                        mui.Typography(
                                            f"{top3_data_enter['title'].iloc[1]}",
                                            component="div",
                                            sx = title_sx                    
                                        ),
                                        mui.Divider(orientation="vertical",sx={"border-width":"1px"}), # divider 추가
                                        mui.Box(
                                            mui.Typography(
                                                f"{int(top3_data_enter['view_count_diff'].iloc[1])}",
                                                    variant='body2', 
                                                sx={
                                                    "font-size" : "25px",
                                                    "fontWeight":"bold",
                                                    "text-align":"center",
                                                    "height":"30px"
                                                    },     
                                                ),   
                                                
                                            mui.Typography(
                                                f"❤️{int(top3_data_enter['like_count_diff'].iloc[1])} +",
                                                    variant='body2', 
                                                sx={
                                                    "font-size" : "14px",
                                                    "fontWeight":"bold",
                                                    "text-align":"center"

                                                    },     
                                                ),    
                                            ) 
                                        ]
                                    )                            
                                    , key='item_2',sx={"borderRadius": '23px',
                                                    # "background": "linear-gradient(#13819b, #27b98e)"
                                                    # if "WAKTA" in f"{top3_data_enter['playlist_title'].iloc[1]}" else "linear-gradient(#e66465, #9198e5)"
                                                    })
                            
                        mui.Card(
                            mui.CardContent(
                                    sx={'display':'flex',
                                        'padding': '2px 0 0 0'
                                        },
                                    children=[
                                        mui.Typography( # 재생목록
                                                    f"🥉{top3_data_enter['playlist_title'].iloc[2]}",
                                                    component="div",
                                                    sx={"font-size":"12px",
                                                        "padding-left": 10,
                                                        "padding-right": 10}                            
                                                ),
                                        mui.Link(
                                            "🔗",
                                            href=f"https://www.youtube.com/watch?v={top3_data_enter['video_id'].iloc[2]}",
                                            target="_blank",
                                            sx={"font-size": "12px",
                                                "font-weight": "bold"}
                                                )                                                                                       
                                            ]                            
                                        ),                             
                            mui.CardMedia( # 썸네일 이미지
                                sx={ "height": 140,
                                    "ovjectFit":"cover",
                                    "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{top3_data_enter['video_id'].iloc[2]}/sddefault.jpg)",
                                    }                            
                            ),
                            mui.CardContent( # 타이틀 조회수 증가량
                                    sx = hot_video_card_sx,
                                        children=[
                                            mui.Typography(# 타이틀
                                                f"{top3_data_enter['title'].iloc[2]}",
                                                component="div",
                                                sx=title_sx                        
                                            ),
                                            mui.Divider(orientation="vertical",sx={"border-width":"1px"}), # divider 추가

                                            mui.Box(
                                                sx={"text-align":"center",
                                                    },
                                                children=[
                                                    mui.Typography(
                                                        f"{int(top3_data_enter['view_count_diff'].iloc[2])}",
                                                            variant='body2', 
                                                        sx={
                                                            "font-size" : "25px",
                                                            "fontWeight":"bold",
                                                            "text-align":"center",
                                                            "height":"30px"
                                                            },     
                                                        ),   
                                                    mui.Typography(
                                                        f"❤️{int(top3_data_enter['like_count_diff'].iloc[2])} +",
                                                            variant='body2', 
                                                        sx={
                                                            "font-size" : "14px",
                                                            "fontWeight":"bold",
                                                            "text-align":"center"
                                                            },     
                                                        ),    
                                                    ]
                                                ) 
                                            ]
                                        )  , key='item_3',sx={"borderRadius": '23px',
                                                    # "background": "linear-gradient(#13819b, #27b98e)"
                                                    # if "WAKTA" in f"{top3_data_enter['playlist_title'].iloc[2]}" else "linear-gradient(#e66465, #9198e5)"
                                                    })


                    # # 노래부분 top3
                        mui.Card(                            
                                mui.CardContent(
                                    sx={'display':'flex',
                                        'padding': '2px 0 0 0'
                                        },
                                    children=[
                                        mui.Typography( # 재생목록
                                                    f"🥇{top3_data_music['playlist_title'].iloc[0]}",
                                                    component="div",
                                                    sx={"font-size":"12px",
                                                        "padding-left": 10,
                                                        "padding-right": 10}                            
                                                ),
                                        mui.Link(
                                            "🔗",
                                            href=f"https://www.youtube.com/watch?v={top3_data_music['video_id'].iloc[0]}",
                                            target="_blank",
                                            sx={"font-size": "12px",
                                                "font-weight": "bold"}
                                                )                                                                                       
                                            ]                            
                                        ),                             
                            mui.CardMedia( # 썸네일 이미지
                                sx={ "height": 140,
                                    "ovjectFit":"cover",
                                    "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{top3_data_music['video_id'].iloc[0]}/sddefault.jpg)",
                                    }                            
                            ),
                            mui.CardContent( # 타이틀 조회수 증가량
                                    sx=hot_video_card_sx,
                                    children=[
                                        mui.Typography(
                                            f"{top3_data_music['title'].iloc[0]}",
                                            component="div",
                                            sx = title_sx                          
                                        ),
                                    
                                        mui.Divider(orientation="vertical",sx={"border-width":"1px"}), # divider 추가

                                        mui.Box(
                                            mui.Typography(
                                                f"{int(top3_data_music['view_count_diff'].iloc[0])}",
                                                    variant='body2', 
                                                sx={
                                                    "font-size" : "25px",
                                                    "fontWeight":"bold",
                                                    "text-align":"center",
                                                    "height":"30px"
                                                    },     
                                                ),   
                                            mui.Typography(
                                                f"❤️{int(top3_data_music['like_count_diff'].iloc[0])} +",
                                                    variant='body2', 
                                                sx={
                                                    "font-size" : "14px",
                                                    "fontWeight":"bold",
                                                    "text-align":"center"

                                                    },     
                                                ),    
                                            ) 
                                        ]
                                    )  , key='item_4',sx={"borderRadius": '23px',
                                                    # "background": "linear-gradient(#13819b, #27b98e)"
                                                    # if "WAKTA" in f"{top3_data_music['playlist_title'].iloc[0]}" else "linear-gradient(#e66465, #9198e5)"
                                                    })
                        
                        mui.Card(                            
                                mui.CardContent(
                                    sx={'display':'flex',
                                        'padding': '2px 0 0 0'
                                        },
                                    children=[
                                        mui.Typography( # 재생목록
                                                    f"🥈{top3_data_music['playlist_title'].iloc[1]}",
                                                    component="div",
                                                    sx={"font-size":"12px",
                                                        "padding-left": 10,
                                                        "padding-right": 10}                            
                                                ),
                                        mui.Link(
                                            "🔗",
                                            href=f"https://www.youtube.com/watch?v={top3_data_music['video_id'].iloc[1]}",
                                            target="_blank",
                                            sx={"font-size": "12px",
                                                "font-weight": "bold"}
                                                )                                                                                       
                                            ]                            
                                        ),                              
                            mui.CardMedia( # 썸네일 이미지
                                sx={ "height": 140,
                                    "ovjectFit":"cover",
                                    "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{top3_data_music['video_id'].iloc[1]}/sddefault.jpg)",
                                    }                            
                            ),
                            mui.CardContent( # 타이틀 조회수 증가량
                                    sx = hot_video_card_sx,
                                    children=[
                                        mui.Typography( # title
                                            f"{top3_data_music['title'].iloc[1]}",
                                            component="div",
                                            sx=title_sx                        
                                        ),
                                        mui.Divider(orientation="vertical",sx={"border-width":"1px"}), # divider 추가
                                        mui.Box( # 조회수 좋아요 증가량 
                                            mui.Typography(
                                                f"{int(top3_data_music['view_count_diff'].iloc[1])}",
                                                    variant='body2', 
                                                sx={
                                                    "font-size" : "25px",
                                                    "fontWeight":"bold",
                                                    "text-align":"center",
                                                    "height":"30px"
                                                    },     
                                                ),   
                                            mui.Typography(
                                                f"❤️{int(top3_data_music['like_count_diff'].iloc[1])} +",
                                                    variant='body2', 
                                                sx={
                                                    "font-size" : "14px",
                                                    "fontWeight":"bold",
                                                    "text-align":"center"

                                                    },     
                                                ),    
                                            ) 
                                        ]
                                    ), key='item_5',sx={"borderRadius": '23px',
                                                    # "background": "linear-gradient(#13819b, #27b98e)"
                                                    # if "WAKTA" in f"{top3_data_music['playlist_title'].iloc[1]}" else "linear-gradient(#e66465, #9198e5)"
                                                    })
                        
                        mui.Card(                        
                            mui.CardContent(
                                sx={'display':'flex',
                                    'padding': '2px 0 0 0'
                                    },
                                children=[
                                    mui.Typography( # 재생목록
                                                f"🥉{top3_data_music['playlist_title'].iloc[2]}",
                                                component="div",
                                                sx={"font-size":"12px",
                                                    "padding-left": 10,
                                                    "padding-right": 10}                            
                                            ),
                                    mui.Link(
                                        "🔗",
                                        href=f"https://www.youtube.com/watch?v={top3_data_music['video_id'].iloc[2]}",
                                        target="_blank",
                                        sx={"font-size": "12px",
                                            "font-weight": "bold"}
                                            )                                                                                       
                                        ]                            
                                    ),                                     
                        mui.CardMedia( # 썸네일 이미지
                            sx={ "height": 140,
                                "ovjectFit":"cover",
                                "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{top3_data_music['video_id'].iloc[2]}/sddefault.jpg)",
                                }                            
                            ) , 
                        mui.CardContent( # 타이틀 조회수 증가량
                                sx = hot_video_card_sx,
                                children=[
                                    mui.Typography( # 타이틀
                                        f"{top3_data_music['title'].iloc[2]}",
                                        component="div",
                                        sx=title_sx             
                                    ),
                                    mui.Divider(orientation="vertical",sx={"border-width":"1px"}), # divider 추가
                                    mui.Box(
                                        mui.Typography(
                                            f"{int(top3_data_music['view_count_diff'].iloc[2])}",
                                                variant='body2', 
                                            sx={
                                                "font-size" : "25px",
                                                "fontWeight":"bold",
                                                "text-align":"center",
                                                "height":"30px"
                                                },     
                                            ),   
                                        mui.Typography(
                                            f"❤️{int(top3_data_music['like_count_diff'].iloc[2])} +",
                                                variant='body2', 
                                            sx={
                                                "font-size" : "14px",
                                                "fontWeight":"bold",
                                                "text-align":"center"

                                                },     
                                            ),    
                                        ) 
                                    ]
                                )                                                              
                                ,key='item_6',sx={"borderRadius": '23px',
                                                # "background": "linear-gradient(#13819b, #27b98e)"
                                                # if "WAKTA" in f"{top3_data_music['playlist_title'].iloc[2]}" else "linear-gradient(#e66465, #9198e5)"
                                                })



 
 
        with col2: # VIDEO_REACT
            st.subheader(" 영상 반응 ")

            with st.container():
                with st.form(key='searchform_channel'):
                    col1,col2= st.columns([3,1])
                    with col1: # top3_title 을 고르면 해당하는 videoId를 가져옵니다.
                        # title
                        top3_title_selectbox = top3_data_enter['title'].tolist() + top3_data_music['title'].tolist()    
                        top3_title = st.selectbox('영상제목',top3_title_selectbox
                                                    , key='top3_title_timeinfo')
                        # videoId
                        videoId = merged_df[merged_df['title'] == top3_title]['video_id'].iloc[0] 

                    with col2: # submit
                        submit_search = st.form_submit_button(label="확인")

                    if submit_search:
                        with st.spinner('댓글수집중..'):
                            comment_df = get_comment(videoId)
                            pos_nega = nivo_pie(comment_df)               
                            most_common_words = wordCount(comment_df)

                            st.session_state.comment_df = comment_df 
                            st.session_state.pos_nega = pos_nega
                            st.session_state.most_common_words = most_common_words

                    if hasattr(st.session_state, 'comment_df'):
                        comment_df = st.session_state.comment_df
            
                        # 시간 정보 통합    
                        all_times = [time for times in comment_df['time_info'] for time in times]
                        minute_only = [int(time.split(':')[0]) for time in all_times]

                        # 구간별 빈도 계산
                        interval_counts = Counter(minute_only) 
                        highlight,highlight_cnt = interval_counts.most_common(1)[0]
                        highlight_seconds = highlight * 60

                        #nivo chart 데이터 형식으로 가공
                        nivo_time_info = [
                            {
                                "id": "view_info",
                                "data": [{"x": key, "y": value} for key, value in sorted(interval_counts.items())]
                            }
                        ]
                    else:
                        st.markdown(''' 
                                    ##### TOP3 영상 반응 요약  
                                    * `submit` 클릭시 해당영상의 댓글을 가져옵니다. 
                                    *  1000개 이상인 경우 좋아요를 1개 이상 받은 댓글들만 분석합니다.
                                    ##### 감성분석
                                    * 긍정과 중립/부정으로 댓글을 분석합니다. 
                                    * 사전에 인터넷, 커뮤니티 댓글로 학습된 언어모델을 이용합니다.
                                    * 정확도는 85% 입니다. 
                                    ##### 영상의 하이라이트 및 키워드
                                    * 시청자가 많이 언급한 장면을 요약합니다.
                                    * 영상에 많이 언급된 멤버들을 요약합니다.
                                    ''')

                    # st.dataframe(comment_df[comment_df['sentiment'] == '중립/부정']['comment'].sample(5))
 
                    
                    if hasattr(st.session_state, 'pos_nega'): # 댓글 긍정/부정 비율
                        pos_nega = st.session_state.pos_nega
                        positive_value = pos_nega[0]["value"]
                        negative_value = pos_nega[1]["value"]
                        
                        positive_per = round(positive_value/(positive_value + negative_value)*100,0)


                        st.markdown(f''' 
                                    ##### 📊 시청자 반응 (정확도 85%)
                                    > 불러온 댓글 중 :red[{positive_per}% 긍정]
                                    > :blue[{round(100-positive_per,0)}%]가 중립 혹은 부정적인 성격을 띄고 있습니다. 
                                    ''' )

                        with elements('media / pos_nega/ hilight'):
                                layout = [
                                    dashboard.Item("item_1", 0, 0, 1, 1),
                                    dashboard.Item("item_2", 2, 0, 1, 1),
                                    dashboard.Item("item_3", 0, 1, 2, 0.6),    
                                    dashboard.Item("item_4", 0, 0, 2, 2)                                
                                ]
                                with dashboard.Grid(layout):

                                    media.Player(url=f"https://youtu.be/{comment_df['video_id'].iloc[0]}?&t={highlight_seconds}"
                                                    ,controls=True, playing=True, volume = 0.2 , light=True, width='100%', height='100%',
                                                    key='item_1')      
                                                                                   
                                    mui.Box(  # pos_nega  
                                        nivo.Pie( 
                                            data=pos_nega,
                                            margin={"top": 10, "right": 30, "bottom": 25, "left": 20 },
                                            innerRadius={0.5},
                                            padAngle={2},
                                            activeOuterRadiusOffset={8},
                                            colors=['#ae8ed9','#68666e'],                   
                                            borderWidth={1},
                                            borderColor={
                                                "from": 'color',
                                                "modifiers": [
                                                    [
                                                        'darker',
                                                        0.2,
                                                        'opacity',
                                                        0.6
                                                    ]
                                                ]
                                            },
                                            enableArcLinkLabels=False,
                                            arcLinkLabelsSkipAngle={10},
                                            arcLinkLabelsTextColor="white",
                                            arcLinkLabelsThickness={0},
                                            arcLinkLabelsColor={ "from": 'color', "modifiers": [] },
                                            arcLabelsSkipAngle={10},
                                            arcLabelsTextColor={ "theme": 'background' },
                                            legends=[
                                                {
                                                    "anchor": "bottom",
                                                    "direction": "row",
                                                    "translateX": 0,
                                                    "translateY": 20,
                                                    "itemWidth": 50,
                                                    "itemsSpacing" : 5,
                                                    "itemHeight": 20,
                                                    "itemTextColor": "white",
                                                    "symbolSize": 7,
                                                    "symbolShape": "circle",
                                                    "effects": [
                                                        {
                                                            "on": "hover",
                                                            "style": {
                                                                "itemTextColor": "white"
                                                            }
                                                        }
                                                    ]
                                                }
                                            ],
                                            theme={
                                                # "background": "#0e1117",
                                                "textColor": "white",
                                                "tooltip": {
                                                    "container": {
                                                        "background": "#3a3c4a",
                                                        "color": "white",
                                                    }
                                                }
                                            },
                                        ),key="item_2", sx ={'borderRadius': '15px','background': '#262730'})

                                    mui.Box(  # 하이라이트       
                                        mui.CardContent(                                            
                                            mui.Typography(
                                                " TimeLine 하이라이트 ",
                                            component="div",
                                            color="text.secondary",
                                            sx={"font-size":"12px",
                                                "text-align" : "left",
                                                } 
                                            ),

                                        sx={    "padding-bottom": "0px",
                                                "padding-top":"5px"}
                                        ),

                                        nivo.Line(
                                            data= nivo_time_info,
                                            margin={'top': 10, 'right': 10, 'bottom': 30, 'left': 10},
                                            xScale={'type': 'point'},
                                            yScale={
                                                'type': 'linear',
                                                'min': 'auto',
                                                'max': 'auto',
                                                'stacked': True,
                                                'reverse': False
                                            },
                                            curve="cardinal",
                                            axisRight=None,
                                            axisBottom=None,
                                            axisLeft=None,

                                            colors= {'scheme': 'red_yellow_blue'},
                                            enableGridX = False,
                                            enableGridY = False,
                                            lineWidth=3,
                                            pointSize=0,
                                            pointColor='white',
                                            pointBorderWidth=1,
                                            pointBorderColor={'from': 'serieColor'},
                                            pointLabelYOffset=-12,
                                            enableArea=True,
                                            areaOpacity='0.15',
                                            useMesh=True,                
                                            theme={
                                                    # "background": "#100F0F", # #262730 #100F0F
                                                    "textColor": "white",
                                                    "tooltip": {
                                                        "container": {
                                                            "background": "#3a3c4a",
                                                            "color": "white",
                                                        }
                                                    }
                                                },
                                            animate= False
                                        ),key='item_3' ,sx={"borderRadius": '15px','background': '#262730'}) 
                                
                                     


                    if hasattr(st.session_state, 'most_common_words'): # 가장 많은 키워드
                        most_common_words = st.session_state.most_common_words
                        # word_df = pd.DataFrame(most_common_words, columns=['word', 'count'])                   
                        top_members = most_common_words[:5]
                        formatted_output = ' '.join([f"{member[0]}({member[1]})" for member in top_members])
                        menber_cnt = len(top_members)

                        # 멤버들의 이미지를 불러오기
                        member_images = get_member_images(top_members)
                        st.session_state.member_images = member_images
                        

                    if hasattr(st.session_state, 'member_images'):
                        member_images = st.session_state.member_images

                        try:
                            for i, member in enumerate(top_members):
                                name = member[0]
                                img = member_images[name]
                        
                            if img:                       
                                with st.container():
                                    st.markdown(f'''
                                        ##### 📊 영상 하이라이트                                               
                                        > :red[{highlight}분] 구간에 가장 많은 :red[하이라이트]가 있습니다. 
                                        썸네일을 클릭해서 하이라이트 장면을 확인해 보세요😀!
                                        * 영상에 언급이 많은 멤버 TOP5                                                                                                                    
                                        ''' )

                                    c1,c2,c3,c4,c5 = st.columns([1,1,1,1,1]) 
                                    with c1:
                                        if menber_cnt > 0 :
                                            st.image(member_images[top_members[0][0]], width=80)
                                            st.metric('hide',f'🥇{top_members[0][0]}',f'{top_members[0][1]}')

                                    with c2:
                                        if menber_cnt > 1 :
                                            st.image(member_images[top_members[1][0]], width=80)
                                            st.metric('hide',f'{top_members[1][0]}',f'{top_members[1][1]}')
                                    
                                    with c3:
                                        if menber_cnt > 2 :
                                            st.image(member_images[top_members[2][0]], width=80)
                                            st.metric('hide',f'{top_members[2][0]}',f'{top_members[2][1]}')
                                    
                                    with c4:
                                        if menber_cnt > 3 :
                                            st.image(member_images[top_members[3][0]], width=80)
                                            st.metric('hide',f'{top_members[3][0]}',f'{top_members[3][1]}')
                                    
                                    with c5:
                                        if menber_cnt > 4 :
                                            st.image(member_images[top_members[4][0]], width=80)
                                            st.metric('hide',f'{top_members[4][0]}',f'{top_members[4][1]}')

                        except KeyError:
                                st.markdown(f'''
                                            ##### 📊 영상 하이라이트                                               
                                            * :red[{highlight}분] 구간에 가장 많은 :red[하이라이트]가 있습니다.                                                                                 
                                            * 영상에 언급이 많은 멤버 TOP5
                                            * {formatted_output}
                                            ''' )                       

    st.divider()
# --------------------------------------------------------------------------------------------------------------------------------------------------------------- #

    with st.container(): # 일별 영상 조회수 순위?
        # 일간기준으로 조회수 증가량 top10 에 들어간 영상을 가져옵니다.  
        # 가장 많이 랭킹에 들어간 영상을 뽑아봅시다.
                
        today_rank = total_diff[['playlist_title','video_id','publishedAt','title','down_at','week_start','view_count_diff']].dropna()               
        rank_enter = today_rank[today_rank['playlist_title'].isin(['WAKTAVERSE : GOMEM ', 'ISEGYE IDOL (예능)'])]
        rank_music = today_rank[today_rank['playlist_title'].isin(['WAKTAVERSE : MUSIC', 'ISEGYE IDOL : MUSIC'])]

        @st.cache_resource
        def static(df,rank):
            df.sort_values(by=["down_at", "view_count_diff"], ascending=[True, False], inplace=True)
            df = df[df['view_count_diff'] > 0]
            df["rank"] = df.groupby("down_at")["view_count_diff"].rank(ascending=False, method='first').astype(int)
            
            today_rank_top = df[df['rank'] <= rank]

            static = today_rank_top.groupby(['playlist_title','title','video_id','publishedAt'])['view_count_diff'].agg(['mean', 'count']).round(0).reset_index()
            static = static.sort_values(by='count', ascending= False).head(5).reset_index()

            return static

        def static_week(df,rank):
            df.sort_values(by=["down_at", "view_count_diff"], ascending=[True, False], inplace=True)
            df = df[df['view_count_diff'] > 0]
            df['rank'] = df.groupby("week_start")["view_count_diff"].rank(ascending=False, method='first').astype(int)          
            
            week_rank_top = df[df['rank'] <= rank]

            static = week_rank_top.groupby(['playlist_title','title','video_id','publishedAt'])['view_count_diff'].agg(['mean', 'count']).round(0).reset_index()
            static = static_week.sort_values(by='count', ascending= False)
            

            return static
            

        static_music = static(rank_music, 1)
        static_enter = static(rank_enter, 5)

        col1,col2 = st.columns([1,1])
        with col1:
            st.subheader('📈 꾸준히 사랑받고 있는 영상(예능)')  
            st.caption('6월부터 지금까지 "전일대비 조회수 증가" 기준 꾸준히 상위권(5)에 들어가있는 예능영상 3개를 뽑아봤습니다.\
                    ')

            with elements("video_rank_enter"):
                layout=[
            
                    dashboard.Item(f"item_1", 0, 0, 1.3, 1, isDraggable=False, isResizable=True ),                    
                    dashboard.Item(f"item_2", 1.3, 0, 1.3, 1, isDraggable=False, isResizable=True ),                    
                    dashboard.Item(f"item_3", 2.6, 0, 1.3, 1, isDraggable=False, isResizable=True ),                    

                    ]
                with dashboard.Grid(layout):
                    mui.Card(
                            mui.CardMedia( # 썸네일 이미지
                                sx={ "height": 150, #h_dGGxhH6YQ
                                    "ovjectFit":"contain",
                                    "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{static_enter['video_id'].iloc[0]}/sddefault.jpg)","borderRadius": "15px",
                                }                            
                            ),
                            mui.CardContent(
                                mui.Typography('')
                            )
                            , key='item_1',sx={'borderRadius':'15px'})


                    mui.Card(
                            mui.CardMedia( # 썸네일 이미지
                                sx={ "height": 150, #h_dGGxhH6YQ
                                    "ovjectFit":"contain",
                                    "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{static_enter['video_id'].iloc[1]}/sddefault.jpg)","borderRadius": "15px",
                                }                            
                            )                                                                                              
                            , key='item_2',sx={'borderRadius':'15px'})
                    
                    mui.Card(
                            mui.CardMedia( # 썸네일 이미지
                                sx={ "height": 150, #h_dGGxhH6YQ
                                    "ovjectFit":"contain",
                                    "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{static_enter['video_id'].iloc[2]}/sddefault.jpg)","borderRadius": "15px",
                                }                            
                            )                                                                                              
                            , key='item_3',sx={'borderRadius':'15px'})                             




            with st.expander("See DATA"):
                st.markdown(f'''
                        #### 풀영상 길이에도 불구하고 ..
                        "{static_enter['title'].iloc[0]}", "{static_enter['title'].iloc[1]}", "{static_enter['title'].iloc[2]}"
                        * 게시된지 1년 이상이 지났지만 상위권 
                        * 대표적으로 :green[합방, 같이보기, 반응] 타입의 영상이 꾸준히 사랑받고 있습니다.
                        * 이세계아이돌 3집 신곡 "KIDDING"의 대성공으로 안무영상이 큰 관심을 받고 있습니다. 
                        * 이세돌, 고멤이 많이 모일수록 시너지가 큽니다.                        
                        ''')  
                
                static_enter['day'] = (today - static_enter['publishedAt'] ).dt.days
                static_enter = static_enter.rename(columns={'count': 'rank_in_cnt', 'mean': 'mean_view'})       
                st.divider()
                st.dataframe(static_enter[['title','day','rank_in_cnt','mean_view']])

        with col2:
            st.subheader('🥇 1위를 가장 많이한 영상(음악)')
            st.caption(f'(2023-06-23 ~ {now_time}) "전일대비 조회수 증가" 기준 1위를 많이한 영상 TOP3입니다.')


            with elements("video_rank_music"):
                layout=[
              
                    dashboard.Item(f"item_1", 0, 0, 1.3, 1, isDraggable=False, isResizable=True ),                    
                    dashboard.Item(f"item_2", 1.3, 0, 1.3, 1, isDraggable=False, isResizable=True ),                    
                    dashboard.Item(f"item_3", 2.6, 0, 1.3, 1, isDraggable=False, isResizable=True ),                    

                    ]
                with dashboard.Grid(layout):
                    mui.Card(                     
                            mui.CardMedia( # 썸네일 이미지
                                sx={ "height": 150, #h_dGGxhH6YQ
                                    "ovjectFit":"contain",
                                    "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{static_music['video_id'].iloc[0]}/sddefault.jpg)","borderRadius": "15px",
                                }                            
                            )                                                      
                             , key='item_1',sx={'borderRadius':'15px'})                            

                    mui.Card(
                            mui.CardMedia( # 썸네일 이미지
                                sx={ "height": 150, #h_dGGxhH6YQ
                                    "ovjectFit":"contain",
                                    "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{static_music['video_id'].iloc[1]}/sddefault.jpg)","borderRadius": "15px",
                                }                            
                            )                                                                                              
                             , key='item_2',sx={'borderRadius':'15px'})
                    
                    mui.Card(
                            mui.CardMedia( # 썸네일 이미지
                                sx={ "height": 150, #h_dGGxhH6YQ
                                    "ovjectFit":"contain",
                                    "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{static_music['video_id'].iloc[2]}/sddefault.jpg)","borderRadius": "15px",
                                }                            
                            )                                                                                              
                             , key='item_3',sx={'borderRadius':'15px'})       
            

            with st.expander("See DATA"):
                static_music['day'] = (today - static_music['publishedAt'] ).dt.days
                static_music = static_music.rename(columns={'count': 'rank_in_cnt', 'mean': 'mean_view'})       

                st.markdown(f'''
                        ##### {static_music['title'].iloc[0]}
                        * 왁타버스 cover/official곡 중, 1위를 가장 많이한 영상입니다.
                        * 영상이 게시된지 :green[{static_music['day'].iloc[0]}]일 동안 :green[{static_music['rank_in_cnt'].iloc[0]}]번 1위 (일별기준)
                        ''')  
                
                st.divider()
                st.dataframe(static_music[['title','day','rank_in_cnt','mean_view']])



    st.divider()        
 # --------------------------------------------------------------고멤 TOP 5 !!-----------------------------------------------------------------------------------------  #

    if comment_data is not None:
        if hasattr(st.session_state, 'comment_data'):
            comment_data = st.session_state.comment_data

        else:
            # comment_data = pd.read_csv(uploaded_file)
            # comment_data['date'] = pd.to_datetime(comment_data['date'], errors='coerce')
            # comment_data['year'] = comment_data['date'].dt.year
            # comment_data['month'] = comment_data['date'].dt.month

            # # st.session_state에 df가 존재하지 않는 경우, 파일을 읽어와서 저장
            # comment_data = gomem_tmp(comment_data)            
            nivo_gomem = monthly_gomem(comment_data)

            comment_data = comment_data.groupby(['video_id','title','year','month'])['tmp'].sum().reset_index()

            st.session_state.comment_data = comment_data 
            st.session_state.nivo_gomem = nivo_gomem

            
        with st.container():
            col1,col2 = st.columns([1.2,2])
            with col1:
                st.subheader('🤡 월별 고정멤버 언급량 TOP5 ')
                st.caption('올해 활약한 멤버 top5를 확인해보세요! ')
                with st.form(key="waktaverse_aka_comment"):
                    c1,c2,c3 = st.columns([1,2,1])       

                    with c1:
                        month_option = st.selectbox('month',[11,10,9,8,7,6,5,4,3,2,1,'all'], key='gomem_month')
                        most_gomem, most_aka = gomem_comment(comment_data,'tmp', 2023, month_option)                    
                        
                        st.session_state.most_gomem = most_gomem
                        st.session_state.most_aka = most_aka

                    with c2:
                        if hasattr(st.session_state, 'most_gomem'):
                            most_gomem = st.session_state.most_gomem
                        if hasattr(st.session_state, 'most_aka'):
                            most_aka = st.session_state.most_aka

                        gomem_aka = st.selectbox('month',['고정멤버','아카데미'], key='gomem_aka')
                        
                        if gomem_aka == '고정멤버':
                            gomem_aka = most_gomem
                            gomem = [item[0] for item in gomem_aka]

                        elif gomem_aka == '아카데미':
                            gomem_aka = most_aka
                            gomem = [item[0] for item in gomem_aka]

                    with c3:                    
                        gomem_img = get_member_images(gomem_aka)                        
                        st.session_state.gomem_img = gomem_img                        
                        submit_search = st.form_submit_button("확인")



                    if hasattr(st.session_state, 'gomem_img'):
                        gomem_img = st.session_state.gomem_img
                        if month_option == 'all':
                            caption = f'2023년 ":green[왁타버스(예능)]" 영상에서 가장 반응이 뜨거웠던 (언급이 많았던) 멤버입니다.'
                        else:
                            caption = f'{month_option}월 ":green[왁타버스(예능)]" 영상에서 가장 반응이 뜨거웠던 (언급이 많았던) 멤버입니다.'
                            
                        st.caption(caption)



                        # st.caption(f'{month_option}월 ":green[왁타버스(예능)]" 영상에서 가장 반응이 뜨거웠던 (언급이 많았던) 멤버입니다.')

                        try:
                            for i, member in enumerate(gomem_aka):
                                name = member[0]
                                img = gomem_img[name]
                        
                            if img:                       
                                with st.container():
                                    c1,c2,c3,c4,c5 = st.columns([1,1,1,1,1]) 
                                    with c1:
                                        if len(gomem) > 0 :
                                            st.image(gomem_img[gomem_aka[0][0]], width=80)
                                            st.metric('hide',f'🥇{gomem_aka[0][0]}',f'{gomem_aka[0][1]}')

                                    with c2:
                                        if len(gomem) > 1 :
                                            st.image(gomem_img[gomem_aka[1][0]], width=80)
                                            st.metric('hide',f'{gomem_aka[1][0]}',f'{gomem_aka[1][1]}')
                                    
                                    with c3:
                                        if len(gomem) > 2 :
                                            st.image(gomem_img[gomem_aka[2][0]], width=80)
                                            st.metric('hide',f'{gomem_aka[2][0]}',f'{gomem_aka[2][1]}')
                                    
                                    with c4:
                                        if len(gomem) > 3 :
                                            st.image(gomem_img[gomem_aka[3][0]], width=80)
                                            st.metric('hide',f'{gomem_aka[3][0]}',f'{gomem_aka[3][1]}')
                                    
                                    with c5:
                                        if len(gomem) > 4 :
                                            st.image(gomem_img[gomem_aka[4][0]], width=80)
                                            st.metric('hide',f'{gomem_aka[4][0]}',f'{gomem_aka[4][1]}')

                        except KeyError:
                                st.write('error')

                if hasattr(st.session_state, 'nivo_gomem'):
                    nivo_gomem = st.session_state.nivo_gomem
                    gomem_option = st.selectbox('gomem', gomem, key='gomem_name')
                    gomem_hot_video = gomem_video(comment_data, gomem_option) 

                    filter_data = [item for item in nivo_gomem if item['id'] in gomem_option]

                with elements("gomem_nivo"):
                    layout=[            
                        dashboard.Item("item_1", 0, 0, 5, 1.5)
                        ]
                    with dashboard.Grid(layout):

                        mui.Box( # 재생목록별 전체 조회수 증가량
                            children =[
                                mui.Typography(f' (2023) {gomem_option} 월별 언급량',
                                            variant="body2",
                                            color="text.secondary",sx={"text-align":"left","font-size":"14px"}),

                                nivo.Line(
                                data= filter_data,
                                margin={'top': 20, 'right': 30, 'bottom': 30, 'left': 40},
                                xScale={'type': 'point',
                                        },

                                curve="cardinal",
                                axisTop=None,
                                axisRight=None,
                                axisBottom=True,

                                # axisLeft={
                                #     'tickSize': 4,
                                #     'tickPadding': 10,
                                #     'tickRotation': 0,
                                #     'legend': '조회수',
                                #     'legendOffset': -70,
                                #     'legendPosition': 'middle'
                                # },
                                colors= {'scheme': 'accent'},
                                enableGridX = False,
                                enableGridY = False,
                                enableArea = True,
                                areaOpacity = 0.3,
                                lineWidth=2,
                                pointSize=5,
                                pointColor='white',
                                pointBorderWidth=0.5,
                                pointBorderColor={'from': 'serieColor'},
                                pointLabelYOffset=-12,
                                useMesh=True,
                                legends=[
                                            {
                                            'anchor': 'top-left',
                                            'direction': 'column',
                                            'justify': False,
                                            # 'translateX': -30,
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
                                        # "background-color": "rgba(158, 60, 74, 0.2)",
                                        "textColor": "white",
                                        "tooltip": {
                                            "container": {
                                                "background": "#3a3c4a",
                                                "color": "white",
                                            }
                                        }
                                    },
                                animate= True)
                                
                                ] ,key="item_1")


            with col2:
                st.markdown(f''' 
                            ### {gomem_option} 영상 더보기
                            *  :green[{gomem_option}]의 언급량이 많은 대표 영상 TOP5 입니다!  ''' )

                with elements("gomem_hot_video"):
                        layout=[
                    
                            dashboard.Item(f"item_0", 0, 0, 2, 1.5, isDraggable=False, isResizable=False  ), #isDraggable=False, isResizable=True                    
                            dashboard.Item(f"item_1", 2, 0, 2, 1.5, isDraggable=False, isResizable=False ),                    
                            dashboard.Item(f"item_2", 4, 0, 2, 1.5, isDraggable=False, isResizable=False ),                    
                            dashboard.Item(f"item_3", 0, 2, 2, 1.5, isDraggable=False, isResizable=False ),                    
                            dashboard.Item(f"item_4", 2, 4, 2, 1.5, isDraggable=False, isResizable=False ),                    

                            ]
                        with dashboard.Grid(layout):
                            for i in range(5):
                                mui.Box(
                                        mui.CardContent( # 재생목록/링크
                                            sx={'display':'flex',
                                                'padding': '2px 0 0 0'
                                                },
                                            children=[
                                                mui.Typography(
                                                            f"{gomem_option} 추천 영상",
                                                            component="div",
                                                            sx={"font-size":"12px",
                                                                "padding-left": 10,
                                                                "padding-right": 10}                            
                                                        ),
                                                mui.Link(
                                                    "🔗",
                                                    href=f"https://www.youtube.com/watch?v={gomem_hot_video['video_id'].iloc[i]}",
                                                    target="_blank",
                                                    sx={"font-size": "12px",
                                                        "font-weight": "bold"}
                                                        )                                                                                       
                                                    ]                            
                                                ),


                                        mui.CardMedia( # 썸네일 이미지
                                            sx={ "height": 150,
                                                "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{gomem_hot_video['video_id'].iloc[i]}/sddefault.jpg)",
                                                # "mt": 0.5
                                                },
                                            ),

                                        mui.CardContent( # 타이틀 조회수증가량
                                            sx = hot_video_card_sx,
                                            children=[
                                                mui.Typography( # 타이틀
                                                    f"{gomem_hot_video['title'].iloc[i]}",
                                                    component="div",
                                                    sx=title_sx                           
                                                ),
                                            
                                                mui.Divider(orientation="vertical",sx={"border-width":"1px"}), # divider 추가
                                            
                                                mui.Box(
                                                    sx={"align-items": "center"},
                                                    children = [
                                                        mui.Typography(
                                                            f"{int(gomem_hot_video['cnt'].iloc[i])}",
                                                                variant='body2', 
                                                            sx={
                                                                "font-size" : "25px",
                                                                "fontWeight":"bold",
                                                                "text-align":"center",
                                                                "height":"30px"
                                                                },     
                                                            ),   
                                                        mui.Typography(
                                                            "언급량",
                                                                variant='body2', 
                                                            sx={
                                                                "font-size" : "10px",
                                                                "fontWeight":"bold",
                                                                "text-align":"center"
                                                                },     
                                                            )
                                                        ]                                                        
                                                    ),
                                                ]
                                            )                       
                                                ,key=f'item_{i}',sx={"borderRadius": '23px'})





# ---------------------------------------------------------- 이세돌 3집 컴백 챌린지 영상 추세----------------------------------------------------------------------------------- #    
    st.divider()

    if isaedol is not None:
        if hasattr(st.session_state, 'isaedol'):
            isaedol = st.session_state.isaedol

        else:
            isaedol = pd.read_csv('csv_data/이세계아이돌_video_2312.csv')
            st.session_state.isaedol = isaedol 


        with st.container():
            st.subheader('🎧(Youtube) 이세계아이돌 챌린지 영상 추세 ')            
            st.caption(' Youtube 에서 "이세계아이돌"과 관련된 영상들이 얼마나 늘어나고 있는지 추세를 확인해보세요! (검색했을 때 뜨는 기준)')

            isaedol['publishedAt'] = pd.to_datetime(isaedol['publishedAt']).dt.strftime('%Y-%m-%d')
            isaedol['publishedAt'] = pd.to_datetime(isaedol['publishedAt'], format='%Y-%m-%d')
            isaedol['year'] = isaedol['publishedAt'].dt.year 
            isaedol['month'] = isaedol['publishedAt'].dt.month 

            isaedol = isaedol[isaedol['year'] > 2021]

            # isae_channel = ['아이네 INE','우왁굳의 돚거','비챤 VIichan','고세구 GOSEGU','왁타버스 WAKTAVERSE','비챤의 나랑놀아','징버거 JINGBURGER','주르르 JURURU','릴파의 꼬꼬','고세구의 좀 더']
            # isaedol['channel'] = '그 외 채널'
            # isaedol.loc[isaedol['channelTitle'].isin(isae_channel),'channel'] ='이세돌/우왁굳 채널'

            isaedol['channel'] = '일반 영상'
            isaedol.loc[isaedol['title'].str.contains('Cover|COVER|cover|커버|챌린지|challenge'),'channel'] ='커버 및 챌린지'

            count_by_year_month = isaedol.groupby(['year', 'month','channel']).size()
            count_df = count_by_year_month.reset_index(name='count')

            total = isaedol.groupby(['year','month']).size()
            total = total.reset_index(name='count')

            channel1_df = count_df[count_df['channel'] == '일반 영상']
            channel2_df = count_df[count_df['channel'] == '커버 및 챌린지']

            # count 값을 한 행씩 더하기
            channel1_df['cumulative_count'] = channel1_df['count'].cumsum() # 누적합 함수 cunsum()
            channel2_df['cumulative_count'] = channel2_df['count'].cumsum()
            total['cumulative_count'] = total['count'].cumsum()

            channel1_df['date'] = channel1_df['year'].astype(str) + '-' + channel1_df['month'].astype(str)
            channel2_df['date'] = channel2_df['year'].astype(str) + '-' + channel2_df['month'].astype(str)
            total['date'] = total['year'].astype(str) + '-' + total['month'].astype(str)


            total['prev_count'] = total['cumulative_count'].shift(1)

            # 상승률 계산
            total['growth_rate'] = round(((total['cumulative_count'] - total['prev_count']) / total['prev_count']) * 100,0)

            col3, col4 = st.columns([2,1])
        
            with col3:

                    def plot_graph():
                        # 데이터 설정
                        x1 = total['date']
                        y1 = total['cumulative_count']

                        x2 = channel2_df['date']
                        y2 = channel2_df['cumulative_count']

                        x3 = channel1_df['date']
                        y3 = channel1_df['cumulative_count']

                        # 그래프의 크기 설정
                        fig, ax = plt.subplots(figsize=(10, 5))
                        fig.set_facecolor('white')
                        ax.set_facecolor('white')

                        # 그래프 그리기 (두 개의 라인 차트를 겹쳐서 표시)
                        plt.plot(x1, y1, marker='o', markersize=3, linestyle='-', color='black', label='total')
                        plt.plot(x2, y2, marker='o', markersize=3, linestyle='-', color='green', label='cover/challenge')
                        plt.plot(x3, y3, marker='o', markersize=3, linestyle='-', color='gray', label='general video')

                        # x 라벨과 y 라벨 설정
                        plt.xlabel('year/month', fontsize=12)
                        plt.ylabel('count',  fontsize=12)

                        # 제목 설정
                        plt.title('(Youtube hashtag) #IsaegayeIdol Charts', fontsize=15)

                        # 세로선 추가
                        plt.axvline(x='2023-6', color='#FF4646', linestyle='--', label='(Kakao Webtoon OST) RockDown/Another world ')
                        plt.axvline(x='2023-8', color='#FF9614', linestyle='--', label='(3rd album) Kidding released')
                        plt.axvline(x='2023-9', color='#FFD732', linestyle='--', label='Isaegye Festival')

                        # 그래프 표시
                        plt.legend()
                        plt.xticks(rotation=45)
                        plt.yticks()
                        plt.tight_layout()

                        st.pyplot(fig)  # Streamlit에 그래프 출력

                    plot_graph()

            with col4:
                    st.markdown(''' 
                                > 🔥이세계아이돌 HOT ISSUE 2023         

                                * (2023.06~07) 카카오웹툰 OST 'RockDown, Another world' EP발매                         
                                * (2023.08.18) 3집 앨범 'Kidding' 발매 
                                * (2023.09.23) '이세계페스티벌' 이세계아이돌 첫공연
                                * (2023.10.08) 서울 이세계아이돌 옥외 스크린 홍보
                                ''')

                    st.markdown('''                                                        
                                > 6월부터 최근 4개월간 이세계아이돌 영상이 :red[209% 증가]했습니다. 
                                
                                **3집 "Kidding"** 을 발표하고 안무 챌린지를 시작하면서 :green[커버곡과 쇼츠폼의 안무챌린지 형태의 영상들]이 많이 늘어나고 있습니다. \n                            
                                **이세계페스티벌 공연** 이후 이세계아이돌의 **무대영상, 페스티벌 VLOG 영상**을 통해 대중들에게 좀 더 다가가는 중입니다.
                                
                                ''')



    st.divider()

# ------ 왁타버스 차트 -------------------------------------------------------------------------------------------------------------------------------------

    st.header("WAKTAVERSE Chart")

    with st.container(): 
        with st.form(key="WAKTAVERSE Chart submit"):
            col0,col1,col2,col3 = st.columns([1,1,3,0.5])
            with col0:
                year_option = st.selectbox('Year',['2023','2022','2021','ALL'], key='year')
            with col1:
                month_option = st.selectbox('Month', ['12','11','10','9','8','7','6','5','4','3','2','1','ALL',], key='month')
            with col2:
                list_option = st.selectbox('재생목록', options = playlist_titles, key='pli')
            with col3:
                submit_search = st.form_submit_button("확인")


            if year_option == 'ALL' :
                filtered_df = merged_df[(merged_df['playlist_title'] == list_option)]
            elif month_option == 'ALL' :
                filtered_df = merged_df[(merged_df['playlist_title'] == list_option) & (merged_df['year'] == year_option)]
            else:
                filtered_df = merged_df[(merged_df['playlist_title'] == list_option) & (merged_df['year'] == year_option) & (merged_df['month'] == month_option)]
       
            filtered_df['prev_view_count'] = filtered_df.groupby('video_id')['view_count'].shift().fillna(0)
            filtered_df['view_count_diff'] = filtered_df['view_count'] - filtered_df['prev_view_count']
                      
            
# --------- 주간별 증가량 nivo_bar chart 위한 # filtered_df 복사-----------------------------------------------------------------------------------------


        new_df = filtered_df.copy() 
        new_df['down_at'] = pd.to_datetime(filtered_df['down_at'], format='%Y-%m-%d')
        new_df = new_df[new_df['down_at'] >='2023-06-19']  # 6월 17일부터 데이터를 수집했기 때문에 그 다음 차이가 계산되는 19일 부터 집계해야한다. (18일 데이터는 없음음)
        new_df['week_start'] = new_df['down_at'] - pd.to_timedelta(new_df['down_at'].dt.dayofweek, unit='d')
        weekly_df = new_df.groupby(['video_id', 'week_start'])['view_count_diff'].sum().reset_index()
        weekly_df['week_start'] = pd.to_datetime(weekly_df['week_start']).dt.strftime('%m-%d')


# -------- nivo_chart 를 위한 데이터 형식 가공 ------------------------------------------------------------------------------------------------------------

    if not filtered_df.empty : 

        # 날짜 데이터를 str 로 바꿔야함
        filtered_df['down_at'] = pd.to_datetime(filtered_df['down_at']).dt.strftime('%m-%d')
        filtered_df['publishedAt'] = pd.to_datetime(filtered_df['publishedAt']).dt.strftime('%Y-%m-%d')
    
        main_data = []
        for video_id, group in filtered_df.groupby('video_id'):
            if len(group) > 0:
                
                title = group.iloc[0]['title']
                publishedAt = group.iloc[0]['publishedAt']
                view_count = group.iloc[-1]['view_count']
                like_count = group.iloc[-1]['like_count'] 
                comment_count = group.iloc[-1]['comment_count']
                view_count_diff = group.iloc[-1]['view_count_diff']

                first_view_count = 0

                weekly_group = weekly_df[weekly_df['video_id'] == video_id]
                weekly_diff_data = [{'x': week_start, 'y': view_count_diff} for week_start, view_count_diff in zip(weekly_group['week_start'], weekly_group['view_count_diff'])]

                main_data.append({
                    'id': title,
                    'video_id': video_id,
                    'publishedAt': publishedAt,
                    'view_count': view_count,
                    'like_count': like_count,
                    'comment_count': comment_count,
                    'view_count_diff': view_count_diff,
                    'data': [{'x': publishedAt, 'y': first_view_count}] + [{'x': down_at, 'y': view_count} for down_at, view_count in zip(group['down_at'], group['view_count']) if down_at >= '06-19'],
                    'diff_data': [{'x': down_at, 'y': view_count_diff} for down_at, view_count_diff in zip(group['down_at'], group['view_count_diff']) if down_at >= '06-19'],
                    'weekly_diff': weekly_diff_data,
                })
        # st.write(main_data)

        # sort 옵션
        with st.container():
            col1,col2,_ = st.columns([10,2,0.1])
            with col1:
                st.markdown(f""" ### 📊 ({year_option}) {list_option}  """)
            with col2:
                sort_option_count = st.selectbox('정렬기준', ['최신순','전일대비 증가순','조회수','좋아요'], key='sort_count')
                
                if sort_option_count == '최신순':
                    main_data = sorted(main_data, key=lambda x: x['publishedAt'], reverse=True)
                elif sort_option_count == '전일대비 증가순':
                    main_data = sorted(main_data, key=lambda x: x['view_count_diff'], reverse=True)
                elif sort_option_count == '조회수':
                    main_data = sorted(main_data, key=lambda x: x['view_count'], reverse=True)
                elif sort_option_count == '좋아요':
                    main_data = sorted(main_data, key=lambda x: x['like_count'], reverse=True)

        # (line) 조회수 그래프
        nivo_data = []
        for item in main_data:
            extracted_item = {
                "id": item["id"],
                "video_id": item["video_id"],
                "data": item["data"],
            }
            nivo_data.append(extracted_item)

        # (line) 전일대비 증가량
        diff_nivo_data = []
        for item in main_data:
            extracted_item = {
                "id": item["id"],
                "video_id": item["video_id"],
                "data": item["diff_data"]
            }
            diff_nivo_data.append(extracted_item)

        # 7일 단위로 합치기
        # new_nivo_data= []
        # for item in nivo_data:
        #     if len(item["data"]) > 7:

        #         # 7일씩 합치기
        #         new_data = [item["data"][0]]
        #         for i in range(1, len(item["data"])):
        #             if i % 7 == 0:
        #                 new_data.append(item["data"][i])
                
        #         new_data.append(item["data"][-1])

        #         # 수정된 데이터를 새로운 리스트에 추가
        #         item["data"] = new_data

        #     # 수정된 데이터를 새로운 리스트에 추가
        #     new_nivo_data.append(item)
        # st.write(new_nivo_data)

    # (nivo_bar) 전일대비 증가량  차트 
        nivo_bar_data = []
        for item in main_data:
            extracted_item = {
                "diff_data": item["diff_data"],
            }
            nivo_bar_data.append(extracted_item)

    # (nivo_bar) 주간 조회수 증가량
        nivo_bar_week = []
        for item in main_data:
            extracted_item = {
                "weekly_diff" : item["weekly_diff"]
            }
            nivo_bar_week.append(extracted_item)

        n = min(len(nivo_data), 30)
    else:
        n = 0
        # st.write('NO DATA')  

# 컨텐츠 (썸네일, line_chart, bar_chart)
    for i in range(n):
        with st.container():
            with elements(f"item{i + 1}"):
                layout = [
                    dashboard.Item("first_item", 0, 0, 2.7, 1.8, isDraggable=False),
                    dashboard.Item("second_item", 2.7, 0, 7, 1.8, isDraggable=False),
                    dashboard.Item("third_item", 10, 0, 1.8, 1.8)
                ]
                with dashboard.Grid(layout):
                    mui.Card( # 썸네일,좋아요,댓글,링크           
                        children=[      
                            mui.Typography(
                                f" {main_data[i]['publishedAt']}",
                                color="text.secondary",
                                sx={"font-size": "8px",
                                    "text-align":"left",
                                    "padding-left":"12px",
                                    "padding-top" : "2px"
                                    },                                            
                            ),
                            mui.CardMedia( # 썸네일 이미지
                                sx={ "height": 170,
                                    "ovjectFit":"cover",
                                    "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://i.ytimg.com/vi/{nivo_data[i]['video_id']}/sddefault.jpg)",
                                    "borderRadius": '5%', 
                                    "backgroundPosition": "top 80%",
                                    # "border": "1.5px solid white",  # 흰색 경계선 추가
                                    },                                
                                title = '썸네일'
                                    ),
                            mui.CardContent(  # 타이틀 
                                sx={"padding-top": "10px",
                                    "padding-bottom":"10px",
                                    "max-height": "100%",
                                    "overflow": "hidden"},

                                    children=[
                                        mui.Typography( # title
                                            f"{nivo_data[i]['id']}",
                                            component="div",
                                            sx={"font-size":"15px",
                                                "fontWeight":"bold",
                                                "height":"45px",
                                                "max-height": "100%",
                                                "overflow": "hidden",
                                                }                            
                                        )],

                                ),
                                                                
                            mui.CardContent( # 댓글 좋아요 링크
                                sx={"display": "flex",
                                    "padding-top": "0",
                                    "padding-bottom":"0",
                                    "gap": "60px",
                                    "align-items": "center", # "position": "fixed"
                                    },
                                    
                                children=[

                                    mui.Typography(
                                            f"❤️ {main_data[i]['like_count']}  댓글 {main_data[i]['comment_count']} ",
                                            variant="body2",
                                            sx={"font-size": "12px"},                                            
                                        ),

                                    mui.Link(
                                        "💻Youtube",
                                        href=f"https://www.youtube.com/watch?v={nivo_data[i]['video_id']}",
                                        target="_blank",
                                        sx={"font-size": "12px",
                                            "font-weight": "bold",
                                            }
                                    ),
                                ]
                            ),
                            
                            ] ,key="first_item",sx={"background-color" : "#0E0E0E", "background-size" : "cover","borderRadius": '20px'})
                            
                    mui.Box(  # nivo_line       
                            nivo.Line(
                                data= [diff_nivo_data[i]],
                                margin={'top': 50, 'right': 50, 'bottom': 20, 'left': 70},
                                xScale={'type': 'point'},
                                yScale={
                                    'type': 'linear',
                                    'min': 'auto',
                                    'max': 'auto',
                                    'stacked': True,
                                    'reverse': False
                                },
                                curve="cardinal",
                                axisRight=None,
                                axisBottom=None,
                                # {
                                #     'tickCount': 5,
                                #     'tickValues': tickValues,  # X축 값들 사이에 구분선을 그리기 위해 설정
                                #     'tickSize': 0,
                                #     'tickPadding': 5,
                                #     'tickRotation': 0,
                                #     'legendOffset': 36,
                                #     'legendPosition': 'middle',
                                # },
                                axisLeft={
                                    'tickSize': 4,
                                    'tickPadding': 10,
                                    'tickRotation': 0,
                                    'legend': '조회수',
                                    'legendOffset': -100,
                                    'legendPosition': 'middle'
                                },
                                colors=  {'scheme': 'accent'},
                                enableGridX = False,
                                enableGridY = False,
                                lineWidth=3,
                                pointSize=0,
                                pointColor='white',
                                pointBorderWidth=1,
                                pointBorderColor={'from': 'serieColor'},
                                pointLabelYOffset=-12,
                                enableArea=True,
                                areaOpacity='0.15',
                                useMesh=True,                
                                theme={
                                        # "background": "#100F0F", # #262730 #100F0F
                                        "textColor": "white",
                                        "tooltip": {
                                            "container": {
                                                "background": "#3a3c4a",
                                                "color": "white",
                                            }
                                        }
                                    },
                                animate= False)
                                
                            # mui.CardContent(
                            #     mui.Typography(
                            #         '최근 7일 평균 조회수 평균 좋아요 '
                            #     )
                            # )
                                ,key='second_item' ,sx={"borderRadius": '15px',"display":"flex","background-color" : "#0E0E0E"},elevation=2) # "background-color":"#0E0E0E"
                    
                    mui.Box( # 전일 대비 조회수
                        sx={"background-color":"#0E0E0E","borderRadius": '15px'},
                        children=[
                            mui.CardContent(
                                # sx={"background-color":"black"},
                                children=[
                                    mui.Typography(
                                        f"{int(main_data[i]['view_count']):,}",
                                        # if main_data[i]['view_count'] >= 1000000 else f"{int(main_data[i]['view_count']):,}",

                                        variant="body2",
                                        sx={
                                            "font-size": "30px",
                                            "fontWeight":"bold",
                                            "text-align": "center",                                            
                                            "mb":0.5} ,                                            
                                    ),
                                    mui.Typography(
                                        f"전일 대비 증가 ",
                                        component="div",
                                        sx={"font-size":"14px",
                                            "text-align": "center",
                                            # "fontWeight":"bold",
                                            } 
                                    ),
                                    mui.Typography(
                                        f"🔥{round(main_data[i]['view_count_diff'])}🔥" 
                                        if main_data[i]['view_count_diff'] >= 100000 else f"{round(main_data[i]['view_count_diff'])}🔺",
                                        # component="div",
                                        sx={"text-align": "center",
                                            "font-size" : "24px",
                                            }
                                    ),
                                ]                    
                            ),
                            mui.Divider(),
                            mui.CardContent(
                                # sx={"pt" : "0"},
                                children=[
                                    mui.Typography(
                                        f"주간 조회수 상승",
                                        component="div",
                                        color="text.secondary",
                                        sx={"font-size":"12px",
                                            "text-align" : "center"}                        
                                    ),
                                ]
                            ),

                            nivo.Bar(
                                data = nivo_bar_week[i]["weekly_diff"],
                                keys=["y"],  # 막대 그래프의 그룹을 구분하는 속성
                                indexBy="x",  # x축에 표시할 속성

                                margin={"top": 10, "right": 30, "bottom": 200, "left": 30},
                                padding={0.5},

                                valueScale={ "type" : 'linear' },
                                indexScale={ "type": 'band', "round": 'true'},
                                borderRadius={4},
                                colors={ 'scheme': 'category10' },

                                innerRadius=0.3,
                                padAngle=0.7,
                                activeOuterRadiusOffset=8,
                                enableGridY= False,
                                axisLeft=None,  # Y축 단위 제거
                                axisBottom=None,

                                enableLabel=False,

                                labelSkipWidth={10},
                                labelSkipHeight={36},

                                theme={
                                        # "background": "black",
                                        "textColor": "white",
                                        "tooltip": {
                                            "container": {
                                                "background": "#3a3c4a",
                                                "color": "white",
                                            }
                                        }
                                    })                       
                                ], key = 'third_item')
                

                pass


else:
    st.write('NO DATA')








