import pandas as pd
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import bigquery,storage
import datetime

import tempfile
now = datetime.datetime.now()

# yotube api -------------------------------------------------------------------------------------

api_key = "AIzaSyBTP9fVCvF9ncANetp4SPn8PZls6Oh4bjI" 
DEVELOPER_KEY = api_key
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)

channel_name = '고세구'

# ------------------------------------------------------------------------------------------------


# 채널id 가져오기
def get_channel_id(api_key, channel_name):
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={channel_name}&type=channel&key={api_key}"
    response = requests.get(url)
    data = response.json()
    channel_Id = data["items"][0]["id"]["channelId"]

    return channel_Id

### 재생목록 별로 가져오기
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
            
            if published_year in [2023]:
                results.append({'playlistId': playlistId, 'publishedAt': publishedAt, 'title': title, 'video_id': video_id})
                if len(results) >= 2:
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


def main():
    channel_Id = get_channel_id(api_key, channel_name)
    playlist, playlist_ids  = get_playlist(channel_Id, api_key)
    video_df, video_ids = get_all_playlist_videos(playlist_ids, api_key)
    static_df = get_static(video_ids, api_key)

    total_df = pd.merge(static_df, video_df, on='video_id')    
    df = pd.merge(total_df, playlist, on='playlistId') 
    df = df.drop_duplicates(subset=['video_id', 'playlistId']) # 중복행 제거
    df = df[['playlist_title','playlistId','video_id','title','publishedAt','view_count','like_count','comment_count']] 
    now = datetime.datetime.now()
    df['down_at'] = now.strftime('%Y-%m-%d')


    credentials_file = 'C:\scraping\my-project-72981-c4ea0ddcafb9.json'
    cd = service_account.Credentials.from_service_account_file(credentials_file)
    client = storage.Client(credentials= cd)

    # 데이터프레임을 CSV 파일로 저장
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        df.to_csv(temp_file.name, index=False, encoding='utf-8-sig') 

    # 업로드할 버킷과 파일 경로 설정
    bucket_name = f'waktaverse/{channel_name}'
    blob_name = f'{channel_name}_{now}.csv'  # 버킷에 저장될 파일 이름

    # 버킷과 연결된 Blob 객체 생성
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)

    # 파일 업로드
    blob.upload_from_filename(temp_file.name)

    # project_id = 'my-project-72981'
    # dataset_id = 'wakta'  # 데이터셋 ID
    # table_id = 'static'  # 테이블 ID

    # destination_table = f"{project_id}.{dataset_id}.{table_id}"

    # df.to_gbq(destination_table, project_id, if_exists='replace', credentials=cd)


main()


# cd = service_account.Credentials.from_service_account_file('my-project-72981-c4ea0ddcafb9.json')

# project_id = 'my-project-72981'
# dataset_id = 'wakta'  # 데이터셋 ID
# table_id = 'static'  # 테이블 ID

# destination_table = f"{project_id}.{dataset_id}.{table_id}"

# df.to_gbq(destination_table, project_id, if_exists='replace', credentials=cd)



# 인증 정보를 지정하는 JSON 파일 경로
# credentials_file = 'C:\scraping\my-project-72981-c4ea0ddcafb9.json'
# cd = service_account.Credentials.from_service_account_file(credentials_file)
# client = storage.Client(credentials= cd)
