from crewai.tools import BaseTool
from typing import Optional
from openai import OpenAI
from config.settings import Config
from utils.logger import logger

class DALLETool(BaseTool):
    name: str = "DALL-E Image Generation Tool"
    description: str = "Generates images using DALL-E API"

    def __init__(self):
        super().__init__()
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

    def _run(self, prompt: str) -> Optional[str]:
        try:
            logger.info(f"Generating cover image with prompt: {prompt}")
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1792x1024",
                quality="standard",
                n=1
            )
            
            image_url = response.data[0].url
            logger.info("Successfully generated cover image")
            return image_url

        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return None