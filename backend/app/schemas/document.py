from enum import Enum
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ProcessingStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DocumentBase(BaseModel):
    filename: str
    title: str | None = None
    supervisory_committee: str | None = None

class DocumentCreate(DocumentBase):
    file_path: str
    project_id: int | None = None

class DocumentResponse(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None = None
    file_path: str
    status: ProcessingStatus
    upload_date: datetime