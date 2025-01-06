from pydantic import BaseModel, Field

class AgentConfig(BaseModel):
    name: str = Field(..., description="The name of the agent.")
    role: str = Field(..., description="The role of the agent.")
    goal: str = Field(..., description="The goal of the agent.")
    backstory: str = Field(..., description="The backstory of the agent.")
    allow_delegation: bool = Field(default=False, description="Whether the agent allows delegation.")
    verbose: bool = Field(default=True, description="Whether the agent operates in verbose mode.")
