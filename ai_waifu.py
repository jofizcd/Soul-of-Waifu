import asyncio
import keyboard
from characterai import PyAsyncCAI
from elevenlabs import generate, set_api_key, play
from whisper_mic import WhisperMic

set_api_key("ВАШ АПИ ТОКЕН ОТ ELEVENLABS") #Сюда надо ввести API с сайта ElevenLabs
client = PyAsyncCAI('ВАШ АПИ ТОКЕН ОТ CHARACTER AI') #Сюда надо ввести API с сайта Character AI
char = 'ID НОМЕР ПЕРСОНАЖА' #Сюда надо ввести ID-номер персонажа с Character AI, с которым вы будете разговаривать

async def main():
    print("Нажми ПРАВЫЙ SHIFT, чтобы записать голос")
    while True:
        if keyboard.is_pressed('RIGHT_SHIFT'):
            chat = await client.chat2.get_chat(char)
            author = {'author_id': chat['chats'][0]['creator_id']}
            mic = WhisperMic(model='small', english=False, energy=300, pause=1)
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
            audio = generate(
                text = textil,
                voice = "Penelope", #Сюда вы можете вписать, какой голос вы хотели бы использовать для озвучки текста персонажа
                model = "eleven_multilingual_v2",
            )
            play(audio)
            print(f"Персонаж ответил: {textil}")

asyncio.run(main())

