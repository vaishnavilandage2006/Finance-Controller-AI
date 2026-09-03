"""Initial schema
Revision ID: 0001
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db import Base,engine
from app.models import *

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade(): Base.metadata.create_all(engine)
def downgrade(): pass
