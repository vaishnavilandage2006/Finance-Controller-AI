"""Add single-file reconciliation fields to run history."""

from alembic import op
import sqlalchemy as sa


revision = "0003_single_file_run_fields"
down_revision = "0002_multi_file_reconciliation"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("reconciliation_runs")}
    additions = [
        ("mode", sa.String(length=30), "multi_file"),
        ("filename", sa.String(length=255), None),
        ("total", sa.Integer(), "0"),
        ("exceptions", sa.Integer(), "0"),
    ]
    for name, column_type, default in additions:
        if name not in columns:
            op.add_column(
                "reconciliation_runs",
                sa.Column(
                    name,
                    column_type,
                    nullable=default is None,
                    server_default=default,
                ),
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("reconciliation_runs")}
    for name in ("exceptions", "total", "filename", "mode"):
        if name in columns:
            op.drop_column("reconciliation_runs", name)
