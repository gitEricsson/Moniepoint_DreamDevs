"""Initial schema — merchant_activities table with analytics indexes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "merchant_activities",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("merchant_id", sa.String(20), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("product", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("channel", sa.String(15), nullable=True),
        sa.Column("region", sa.String(30), nullable=True),
        sa.Column("merchant_tier", sa.String(10), nullable=True),
    )
    op.create_index("ix_ma_merchant_id", "merchant_activities", ["merchant_id"])
    op.create_index("ix_ma_status_product", "merchant_activities", ["status", "product"])
    op.create_index("ix_ma_event_timestamp", "merchant_activities", ["event_timestamp"])
    op.create_index(
        "ix_ma_kyc_partial",
        "merchant_activities",
        ["product", "event_type", "merchant_id"],
        postgresql_where=sa.text("product = 'KYC' AND status = 'SUCCESS'"),
    )


def downgrade() -> None:
    op.drop_index("ix_ma_kyc_partial", table_name="merchant_activities")
    op.drop_index("ix_ma_event_timestamp", table_name="merchant_activities")
    op.drop_index("ix_ma_status_product", table_name="merchant_activities")
    op.drop_index("ix_ma_merchant_id", table_name="merchant_activities")
    op.drop_table("merchant_activities")
