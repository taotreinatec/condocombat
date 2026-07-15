from __future__ import annotations
from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Apartamento(Base):
    __tablename__ = "apartamentos"

    __table_args__ = (
        UniqueConstraint(
            "numero", "bloco", "torre", "condominio_id",
            name="uq_apartamento_identificacao",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero: Mapped[str] = mapped_column(String(10), nullable=False)
    bloco: Mapped[str | None] = mapped_column(String(10), nullable=True)
    torre: Mapped[str | None] = mapped_column(String(50), nullable=True)
    area: Mapped[float | None] = mapped_column(Float, nullable=True)
    condominio_id: Mapped[int] = mapped_column(
        ForeignKey("condominios.id"), nullable=False, index=True
    )

    condominio: Mapped["Condominio"] = relationship(  # noqa: F821
        "Condominio", back_populates="apartamentos"
    )
    moradores: Mapped[list["Morador"]] = relationship(  # noqa: F821
        "Morador", back_populates="apartamento"
    )
