import discord
from discord import app_commands
from core.classes import Cog_extension
from faster_whisper import WhisperModel
import pandas as pd
import time
import yt_dlp
import os
from typing import Literal

# youtube影片網址下載為mp3
def download_audio_from_youtube(video_url:str):
    try:
        output_file_yt = "yt.mp3"

        #-x是提取音訊用的 check=True表示如果yt-dlp命令失敗則會引發錯誤    
        with yt_dlp.YoutubeDL({'extract_audio':True, 'format': 'bestaudio', 'outtmpl':'yt.mp3', 'extractor_args': {'youtube':{'player_client':'ios'}}) as video:
            video.download(video_url)
        print(f"The audio file has been downloaded as {output_file_yt}")
        return output_file_yt
    
    except Exception as e:
        print(f"An error occurred when downloading audio files: {e}")
        return None



def transcribe(audio, lang, mod):
    print(f"transcribing({audio})") 
    model = WhisperModel(mod)
    segments, info = model.transcribe(audio, language=lang, vad_filter=False, vad_parameters=dict(min_silence_duration_ms=100))  #Segments是以每個有100毫秒的無人聲片段所切間隔
    language = info[0] #音訊使用語言
    print("Transcription language", info[0])
    segments = list(segments) #從這開始進行音訊轉換
    return language, segments

def formattedtime(seconds):
    final_time = time.strftime("%H:%M:%S", time.gmtime(float(seconds))) #從檔案開始將每個間隔所表示時間寫成字串
    return f"{final_time},{seconds.split('.')[1]}"

def writetocsv(segments):
    output_file = "output.csv"
    cols = ["start", "end", "text"] #csv每行結構: ["開始時間", "結束時間", "文字"]
    data = []
    for segment in segments:
        start = formattedtime(format(segment.start, ".3f"))
        end = formattedtime(format(segment.end, ".3f"))
        data.append([start, end, segment.text]) 

    df = pd.DataFrame(data, columns=cols) 
    df.to_csv(output_file, index=False) #利用pandas將資料寫入csv檔
    return output_file

def generatesrt(segments):
    output_file = 'output.srt'
    count = 0
    
    with open(output_file, 'w', encoding='utf8') as file:
        for segment in segments:
            start = formattedtime(segment.start)
            end = formattedtime(segment.end)
            count += 1
            txt = f"{count}\n{start} --> {end}\n{segment.text}\n\n" #srt檔案表示法(/表示分行): 順序/開始時間 --> 結束時間/文字
            file.write(txt) #讀取csv檔並寫入srt
    return output_file         

class VideoClip(Cog_extension):
    @app_commands.command(description='Convert a Youtube url to srt or csv files')
    @app_commands.describe(url='The youtube url you want to transcribe as text',
                           language='The language you want to transcribe as. (in language code)',
                           model='The model you want to use for the transcription.',
                           mode='The format of the output file')
    async def convert(self, interaction:discord.Interaction, url:str, language:str=None, model:Literal['tiny', 'base', 'medium', 'large']='base', mode:Literal['csv', 'srt', 'txt']='srt'):
        print("Processing")  
        await interaction.response.send_message("Please wait for a while.")
        output_file = download_audio_from_youtube(url)

        if output_file:
            print("Watch out! Program started...")
            lang, segments = transcribe(output_file, language, model)
            writetocsv(segments)
            os.remove(output_file) #轉檔完刪除mp3檔案
            if mode == 'txt':
                with open('output.txt', 'w', encoding='utf8') as file:
                    file.write(segments.text + '\n')
            elif mode == 'srt': #當模式為srt檔時進入
                srtFile = generatesrt("output.csv")
                await interaction.followup.send(content=f"Here is your srt file in language {lang}!", file=discord.File(srtFile))
            else:
                csvFile = writetocsv(segments)
                await interaction.followup.send(content=f"Here is your csv file in language {lang}!", file=discord.File(csvFile))
            
            if os.path.exists('output.txt'):
                os.remove('output.txt')
            if os.path.exists('output.csv'):
                os.remove('output.csv')
            if os.path.exists('output.srt'):
                os.remove('output.srt')

        else:
            await interaction.followup.send("Please check your inserted url")

async def setup(bot):
    await bot.add_cog(VideoClip(bot))
