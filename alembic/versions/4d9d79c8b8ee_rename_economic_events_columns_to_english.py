"""Rename economic_events columns to English.

Revision ID: 4d9d79c8b8ee
Revises: 3de8543205ef
Create Date: 2026-04-13 13:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4d9d79c8b8ee"
down_revision: Union[str, Sequence[str], None] = "3de8543205ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("economic_events", schema=None) as batch_op:
        batch_op.alter_column("hora", new_column_name="time")
        batch_op.alter_column("noticia", new_column_name="title")
        batch_op.alter_column("pais", new_column_name="country")
        batch_op.alter_column("moneda", new_column_name="currency")
        batch_op.alter_column("importancia", new_column_name="importance")
        batch_op.alter_column("prevision", new_column_name="forecast")
        batch_op.alter_column("anterior", new_column_name="previous")
        batch_op.alter_column("sorpresa", new_column_name="surprise")
        batch_op.alter_column("analisis_rapido", new_column_name="quick_summary")
        batch_op.alter_column("impacto_rapido", new_column_name="quick_impact")
        batch_op.alter_column("sentimiento_rapido", new_column_name="quick_sentiment")
        batch_op.alter_column("analisis_profundo", new_column_name="deep_summary")
        batch_op.alter_column("contexto_macro", new_column_name="macro_context")
        batch_op.alter_column("niveles_tecnicos", new_column_name="technical_levels")
        batch_op.alter_column("estrategias_trading", new_column_name="trading_strategies")
        batch_op.alter_column("activos_impactados", new_column_name="impacted_assets")

    names = _index_names("economic_events")
    if "ix_economic_events_importancia" in names:
        op.drop_index("ix_economic_events_importancia", table_name="economic_events")

    # Rebuild with English column name for consistency.
    if "idx_date_importance" in names:
        op.drop_index("idx_date_importance", table_name="economic_events")
    op.create_index("idx_date_importance", "economic_events", ["date", "importance"], unique=False)

    if "ix_economic_events_importance" not in _index_names("economic_events"):
        op.create_index("ix_economic_events_importance", "economic_events", ["importance"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    names = _index_names("economic_events")
    if "ix_economic_events_importance" in names:
        op.drop_index("ix_economic_events_importance", table_name="economic_events")
    if "idx_date_importance" in names:
        op.drop_index("idx_date_importance", table_name="economic_events")

    with op.batch_alter_table("economic_events", schema=None) as batch_op:
        batch_op.alter_column("time", new_column_name="hora")
        batch_op.alter_column("title", new_column_name="noticia")
        batch_op.alter_column("country", new_column_name="pais")
        batch_op.alter_column("currency", new_column_name="moneda")
        batch_op.alter_column("importance", new_column_name="importancia")
        batch_op.alter_column("forecast", new_column_name="prevision")
        batch_op.alter_column("previous", new_column_name="anterior")
        batch_op.alter_column("surprise", new_column_name="sorpresa")
        batch_op.alter_column("quick_summary", new_column_name="analisis_rapido")
        batch_op.alter_column("quick_impact", new_column_name="impacto_rapido")
        batch_op.alter_column("quick_sentiment", new_column_name="sentimiento_rapido")
        batch_op.alter_column("deep_summary", new_column_name="analisis_profundo")
        batch_op.alter_column("macro_context", new_column_name="contexto_macro")
        batch_op.alter_column("technical_levels", new_column_name="niveles_tecnicos")
        batch_op.alter_column("trading_strategies", new_column_name="estrategias_trading")
        batch_op.alter_column("impacted_assets", new_column_name="activos_impactados")

    op.create_index("idx_date_importance", "economic_events", ["date", "importancia"], unique=False)
    if "ix_economic_events_importancia" not in _index_names("economic_events"):
        op.create_index("ix_economic_events_importancia", "economic_events", ["importancia"], unique=False)
