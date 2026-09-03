"""Add multi-file reconciliation run history."""

from alembic import op
import sqlalchemy as sa


revision = "0002_multi_file_reconciliation"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("reconciliation_runs"):
        op.create_table(
            "reconciliation_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("run_id", sa.String(length=40), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("user_email", sa.String(length=255), nullable=False),
            sa.Column("bank_filename", sa.String(length=255), nullable=False),
            sa.Column("ledger_filename", sa.String(length=255), nullable=False),
            sa.Column("settlement_filename", sa.String(length=255), nullable=True),
            sa.Column("bank_records", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ledger_records", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("settlement_records", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("matched", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("partial", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("unmatched", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("duplicate", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("match_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("total_variance", sa.Float(), nullable=False, server_default="0"),
            sa.UniqueConstraint("run_id"),
        )
    index_names = {
        index["name"]
        for index in inspector.get_indexes("reconciliation_runs")
    }
    if "ix_reconciliation_runs_run_id" not in index_names:
        op.create_index(
            "ix_reconciliation_runs_run_id",
            "reconciliation_runs",
            ["run_id"],
            unique=True,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("reconciliation_runs"):
        index_names = {
            index["name"]
            for index in inspector.get_indexes("reconciliation_runs")
        }
        if "ix_reconciliation_runs_run_id" in index_names:
            op.drop_index(
                "ix_reconciliation_runs_run_id",
                table_name="reconciliation_runs",
            )
        op.drop_table("reconciliation_runs")
