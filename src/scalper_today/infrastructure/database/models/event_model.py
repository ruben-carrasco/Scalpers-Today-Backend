from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class EventModel(Base):
    __tablename__ = "economic_events"

    # Primary key
    id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Event metadata
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    hora: Mapped[str] = mapped_column(String(10))

    # Event details
    noticia: Mapped[str] = mapped_column(String(500))
    pais: Mapped[str] = mapped_column(String(50))
    moneda: Mapped[str] = mapped_column(String(10))
    importancia: Mapped[int] = mapped_column(Integer, index=True)

    # Economic data
    actual: Mapped[str] = mapped_column(String(100), default="")
    prevision: Mapped[str] = mapped_column(String(100), default="")
    anterior: Mapped[str] = mapped_column(String(100), default="")
    sorpresa: Mapped[str] = mapped_column(String(20), default="neutral")

    # Source
    url: Mapped[str] = mapped_column(String(500), default="")

    # AI Analysis - Quick (all events)
    analisis_rapido: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    impacto_rapido: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sentimiento_rapido: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # AI Analysis - Deep (high-impact only)
    analisis_profundo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contexto_macro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    niveles_tecnicos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estrategias_trading: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    activos_impactados: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Analysis status tracking
    has_quick_analysis: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    has_deep_analysis: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_date_importance", "date", "importancia"),
        Index("idx_analysis_status", "date", "has_quick_analysis", "has_deep_analysis"),
    )

    # English property aliases for domain layer compatibility
    @property
    def time(self) -> str:
        return self.hora

    @time.setter
    def time(self, value: str) -> None:
        self.hora = value

    @property
    def title(self) -> str:
        return self.noticia

    @title.setter
    def title(self, value: str) -> None:
        self.noticia = value

    @property
    def country(self) -> str:
        return self.pais

    @country.setter
    def country(self, value: str) -> None:
        self.pais = value

    @property
    def currency(self) -> str:
        return self.moneda

    @currency.setter
    def currency(self, value: str) -> None:
        self.moneda = value

    @property
    def importance(self) -> int:
        return self.importancia

    @importance.setter
    def importance(self, value: int) -> None:
        self.importancia = value

    @property
    def forecast(self) -> str:
        return self.prevision

    @forecast.setter
    def forecast(self, value: str) -> None:
        self.prevision = value

    @property
    def previous(self) -> str:
        return self.anterior

    @previous.setter
    def previous(self, value: str) -> None:
        self.anterior = value

    @property
    def surprise(self) -> str:
        return self.sorpresa

    @surprise.setter
    def surprise(self, value: str) -> None:
        self.sorpresa = value
