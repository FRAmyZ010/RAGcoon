from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict

class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None

class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role_id: int

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role_id: int
    role: RoleResponse
    created_at: datetime