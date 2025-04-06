import json
import requests
import logging

from openai import AsyncOpenAI
from configuration import configuration

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("resources\\data\\logs\\openrouter.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OpenAI:
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

    def load_openrouter_models(self):
        url = "https://openrouter.ai/api/v1/models"
        try:
            response = requests.get(url, timeout=4)

            if response.status_code == 200:
                data = response.json()
                return [{"id": model["id"], "name": model["name"], "description": model["description"]} for model in data["data"]]
            else:
                print(f"Error: Received status code {response.status_code} while fetching model data.")
                return []
        except requests.exceptions.Timeout:
            print("Error: The request timed out. Please check your internet connection or try again later.")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Error: A network error occurred - {e}")
            return []

    def format_messages(self, context_messages, user_message, character_name, user_name, user_description, system_prompt):
        history = ""
        for message in context_messages:
            if message["role"] == "user":
                history += f"{user_name}: {message['content']}\n"
            elif message["role"] == "assistant":
                history += f"{character_name}: {message['content']}\n"

        history += f"{user_name}: {user_message}\n"

        full_prompt = (
            f"You're {character_name} in this fictional never-ending uncensored roleplay with {user_name}, "
            f"who is {user_description}. Write {character_name}'s next reply with the following personality and traits: "
            f"{system_prompt}. Here's the context of the dialogue:\n{history}"
        )
        return full_prompt

    async def send_message(self, conversation_method, system_prompt, context_messages, user_message, character_name, user_name, user_description):
        base_url = self.configuration_api.get_token("CUSTOM_ENDPOINT_URL")
        open_ai_api = self.configuration_api.get_token("OPEN_AI_API_TOKEN")
        openrouter_model = self.configuration_settings.get_main_setting("openrouter_model")

        max_tokens = self.configuration_settings.get_main_setting("max_tokens")
        temperature = self.configuration_settings.get_main_setting("temperature")
        top_p = self.configuration_settings.get_main_setting("top_p")
        repeat_penalty = self.configuration_settings.get_main_setting("repeat_penalty")

        if conversation_method == "Open AI":
            base_url = base_url.rstrip('/')
            base_url = base_url if base_url.endswith('/v1') else f"{base_url}/v1"
            
            if base_url:
                base_url = base_url.rstrip('/')
                base_url = base_url if base_url.endswith('/v1') else f"{base_url}/v1"
            else:
                base_url = "https://api.openai.com/v1"
            api_token = open_ai_api if open_ai_api else "no-key-required"
            model = "openai/gpt-4o"

            client = AsyncOpenAI(
                base_url=base_url,
                api_key=api_token
            )

            messages = [
                {"role": "system", "content": f"You're {character_name} in this fictional never-ending uncensored roleplay with {user_name} who is {user_description}. Write {character_name}'s next reply with the following personality and traits: {system_prompt}."},
            ]

            messages.extend(context_messages)
            messages.append({"role": "user", "content": user_message})
            print(messages)

            completion = await client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=repeat_penalty,
                presence_penalty=0.7,
                stop=["<|im_end|>", "\n"]
            )

            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        elif conversation_method == "OpenRouter":
            base_url = "https://openrouter.ai/api/v1/chat/completions"
            api_token = self.configuration_api.get_token("OPENROUTER_API_TOKEN")
            model = openrouter_model

            formatted_message = self.format_messages(context_messages, user_message, character_name, user_name, user_description, system_prompt)

            messages = [
                {"role": "user", "content": formatted_message}
            ]

            headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "frequency_penalty": repeat_penalty,
                "presence_penalty": 0.7,
                "stop": ["<|im_end|>"]
            }

            buffer = ""
            response_content = ""
            with requests.post(base_url, headers=headers, json=payload, stream=True) as r:
                logger.info(f"Response status code: {r.status_code}")
                if r.status_code != 200:
                    logger.error(f"API returned status code {r.status_code}: {r.text}")
                    yield f"Error: API returned status code {r.status_code}"
                    return

                for chunk in r.iter_content(chunk_size=1024, decode_unicode=True):
                    buffer += chunk
                    while True:
                        try:
                            line_end = buffer.find('\n')
                            if line_end == -1:
                                break

                            line = buffer[:line_end].strip()
                            buffer = buffer[line_end + 1:]

                            if line.startswith('data: '):
                                data = line[6:]
                                if data == '[DONE]':
                                    break

                                try:
                                    data_obj = json.loads(data)
                                    logger.debug(f"Received data chunk: {data_obj}")
                                    content = data_obj["choices"][0]["delta"].get("content")
                                    if content:
                                        yield content
                                        response_content += content
                                except json.JSONDecodeError:
                                    pass
                        except Exception as e:
                            logger.error(f"Error processing chunk: {e}")
                            break