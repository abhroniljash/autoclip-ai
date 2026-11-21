"""Add password hashes for user authentication.

Revision ID: 0001_user_auth
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_user_auth"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("password_hash", sa.String(length=512), nullable=True))
    # Existing projects remain unowned until an administrator explicitly assigns them.
    # New projects are always created with the authenticated user's ID.


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_column("password_hash")
