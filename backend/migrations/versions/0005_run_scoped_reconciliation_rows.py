"""Add run ownership to reconciliation results and review items."""

from alembic import op
import sqlalchemy as sa


revision = "0005_run_scoped_reconciliation_rows"
down_revision = "0004_optional_transaction_date"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    result_columns = {column["name"] for column in inspector.get_columns("reconciliation_results")}
    if "run_id" not in result_columns:
        op.add_column("reconciliation_results", sa.Column("run_id", sa.String(length=40), nullable=True))
        op.create_index("ix_reconciliation_results_run_id", "reconciliation_results", ["run_id"])

    review_columns = {column["name"] for column in inspector.get_columns("review_queue")}
    if "run_id" not in review_columns:
        op.add_column("review_queue", sa.Column("run_id", sa.String(length=40), nullable=True))
        op.create_index("ix_review_queue_run_id", "review_queue", ["run_id"])

    run_columns = {column["name"] for column in inspector.get_columns("reconciliation_runs")}
    if "status" not in run_columns:
        op.add_column(
            "reconciliation_runs",
            sa.Column("status", sa.String(length=20), nullable=False, server_default="COMPLETED"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "status" in {column["name"] for column in inspector.get_columns("reconciliation_runs")}:
        op.drop_column("reconciliation_runs", "status")
    if "run_id" in {column["name"] for column in inspector.get_columns("review_queue")}:
        op.drop_index("ix_review_queue_run_id", table_name="review_queue")
        op.drop_column("review_queue", "run_id")
    if "run_id" in {column["name"] for column in inspector.get_columns("reconciliation_results")}:
        op.drop_index("ix_reconciliation_results_run_id", table_name="reconciliation_results")
        op.drop_column("reconciliation_results", "run_id")