import re
import streamlit as st
import numpy as np
import pandas as pd
import requests
import pickle


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

from collections import Counter
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

# ------------------------------------------------------------------------------------------------------------------------------------ #


word_freq_counter = Counter()
twi = Twitter()

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
import isodate
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

def benfit_cal(df):

    df['ad_count'] = 1
    df.loc[df['seconds'] >= 480,'ad_count'] = 2
    df.loc[df['seconds'] >= 1800,'ad_count'] = 4
    df.loc[df['seconds'] < 10,'ad_count'] = 0

    df['ad_benefit'] = (3500 * (df['view_count'] * 0.6) / 1000) * 0.55
    df.loc[df['title'].str.contains('COVER|cover|Cover|OST'), 'ad_benefit'] = 0

    df['cost'] = (df['seconds']/60) * 20000
    df.loc[df['seconds'] > 1500, 'cost'] = 100000
   
    df['benefit'] = df['ad_benefit'] - df['cost']
 
    df['ad_benefit'] = df['ad_benefit'].astype(int)
    df['cost'] = df['cost'].astype(int)
    df['benefit'] = df['benefit'].astype(int)    

    return df



# ------------------------------------------------------------- sentiment test ------------------------------------------------------------- #

# 댓글 가져오고 / sentiment 적용
def get_comment(videoId):
    # videoId = 'Lm1AiWIMbO0'
    comments = list()
    response = youtube.commentThreads().list(part='snippet,replies', videoId = videoId, maxResults=100).execute()

    while response:
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']
            comments.append([comment['textDisplay'], comment['likeCount']]) # comment['publishedAt'],

            if item['snippet']['totalReplyCount'] > 0:
                for reply_item in item['replies']['comments']:
                    reply = reply_item['snippet']
                    comments.append([reply['textDisplay'],  reply['likeCount']]) #reply['publishedAt'], 

        if 'nextPageToken' in response:
            response = youtube.commentThreads().list(part='snippet,replies', videoId = videoId, pageToken=response['nextPageToken'], maxResults=100).execute()
        else:
            break

    comment_df = pd.DataFrame(comments)
    comment_df.columns = ['comment', 'like']
    comment_df['video_id'] = videoId

    def extract_time_info(comment):
        time_pattern = r"(\d+:\d+)</a>"  # youtube timeline 의 경우, </a> 태그로 감싸져있음.
        time_info = re.findall(time_pattern, comment)
        return time_info
    
    comment_df['time_info'] = comment_df['comment'].apply(extract_time_info)      
    comment_df['comment'] = comment_df['comment'].apply(lambda x: re.sub('[^ㄱ-ㅎㅏ-ㅣ가-힣 ]+', '',x))
    comment_df['comment'] = comment_df['comment'].apply(lambda x: emoticon_normalize(x, num_repeats=3))


    if len(comment_df['comment']) > 1000: # 댓글이 1000 개 이상인경우 좋아요 조건
        comment_df = comment_df[comment_df['like'] > 0]
        comment_df[['score', 'tmp']] = comment_df['comment'].apply(lambda x: pd.Series(sentiment_predict(x)))
    else: 
        comment_df[['score', 'tmp']] = comment_df['comment'].apply(lambda x: pd.Series(sentiment_predict(x)))
    
    return comment_df



# 토크나이져
tokenizer_pickle_path = "C:/scraping/model/tokenizer.pickle"
with open(tokenizer_pickle_path, "rb") as f:
    tokenizer = pickle.load(f)

# 모델
@st.cache_resource
def loaded_model():
    model = load_model('C:/scraping/model/Bilstm.h5')
    return model
nlp_model = loaded_model()

# 토크나이져 
@st.cache_data
def load_tokenizer():
    with open(tokenizer_pickle_path, "rb") as f:
        tokenizer = pickle.load(f)

    return tokenizer
tokenizer = load_tokenizer()

# ------------------------------------------------------------------------------------------------------------------------------------------- #

gomem = ['루숙','해루석','뢴트','뢴트게늄','풍신','단답','단단벌레','하쿠',
          '춘식','곽춘식','김치만두번영택사스가','김치만두','만두',
          '캘칼','캘리칼리','캘리칼리데이빈슨',
          '왁파고','황파고','파고','혜지','독고혜지','히키퀸','히키킹',
          '도파민','파민','융터르','카르나르','융털','권민','호드','덕수','이덕수',
          '프리터','소피아','춘피아','비지니스킴','비킴']

akadam = ['설리반','캡틴설리반','불곰','길버트','닌닌',
          '미미짱짱','세용','진희','지니','시리안','젠투','젠크리트',
          '셈이','수셈이','빅토리','발렌타인','발렌','아마최','아마데우스최']

isedol = ['이세돌','이세계','챠니','챤이','비챤','릴파','르르땅','주르르','아잉네','아이네','세구','고세구','눈나구','지구즈','언니즈','막내즈','부산즈','개나리즈']

def sentiment_predict(comment):
    words = [
          (['우왁굳','왁굳','영택'],'Noun'), (['천양','대월향'],'Noun'),          
          # 이세돌, 고멤,아카
          (isedol,'Noun'), (gomem,'Noun'),(akadam,'Noun'),

          # 그외 단어들
          ('헨타이','Noun'), ('튽훈','Noun'),('가성비','Noun'),
          (['레전드','레게노'],'Noun'), (['아웃트로','인트로'],'Noun'),(['브이알챗','브이알'],'Noun'),(['수듄','고로시','뇌절'],'Noun'),(['킹아','킹애','존맛탱'],'Adjective'),
          (['상현','하현'],'Noun'), (['고멤','고정멤버','아카데미'],'Noun'), (['고단씨','준구구','준99'],'Noun'),(['십덕','씹덕','오타쿠'],'Noun'),                        
          (['ㄱㅇㅇ','ㄹㄱㄴ','ㄺㄴ','ㅅㅌㅊ','ㅎㅌㅊ','ㅆㅅㅌㅊ','ㅆㅎㅌㅊ'],'KoreanParticle'),
          (['눕프로해커','눕프핵','마크','마인크래프트','왁파트','똥겜'],'Noun'), ('상황극','Noun'), ('족마신','Noun')
            ]

    for word in words:
        name, poomsa = word
        twi.add_dictionary(name, poomsa)

    stopwords = ['의', '가', '은', '는','이', '과', '도', '를', '으로', '자', '에', '하고', '세요', '니다', '입니다',
                '하다', '을', '이다', '다', '것', '로', '에서', '그', '인', '서', '네요', '음', '임','랑',
                '게', '요', '에게', '엔', '이고', '거', '예요', '이에요', '어요', '어서', '여요', '하여']

    comment = re.sub(r'[^ㄱ-ㅎㅏ-ㅣ가-힣 ]','', comment)
    tmp = twi.morphs(comment, norm=True, stem=True)  #토큰화
    tmp = [word for word in tmp if not word in stopwords]  #불용어 제거
    encoded = tokenizer.texts_to_sequences([tmp])
    pad_new = pad_sequences(encoded, maxlen = 44)
    score = float(nlp_model.predict(pad_new))

    return score, tmp

# sentiment 결과를 nivo_data 형태로
def nivo_pie(comment_df):
    comment_df['sentiment'] = comment_df['score'].apply(lambda x:'호감' if x > 0.5 else'중립/부정')
    positive = comment_df[comment_df['sentiment'] =='호감'].shape[0]
    negative = comment_df[comment_df['sentiment'] == '중립/부정'].shape[0]
    pos_nega = [
        {"id": "호감", "label": "호감", "value": positive},
        {"id": "중립/부정", "label": "중립/부정", "value": negative}
    ]
    return pos_nega

# 댓글의 키워드 분석
word_rules = {
    # "우왁굳" : ['왁굳','영택','오영택','우왁굳','왁굳형'],
    "뢴트게늄" : ['뢴트게늄','뢴트','초코푸딩'],
    "해루석" : ['루숙','해루석','해루숙','루석'],
    "캘리칼리": ['캘칼', '캘리칼리', '캘리칼리데이빈슨'],
    "도파민" :['도파민','파민','박사'],
    "소피아" : ['소피아','춘피아'],
    "권민" : ['권민','쿤미옌'],
    "왁파고": ['왁파고', '파고', '황파고'],
    "독고혜지": ['혜지','독고혜지'],
    "비밀소녀": ['비소','비밀소녀','비밀이모'],
    "히키킹" : ['히키킹','히키퀸','히키킹구'],
    "곽춘식" : ['춘식','곽춘식','춘피아'],
    "김치만두" : ['만두','김치만두번영택사스가','김치만두','만두'],
    "하쿠" : ['하쿠','미츠네 하쿠'],
    "비즈니스킴":['비킴','비즈니스킴'],
    "풍신" :['풍신'],
    "프리터":['프리터'],
    "단답벌레" : ['단답벌레','단답'],
    "융터르" : ['카르나르','융털','융터르'],
    "호드" : ['호드','노스페라투스'],
    "이덕수" : ['덕수','이덕수'],

    "미미짱짱세용" : ['미미짱짱세용','세용'],
    "닌닌" : ['닌닌'],
    "젠투" : ['젠투','젠크리트'],
    "수셈이" : ['셈이','수셈이'],
    "아마최" : ['아마데우스최','아마최'],
    "진희" : ['진희','지니'],
    "수셈이": ['셈이','수셈이'],
    "발렌타인" : ['발렌','발렌타인'],
    "시리안": ['시리안'],
    "길버트":['길버트'],
    "빅토리":['빅토리'],

    "이세돌" :['이세돌','세돌','이세계아이돌'],
    "아이네" : ['아이네','아잉네','햄이네'],
    "징버거" : ['징버거','버거','버거땅'],
    "릴파" : ['릴파'],
    "주르르" : ['르르땅','주르르','르르'],
    "고세구" : ['고세구','세구땅','세구','눈나구','막내즈'],
    "비챤" : ['챠니','챤이','비챤','막내즈']
}



def wordCount(comment_df):
    all_tmp = [word for sublist in comment_df['tmp'] for word in sublist] # word = 리스트 속 ['단어들']
 
#   통일된 단어들만 추출
    unified_words = []
    for word in all_tmp:
        for unified_word, variations in word_rules.items():
            if word in variations:
                unified_words.append(unified_word)
                break
 
    unified_tmp = Counter(unified_words)
    most_common_words = unified_tmp.most_common(10)

    return most_common_words


def get_member_images(top_members):

    member_images = {}
    for i, member in enumerate(top_members):
        name = member[0]
        image_path = f"C:/scraping/img/{name}.jpg"  # 이미지 파일 이름 생성 
        img = Image.open(image_path).convert("RGBA")

        # 원형으로 크롭
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + img.size, fill=255)
        img.putalpha(mask)

        # 크기 조절
        img = img.resize((80, 80))

        member_images[name] = img

    return member_images







# 단어를 통일시키는 함수
def unify_word(word, gomem_word):
    for unified_word, variations in gomem_word.items():
        if word in variations:
            return unified_word
    return word

def unify_tmp(tmp, gomem_word):
    return [unify_word(word, gomem_word) for word in tmp] # tmp 에 있는 word 들을 

# 월별 고멤 언급량
def gomem_comment(df, col, year, month):
    if month == 'all':
        df = df[df['year'] == year]
    else:
        df = df[(df['year'] == year) & (df['month'] == month)]

    all_tmp = [word for sublist in df[col] for word in sublist] # word = 리스트 속 ['단어들']

    gomem_word = {
        # "우왁굳" : ['왁굳','영택','오영택','우왁굳','왁굳형'],
        "뢴트게늄" : ['뢴트게늄','뢴트','초코푸딩'],
        "해루석" : ['루숙','해루석','해루숙','루석'],
        "캘리칼리": ['캘칼', '캘리칼리', '캘리칼리데이빈슨'],
        "도파민" :['도파민','파민','박사','할배즈'],
        "소피아" : ['소피아','춘피아'],
        "권민" : ['권민','쿤미옌'],
        "왁파고": ['왁파고', '파고', '황파고'],
        "독고혜지": ['혜지','독고혜지'],
        "비밀소녀": ['비소','비밀소녀','비밀이모'],
        "히키킹" : ['히키킹','히키퀸'],
        "곽춘식" : ['춘식','곽춘식','춘피아'],
        "김치만두" : ['김치만두','만두','김치만두번영택사스가'],
        "하쿠" : ['하쿠','미츠네 하쿠'],
        "비즈니스킴":['비킴','비즈니스킴'],
        "풍신" :['풍신','할배즈'],
        "프리터":['프리터'],
        "단답벌레" : ['단답벌레','단답'],
        "융터르" : ['카르나르','융털','융터르'],
        "호드" : ['호드','노스페라투스'],
        "이덕수" : ['덕수','이덕수','할배즈'],
    }

    aka_word = {   
        "미미짱짱세용" : ['미미짱짱세용','세용'],
        "닌닌" : ['닌닌'],
        "젠투" : ['젠투','젠크리트'],
        "수셈이" : ['셈이','수셈이'],
        "아마최" : ['아마데우스최','아마최'],
        "진희" : ['진희','지니'],
        "수셈이": ['셈이','수셈이'],
        "발렌타인" : ['발렌','발렌타인'],
        "시리안": ['시리안'],
        "길버트":['길버트'],
        "빅토리":['빅토리'],
        "설리반":['설리반']
    }
    # 통일된 단어들만 추출 (gomem_word에 있는 단어들만 포함)

    unified_tmp = unify_tmp(all_tmp, gomem_word)
    unified_tmp = [word for word in unified_tmp if word in gomem_word]
    
    unified_tmp = Counter(unified_tmp)
    most_gomem = unified_tmp.most_common(5)

    return most_gomem

# 최종 실행함수

@st.cache_data
def monthly_gomem(df):
  # 월별로 데이터를 계산하고 저장할 딕셔너리를 초기화합니다.
    gomem_chart = {}

  # 각 월별 데이터 계산 및 저장
    for month in range(1, 10):
        most_common_words = gomem_comment(df, 'tmp', 2023, month)
        month_data = [{'id': gomem_name, 'count': count} for gomem_name, count in most_common_words]
        gomem_chart[month] = month_data

  # 고멤 이름을 추출합니다.(중복x)
    member_names = set(item['id'] for month_data in gomem_chart.values() for item in month_data)

  # 결과를 담을 리스트를 초기화합니다.
    result = []

    # 각 고멤에 대한 데이터를 생성합니다.
    for member_name in member_names:
        member_data = {
            "id": member_name,
            "data": []
        }
        for month, month_data in gomem_chart.items():
            month_count = next((item['count'] for item in month_data if item['id'] == member_name), 0)
            member_data['data'].append({
                "x": month,
                "y": month_count
            })
        
        result.append(member_data)

    return result


def count_word(word_list, target_word):
    return word_list.count(target_word)


# 최종 실행함수 원하는 '고멤' 언급이 많은 video_id 찾기
def gomem_video(df, gomem):  
  
  # 단어통일
  df['tmp'] = df['tmp'].apply(lambda x: unify_tmp(x, word_rules))
  # '고멤' 단어가 언급된 빈도를 계산하여 데이터프레임에 추가
  df['cnt'] = df['tmp'].apply(lambda x: count_word(x, gomem))
  gomem_hot_video = df[df['cnt'] == df['cnt']].nlargest(5,'cnt')[['video_id','title','cnt']]

  # 결과 출력
  return gomem_hot_video


def gomem_tmp(df):

    # df['comment'] = df['comment'].str.replace("[^ㄱ-ㅎㅏ-ㅣ가-힣 ]"," ")
    # df['comment'].replace('', np.nan, inplace=True)  #비어 있는 행은 null값으로 처리
    # df.dropna(how='any', inplace=True)  #null 값 제거

    words = [
        (['우왁굳','왁굳','영택'],'Noun'), (['천양','대월향'],'Noun'),
        # 이세돌, 고멤,아카
        (isedol,'Noun'), (gomem,'Noun'),(akadam,'Noun'),

        # 그외 단어들
        ('헨타이','Noun'), ('튽훈','Noun'),('가성비','Noun'),
        (['레전드','레게노'],'Noun'), (['아웃트로','인트로'],'Noun'),(['브이알챗','브이알'],'Noun'),(['수듄','고로시','뇌절'],'Noun'),(['킹아','킹애','존맛탱'],'Adjective'),
        (['상현','하현'],'Noun'), (['고멤','고정멤버','아카데미'],'Noun'), (['고단씨','준구구','준99'],'Noun'),(['십덕','씹덕','오타쿠'],'Noun'),
        (['ㄱㅇㅇ','ㄹㄱㄴ','ㄺㄴ','ㅅㅌㅊ','ㅎㅌㅊ','ㅆㅅㅌㅊ','ㅆㅎㅌㅊ'],'KoreanParticle'),
        (['눕프로해커','눕프핵','마크','마인크래프트','왁파트','똥겜'],'Noun'), ('상황극','Noun'), ('족마신','Noun')
            ]

    for word in words:
        name, poomsa = word
        twi.add_dictionary(name, poomsa)

        stopwords = ['의', '가', '은', '는','이', '과', '도', '를', '으로', '자', '에', '하고', '세요', '니다', '입니다',
                    '하다', '을', '이다', '다', '것', '로', '에서', '그', '인', '서', '네요', '음', '임','랑',
                    '게', '요', '에게', '엔', '이고', '거', '예요', '이에요', '어요', '어서', '여요', '하여']

    text_token = []
    for sentence in tqdm(df['comment']):
        tmp = []
        tmp = twi.morphs(sentence, stem=True, norm=True)  #토큰화
        tmp = [word for word in tmp if not word in stopwords]  #불용어 제거
        text_token.append(tmp)

    df['tmp'] = text_token
    
    return df