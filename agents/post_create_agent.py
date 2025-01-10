from crewai import Agent
import openai
from typing import Dict, Any, Optional
from utils.logger import logger

class PostCreateAgent(Agent):
    """
    Agent for creating professional LinkedIn posts by synthesizing insights and research.
    Uses GPT-4 for content generation and optionally DALL-E for multimedia elements.
    """

    def run(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info("PostCreateAgent: Starting post creation process")
        try:
            # Validate context
            if not context:
                logger.error("PostCreateAgent: No context provided")
                raise ValueError("Context is required for post creation")

            required_fields = ['creative_insights', 'research_references']
            for field in required_fields:
                if field not in context:
                    logger.error(f"PostCreateAgent: Missing required field '{field}' in context")
                    raise ValueError(f"Context must include '{field}'")

            # Extract and log inputs
            creative_insights = context["creative_insights"]
            research_references = context["research_references"]
            logger.debug(f"PostCreateAgent: Processing creative insights: {creative_insights[:100]}...")
            logger.debug(f"PostCreateAgent: Processing research references: {research_references[:100]}...")

            # Generate content
            prompt = self._create_prompt(creative_insights, research_references)
            logger.info("PostCreateAgent: Generating text content with GPT-4")
            
            response = openai.Completion.create(
                model="text-davinci-003",
                prompt=prompt,
                max_tokens=500,
                temperature=0.7
            )
            content = response.choices[0].text.strip()
            logger.info(f"PostCreateAgent: Generated content preview: {content[:100]}...")

            # Handle multimedia generation if required
            image = None
            if context.get("image_required", False):
                logger.info("PostCreateAgent: Starting image generation with DALL-E")
                image = self._generate_image(context)
                logger.info("PostCreateAgent: Successfully generated image")

            # Prepare output
            output = {
                "content": content,
                "image": image,
                "status": "success"
            }
            logger.info(f"PostCreateAgent: Final output: {str(output)[:200]}...")
            
            return {"content": content, "status": "success"}
            #return output

        except Exception as e:
            error_msg = f"PostCreateAgent failed: {str(e)}"
            logger.exception(error_msg)
            return {
                "content": None,
                "image": None,
                "status": "error",
                "error": str(e)
        }

    def _create_prompt(self, creative_insights: str, research_references: str) -> str:
        """Create the prompt for content generation."""
        return (
            "Using the following creative insights and research, create a professional LinkedIn post:\n\n"
            f"Creative Insights: {creative_insights}\n\n"
            f"Research References: {research_references}\n\n"
            "The post should be engaging, professional, and aligned with LinkedIn's audience."
        )

    def _generate_image(self, context: Dict[str, Any]) -> Optional[str]:
        """Generate image using DALL-E."""
        try:
            image_prompt = context.get(
                "image_prompt", 
                "A visually appealing graphic about AI innovations."
            )
            logger.debug(f"PostCreateAgent: Using image prompt: {image_prompt}")
            
            response = openai.Image.create(
                prompt=image_prompt,
                n=1,
                size="1024x1024"
            )
            return response['data'][0]['url']
        except Exception as e:
            logger.error(f"PostCreateAgent: Image generation failed: {str(e)}")
            return None