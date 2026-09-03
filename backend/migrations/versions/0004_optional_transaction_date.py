"""Allow reconciliation transactions without source dates."""

from alembic import op
import sqlalchemy as sa


revision = "0004_optional_transaction_date"
down_revision = "0003_single_file_run_fields"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {
        column["name"]: column
        for column in inspector.get_columns("transactions")
    }
    if columns.get("date", {}).get("nullable") is False:
        with op.batch_alter_table("transactions") as batch_op:
            batch_op.alter_column(
                "date",
                existing_type=sa.String(length=30),
                nullable=True,
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {
        column["name"]: column
        for column in inspector.get_columns("transactions")
    }
    if columns.get("date", {}).get("nullable") is True:
        with op.batch_alter_table("transactions") as batch_op:
            batch_op.alter_column(
                "date",
                existing_type=sa.String(length=30),
                nullable=False,
            )