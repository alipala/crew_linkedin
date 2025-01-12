from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime


class AgentConfig(BaseModel):
    name: str = Field(..., description="The name of the agent.")
    role: str = Field(..., description="The role of the agent.")
    goal: str = Field(..., description="The goal of the agent.")
    backstory: str = Field(..., description="The backstory of the agent.")
    allow_delegation: bool = Field(default=False, description="Whether the agent allows delegation.")
    verbose: bool = Field(default=True, description="Whether the agent operates in verbose mode.")

class PostMetrics(BaseModel):
    """Model for post engagement metrics."""
    reactions: int = Field(default=0, description="Number of reactions on the post")
    comments: int = Field(default=0, description="Number of comments on the post")
    shares: int = Field(default=0, description="Number of shares/reposts")

class LinkedInPost(BaseModel):
    """Model for LinkedIn post data."""
    post_id: Optional[str] = Field(default=None, description="Unique identifier for the post")
    text: str = Field(..., description="Content of the post")
    date: Optional[str] = Field(default=None, description="Post creation date")
    metrics: PostMetrics = Field(default_factory=PostMetrics, description="Engagement metrics")
    url: Optional[str] = Field(default=None, description="URL to the post")
    linked_url: Optional[str] = Field(default=None, description="URL referenced in the post")
    scraped_at: datetime = Field(default_factory=datetime.now, description="Timestamp of when the post was scraped")
    is_ai_related: bool = Field(default=False, description="Whether the post is AI-related")
    matched_ai_topics: List[str] = Field(default_factory=list, description="AI topics found in the post")

class LinkedInPostContent(BaseModel):
    """Model for structured LinkedIn post content"""
    title: str = Field(description="The title of the LinkedIn post")
    content: str = Field(description="The main content of the LinkedIn post")