from utils.logger import logger
import os
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from utils.linkedin_scrape_tool import LinkedInScrapeTool
from utils.notification_slack_tool import NotificationSlackTool
from utils.models import LinkedInPostContent
import ssl
import logging

ssl._create_default_https_context = ssl._create_unverified_context

logging.basicConfig(level=logging.DEBUG)


def main():
    try:
        # Initialize tools
        linkedin_tool = LinkedInScrapeTool()
        serper_tool = SerperDevTool()
        notification_slack_tool = NotificationSlackTool()

        # Initialize agents
        linkedin_scrape_agent = Agent(
            role="LinkedIn Content Explorer",
            goal="Identify and collect engaging LinkedIn posts about AI topics",
            backstory="Expert at discovering trending AI content on LinkedIn.",
            tools=[linkedin_tool],
            llm="gpt-4o-mini",
            verbose=True
        )

        linkedin_analyze_agent = Agent(
            role="LinkedIn Engagement Analyst",
            goal="Analyze LinkedIn posts to identify trends and engagement metrics",
            backstory="Expert at analyzing engagement patterns and identifying successful content strategies.",
            llm="gpt-4o-mini",
            verbose=True
        )

        brainstorm_agent = Agent(
            role="Creative Insights Generator",
            goal="Generate content ideas based on analyzed data",
            backstory="Expert at identifying content opportunities and crafting engaging narratives.",
            llm="gpt-4o-mini",
            verbose=True
        )

        web_search_agent = Agent(
            role="Knowledge Discovery Specialist",
            goal="Research and validate content topics",
            backstory="Expert at finding authoritative sources and relevant research.",
            tools=[serper_tool],
            llm="gpt-3.5-turbo",
            verbose=True
        )

        post_create_agent = Agent(
            role="LinkedIn Content Creator",
            goal="Create engaging LinkedIn posts",
            backstory="Expert at writing viral LinkedIn content.",
            llm="gpt-4o-mini",
            verbose=True
        )

        notification_agent = Agent(
            role="Notification Coordinator",
            goal="Handle content review notifications",
            backstory="Expert at managing content workflow and gathering feedback.",
            tools=[notification_slack_tool],
            llm="gpt-3.5-turbo",
            verbose=True
        )

        # Initialize tasks
        scrape_task = Task(
            description="Scrape LinkedIn for popular AI-related posts",
            expected_output="List of relevant LinkedIn posts with engagement metrics",
            agent=linkedin_scrape_agent
        )

        analyze_task = Task(
            description="Analyze scraped posts for engagement patterns",
            expected_output="Analysis report of engagement trends",
            agent=linkedin_analyze_agent,
            context=[scrape_task]
        )

        brainstorm_task = Task(
            description="Generate content ideas based on analysis",
            expected_output="List of content suggestions with rationale",
            agent=brainstorm_agent,
            context=[analyze_task]
        )

        web_search_task = Task(
            description="Research supporting content for chosen topics",
            expected_output="Research findings with sources",
            agent=web_search_agent,
            context=[brainstorm_task]
        )

        create_post_task = Task(
            description="""Create a single, focused LinkedIn post based on the research. 
            Focus on the most engaging topic and create one cohesive post. 
            The output must be a single post with a title and content.""",
            expected_output="""A single LinkedIn post in JSON format with two fields:
            - title: The post title
            - content: The main post content""",
            agent=post_create_agent,
            context=[web_search_task],
            output_pydantic=LinkedInPostContent,
            verbose=True
        )

        notify_user_task = Task(
            description="""Send this LinkedIn post for review via Slack using the following format:
            Input format: A dictionary containing 'context' with the post data.
            The post data should include 'title' and 'content' fields.""",
            expected_output="Confirmation of the Slack notification being sent",
            agent=notification_agent,
            context=[create_post_task],
            verbose=True
            )

        # Create and execute crew
        crew = Crew(
            agents=[
                linkedin_scrape_agent,
                linkedin_analyze_agent,
                brainstorm_agent,
                web_search_agent,
                post_create_agent,
                notification_agent
            ],
            tasks=[
                scrape_task,
                analyze_task,
                brainstorm_task,
                web_search_task,
                create_post_task,
                notify_user_task
            ],
            process=Process.sequential,
            verbose=True
        )

        result = crew.kickoff()
        logger.info("Crew execution completed successfully.")
        return result

    except Exception as e:
        logger.exception(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    main()