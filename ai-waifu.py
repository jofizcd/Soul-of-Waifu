import keyboard
from characterai import PyCAI
from elevenlabs import generate, play, set_api_key
from whisper_mic.whisper_mic import WhisperMic

#API from ElevenLabs
set_api_key("YOUR API")

#API from CharacterAI
client = PyCAI('YOUR API')

#Enter a CHARACTER_ID
char = input('Enter CHAR: ')

#Enter your username
user_name = 'Jofi Subscriber'

chat = client.chat.get_chat(char)

history_id = chat['external_id']

participants = chat['participants']

if not participants[0]['is_human']:
    tgt = participants[0]['user']['username']
else:
    tgt = participants[1]['user']['username']

if __name__ == "__main__":
    try:
        print("Press and hold Right Shift to start recording")
        while True:
            if keyboard.is_pressed('RIGHT_SHIFT'):
                print("Recording...")
                mic = WhisperMic() #Whisper MIC  
                result = mic.listen() #Record your voice and convert it to text
                message = result
                print(user_name,"said: ", message)
                data = client.chat.send_message(
                    char, message, history_external_id=history_id, tgt=tgt, filtering=True
                )

                name = data['src_char']['participant']['name']
                textil = data['replies'][0]['text']
    
                audio = generate(
                    text=textil,
                    voice="Lilia", #Choose a voice from ElevenLabs
                    model='eleven_monolingual_v1'
                )

                play(audio)

                print(f"{name}: {textil}")
    except KeyboardInterrupt:
        t.join()
        print("Stopped")