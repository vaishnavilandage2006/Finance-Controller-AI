"""Restore the run lookup index after the SQLite constraint migration."""

from alembic import op
import sqlalchemy as sa


revision = "0007_restore_review_run_index"
down_revision = "0006_allow_repeated_review_transactions"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "ix_review_queue_run_id" not in {index["name"] for index in inspector.get_indexes("review_queue")}:
        op.create_index("ix_review_queue_run_id", "review_queue", ["run_id"])


def downgrade():
    op.drop_index("ix_review_queue_run_id", table_name="review_queue")