from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.department import DepartmentCreate, DepartmentDetail, DepartmentRead, DepartmentUpdate
from app.schemas.employee import EmployeeCreate, EmployeeRead
from app.services import departments as service

router = APIRouter(prefix="/departments", tags=["departments"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate, db: DbSession) -> DepartmentRead:
    return service.create_department(db, payload)


@router.post(
    "/{department_id}/employees/",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    department_id: int,
    payload: EmployeeCreate,
    db: DbSession,
) -> EmployeeRead:
    return service.create_employee(db, department_id, payload)


@router.get("/{department_id}", response_model=DepartmentDetail)
def get_department(
    department_id: int,
    db: DbSession,
    depth: Annotated[int, Query(ge=0, le=5)] = 1,
    include_employees: bool = True,
) -> DepartmentDetail:
    return service.get_department_tree(
        db,
        department_id,
        depth=depth,
        include_employees=include_employees,
    )


@router.patch("/{department_id}", response_model=DepartmentRead)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: DbSession,
) -> DepartmentRead:
    return service.update_department(db, department_id, payload)


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int,
    db: DbSession,
    mode: Literal["cascade", "reassign"] = Query(...),
    reassign_to_department_id: int | None = None,
) -> Response:
    service.delete_department(
        db,
        department_id,
        mode=mode,
        reassign_to_department_id=reassign_to_department_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
