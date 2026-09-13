from datetime import datetime
from pydantic import BaseModel, ConfigDict

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