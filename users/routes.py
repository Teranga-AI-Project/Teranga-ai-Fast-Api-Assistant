from fastapi import APIRouter, Depends
# from sqlalchemy.orm import Session
from auth.dependencies import get_current_user, get_db
from users.schemas import UserSchema
from users.models import User as UserModel

router = APIRouter()

@router.get("/me", response_model=UserSchema)
def read_users_me(current_user: UserModel = Depends(get_current_user)):
    return current_user
