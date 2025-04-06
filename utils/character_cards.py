import aiohttp

from configuration import configuration

class CharactersCard():
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

    async def fetch_trending_character_data(self):
        self.nsfw_query = self.configuration_settings.get_main_setting("nsfw_query")
        if self.nsfw_query:
            url = "https://gateway.chub.ai/search?first=50&page=1&namespace=characters&nsfw=true&nsfw_only=false&nsfl=false&min_tokens=100&max_tokens=100000&chub=true&sort=trending&venus=true&count=false"
        else:
            url = "https://gateway.chub.ai/search?first=50&page=1&namespace=characters&nsfw=false&nsfw_only=false&nsfl=false&min_tokens=100&max_tokens=100000&chub=true&sort=trending&venus=true&count=false"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200: 
                    try:
                        data = await response.json()
                        return data
                    except Exception as e:
                        print("JSON error:", e)
                else:
                    print(f"{response.status}, {await response.text()}")

    async def search_character(self, character_name):
        self.nsfw_query = self.configuration_settings.get_main_setting("nsfw_query")
        if self.nsfw_query:
            url = f"https://gateway.chub.ai/search?first=50&page=1&namespace=characters&search={character_name}&include_forks=true&nsfw=true&nsfw_only=false&nsfl=false&asc=false&min_ai_rating=0&min_tokens=100&max_tokens=100000&chub=true&exclude_mine=true&sort=default&topics=&inclusive_or=false&recommended_verified=false&venus=true&count=false"
        else:
            url = f"https://gateway.chub.ai/search?excludetopics=NSFW&first=50&page=1&namespace=characters&search={character_name}&include_forks=true&nsfw=false&nsfw_only=false&nsfl=false&asc=false&min_ai_rating=0&min_tokens=100&max_tokens=100000&chub=true&exclude_mine=true&sort=default&topics=&inclusive_or=false&recommended_verified=false&venus=true&count=false"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200: 
                    try:
                        data = await response.json()
                        return data
                    except Exception as e:
                        print("JSON error:", e)
                else:
                    print(f"{response.status}, {await response.text()}")

    async def get_character_information(self, full_path):
        url = f"https://gateway.chub.ai/api/characters/{full_path}?full=true&nocache=0.6411485396222347"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()

                            node = data.get("node")
                            if node:
                                character_name = node.get('name', 'Unknown')
                                character_title = node.get('tagline', 'No tagline')
                                character_avatar_url = node.get('avatar_url', 'No avatar')
                                downloads = node.get('starCount', 0)
                                likes = node.get('n_favorites', 0)
                                total_tokens = node.get('nTokens', 0)
                                character_description = node.get('definition', {}).get('description', 'No description')
                                character_personality = node.get('definition', {}).get('personality', 'No personality')
                                character_scenario = node.get('definition', {}).get('scenario', '')
                                if character_scenario:
                                    character_personality += f" {character_scenario}"
                                first_message = node.get('definition', {}).get('first_message', 'No first message')

                                return (
                                    character_name,
                                    character_title,
                                    character_avatar_url,
                                    downloads,
                                    likes,
                                    total_tokens,
                                    character_description,
                                    character_personality,
                                    first_message
                                )
                            else:
                                return (
                                    'Unknown', 'No tagline', 'No avatar', 0, 0, 0,
                                    'No description', 'No personality', 'No first message'
                                )
                        except Exception as e:
                            print("JSON Error:", e)
                            return (
                                'Unknown', 'No tagline', 'No avatar', 0, 0, 0,
                                'No description', 'No personality', 'No first message'
                            )
                    elif response.status == 422:
                        print(f"Error 422: {url}")
                        print(await response.text())
                        return (
                            'Error', 'Invalid request', 'No data', 0, 0, 0,
                            'Invalid description', 'Invalid personality', 'Invalid message'
                        )
                    else:
                        print(f"{response.status}, {await response.text()}")
                        return (
                            'Unknown', 'No tagline', 'No avatar', 0, 0, 0,
                            'No description', 'No personality', 'No first message'
                        )
            except aiohttp.ClientError as e:
                print(f"API connection error: {e}")
                return (
                    'Unknown', 'Connection error', 'No avatar', 0, 0, 0,
                    'No description', 'No personality', 'No first message'
                )
    