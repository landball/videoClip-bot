import requests
import discord
from discord import app_commands
from core.classes import Cog_extension
from faster_whisper import WhisperModel
import pandas as pd
import time
from typing import Literal
import os

def get_confirm_token(response:requests.Response):
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            return value

    return None


def save_response_content(response:requests.Response, destination):
    CHUNK_SIZE = 32768

    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)

def download_file_from_google_drive(file_id, destination):
    URL = "https://docs.google.com/uc?export=download&confirm=1" #Google drive 要求下載的連結

    session = requests.Session()

    response = session.get(URL, params={"id": file_id}, stream=True) 
    token = get_confirm_token(response)

    if token:
        params = {"id": file_id, "confirm": token}
        response = session.get(URL, params=params, stream=True)

    save_response_content(response, destination)

def transcribe(audio, lang, mod):
    print(f"transcribing({audio})") 
    model = WhisperModel(mod)
    segments, info = model.transcribe(audio, language=lang, vad_filter=False, vad_parameters=dict(min_silence_duration_ms=100))  #Segments是以每個有100毫秒的無人聲片段所切間隔
    language = info[0] #音訊使用語言
    print("Transcription language", language)
    segments = list(segments) #從這開始進行音訊轉換
    return segments

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

class GenerateSubtitle(Cog_extension):
    @app_commands.command(description='Generate a text file from specific google drive url')
    @app_commands.describe(url='The google drive url link you want to transcribe', 
                           language='The target language you want to transcribe to', 
                           model='The transcribing model in whisper', 
                           frmat='The output file format')
    async def generate_text_file(self, 
                                 interaction:discord.Interaction, 
                                 url:str,  
                                 language:str=None, 
                                 model:Literal['tiny', 'base', 'medium', 'large']='base', 
                                 frmat:Literal['txt', 'srt', 'csv']='txt'):
        await interaction.response.send_message('Started processing, please wait...')
        file_id = url.split('/')[-2]
        destination = 'output.mp3'
        download_file_from_google_drive(file_id, destination)
        if destination:
            segments = transcribe(destination, language, model)
            os.remove(destination)
            if frmat == 'txt':
                result = 'output.txt'
                with open(result, 'w', encoding='utf8') as file:
                    for segment in segments:
                        file.write(segment.text+'\n')
            elif frmat == 'csv':
                result = writetocsv(segments)
            elif frmat == 'srt':
                result = generatesrt(segments)
            else:
                await interaction.followup.send('Invalid format! please choose an available format for the output file.')
                return
            await interaction.followup.send(content=f"Here's your {frmat} file!", file=discord.File(f"output.{frmat}"))

            if os.path.exists('output.txt'):
                os.remove('output.txt')
            if os.path.exists('output.csv'):
                os.remove('output.txt')
            if os.path.exists('output.srt'):
                os.remove('output.txt')
        
        else:
            await interaction.followup.send("Please check your inserted url")


async def setup(bot):
    await bot.add_cog(GenerateSubtitle(bot))
