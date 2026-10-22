from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class RagConfigBase(BaseModel):
    key: str
    value: str
    description: str | None = None

class RagConfigCreate(RagConfigBase):
    pass

class RagConfigUpdate(BaseModel):
    value: str
    description: str | None = None

class RagConfigResponse(RagConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: datetime


class ChatSettingsIn(BaseModel):
    llm_model: str = Field(min_length=1, max_length=100)
    temperature: float = Field(ge=0, le=2)
    system_prompt: str = Field(min_length=1, max_length=8000)
    top_k: int = Field(ge=1, le=100)
    similarity_threshold: float = Field(ge=-1, le=1)


class ChatSettingsOut(ChatSettingsIn):
    saved: bool
    model_options: list[str]