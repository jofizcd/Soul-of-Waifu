import os
import time
import json
import torch
import curses
import asyncio
import keyboard
import pyfiglet
import sounddevice as sd
from gpytranslate import Translator
from colorama import Fore, Style
from characterai import PyAsyncCAI
from elevenlabs import generate, set_api_key, play
from whisper_mic import WhisperMic

char_list = []
char_name = {}
character_id = {}
config = {}

class MainMenu:
    def __init__(self):
        self.stdscr = curses.initscr()

    def create_menu(self):
        # turn off cursor blinking
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        self.stdscr.refresh()
        self.screen_height, self.screen_width = self.stdscr.getmaxyx()
        
        options = ['Начать общение', 'Редактор персонажей', 'Редактировать конфигурационный файл', 'Выход']

        current_option = 0

        while True:
            self.stdscr.clear()
            self.stdscr.addstr(0, 0, "Добро пожаловать в Soul of Waifu - место, где персонажи оживают!", curses.A_BOLD)

            for i, option in enumerate(options):
                if i == current_option:
                    self.stdscr.addstr(i+2, 0, f"> {option}", curses.A_REVERSE)
                else:
                    self.stdscr.addstr(i+2, 0, f"  {option}")

            key = self.stdscr.getch()
            if key == curses.KEY_UP and current_option > 0:
                current_option -= 1
            elif key == curses.KEY_DOWN and current_option < len(options)-1:
                current_option += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if current_option == 3:
                    if self.confirm("Ты точно хочешь выйти?"):
                        exit()
                elif current_option == 0:
                    asyncio.run(self.create_menu_mode())
                elif current_option == 1:
                    curses.endwin()
                    configuration = Configuration()
                    configuration.editor_char() 
                elif current_option == 2:
                    curses.endwin()
                    configuration = Configuration()
                    configuration.update_config()
    
    async def create_menu_mode(self):
        #Turn off cursor blinking
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        self.stdscr.refresh()
        self.screen_height, self.screen_width = self.stdscr.getmaxyx()
        
        options = ['Текстовый режим', 'Разговорный режим с озвучкой ElevenLabs', 'Разговорный режим с русской озвучкой SileroTTS', 'Разговорный режим с английской озвучкой SileroTTS', 'Выход в главное меню']

        current_option = 0

        while True:
            self.stdscr.clear()
            self.stdscr.addstr(0, 0, "Выберите режим диалога", curses.A_BOLD)

            for i, option in enumerate(options):
                if i == current_option:
                    self.stdscr.addstr(i+2, 0, f"> {option}", curses.A_REVERSE)
                else:
                    self.stdscr.addstr(i+2, 0, f"  {option}")

            key = self.stdscr.getch()
            if key == curses.KEY_UP and current_option > 0:
                current_option -= 1
            elif key == curses.KEY_DOWN and current_option < len(options)-1:
                current_option += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if current_option == 4:
                    print("Переход в главное меню...")
                    time.sleep(1)
                    menu = MainMenu()
                    menu.create_menu()
                elif current_option == 0:
                    curses.endwin()
                    await mode1()
                elif current_option == 1:
                    curses.endwin()
                    await mode2()
                elif current_option == 2:
                    curses.endwin()
                    await mode3()
                elif current_option == 3:
                    curses.endwin()
                    await mode4()
    
    def confirm(self, confirmation_text):
        self.print_center(confirmation_text)

        current_option = "Да"
        self.print_confirm(current_option)

        while 1:
            key = self.stdscr.getch()

            if key == curses.KEY_RIGHT and current_option == "Да":
                current_option = "Нет"
            elif key == curses.KEY_LEFT and current_option == "Нет":
                current_option = "Да"
            elif key == curses.KEY_ENTER or key in [10, 13]:
                return True if current_option == "Да" else False

            self.print_confirm(current_option)
    
    def print_confirm(self, selected="Да"):
        curses.setsyx(self.screen_height // 2 + 1, 0)
        self.stdscr.clrtoeol()

        y = self.screen_height // 2 + 1
        options_width = 10

        #Вывести "Да"
        option = "Да"
        x = self.screen_width // 2 - options_width // 2 + len(option)
        if selected == option:
            self.color_print(y, x, option, 1)
        else:
            self.stdscr.addstr(y, x, option)

        #Вывести "Нет"
        option = "Нет"
        x = self.screen_width // 2 + options_width // 2 - len(option)
        if selected == option:
            self.color_print(y, x, option, 1)
        else:
            self.stdscr.addstr(y, x, option)

        self.stdscr.refresh()
    
    def print_center(self, text):
        self.stdscr.clear()
        x = self.screen_width // 2 - len(text) // 2
        y = self.screen_height // 2
        self.stdscr.addstr(y, x, text)
        self.stdscr.refresh()
    
    def color_print(self, y, x, text, pair_num):
        stdscr = curses.initscr()
        curses.start_color()
        curses.init_pair(pair_num, curses.COLOR_BLACK, curses.COLOR_WHITE)
        stdscr.attron(curses.color_pair(pair_num))
        stdscr.addstr(y, x, text)
        stdscr.attroff(curses.color_pair(pair_num))
        stdscr.refresh()
        curses.endwin()

class Configuration:
    def load_config(self):
        config_path = os.path.join(current_dir, 'config.json')
        if not os.path.exists(config_path):
            print("Создание конфигурационного файла...")
            time.sleep(1)
            data_config = {
                "config": {}
            }
            with open('config.json', 'w') as config_file:
                json.dump(data_config, config_file)
        else:
            with open('config.json', 'r') as config_file:
                main_config = json.load(config_file)
            return main_config
        
        if 'characterai_api' not in config:
            config['characterai_api'] = input("Введите ваш API-ключ от Character AI: ")
            self.save_configuration()
            print("API-ключ от Character AI успешно добавлен")
            
        if 'elevenlabs_api' not in config:
            config['elevenlabs_api'] = input("Введите ваш API-ключ от ElevenLabs: ")
            self.save_configuration()
            print("API-ключ ElevenLabs успешно добавлен")
            
        if 'device_torch' not in config:
            while True:
                config['device_torch'] = input("Выберите устройство работы озвучки SileroTTS (cuda (видеокарта) или cpu (процессор)): ")
                if config["device_torch"].lower() == "cuda" or config["device_torch"].lower() == "cpu":
                    self.save_configuration()
                    print("Устройство успешно выбрано")
                    break
                else:
                    print("Ошибка: введите название устройства корректно")
                    
        if 'speaker_silero' not in config:            
            while True:
                config['speaker_silero'] = input("Введите название голоса для Silero (aidar, baya, kseniya, xenia, random): ")
                if config['speaker_silero'].lower() == "aidar" or config['speaker_silero'].lower() == "baya" or config['speaker_silero'].lower() == "kseniya" or config['speaker_silero'].lower() == "xenia" or config['speaker_silero'].lower() == "random":
                    self.save_configuration()
                    print("Голос озвучки успешно выбран")
                    break
                else:
                    print("Ошибка: введите название спикера корректно")
               
        if 'speaker_elevenlabs' not in config:
            config['speaker_elevenlabs'] = input("Введите название голоса для ElevenLabs: ")
            self.save_configuration()
            print("Голос озвучки успешно выбран")
            
        print("Конфигурационный файл успешно создан!")
    
    def load_char_config(self):
        current_dir = os.getcwd()
        config_path = os.path.join(current_dir, 'char_config.json')
        if not os.path.exists(config_path):
            print("Создание конфигурационного файла для хранения персонажей...")
            time.sleep(1)
            data_char = {
                "char_list": [],
                "char_name": {},
                "character_id": {}
            }
            with open('char_config.json', 'w') as config_file:
                json.dump(data_char, config_file)
        else:
            with open('char_config.json', 'r') as config_file:
                data = json.load(config_file)
                char_list.extend(data["char_list"])
                char_name.update(data["char_name"])
                character_id.update(data["character_id"])
            
        if 'persona' not in character_id:
            character_id['persona'] = config['characterai_api']
            self.save_char_data()
            print("Конфигурационный файл успешно создан!")
        
        time.sleep(1)
    
    def update_config(self):
        clear_console()
        configuration = Configuration()
        config = configuration.load_config()
        print("Доступные переменные для изменения: ")
        print("")
        for key in config['config']:
            print(key)
        
        print('--------------------')
        chosen_variable = input("Введите " + Fore.CYAN + "название" + Style.RESET_ALL + " переменной, которую хотите изменить. Или введите " + Fore.CYAN + "Выход" + Style.RESET_ALL +", чтобы выйти в главное меню: ")
        print("")
        
        if chosen_variable == "выход" or chosen_variable == "Выход":
            print("")
            print("Переход в главное меню...")
            time.sleep(1)
            menu = MainMenu()
            menu.create_menu()
        
        if chosen_variable not in config['config']:
            print('Ошибка: выбранная переменная отсутствует в конфиге')
            return

        new_value = input(f"Значение переменной {chosen_variable}:  " + Fore.CYAN + f"{config['config'][chosen_variable]}." + Style.RESET_ALL + " Введите новое значение переменной: ")
        config['config'][chosen_variable] = new_value
    
        with open('config.json', 'w') as config_file:
            json.dump(config, config_file)
        
        print("")
        print("Переменная конфига успешно обновлена!")
        print("")
        time.sleep(1)
        print("Переход в главное меню...")
        time.sleep(1)
        print("-------------------------------------")   
        menu = MainMenu()
        menu.create_menu()
    
    def print_char(self):
        if len(char_list) > 0:
            print("Доступные персонажи:")
            for i, char in enumerate(char_list):
                name = char_name.get(char, f"Персонаж{i+1}")
                print(Fore.CYAN + f"{i+1}. {name} " + Style.RESET_ALL + f"ID: ({char})")
        else:
            print("Вы не добавили ни одного персонажа")
            print("")
    
    def editor_char(self):
        clear_console()
        configuration = Configuration()
        print("Добро пожаловать в редактор персонажей!")
        print("")  
        while True:
            configuration.print_char()
            selection = input("Введите слово " + Fore.CYAN + 'Добавить' + Style.RESET_ALL + " для добавления нового персонажа или слово " + Fore.CYAN + 'Удалить' + Style.RESET_ALL + " для удаления персонажа или слово " + Fore.CYAN + 'Выход' + Style.RESET_ALL + ", чтобы выйти в главное меню: " )
            print("")
            if selection.lower() == 'добавить' or selection.lower() == 'Добавить':
                name = input("Введите имя нового персонажа: ")
                char_id = input("Введите ID нового персонажа: ")
                configuration.add_char(name, char_id)
            elif selection.lower() == 'удалить' or selection.lower() == 'Удалить':
                configuration.del_char()
            elif selection.lower() == 'выход' or selection.lower() == 'Выход':
                print("Переход в главное меню...")
                time.sleep(1)
                menu = MainMenu()
                menu.create_menu()
            else:
                print(Fore.RED + "Ошибка: введите команду корректно" + Style.RESET_ALL)
        
    def selector_char(self):
        clear_console()
        print("Добро пожаловать в селектор персонажей!")
        print("")  
        time.sleep(1)
        while True:
            self.print_char()
            print("-------------------------------------")   
            selection = input("Введите " + Fore.CYAN + "цифру" + Style.RESET_ALL + " персонажа, с которым вы хотите начать общение: ")
            if selection.isdigit() and 1 <= int(selection) <= len(char_list):
                return char_list[int(selection)-1]
            else:
                print(Fore.RED + "Ошибка: введите цифру персонажа" + Style.RESET_ALL)
        
    def add_char(self, name, char_id):
        configuration = Configuration()
        if char_id in char_list:
            print("Такой персонаж уже есть")
            return
        c_api = character_id.get('persona', '')
        char_list.append(char_id)
        char_name[char_id] = name
        character_id[char_id] = c_api
        
        configuration.save_char_data()
        
        print("Персонаж успешно добавлен!")
    
    def del_char(self):
        configuration = Configuration()
        if len(char_list) > 0:
            configuration.print_char()
            while True:
                selection = input("Введите номер персонажа, которого хотите удалить: ")
                if selection.isdigit() and 1 <= int(selection) <= len(char_list):
                    remove_char = char_list.pop(int(selection)-1)
                    name = char_name.pop(remove_char)
                    character_id.pop(remove_char)
                    configuration.save_char_data()
                    print(f"Персонаж '{name}' был удален")
                    break
                else:
                    print(Fore.RED + "Ошибка: введите номер персонажа" + Style.RESET_ALL)
        else:
            print("Список доступных персонажей пуст. Переход в редактор...")
            time.sleep(1)
            self.editor_char()
                   
    def save_char_data(self):
        data_char = {
            "char_list": char_list,
            "char_name": char_name,
            "character_id": character_id  
        }
        with open('char_config.json', 'w') as config_file:
            json.dump(data_char, config_file)
    
    def save_configuration(self):
        data_config = {
            "config": config
        }
        with open('config.json', 'w') as config_file:
            json.dump(data_config, config_file)

def logoPRINT():
    naming = "Soul of Waifu"
    signature = "                                                         [by jofi]"
    ascii_text = pyfiglet.figlet_format(naming, font="slant")
    space = ""
    result = ascii_text + space + signature 
    print(result)
    print(space)

def logoPRINT_time():
    logoPRINT()
    time.sleep(2)

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')
    logoPRINT()

def check_silero_models(): #Проверка наличия моделей SileroTTS
    if not os.path.isfile(local_file_ru):
        print("Идёт загрузка модели SileroTTS RU")
        print("")
        torch.hub.download_url_to_file('https://models.silero.ai/models/tts/ru/v4_ru.pt',
                                    local_file_ru)
        print("_____________________________________________________")
        print("")
    if not os.path.isfile(local_file_eng):
        print("Идёт загрузка модели SileroTTS EN")
        print("")
        torch.hub.download_url_to_file('https://models.silero.ai/models/tts/en/v3_en.pt',
                                    local_file_eng)

def whisper_mic(): #Запись слов с микрофона
    mic = WhisperMic(model='base', english=False, energy=300, pause=1)
    print(Fore.CYAN + "Запись началась, " + Fore.RED + "говорите..." + Style.RESET_ALL)
    mic_message = mic.listen()
    return mic_message

def elevenlabs_dub(message_char): #Озвучка ElevenLabs
    audio = generate(
        text = message_char,
        voice = speaker_elevenlabs,
        model = 'eleven_multilingual_v2'
    )
    
    return audio

def silero_dub(model, message_char, sample_rate): #Русская озвучка SileroTTS
    audio = model.apply_tts(text = message_char, speaker = speaker, sample_rate = sample_rate, put_accent = put_accent, put_yo = put_yo)
    sd.play(audio, sample_rate)
    time.sleep(len(audio) / sample_rate)
    sd.stop

def silero_dub_en(model, message_char, sample_rate): #Английская озвучка SileroTTS
    audio = model.apply_tts(text = message_char, speaker = speaker_en, sample_rate = sample_rate)
    sd.play(audio, sample_rate)
    time.sleep(len(audio) / sample_rate)
    sd.stop

def get_char():
    configuration = Configuration()
    print("-------------------------------------")
    char = configuration.selector_char()
    return char

def main():
    #Logo display
    logoPRINT_time()
    #Checking availability of Silero TTS models
    check_silero_models()
    
    #Create main menu
    menu = MainMenu()
    menu.create_menu()

async def mode1(): #Текстовый режим с озвучкой SileroTTS
    print("-------------------------------------")
    print("Выбран режим с " + Fore.CYAN + "текстовым общением и озвучкой SileroTTS" + Style.RESET_ALL)
    time.sleep(1)
    char = get_char()
    clear_console()
    print("Персонаж " + Fore.RED + f"{char_name.get(char)}" + Style.RESET_ALL + " был выбран")
    print("Чтобы выйти в главное меню, напишите" + Fore.CYAN + " Выход" + Style.RESET_ALL)
    print("")
    while True:
        time.sleep(1)
        t = Translator()
        message_user = input(Fore.CYAN + "Вы: " + Style.RESET_ALL)
        if message_user.lower() == 'Выход' or message_user.lower() == 'выход':
            break
        translation = await t.translate(message_user, targetlang='en') #Язык, на который переводится текст
        message_user = translation.text
        chat = await client.chat2.get_chat(char)
        author = {'author_id': chat['chats'][0]['creator_id']}
        async with client.connect() as chat2:
            data = await chat2.send_message(
                char, chat['chats'][0]['chat_id'],
                message_user, author)
        text_cai = data['turn']['candidates'][0]['raw_content']
        translation = await t.translate(text_cai, targetlang='ru') #Язык, на который переводится текст
        message_char = translation.text
        model = torch.package.PackageImporter(local_file_ru).load_pickle("tts_models", "model")
        model.to(device)
        print(Fore.BLUE + "Персонаж ответил: " + Style.RESET_ALL + f"{message_char}")
        print("-------------------------------------")
        silero_dub(model, message_char, sample_rate)

async def mode2(): #Режим с озвучкой ElevenLabs
    print("-------------------------------------")
    print("Выбран режим с " + Fore.CYAN + "озвучкой ElevenLabs" + Style.RESET_ALL)
    time.sleep(1)
    char = get_char()
    clear_console()
    print("Персонаж " + Fore.RED + f"{char_name.get(char)}" + Style.RESET_ALL + " был выбран")
    print("")
    print("Чтобы выйти в главное меню, скажи" + Fore.CYAN + " Выход" + Style.RESET_ALL)
    print("Нажми на " + Fore.CYAN +"ПРАВЫЙ SHIFT" + Style.RESET_ALL + ", чтобы запустить программу...")
    while True:
        if keyboard.is_pressed('RIGHT_SHIFT'):
            while True:
                t = Translator()
                message_user = whisper_mic()
                print(Fore.CYAN + "Вы: " + Style.RESET_ALL, message_user)
                translation = await t.translate(message_user, targetlang='en') #Язык, на который переводится текст
                message_user = translation.text
                chat = await client.chat2.get_chat(char)
                author = {'author_id': chat['chats'][0]['creator_id']}
                async with client.connect() as chat2:
                    data = await chat2.send_message(
                        char, chat['chats'][0]['chat_id'],
                        message_user, author
                    )
                text_cai = data['turn']['candidates'][0]['raw_content']
                translation = await t.translate(text_cai, targetlang="ru") #Язык, на который переводится текст
                message_char = translation.text
                audio = elevenlabs_dub(message_char)
                print(Fore.BLUE + "Персонаж ответил: " + Style.RESET_ALL + f"{message_char}")
                print("-------------------------------------") 
                play(audio)   
    
async def mode3(): #Режим с русской озвучкой SileroTTS
    print("-------------------------------------")
    print("Выбран режим с " + Fore.CYAN + "русской озвучкой SileroTTS" + Style.RESET_ALL)
    time.sleep(1)
    char = get_char()
    clear_console()
    print("Персонаж " + Fore.RED + f"{char_name.get(char)}" + Style.RESET_ALL + " был выбран")
    print("")
    print("Чтобы выйти в главное меню, скажи" + Fore.CYAN + " Выход" + Style.RESET_ALL)
    print("Нажми на " + Fore.CYAN +"ПРАВЫЙ SHIFT" + Style.RESET_ALL + ", чтобы запустить программу...")
    while True:
        if keyboard.is_pressed('RIGHT_SHIFT'):
            while True:
                t = Translator()
                message_user = whisper_mic() 
                print(Fore.CYAN + "Вы: " + Style.RESET_ALL, message_user)     
                translation = await t.translate(message_user, targetlang='en') #Язык, на который переводится текст
                message_user = translation.text
                chat = await client.chat2.get_chat(char)
                author = {'author_id': chat['chats'][0]['creator_id']}
                async with client.connect() as chat2:
                    data = await chat2.send_message(
                        char, chat['chats'][0]['chat_id'],
                        message_user, author
                    )
                text_cai = data['turn']['candidates'][0]['raw_content']
                translation = await t.translate(text_cai, targetlang='ru') #Язык, на который переводится текст
                message_char = translation.text
                model = torch.package.PackageImporter(local_file_ru).load_pickle("tts_models", "model")
                model.to(device)
                print(Fore.BLUE + "Персонаж ответил: " + Style.RESET_ALL + f"{message_char}")
                print("-------------------------------------") 
                silero_dub(model, message_char, sample_rate)

async def mode4(): #Режим с английской озвучкой SileroTTS
    print("-------------------------------------")
    print("Выбран режим с " + Fore.CYAN + "английской озвучкой SileroTTS" + Style.RESET_ALL)
    time.sleep(1)
    char = get_char()
    clear_console()
    print("Персонаж " + Fore.RED + f"{char_name.get(char)}" + Style.RESET_ALL + " был выбран")
    print("")
    print("Чтобы выйти в главное меню, скажи" + Fore.CYAN + " Выход" + Style.RESET_ALL)
    print("Нажми на " + Fore.CYAN +"ПРАВЫЙ SHIFT" + Style.RESET_ALL + ", чтобы запустить программу...")
    while True:
        if keyboard.is_pressed('RIGHT_SHIFT'):
            while True:
                t = Translator()
                message_user = whisper_mic()
                print(Fore.CYAN + "Вы: " + Style.RESET_ALL, message_user)
                translation = await t.translate(message_user, targetlang='en') #Язык, на который переводится текст
                message_user = translation.text
                chat = await client.chat2.get_chat(char)
                author = {'author_id': chat['chats'][0]['creator_id']}
                async with client.connect() as chat2:
                    data = await chat2.send_message(
                        char, chat['chats'][0]['chat_id'],
                        message_user, author
                    )
                text_cai = data['turn']['candidates'][0]['raw_content']
                message_char = text_cai
                model = torch.package.PackageImporter(local_file_eng).load_pickle("tts_models", "model")
                model.to(device)
                print(Fore.BLUE + "Персонаж ответил: " + Style.RESET_ALL + f"{message_char}")
                print("-------------------------------------") 
                silero_dub_en(model, message_char, sample_rate)

#Создание и чтение конфигурационного файла
current_dir = os.getcwd()
conf = Configuration()
conf.load_config()
conf.load_char_config()
main_config = conf.load_config()
    
#Переменные из конфигурационного файла
elevenlabs_api = main_config['config']['elevenlabs_api']
characterai_api = main_config['config']['characterai_api']
device_torch = main_config['config']['device_torch']
speaker_silero = main_config['config']['speaker_silero']
speaker_elevenlabs = main_config['config']['speaker_elevenlabs']

#Главные переменные
set_api_key(elevenlabs_api)
client = PyAsyncCAI(characterai_api)

#Переменные для озвучки
local_file_ru = 'model_silero_ru.pt'
local_file_eng = 'model_silero_eng.pt'
device = torch.device(device_torch)
torch.set_num_threads(12)
voice = speaker_elevenlabs
speaker = speaker_silero
speaker_en = 'en_0'
sample_rate = 48000
put_accent = True
language = 'ru'
put_yo = True

current_dir = os.getcwd()
config_path = os.path.join(current_dir, 'config.json')

#Запуск программы
main()