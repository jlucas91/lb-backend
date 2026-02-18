"""rename username to email and add smugmug_nick

Revision ID: 61718e3dc8b5
Revises: 4c4cb6c093dc
Create Date: 2026-02-18 01:41:33.415057

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61718e3dc8b5'
down_revision: Union[str, None] = '4c4cb6c093dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'smugmug_accounts', 'username',
        new_column_name='email',
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )
    op.add_column(
        'smugmug_accounts',
        sa.Column('smugmug_nick', sa.String(length=255), nullable=False, server_default=''),
    )
    # Remove the server default after backfilling
    op.alter_column('smugmug_accounts', 'smugmug_nick', server_default=None)


def downgrade() -> None:
    op.drop_column('smugmug_accounts', 'smugmug_nick')
    op.alter_column(
        'smugmug_accounts', 'email',
        new_column_name='username',
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )
