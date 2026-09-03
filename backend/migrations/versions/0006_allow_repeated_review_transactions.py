"""Remove the legacy transaction-only review uniqueness constraint."""

from alembic import op
import sqlalchemy as sa


revision = "0006_allow_repeated_review_transactions"
down_revision = "0005_run_scoped_reconciliation_rows"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return
    metadata = sa.MetaData()
    review_queue = sa.Table(
        "review_queue",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=40), nullable=True),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    with op.batch_alter_table("review_queue", copy_from=review_queue, recreate="always"):
        pass


def downgrade():
    raise NotImplementedError("The run-scoped review queue cannot restore transaction-only uniqueness without data loss.")