from pathlib import Path
import sys

from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Base, engine
from app.models import *


config = context.config

target_metadata = Base.metadata


def run_migrations_offline():
	context.configure(
		url=str(engine.url),
		target_metadata=target_metadata,
		literal_binds=True,
		dialect_opts={"paramstyle": "named"},
	)
	with context.begin_transaction():
		context.run_migrations()


def run_migrations_online():
	with engine.connect() as connection:
		context.configure(
			connection=connection,
			target_metadata=target_metadata,
		)
		with context.begin_transaction():
			context.run_migrations()


if context.is_offline_mode():
	run_migrations_offline()
else:
	run_migrations_online()
