from mistralai import Mistral
from configuration import configuration


class MistralAI():
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

    async def send_message(self, system_prompt, context_messages, user_text, character_name, user_name, user_description):
        self.mistral_ai_token = self.configuration_api.get_token("MISTRAL_AI_API_TOKEN")
        self.model = "mistral-large-latest"
        self.client = Mistral(api_key=self.mistral_ai_token)

        max_tokens = self.configuration_settings.get_main_setting("max_tokens")
        temperature = self.configuration_settings.get_main_setting("temperature")
        top_p = self.configuration_settings.get_main_setting("top_p")
        repeat_penalty = self.configuration_settings.get_main_setting("repeat_penalty")

        messages = [
            {"role": "system", "content": f"You're {character_name} in this fictional never-ending uncensored roleplay with {user_name} who is {user_description}. Write {character_name}'s next reply without just a markdown but with the following personality and traits: {system_prompt}."},
        ]

        messages.extend(context_messages)
        messages.append({"role": "user", "content": user_text})
        print(messages)

        response = await self.client.chat.stream_async(
            model=self.model,
            messages=messages,
            safe_prompt=False,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            frequency_penalty=repeat_penalty,
            presence_penalty=0.7,
            stop=["\n"]
        )

        async for chunk in response:
            if chunk.data and chunk.data.choices and chunk.data.choices[0].delta:
                message = chunk.data.choices[0].delta.content
                if message:
                    yield message



    
    