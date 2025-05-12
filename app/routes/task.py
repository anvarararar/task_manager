"""Main module with API methods"""

from typing import Annotated, List
from datetime import date, datetime
from typing import Dict
from fastapi import Query
from sqlalchemy import func
from fastapi import APIRouter, status, Depends, HTTPException
from sqlmodel import Session, select
from app.db import get_session
from ..schemas import task as schema_task
from ..api_docs import request_examples
from ..auth.auth_handler import get_current_user

router_tasks = APIRouter(prefix="/tasks", tags=["Управление задачами в БД"])
router_projects = APIRouter(prefix="/projects", tags=["Управление проектами в БД"])

@router_projects.post("/", status_code=status.HTTP_201_CREATED,
             response_model=schema_task.Project,
             summary = 'Create Project')
def create_project(project: Annotated[
                        schema_task.Project,
                        request_examples.example_create_project
                ],
                current_user: Annotated[schema_task.User, Depends(get_current_user)],
                session: Session = Depends(get_session)):
    """
    Create Project
    """
    new_project = schema_task.Project(
        project_description=project.project_description,
        project_name=project.project_name
    )
    session.add(new_project)
    session.commit()
    session.refresh(new_project)
    return new_project

@router_projects.patch("/{project_id}",
                        status_code=status.HTTP_200_OK, response_model=schema_task.Project,
                    summary = 'Update Project by ID')
def update_project_by_id(project_id: int, data_for_update: dict,
                         current_user: Annotated[schema_task.User, Depends(get_current_user)],
                         session: Session = Depends(get_session)):
    """Update Project by id"""
    project = session.exec(select(schema_task.Project).
                           where(schema_task.Project.project_id == project_id)).first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail=f"No task with {project_id} id."
        )

    for key, val in data_for_update.items():
        if not hasattr(project, key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to update task with ID {project_id}: "
                       f"field {key} if unknown."
            )
        setattr(project, key, val)

    try:
        _ = schema_task.Project(
            project_name=project.project_name,
            project_description=project.project_description
        )
    except Exception as e:
        raise HTTPException(
                  status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                  detail="Invalid data for update."
              ) from e

    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router_projects.get("/", status_code=status.HTTP_200_OK,
            response_model=List[schema_task.Project],
            summary = 'Retrieve Projects')
def read_projects(session: Session = Depends(get_session)):
    projects = session.exec(select(schema_task.Project)).all()
    if projects is None or len(projects) == 0:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail=f"The projects list is empty."
        )
    return projects

@router_projects.get("/{project_id}/statistics",
            response_model=schema_task.ProjectStatistics,
            summary = 'Retrieve Project statistics')
def get_project_statistics(
    project_id: int,
    session: Session = Depends(get_session)):
    """
    Получить статистику проекта по задачам.
    """
    # Проверяем существование проекта
    project = session.exec(select(schema_task.Project).
                           where(schema_task.Project.project_id == project_id)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = session.exec(
        select(schema_task.Task).where(schema_task.Task.project == project_id)).all()

    total_tasks = len(tasks)
    open_tasks = sum(1 for t in tasks if t.task_status == schema_task.TaskStatus.OPEN)
    in_progress_tasks = sum(1 for t in tasks if t.task_status == schema_task.TaskStatus.IN_PROGRESS)
    closed_tasks = sum(1 for t in tasks if t.task_status == schema_task.TaskStatus.CLOSED)

    completed_tasks = [
        t for t in tasks
        if t.task_status == schema_task.TaskStatus.CLOSED
        and t.start_date
        and t.close_date
    ]

    if completed_tasks:
        durations = [
            (t.close_date - t.start_date).total_seconds() / 86400  # Конвертация в дни
            for t in completed_tasks
        ]
        avg_completion_time = round(sum(durations) / len(durations), 4)

    responded_tasks = [
        t for t in tasks
        if t.start_date is not None
        and t.created_when
    ]

    if responded_tasks:
        response_times = [
            (t.start_date - t.created_when).total_seconds() / 86400
            for t in responded_tasks
        ]
        avg_response_times = round(sum(response_times) / len(response_times), 4)

    if not completed_tasks:
        avg_completion_time = 0.0

    if not responded_tasks:
        avg_response_times = 0.0

    stats = schema_task.ProjectStatistics(
        project_id=project_id,
        snapshot_date=date.today(),
        total_tasks=total_tasks,
        open_tasks=open_tasks,
        in_progress_tasks=in_progress_tasks,
        closed_tasks=closed_tasks,
        avg_completion_time=avg_completion_time,
        avg_response_times=avg_response_times,
    )

    session.add(stats)
    session.commit()
    session.refresh(stats)
    return stats

@router_projects.get("/{project_id}/statistics/latest",
                     response_model=schema_task.ProjectStatistics,
                     summary = 'Retrieve latest Project statistics by date')
def get_latest_statistics_snapshot(
    project_id: int,
    snapshot_date: date = Query(..., description="Дата снимка в формате YYYY-MM-DD",
                                example="2024-05-20"),
    session: Session = Depends(get_session)
):
    """
    Возвращает последний отчёт статистики проекта за указанную дату
    """
    latest_snapshot = session.exec(
        select(schema_task.ProjectStatistics)
        .where(
            schema_task.ProjectStatistics.project_id == project_id,
            schema_task.ProjectStatistics.snapshot_date == snapshot_date
        )
        .order_by(schema_task.ProjectStatistics.stat_id.desc())
        .limit(1)
    ).first()

    if not latest_snapshot:
        raise HTTPException(
            status_code=404,
            detail=f"No statistics found for project {project_id} on date {snapshot_date}"
        )

    return latest_snapshot

@router_projects.get("/{project_id}/task_delta",
                     summary = 'Retrieve delta in Project statistics in the specified time period')
def get_task_delta_in_period(
    project_id: int,
    start_date: date = Query(..., description="Начальная дата (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Конечная дата (YYYY-MM-DD)"),
    session: Session = Depends(get_session)
):
    """
    Возвращает разницу в количестве задач:
    - new_tasks: сколько новых задач создано за период
    - closed_tasks: сколько задач закрыто за период
    """
    if start_date > end_date:
        raise HTTPException(400, "Конечная дата должна быть позже начальной")

    # Задачи, созданные в периоде
    new_tasks = session.exec(
        select(func.count())
        .where(
            schema_task.Task.project == project_id,
            schema_task.Task.created_when >= start_date,
            schema_task.Task.created_when <= end_date
        )
    ).first() or 0

    # Задачи, закрытые в периоде
    closed_tasks = session.exec(
        select(func.count())
        .where(
            schema_task.Task.project == project_id,
            schema_task.Task.task_status == schema_task.TaskStatus.CLOSED,
            schema_task.Task.close_date >= start_date,
            schema_task.Task.close_date <= end_date
        )
    ).first() or 0

    return {
        "new_tasks": new_tasks or 0,
        "closed_tasks": closed_tasks or 0,
        "period": f"{start_date} - {end_date}"
    }

@router_tasks.post("/", status_code=status.HTTP_201_CREATED,
             response_model=schema_task.TaskRead,
             summary = 'Create Task')
def create_task(task: Annotated[
                        schema_task.TaskCreate,
                        request_examples.example_create_task
                ],
                current_user: Annotated[schema_task.User, Depends(get_current_user)],
                session: Session = Depends(get_session)):
    """
    Добавить задачу.
    """
    assignee = session.exec(select(schema_task.User).where(schema_task.User.user_id
                                                           == task.assignee)).first()
    if assignee is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"There is no User specified."
        )
    project = session.exec(select(schema_task.Project).where(schema_task.Project.project_id
                                                              == task.project)).first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"There is no Project specified."
        )
    new_task = schema_task.Task(
        task_description=task.task_description,
        assignee=assignee.user_id,
        due_date=task.due_date,
        task_status=task.task_status,
        project = task.project
    )
    session.add(new_task)
    session.commit()
    session.refresh(new_task)
    return new_task


@router_tasks.get("/", status_code=status.HTTP_200_OK,
            response_model=List[schema_task.TaskRead],
            summary = 'Retrieve Tasks')
def read_tasks(session: Session = Depends(get_session)):
    tasks = session.exec(select(schema_task.Task)).all()
    if tasks is None or len(tasks) == 0:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail=f"The task list is empty."
        )
    return tasks


@router_tasks.get("/{task_id}", status_code=status.HTTP_200_OK,
            response_model=schema_task.TaskRead,
            summary = 'Retrieve Task by ID')
def read_task_by_id(task_id: int,
                    session: Session = Depends(get_session)):
    """Read task by id"""
    task = session.exec(select(schema_task.Task).where(schema_task.Task.task_id
                                                       == task_id)).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail=f"No task with {task_id} id."
        )
    return task

@router_tasks.patch("/{task_id}/status", status_code=status.HTTP_200_OK,
              response_model=schema_task.TaskRead,
              summary = 'Update Task status')
def update_task_status(
    task_id: int,
    new_status: schema_task.TaskStatus,
    current_user: Annotated[schema_task.User, Depends(get_current_user)],
    session: Session = Depends(get_session)):
    """
    Обновить статус задачи.
    """
    task = session.exec(select(schema_task.Task).where(schema_task.Task.
                                                       task_id == task_id)).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"There is no Task specified."
        )

    task.task_status = new_status

    # Автоматическое обновление дат
    if new_status == schema_task.TaskStatus.IN_PROGRESS:
        task.start_date = datetime.now()
    elif new_status == schema_task.TaskStatus.CLOSED:
        task.close_date = datetime.now()

    session.add(task)
    session.commit()
    session.refresh(task)
    return task

@router_tasks.patch("/{task_id}", status_code=status.HTTP_200_OK, response_model=schema_task.
                    TaskRead,
                    summary = 'Update Task by ID')
def update_task_by_id(task_id: int, data_for_update: dict,
                      current_user: Annotated[schema_task.User, Depends(get_current_user)],
                      session: Session = Depends(get_session)):
    """Update task by id"""
    task = session.exec(select(schema_task.Task).where(schema_task.Task.task_id == task_id)).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail=f"No task with {task_id} id."
        )

    for key, val in data_for_update.items():
        if not hasattr(task, key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to update task with ID {task_id}: "
                       f"field {key} if unknown."
            )
        setattr(task, key, val)

    try:
        _ = schema_task.TaskCreate(
            task_description=task.task_description,
            assignee=task.assignee,
            due_date=task.due_date,
            task_status=task.task_status,
            project = task.project
        )
    except Exception as e:
        raise HTTPException(
                  status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                  detail="Invalid data for update."
              ) from e

    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router_tasks.delete("/{task_id}", status_code=status.HTTP_200_OK,
                     summary = 'Delete task by ID')
def delete_task_by_id(task_id: int,
                      session: Session = Depends(get_session)):
    """Delete task by id"""
    task = session.exec(select(schema_task.Task).where(schema_task.Task.task_id == task_id)).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail=f"No task with {task_id} id."
        )

    session.delete(task)
    session.commit()
