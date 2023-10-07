import re
import streamlit as st
import numpy as np
import pandas as pd
import requests
import pickle
import isodate
import warnings
warnings.filterwarnings("ignore")

from datetime import datetime as dt
from tqdm import tqdm
from googleapiclient.discovery import build

from ckonlpy.tag import Twitter

import tensorflow as tf
from keras.models import Model, load_model
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences
from soynlp.normalizer import *

from dotenv import load_dotenv

from PIL import Image, ImageDraw

# -------------------------------------------------------- yotube api v3 ------------------------------------------------------------- #
# api_key = os.getenv('api_key')
# DEVELOPER_KEY = api_key
# YOUTUBE_API_SERVICE_NAME = "youtube"
# YOUTUBE_API_VERSION = "v3"


DEVELOPER_KEY = (
    # Very Important Point
    st.secrets["youtube_api_key"]
).get('DEVELOPER_KEY')

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)


# -------------------------------------------------- youtubue api 와 관련된 def ------------------------------------------------------- #

# 채널id 가져오기
def get_channel_id(api_key, channel_name):
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={channel_name}&type=channel&key={api_key}"
    response = requests.get(url)
    data = response.json()
    channel_Id = data["items"][0]["id"]["channelId"]

    return channel_Id

# 구독자수
def get_sub(api_key,channel_Id):
    url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_Id}&fields=items/statistics&key={api_key}"
    response = requests.get(url)
    data = response.json()
    subscribe = data["items"][0]["statistics"]["subscriberCount"]

    return subscribe

# 재생목록 별로 가져오기
def get_playlist (channel_Id,api_key):
    playlist = 'https://www.googleapis.com/youtube/v3/playlists?part=snippet,contentDetails&channelId={}&maxResults=50&key={}'

    url = playlist.format(channel_Id, api_key)
    response = requests.get(url)
    data = response.json()

    play_list = []
    for item in data['items']:
        id = item['id']
        title = item['snippet']['title']
        play_list.append({'id': id, 'title': title})

    df = pd.DataFrame(play_list)
    playlist = df.rename(columns={'id': 'playlistId', 'title': 'playlist_title'})       
    playlist_ids = playlist['playlistId'].tolist()

    return playlist, playlist_ids

# 재생목록별 동영상 id 
def get_playlist_video(playlist_id, api_key):
    video_url = 'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&status=&playlistId={}&key={}'
    results = []
    page_token = None
    while True:
        url = video_url.format(playlist_id, api_key)
        if page_token:
            url += '&pageToken={}'.format(page_token)
        response = requests.get(url)
        data = response.json()
        items = data['items']
        for item in items:
            snippet = item['snippet']
            playlistId = snippet['playlistId']
            publishedAt = snippet['publishedAt']
            title = snippet['title']
            video_id = snippet['resourceId']['videoId']
            published_year = int(publishedAt[:4])
            
            if published_year in [2021,2022,2023]:
                results.append({'playlistId': playlistId, 'publishedAt': publishedAt, 'title': title, 'video_id': video_id})
                if len(results) >= 1000:
                    break
        page_token = data.get('nextPageToken')
        if not page_token:
            break
    return results

def get_all_playlist_videos(playlist_ids, api_key):
    video = []
    for playlist_id in playlist_ids:
        video_data = get_playlist_video(playlist_id, api_key)
        video.extend(video_data)

    video_df = pd.DataFrame(video)
    video_ids = video_df['video_id'].tolist()

    return video_df, video_ids

# 본채널 재생목록
def get_all_playlist_videos_wak(wakgood_playlist, api_key):
    data = {
        "channelname": [
            "마크",
            "vrchat",
            "핫클립,하이라이트",
            "합방,시리즈,기타 컨텐츠",
            "노가리",
            "똥겜",
            "왁튜브 처음 추천",
            "gta5",
            "아르마 랜덤 고지전",
            "vr게임"
        ],
        "channel_list": [
            "PLfASGV4peeDRjN43IAUD8E_ocPpQ-pLLj",
            "PLfASGV4peeDSYeZd-ANyFhQCpTdpEDoZU",
            "PLfASGV4peeDSrok3-5jYJbEYZkSLIm6XV",
            "PLfASGV4peeDR8dgzL-2HSOeFzaeNGPvsJ",
            "PLfASGV4peeDQki0gGkzjhnSIjd_ZwSLap",
            "PLfASGV4peeDRf016kTwfYaRZuL2591HW9",
            "PLfASGV4peeDR20eG9x1FcaFdynFu5_fgc",
            "PLfASGV4peeDRXzcvphetxpbNwDvARKKdS",
            "PLfASGV4peeDS2rd97gC0gRjVf-I3ekC1c",
            "PLfASGV4peeDRSU8ZykUEHqERUh7lZQ0I2"
        ]
    }
    
    wakgood = pd.DataFrame(data)
    wakgood_playlist = wakgood['channel_list'].tolist()

    video = []
    for playlist_id in wakgood_playlist:
        video_data = get_playlist_video(playlist_id, api_key)
        video.extend(video_data)

    video_df = pd.DataFrame(video)
    video_ids = video_df['video_id'].tolist()

    return video_df, video_ids

# 영상별 조회수 및 좋아요 static
def get_static(video_ids, api_key):
    url_template = 'https://www.googleapis.com/youtube/v3/videos?id={}&key={}&part=statistics'
    
    result_static = []
    for video_id in video_ids:
        url = url_template.format(video_id, api_key)
        response = requests.get(url)
        static = response.json()
        result_static.append(static)

    video_ids = []
    view_counts = []
    like_counts = []
    comment_counts = []

    for item in result_static:
        try:
            video_id = item['items'][0]['id']
            view_count = item['items'][0]['statistics']['viewCount']
            like_count = item['items'][0]['statistics']['likeCount']
            comment_count = item['items'][0]['statistics']['commentCount']
        except (KeyError,IndexError):
            continue
        video_ids.append(video_id)
        view_counts.append(view_count)
        like_counts.append(like_count)
        comment_counts.append(comment_count)


    static_df = pd.DataFrame({'video_id': video_ids,
                'view_count': view_counts,
                'like_count': like_counts,
                'comment_count': comment_counts})
    
    static_df['view_count'] = static_df['view_count'].astype(int)
    static_df['like_count'] = static_df['like_count'].astype(int)
    static_df['comment_count'] = static_df['comment_count'].astype(int)


    return static_df

# 최근 영상 최대 1000개 [2023,2022,2021]
def scroll(channel_Id):
      video_list = []
      # 스크롤이 되지 않을 때까지 nextpageToken 무한 호출
      try :
          res = youtube.channels().list(id=channel_Id, part='contentDetails').execute()
          # 플레이리스트 가져오기
          playlist_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']

          # playlist_id = 'PLfASGV4peeDSYeZd-ANyFhQCpTdpEDoZU' #각 재생목록 마다 고유 아이디가 있음 # 그런데 플레이리스트id 형식이 아니라 전체동영상을 가져오는듯?

          next_page = None
          # 영상 개수가 1000이 넘지 않도록 수집
          while len(video_list) < 1000:
              # 다음 페이지의 Token 반환
              res = youtube.playlistItems().list(playlistId=playlist_id,part='snippet',maxResults=50,pageToken=next_page).execute()
              video_list += res['items']
              next_page = res.get('nextPageToken')

              if next_page is None :
                  break
          # 영상 JSON 데이터 리스트 반환
          return video_list

      except Exception as e:
          print('API 호출 한도 초과') # API 할당량 초과 예외처리
          return video_list

# 영상의 길이
def video_duration(video_ids, api_key):
    data = []
    for video_id in video_ids:
        url = f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails&id={video_id}&key={api_key}"
        response = requests.get(url)
        video_data = response.json()

        try:
            duration = video_data['items'][0]['contentDetails']['duration']
            data.append({'video_id': video_id, 'Duration': duration})
        except KeyError:
            data.append({'video_id': video_id, 'Duration': 'Unknown'})

    # DataFrame 생성
    duration_df = pd.DataFrame(data)

    def iso_to_seconds(iso_duration):
        time_delta = isodate.parse_duration(iso_duration)
        return int(time_delta.total_seconds())

    duration_df['seconds'] = duration_df['Duration'].apply(iso_to_seconds)
    
    return duration_df


# 수익 계산용 
def benfit_cal(df):

    df['ad_count'] = 1
    df.loc[df['seconds'] >= 480,'ad_count'] = 2
    df.loc[df['seconds'] >= 1800,'ad_count'] = 4
    df.loc[df['seconds'] < 10,'ad_count'] = 0
    
    df['ad_benefit'] = (3500 * (df['view_count'] * 0.6) / 1000) * 0.55

    df.loc[df['playlist_title'] == 'shorts', 'ad_benefit'] = (120 * df['view_count'] * 1 / 1000) * 0.55
    df.loc[df['playlist_title'].str.contains('MUSIC'),'ad_benefit'] = 0

    df.loc[df['title'].str.contains('COVER|cover|Cover|OST'), 'ad_benefit'] = 0

    df['cost'] = (df['seconds']/60) * 30000
    df.loc[df['seconds'] > 1500, 'cost'] = 100000
    

    df['benefit'] = df['ad_benefit'] - df['cost']
 
    df['ad_benefit'] = df['ad_benefit'].astype(int)
    df['cost'] = df['cost'].astype(int)
    df['benefit'] = df['benefit'].astype(int)    
    df['reaction'] = df['like_count'] + df['comment_count']
    
    return df
