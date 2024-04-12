import os
import time
from googleapiclient.discovery import build
from google.oauth2 import service_account
from pytube.exceptions import AgeRestrictedError
from pytube import Playlist, YouTube
from pydub import AudioSegment

MIN_DURATION = 61
MAX_DURATION = 420

def create_subdirectories(parent_directory, category, name):
    subdirectory = os.path.join(parent_directory, category, name)
    if not os.path.exists(subdirectory):
        os.makedirs(subdirectory)
    return subdirectory

def replace_invalid_characters(string):
    invalid_characters = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_characters:
        string = string.replace(char, '-')
    return string

def download_audio(playlist_url, channel_id, path_to_save, download_video=False):
    if not os.path.exists(path_to_save):
        os.makedirs(path_to_save)

    if playlist_url:
        playlist = Playlist(playlist_url)
        playlist_title = replace_invalid_characters(playlist.title)
        playlist_directory = create_subdirectories(path_to_save, "playlist", playlist_title)

        for video in playlist.videos:
            print(f'Tải xuống video: {video.title}')
            if download_video:
                video_stream = video.streams.filter(progressive=True, file_extension='mp4').first()
                video_file = video_stream.download(output_path=playlist_directory)
                print(f"Đã tải xuống video: {video.title}")
            else:
                video_stream = video.streams.filter(only_audio=True).first()
                audio_file = video_stream.download(output_path=playlist_directory)
                
                mp4_path = os.path.join(playlist_directory, audio_file)
                mp3_filename = os.path.splitext(audio_file)[0] + ".mp3"
                mp3_path = os.path.join(playlist_directory, mp3_filename)
                audio = AudioSegment.from_file(mp4_path, format="mp4")
                audio.export(mp3_path, format="mp3")

                os.remove(mp4_path)
                print(f"Đã chuyển đổi và xoá {audio_file}")

    elif channel_id:
        SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

        credentials = service_account.Credentials.from_service_account_info({

            file_service_account

        })

        youtube = build('youtube', 'v3', credentials=credentials)

        channel_request = youtube.channels().list(
            part='snippet',
            id=channel_id,
        )

        try:
            channel_response = channel_request.execute()
            channel_title = replace_invalid_characters(channel_response['items'][0]['snippet']['title'])

            channel_directory = create_subdirectories(path_to_save, "channel", channel_title)

        except Exception as e:
            print(f"Lỗi khi truy cập kênh: {e}. Vui lòng đảm bảo rằng channel_id là hợp lệ và tệp JSON của dịch vụ có quyền truy cập vào YouTube Data API v3.")
            return

        next_page_token = None
        file_counter = 1
        retry_count = 2  

        downloaded_songs = {}

        while True:
            try:
                video_request = youtube.search().list(
                    part='snippet',
                    channelId=channel_id,
                    type='video',
                    maxResults=50,
                    pageToken=next_page_token  
                ).execute()

                for item in video_request['items']:
                    video_id = item['id']['videoId']
                    video_title = replace_invalid_characters(item['snippet']['title'])

                    if any(substring in video_title.lower() for substring in ['karaoke', 'demo']):
                        print(f"Bỏ qua video '{video_title}' vì là video Karaoke/Demo.")
                        continue

                    try:
                        yt = YouTube('https://www.youtube.com/watch?v=' + video_id)
                        if download_video:
                            video_stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
                            video_file = video_stream.download(output_path=channel_directory)
                            print(f"Đã tải xuống video: {video_title}")
                        else:
                            stream = yt.streams.filter(only_audio=True).first()

                            if not stream:
                                print(f"Không tìm thấy stream âm thanh cho video '{video_title}'.")
                                continue

                            if yt.length >= MIN_DURATION and yt.length <= MAX_DURATION:
                                if video_title in downloaded_songs:
                                    print(f"Video'{video_title}' đã được tải xuống. Bỏ qua...")
                                    continue

                                audio_file = stream.download(output_path=channel_directory, filename=video_id + '.mp4')

                                audio = AudioSegment.from_file(audio_file, format="mp4")
                                mp3_filename = f"{video_title}.mp3"  
                                mp3_path = os.path.join(channel_directory, mp3_filename)
                                audio.export(mp3_path, format="mp3")

                                os.remove(audio_file)
                                downloaded_songs[video_title] = True  
                                print(f"{file_counter}. Đã tải bài --> {video_title}")
                                file_counter += 1
                            else:
                                print(f"Video '{video_title}' có thời lượng không phù hợp và sẽ không được tải xuống.")
                    except AgeRestrictedError:  
                        print(f"Video '{video_title}' bị hạn chế độ tuổi và sẽ không được tải xuống.")
                    except Exception as e:
                        print(f"Lỗi khi xử lý video '{video_title}': {e}")

                if 'nextPageToken' in video_request:
                    next_page_token = video_request['nextPageToken']
                else:
                    break
            except Exception as e:
                print(f"Lỗi: {e}. Thử lại sau 5 giây.")
                time.sleep(5)  

def download_single_media(url, path_to_save, download_video=False):
    if not os.path.exists(path_to_save):
        os.makedirs(path_to_save)

    try:
        yt = YouTube(url)
        media_title = replace_invalid_characters(yt.title)

        if download_video:
            # video_stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
            video_stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            video_file = video_stream.download(output_path=path_to_save)
            print(f"Đã tải xuống video: {media_title}")
        else:
            stream = yt.streams.filter(only_audio=True).first()

            if not stream:
                print(f"Không tìm thấy stream âm thanh cho video '{media_title}'.")
                return

            audio_file = stream.download(output_path=path_to_save, filename=media_title + '.mp4')

            audio = AudioSegment.from_file(audio_file, format="mp4")
            mp3_filename = f"{media_title}.mp3"
            mp3_path = os.path.join(path_to_save, mp3_filename)
            audio.export(mp3_path, format="mp3")

            os.remove(audio_file)
            print(f"Đã tải và chuyển đổi nhạc: {media_title}")

    except Exception as e:
        print(f"Lỗi khi xử lý đa phương tiện từ URL '{url}': {e}")

if __name__ == "__main__":
    choice = int(input("Bạn muốn tải video hay nhạc?\n1. Video\n2. Nhạc\nChọn: "))
    path_to_save = "data_download"
    category = "video" if choice == 1 else "music"
    playlist_directory = create_subdirectories(path_to_save, category, "")

    if choice == 1:
        sub_choice = int(input("Bạn muốn tải từ playlist hay từ kênh YouTube, hoặc từ URL cụ thể?\n1. Playlist\n2. Kênh YouTube\n3. URL cụ thể\nChọn: "))
        if sub_choice == 1:
            playlist_url = input("Nhập link danh sách phát YouTube: ")
            download_audio(playlist_url, None, playlist_directory, download_video=True)
            print("Tải và chuyển đổi video từ playlist hoàn tất.")
        elif sub_choice == 2:
            channel_id = input("Nhập ID của kênh YouTube: ")
            download_audio(None, channel_id, playlist_directory, download_video=True)
            print("Tải và chuyển đổi video từ kênh YouTube hoàn tất.")
        elif sub_choice == 3:
            media_url = input("Nhập URL cụ thể của video YouTube: ")
            download_single_media(media_url, playlist_directory, download_video=True)
            print("Tải và chuyển đổi video từ URL cụ thể hoàn tất.")
        else:
            print("Lựa chọn không hợp lệ.")
    elif choice == 2:
        sub_choice = int(input("Bạn muốn tải từ playlist hay từ kênh YouTube, hoặc từ URL cụ thể?\n1. Playlist\n2. Kênh YouTube\n3. URL cụ thể\nChọn: "))
        if sub_choice == 1:
            playlist_url = input("Nhập link danh sách phát YouTube: ")
            download_audio(playlist_url, None, playlist_directory, download_video=False)
            print("Tải và chuyển đổi nhạc từ playlist hoàn tất.")
        elif sub_choice == 2:
            channel_id = input("Nhập ID của kênh YouTube: ")
            download_audio(None, channel_id, playlist_directory, download_video=False)
            print("Tải và chuyển đổi nhạc từ kênh YouTube hoàn tất.")
        elif sub_choice == 3:
            media_url = input("Nhập URL cụ thể của video YouTube: ")
            download_single_media(media_url, playlist_directory, download_video=False)
            print("Tải và chuyển đổi nhạc từ URL cụ thể hoàn tất.")
        else:
            print("Lựa chọn không hợp lệ.")
    else:
        print("Lựa chọn không hợp lệ.")
