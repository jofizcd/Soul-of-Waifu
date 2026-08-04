import os
import base64
import asyncio
import logging
import datetime
from typing import Optional

import aiohttp

from app.configuration import configuration

logger = logging.getLogger("ImageGenerator")

_TIMEOUT_LOCAL = aiohttp.ClientTimeout(total=120)
_TIMEOUT_CLOUD = aiohttp.ClientTimeout(total=60)

PROVIDER_A1111    = "Automatic1111"
PROVIDER_COMFYUI  = "ComfyUI (A1111 API)"
PROVIDER_DALLE    = "DALL-E 3"
PROVIDER_NOVELAI  = "NovelAI"
PROVIDER_FLUX     = "FLUX"

class ImageGenerator:
    """
    Manages async image generation across multiple providers.

    Usage:
        generator = ImageGenerator()
        relative_path = await generator.generate_image(core_prompt, character_name)
    """

    def __init__(self) -> None:
        self.config     = configuration.ConfigurationSettings()
        self.api_config = configuration.ConfigurationAPI()

    async def generate_image(self, core_prompt: str, character_name: str) -> Optional[str]:
        """
        Build the full prompt from settings, dispatch to the active provider,
        save the result, and return the gallery-relative path.

        Returns None on any failure so the caller can handle it gracefully.
        """
        provider = self.config.get_main_setting("image_provider") or PROVIDER_A1111
        prefix   = self.config.get_main_setting("image_prefix_prompt") or "masterpiece, best quality, very aesthetic, vivid colors, depth of field"
        negative = self.config.get_main_setting("image_negative_prompt") or \
                   "worst quality, low quality, normal quality, lowres, jpeg artifacts, blurry, bad anatomy, bad hands, missing fingers, extra digits, fewer digits, poorly drawn hands, poorly drawn face, mutated, deformed, ugly, bad proportions, extra limbs, fused fingers, too many fingers, watermark, signature, text"

        width  = int(self.config.get_main_setting("image_width")  or 512)
        height = int(self.config.get_main_setting("image_height") or 768)
        steps  = int(self.config.get_main_setting("image_steps")  or 20)

        full_prompt = f"{prefix}, {core_prompt}" if prefix else core_prompt

        logger.info("Generating image via %s | prompt: %s", provider, full_prompt)

        img_data: Optional[bytes] = None

        try:
            if provider == PROVIDER_A1111 or provider == PROVIDER_COMFYUI:
                logger.debug(f"Calling generate_a1111 with steps={steps}, width={width}, height={height}")
                img_data = await self.generate_a1111(full_prompt, negative, width, height, steps)

            elif provider == PROVIDER_DALLE:
                logger.debug("Calling generate_dalle")
                img_data = await self.generate_dalle(full_prompt)

            elif provider == PROVIDER_NOVELAI:
                logger.debug(f"Calling generate_novelai with steps={steps}, width={width}, height={height}")
                img_data = await self.generate_novelai(full_prompt, negative, width, height, steps)

            elif provider == PROVIDER_FLUX:
                logger.debug(f"Calling generate_flux with width={width}, height={height}")
                img_data = await self.generate_flux(full_prompt, width, height)

            else:
                logger.error("Unsupported image provider: %s", provider)
                return None
                
            if img_data:
                logger.info(f"Successfully received image data from {provider} ({len(img_data)} bytes). Saving...")
            else:
                logger.warning(f"No image data returned from {provider}.")

            return await self.save_image(img_data, character_name)
        except Exception as e:
            logger.error(f"Exception during generate_image routing: {e}", exc_info=True)
            return None

    # Provider: Automatic1111 / ComfyUI-compatible WebUI
    async def generate_a1111(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
    ) -> Optional[bytes]:
        api_url = self.config.get_main_setting("image_api_url") or "http://127.0.0.1:7860"
        url = f"{api_url.rstrip('/')}/sdapi/v1/txt2img"

        payload = {
            "prompt":          prompt,
            "negative_prompt": negative_prompt,
            "width":           width,
            "height":          height,
            "steps":           steps,
            "sampler_name":    "DPM++ 2M Karras",
            "cfg_scale":       7,
        }

        logger.debug(f"A1111 payload: {payload}")

        try:
            logger.debug(f"Attempting to connect to A1111 API at {url}")
            async with aiohttp.ClientSession(timeout=_TIMEOUT_LOCAL) as session:
                async with session.post(url, json=payload) as response:
                    logger.debug(f"A1111 API responded with status {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        logger.debug("Successfully decoded JSON from A1111 response.")
                        return base64.b64decode(data["images"][0])
                    else:
                        body = await response.text()
                        logger.error("A1111 error %d: %s", response.status, body[:300])
                        return None

        except aiohttp.ClientConnectionError:
            logger.error("A1111: cannot connect to %s — is the WebUI running?", url)
            return None
        except asyncio.TimeoutError:
            logger.error("A1111: request timed out after %ds", _TIMEOUT_LOCAL.total)
            return None
        except Exception as exc:
            logger.exception("A1111: unexpected error: %s", exc)
            return None

    # Provider: DALL-E 3
    async def generate_dalle(self, prompt: str) -> Optional[bytes]:
        openai_key = self.api_config.get_token("OPEN_AI_API_TOKEN")
        if not openai_key:
            logger.error("DALL-E: no OpenAI API key configured.")
            return None

        gen_url = "https://api.openai.com/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type":  "application/json",
        }
        payload = {
            "model":  "dall-e-3",
            "prompt": prompt,
            "n":      1,
            "size":   "1024x1024",
            "response_format": "b64_json"
        }

        try:
            async with aiohttp.ClientSession(timeout=_TIMEOUT_CLOUD) as session:
                async with session.post(gen_url, headers=headers, json=payload) as gen_resp:
                    if gen_resp.status != 200:
                        body = await gen_resp.text()
                        logger.error("DALL-E generation error %d: %s", gen_resp.status, body[:300])
                        return None
                    gen_data  = await gen_resp.json()
                    
                    b64 = gen_data["data"]["b64_json"]
                    return base64.b64decode(b64)

        except aiohttp.ClientConnectionError:
            logger.error("DALL-E: network connection failed.")
            return None
        except asyncio.TimeoutError:
            logger.error("DALL-E: request timed out after %ds", _TIMEOUT_CLOUD.total)
            return None
        except Exception as exc:
            logger.exception("DALL-E: unexpected error: %s", exc)
            return None

    # Provider: NovelAI
    async def generate_novelai(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
    ) -> Optional[bytes]:
        novelai_key = self.api_config.get_token("NOVELAI_API_TOKEN")
        if not novelai_key:
            logger.error("NovelAI: no API token configured.")
            return None

        url = "https://image.novelai.net/ai/generate-image"
        headers = {
            "Authorization": f"Bearer {novelai_key}",
            "Content-Type":  "application/json",
        }
        payload = {
            "input":  prompt,
            "model":  "nai-diffusion-4",
            "action": "generate",
            "parameters": {
                "width":               width,
                "height":              height,
                "steps":               steps,
                "scale":               7,
                "sampler":             "k_dpmpp_2m",
                "negative_prompt":     negative_prompt,
                "n_samples":           1,
                "ucPreset":            0,
                "qualityToggle":       True,
            },
        }

        try:
            async with aiohttp.ClientSession(timeout=_TIMEOUT_CLOUD) as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        zip_bytes = await response.read()
                        return self._extract_novelai_image(zip_bytes)
                    else:
                        body = await response.text()
                        logger.error("NovelAI error %d: %s", response.status, body[:300])
                        return None

        except aiohttp.ClientConnectionError:
            logger.error("NovelAI: network connection failed.")
            return None
        except asyncio.TimeoutError:
            logger.error("NovelAI: request timed out after %ds", _TIMEOUT_CLOUD.total)
            return None
        except Exception as exc:
            logger.exception("NovelAI: unexpected error: %s", exc)
            return None

    @staticmethod
    def _extract_novelai_image(zip_bytes: bytes) -> Optional[bytes]:
        import zipfile
        from io import BytesIO

        try:
            with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
                for name in zf.namelist():
                    if name.lower().endswith(".png"):
                        return zf.read(name)
            logger.error("NovelAI: no PNG found in zip response.")
            return None
        except zipfile.BadZipFile:
            logger.error("NovelAI: response is not a valid zip archive.")
            return None

    # Provider: FLUX
    async def generate_flux(
        self,
        prompt: str,
        width: int,
        height: int,
    ) -> Optional[bytes]:
        """
        Generate an image using FLUX Pro via the fal.ai API.
        Requires a FAL_API_TOKEN token in api.json.
        """
        fal_key = self.api_config.get_token("FAL_API_TOKEN")
        if not fal_key:
            logger.error("FLUX: no fal.ai API token configured.")
            return None

        url = "https://fal.run/fal-ai/flux-pro/v1.1"
        headers = {
            "Authorization": f"Key {fal_key}",
            "Content-Type":  "application/json",
        }
        payload = {
            "prompt":           prompt,
            "image_size":       {"width": width, "height": height},
            "num_images":       1,
            "output_format":    "png",
        }

        try:
            async with aiohttp.ClientSession(timeout=_TIMEOUT_CLOUD) as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data      = await response.json()
                        image_url = data["images"][0]["url"]
                        async with session.get(image_url) as img_resp:
                            if img_resp.status == 200:
                                return await img_resp.read()
                            else:
                                logger.error("FLUX: image download failed %d", img_resp.status)
                                return None
                    else:
                        body = await response.text()
                        logger.error("FLUX error %d: %s", response.status, body[:300])
                        return None

        except aiohttp.ClientConnectionError:
            logger.error("FLUX: network connection failed.")
            return None
        except asyncio.TimeoutError:
            logger.error("FLUX: request timed out after %ds", _TIMEOUT_CLOUD.total)
            return None
        except Exception as exc:
            logger.exception("FLUX: unexpected error: %s", exc)
            return None

    async def save_image(self, image_data: Optional[bytes], character_name: str) -> Optional[str]:
        """
        Save PNG bytes to the character's gallery directory.
        """
        if not image_data:
            return None

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename  = f"img_{timestamp}.png"

        base_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "gallery",
            character_name
        )
        save_dir  = os.path.normpath(base_dir)
        file_path = os.path.join(save_dir, filename)

        def _write() -> Optional[str]:
            try:
                os.makedirs(save_dir, exist_ok=True)
                with open(file_path, "wb") as fh:
                    fh.write(image_data)
                logger.info("Image saved: %s", file_path)
                return file_path
            except OSError as err:
                logger.error("Failed to save image to %s: %s", file_path, err)
                return None

        return await asyncio.to_thread(_write)
