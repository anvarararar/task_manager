"""Tests"""

from fastapi import APIRouter, status, Depends
from sqlalchemy import text
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from sqlmodel import Session, select, SQLModel
from app.db import get_session, engine
from app.schemas.task import User
from ..auth.auth_handler import get_current_user

router = APIRouter(prefix="/utils", tags=["Вспомогательные инструменты"])

@router.get("/test-db", status_code=status.HTTP_200_OK)
def test_database(session: Session = Depends(get_session)):
    """
    Test Hello World
    """
    result = session.exec(select(text("'Hello world'"))).all()
    return result


@router.get("/create-db-tables",
            status_code=status.HTTP_200_OK)
def test_create_database():
    """
    Test DB creation
    """
    SQLModel.metadata.create_all(engine)
    return {"message": "Tables created"}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@router.get("/test-auth")
def show_access_token(token: str = Depends(oauth2_scheme)):
    """
    Test auth
    """
    return {"token": token}


@router.get("/me", response_model=int,
            summary = 'Получить ID вошедшего пользователя')
def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Test get user id
    """
    return current_user.user_id
