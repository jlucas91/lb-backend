"""add project_location_files table and featured_file_id to project_locations

Revision ID: a1b2c3d4e5f6
Revises: 24091545eac9
Create Date: 2026-02-16 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '24091545eac9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'project_location_files',
        sa.Column('project_location_id', sa.Uuid(), nullable=False),
        sa.Column('file_id', sa.Uuid(), nullable=False),
        sa.Column('added_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_location_id'], ['project_locations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('project_location_id', 'file_id'),
    )
    op.add_column(
        'project_locations',
        sa.Column('featured_file_id', sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        'fk_project_locations_featured_file_id',
        'project_locations',
        'files',
        ['featured_file_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_project_locations_featured_file_id', 'project_locations', type_='foreignkey')
    op.drop_column('project_locations', 'featured_file_id')
    op.drop_table('project_location_files')
