import openai
from crewai import Agent, Task, Crew, Process
from utils.logger import logger 

class PostCreateAgent(Agent):
    """
    Agent for creating professional LinkedIn posts by synthesizing insights and research.
    Uses GPT-4 for content generation and optionally DALL-E for multimedia elements.
    """
    
    def run(self, context=None):
        logger.info("PostCreateAgent: Starting post creation process...")
        
        if not context or "creative_insights" not in context or "research_references" not in context:
            logger.error("PostCreateAgent: Missing required inputs in context.")
            raise ValueError("Context must include 'creative_insights' and 'research_references'.")
        
        # Extract inputs
        creative_insights = context["creative_insights"]
        research_references = context["research_references"]

        # Combine insights and references into a prompt
        prompt = (
            "Using the following creative insights and research, create a professional LinkedIn post:\n\n"
            f"Creative Insights: {creative_insights}\n\n"
            f"Research References: {research_references}\n\n"
            "The post should be engaging, professional, and aligned with LinkedIn's audience."
        )

        # Generate content using GPT-4
        logger.info("PostCreateAgent: Generating text content with GPT-4...")
        response = openai.Completion.create(
            model="text-davinci-003",  # Replace with "gpt-4" if GPT-4 is available
            prompt=prompt,
            max_tokens=500,
            temperature=0.7
        )
        content = response.choices[0].text.strip()

        # Optional: Generate multimedia element (image)
        image_required = context.get("image_required", False)
        image = None
        if image_required:
            logger.info("PostCreateAgent: Generating image with DALL-E...")
            image_response = openai.Image.create(
                prompt=context.get("image_prompt", "A visually appealing graphic about AI innovations."),
                n=1,
                size="1024x1024"
            )
            image = image_response['data'][0]['url']

        result = {
            "content": content,
            "image": image
        }

        logger.info("PostCreateAgent: Post creation completed successfully.")
        return result
