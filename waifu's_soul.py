print('''
   _____             __         ____   _       __      _ ____     
  / ___/____  __  __/ /  ____  / __/  | |     / ____ _(_/ ____  __
  \__ \/ __ \/ / / / /  / __ \/ /_    | | /| / / __ `/ / /_/ / / /
 ___/ / /_/ / /_/ / /  / /_/ / __/    | |/ |/ / /_/ / / __/ /_/ / 
/____/\____/\__,_/_/   \____/_/       |__/|__/\__,_/_/_/  \__,_/  
                                                                                          
                                                         [by jofi]
''')
import os
import asyncio
import keyboard
import torch
import time
import sounddevice as sd
from gpytranslate import Translator
from characterai import PyAsyncCAI
from elevenlabs import generate, set_api_key, play
from whisper_mic import WhisperMic

set_api_key("API-ключ от ElevenLabs") #Сюда надо ввести API с сайта ElevenLabs
client = PyAsyncCAI('API-ключ от Character AI') #Сюда надо ввести API с сайта Character AI
char = 'ID персонажа Character AI' #Сюда надо ввести ID персонажа с Character AI, с которым вы будете разговаривать

language = 'ru' #Выбираете язык модели
model_id = 'v4_ru' #Выбираете модель и вписываете её ID
local_file = 'model.pt'
device = torch.device('cpu')
torch.set_num_threads(12) #Число потоков вашего процессора

speaker = 'baya' #Все голоса: 'aidar', 'baya', 'kseniya', 'xenia', 'random'
sample_rate = 48000 #Все частоты дискретизации: '8000', '24000', '48000'
put_accent=True
put_yo=True

voice = "Penelope" #Тут вы выбираете голос для TTS от EleveneLabs

if not os.path.isfile(local_file):
    torch.hub.download_url_to_file('https://models.silero.ai/models/tts/ru/v4_ru.pt',
                                   local_file)  

async def main():
    mode = input("Выбери технологию Text-To-Speech (1 - ElevenLabs, 2 - Silero TTS (Только персонаж), 3 - Silero TTS (Персонаж и пользователь)): ")
    if mode == '1':
        print("Нажми ПРАВЫЙ SHIFT, чтобы запустить программу...")
        while True:
            if keyboard.is_pressed('RIGHT_SHIFT'):
                while True:
                    t = Translator()
                    chat = await client.chat2.get_chat(char)
                    author = {'author_id': chat['chats'][0]['creator_id']}
                    mic = WhisperMic(model='small', english=False, energy=300, pause=1, mic_index=1)
                    print("Запись пошла, говорите...")
                    msg1 = mic.listen()
                    messageC = msg1
                    print("Ты сказал:", msg1)
                    async with client.connect() as chat2:
                        data = await chat2.send_message(
                            char, chat['chats'][0]['chat_id'],
                            messageC, author
                        )
                    textil = data['turn']['candidates'][0]['raw_content']
                    translation = await t.translate(textil, targetlang="ru") #Язык, на который будут переводиться слова
                    audio = generate(
                        text = translation.text,
                        voice = voice,
                        model = "eleven_multilingual_v2",
                    )
                    print(f"Персонаж ответил: {translation.text}")
                    play(audio)
                    
                
    elif mode == '2':
        print("Нажми ПРАВЫЙ SHIFT, чтобы записать голос")
        while True:
            if keyboard.is_pressed('RIGHT_SHIFT'):
                while True:
                    t = Translator()
                    chat = await client.chat2.get_chat(char)
                    author = {'author_id': chat['chats'][0]['creator_id']}
                    mic = WhisperMic(model='small', english=False, energy=300, pause=1, mic_index=1)
                    print("Запись пошла, говорите...")
                    msg1 = mic.listen()
                    messageC = msg1
                    print("Ты сказал:", msg1)
                    async with client.connect() as chat2:
                        data = await chat2.send_message(
                            char, chat['chats'][0]['chat_id'],
                            messageC, author
                        )
                    textil = data['turn']['candidates'][0]['raw_content']
                    translation = await t.translate(textil, targetlang="ru") #Язык, на который будут переводиться слова
                    model = torch.package.PackageImporter(local_file).load_pickle("tts_models", "model")
                    model.to(device)
                    audio = model.apply_tts(text=translation.text,
                                            speaker=speaker,
                                            sample_rate=sample_rate,
                                            put_accent=put_accent,
                                            put_yo=put_yo)
                    print(f"Персонаж ответил: {translation.text}")
                    sd.play(audio, sample_rate)
                    time.sleep(len(audio) / sample_rate)
                    sd.stop()
    
    elif mode == '3':
        print("Нажми ПРАВЫЙ SHIFT, чтобы записать голос")
        while True:
            if keyboard.is_pressed('RIGHT_SHIFT'):
                while True:
                    t = Translator()
                    chat = await client.chat2.get_chat(char)
                    author = {'author_id': chat['chats'][0]['creator_id']}
                    mic = WhisperMic(model='small', english=False, energy=300, pause=1, mic_index=1)
                    print("Запись пошла, говорите...")
                    msg1 = mic.listen()
                    translation = await t.translate(msg1, targetlang='en') #Язык, на который будут переводиться слова
                    print("Ты сказал:", msg1)
                    async with client.connect() as chat2:
                        data = await chat2.send_message(
                            char, chat['chats'][0]['chat_id'],
                            translation.text, author
                        )
                    textil = data['turn']['candidates'][0]['raw_content']
                    translation = await t.translate(textil, targetlang='ru') #Язык, на который будут переводиться слова
                    model = torch.package.PackageImporter(local_file).load_pickle("tts_models", "model")
                    model.to(device)
                    audio = model.apply_tts(text=translation.text,
                                            speaker=speaker,
                                            sample_rate=sample_rate,
                                            put_accent=put_accent,
                                            put_yo=put_yo)
                    print(f"Персонаж ответил: {translation.text}")
                    sd.play(audio, sample_rate)
                    time.sleep(len(audio) / sample_rate)
                    sd.stop()                

asyncio.run(main())
