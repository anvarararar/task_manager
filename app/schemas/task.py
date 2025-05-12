"""Models for DM"""

from datetime import date, timedelta, datetime
from enum import Enum
from typing import Optional, Annotated, TypeAlias
from pydantic import (BaseModel, Field, BeforeValidator, EmailStr)
from pydantic_settings import SettingsConfigDict
from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field as SQLField


def _empty_str_or_none(value: str | None) -> None:
    if value is None or value == "":
        return None
    raise ValueError("Expected empty value")


EmptyStrOrNone: TypeAlias = Annotated[None, BeforeValidator(_empty_str_or_none)]

class TaskStatus(str, Enum):
    """ENUM for task_status parameter"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"

class TaskCreate(BaseModel):
    """Model for Task"""
    task_description: str = Field(
        description="Описание задачи",
        max_length=300
    )
    assignee: int
    due_date: Optional[date] = Field(
        description="Крайний срок исполнения задачи. "
                    "Не допускаются даты, более ранние, "
                    "чем сегодняшняя.",
        gt=date.today() - timedelta(days=1),
        default_factory=lambda: date.today() + timedelta(days=1)
    )
    task_status: TaskStatus = Field(
        TaskStatus.OPEN,
        description="Статус задачи"
    )
    start_date: Optional[datetime] = Field(default=None)  # Начало работы
    close_date: Optional[datetime] = Field(default=None)  # Завершение
    project: int
    created_when: Optional[datetime] = Field(default=None)


class TaskRead(TaskCreate):
    """Model for Task responce"""
    task_id: int
    due_date: EmptyStrOrNone | date
    start_date: EmptyStrOrNone | datetime
    close_date: EmptyStrOrNone | datetime


class User(SQLModel, table=True):
    """Model for User"""
    __table_args__ = (UniqueConstraint("email"),)
    user_id: int = SQLField(default=None, nullable=False, primary_key=True)
    email: str = SQLField(nullable=True, unique_items=True)
    password: str | None
    name: str

    model_config = SettingsConfigDict(
        json_schema_extra = {
            "example": {
                "name": "Василий",
                "email": "user@example.com",
                "password": "qwerty"
            }
        })

class UserCrendentials(BaseModel):
    """Model for User's credentials"""
    email: EmailStr
    password: str

    model_config = SettingsConfigDict(
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "querty"
            }
        })

class Project(SQLModel, table=True):
    """Model and table for Projects"""
    project_id: int = SQLField(default=None, nullable=False, primary_key=True)
    project_name: str
    project_description: str | None


class Task(SQLModel, TaskRead, table=True):
    """Table for Users"""
    task_id: int = SQLField(default=None, nullable=False, primary_key=True)
    due_date: date
    assignee: int = SQLField(foreign_key="user.user_id")
    project: int = SQLField(default=None, nullable=True, foreign_key="project.project_id")
    task_status: TaskStatus = SQLField(default=TaskStatus.OPEN)
    start_date: datetime = SQLField(default=None, nullable=True)
    close_date: datetime = SQLField(default=None, nullable=True)
    created_when: datetime = SQLField(default_factory=datetime.now)

class ProjectStatistics(SQLModel, table=True):
    """Table for reporting info"""
    stat_id: int = SQLField(default=None, primary_key=True)
    project_id: int = SQLField(foreign_key="project.project_id")
    snapshot_date: date = SQLField(default_factory=date.today)  # Дата снимка
    total_tasks: int = 0
    open_tasks: int = 0
    in_progress_tasks: int = 0
    closed_tasks: int = 0
    avg_completion_time: float = 0  # Среднее время выполнения в днях
    avg_response_times: float = 0
