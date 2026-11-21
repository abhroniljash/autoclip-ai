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
    inspector = sa.inspect(op.get_bind())
    if "users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "password_hash" not in columns:
            with op.batch_alter_table("users") as batch:
                batch.add_column(sa.Column("password_hash", sa.String(length=512), nullable=True))


def downgrade():
    inspector = sa.inspect(op.get_bind())
    if "users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "password_hash" in columns:
            with op.batch_alter_table("users") as batch:
                batch.drop_column("password_hash")
