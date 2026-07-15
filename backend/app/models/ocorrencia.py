from __future__ import annotations
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Ocorrencia(Base):
    __tablename__ = "ocorrencias"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    categoria: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    gravidade: Mapped[str] = mapped_column(
        String(20), default="media", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="aberta", nullable=False, index=True
    )
    apartamento_id: Mapped[int] = mapped_column(
        ForeignKey("apartamentos.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    apartamento_origem: Mapped["Apartamento"] = relationship(  # noqa: F821
        "Apartamento", backref="ocorrencias"
    )
