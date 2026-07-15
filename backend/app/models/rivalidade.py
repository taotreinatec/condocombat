from __future__ import annotations
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Rivalidade(Base):
    __tablename__ = "rivalidades"

    __table_args__ = (
        UniqueConstraint(
            "apartamento_a_id", "apartamento_b_id",
            name="uq_rivalidade_apartamentos",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    apartamento_a_id: Mapped[int] = mapped_column(
        ForeignKey("apartamentos.id"), nullable=False, index=True
    )
    apartamento_b_id: Mapped[int] = mapped_column(
        ForeignKey("apartamentos.id"), nullable=False, index=True
    )
    motivo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nivel: Mapped[str] = mapped_column(
        String(20), default="moderado", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="ativa", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    apartamento_a: Mapped["Apartamento"] = relationship(  # noqa: F821
        "Apartamento", foreign_keys=[apartamento_a_id], backref="rivalidades_como_a"
    )
    apartamento_b: Mapped["Apartamento"] = relationship(  # noqa: F821
        "Apartamento", foreign_keys=[apartamento_b_id], backref="rivalidades_como_b"
    )
