from __future__ import annotations

import logging
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import Select, exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.employee import Employee
from app.schemas.department import DepartmentCreate, DepartmentDetail, DepartmentNode, DepartmentUpdate
from app.schemas.employee import EmployeeCreate

logger = logging.getLogger(__name__)

DeleteMode = Literal["cascade", "reassign"]


def get_department_or_404(db: Session, department_id: int) -> Department:
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )
    return department


def _parent_filter(parent_id: int | None):
    if parent_id is None:
        return Department.parent_id.is_(None)
    return Department.parent_id == parent_id


def _department_name_exists(
    db: Session,
    *,
    name: str,
    parent_id: int | None,
    exclude_department_id: int | None = None,
) -> bool:
    stmt: Select[tuple[bool]] = select(
        exists().where(Department.name == name).where(_parent_filter(parent_id))
    )
    if exclude_department_id is not None:
        stmt = select(
            exists()
            .where(Department.name == name)
            .where(_parent_filter(parent_id))
            .where(Department.id != exclude_department_id)
        )
    return bool(db.execute(stmt).scalar())


def _ensure_name_is_unique(
    db: Session,
    *,
    name: str,
    parent_id: int | None,
    exclude_department_id: int | None = None,
) -> None:
    if _department_name_exists(
        db,
        name=name,
        parent_id=parent_id,
        exclude_department_id=exclude_department_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department name must be unique within one parent",
        )


def _ensure_parent_exists(db: Session, parent_id: int | None) -> None:
    if parent_id is not None and db.get(Department, parent_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent department not found",
        )


def _ensure_no_cycle(db: Session, *, department_id: int, new_parent_id: int | None) -> None:
    if new_parent_id is None:
        return

    if department_id == new_parent_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department cannot be parent of itself",
        )

    current = db.get(Department, new_parent_id)
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent department not found",
        )

    visited: set[int] = set()
    while current is not None:
        if current.id in visited:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cycle detected in department tree",
            )
        visited.add(current.id)

        if current.id == department_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot move department inside its own subtree",
            )

        if current.parent_id is None:
            break
        current = db.get(Department, current.parent_id)


def create_department(db: Session, payload: DepartmentCreate) -> Department:
    _ensure_parent_exists(db, payload.parent_id)
    _ensure_name_is_unique(db, name=payload.name, parent_id=payload.parent_id)

    department = Department(name=payload.name, parent_id=payload.parent_id)
    db.add(department)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.info("department create integrity error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department violates unique constraints",
        ) from exc

    db.refresh(department)
    return department


def create_employee(db: Session, department_id: int, payload: EmployeeCreate) -> Employee:
    get_department_or_404(db, department_id)

    employee = Employee(
        department_id=department_id,
        full_name=payload.full_name,
        position=payload.position,
        hired_at=payload.hired_at,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def update_department(db: Session, department_id: int, payload: DepartmentUpdate) -> Department:
    department = get_department_or_404(db, department_id)
    data = payload.model_dump(exclude_unset=True)

    new_name = data.get("name", department.name)
    new_parent_id = data.get("parent_id", department.parent_id)

    if "parent_id" in data:
        _ensure_no_cycle(db, department_id=department.id, new_parent_id=new_parent_id)
    else:
        _ensure_parent_exists(db, new_parent_id)

    _ensure_name_is_unique(
        db,
        name=new_name,
        parent_id=new_parent_id,
        exclude_department_id=department.id,
    )

    department.name = new_name
    department.parent_id = new_parent_id

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.info("department update integrity error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department violates unique constraints",
        ) from exc

    db.refresh(department)
    return department


def _employees_for_department(db: Session, department_id: int) -> list[Employee]:
    stmt = (
        select(Employee)
        .where(Employee.department_id == department_id)
        .order_by(Employee.full_name.asc(), Employee.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


def _children_for_department(db: Session, department_id: int) -> list[Department]:
    stmt = (
        select(Department)
        .where(Department.parent_id == department_id)
        .order_by(Department.name.asc(), Department.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


def _build_node(
    db: Session,
    department: Department,
    *,
    depth: int,
    include_employees: bool,
) -> DepartmentNode:
    employees = _employees_for_department(db, department.id) if include_employees else None

    children: list[DepartmentNode] = []
    if depth > 0:
        for child in _children_for_department(db, department.id):
            children.append(
                _build_node(
                    db,
                    child,
                    depth=depth - 1,
                    include_employees=include_employees,
                )
            )

    return DepartmentNode(department=department, employees=employees, children=children)


def get_department_tree(
    db: Session,
    department_id: int,
    *,
    depth: int,
    include_employees: bool,
) -> DepartmentDetail:
    department = get_department_or_404(db, department_id)
    node = _build_node(db, department, depth=depth, include_employees=include_employees)
    return DepartmentDetail(**node.model_dump())


def _ensure_reassign_children_have_no_name_conflicts(db: Session, department: Department) -> None:
    children = _children_for_department(db, department.id)
    if not children:
        return

    child_ids = {child.id for child in children}
    for child in children:
        stmt = (
            select(Department.id)
            .where(Department.name == child.name)
            .where(_parent_filter(department.parent_id))
            .where(Department.id != department.id)
            .where(Department.id.not_in(child_ids))
            .limit(1)
        )
        conflict_id = db.execute(stmt).scalar_one_or_none()
        if conflict_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Cannot reassign child departments to deleted department parent: "
                    f"name conflict for '{child.name}'"
                ),
            )


def delete_department(
    db: Session,
    department_id: int,
    *,
    mode: DeleteMode,
    reassign_to_department_id: int | None,
) -> None:
    department = get_department_or_404(db, department_id)

    if mode == "cascade":
        db.delete(department)
        db.commit()
        return

    if mode != "reassign":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported delete mode",
        )

    if reassign_to_department_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reassign_to_department_id is required for reassign mode",
        )

    if reassign_to_department_id == department_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot reassign employees to deleted department",
        )

    get_department_or_404(db, reassign_to_department_id)
    _ensure_reassign_children_have_no_name_conflicts(db, department)

    db.execute(
        update(Employee)
        .where(Employee.department_id == department_id)
        .values(department_id=reassign_to_department_id)
    )
    db.execute(
        update(Department)
        .where(Department.parent_id == department_id)
        .values(parent_id=department.parent_id)
    )
    db.delete(department)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.info("department delete reassign integrity error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Delete reassign violates database constraints",
        ) from exc
