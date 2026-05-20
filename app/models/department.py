from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.employee import Employee


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        Index("ix_departments_parent_id", "parent_id"),
        Index(
            "uq_departments_parent_name_not_null",
            "parent_id",
            "name",
            unique=True,
            postgresql_where=text("parent_id IS NOT NULL"),
            sqlite_where=text("parent_id IS NOT NULL"),
        ),
        Index(
            "uq_departments_root_name",
            "name",
            unique=True,
            postgresql_where=text("parent_id IS NULL"),
            sqlite_where=text("parent_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    parent: Mapped[Department | None] = relationship(
        "Department",
        remote_side=[id],
        back_populates="children",
    )
    children: Mapped[list[Department]] = relationship(
        "Department",
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    employees: Mapped[list[Employee]] = relationship(
        "Employee",
        back_populates="department",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
