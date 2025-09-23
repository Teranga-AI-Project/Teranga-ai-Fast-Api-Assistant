from pydantic import BaseModel

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class UserSchema(UserBase):
    id: int
    email: str
    # is_active: bool

    class Config:
        # orm_mode = True
        from_attributes = True
