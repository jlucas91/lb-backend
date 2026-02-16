"""generic file system with STI and join tables

Revision ID: 30cc1d54bcee
Revises: b5bf6597608c
Create Date: 2026-02-15 22:09:25.388369

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "30cc1d54bcee"
down_revision: str | None = "b5bf6597608c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop old join tables that depend on the old files table
    op.drop_table("location_files")
    op.drop_table("scouting_files")
    # Drop old files table (location_id/scouting_id coupled design)
    op.drop_table("files")

    # Create new standalone files table with STI
    op.create_table(
        "files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("file_category", sa.String(length=20), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("thumbnail_key", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"], ["users.id"], name=op.f("fk_files_uploaded_by_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_files")),
    )
    op.create_index(
        op.f("ix_files_uploaded_by_id"), "files", ["uploaded_by_id"], unique=False
    )

    # Create location_files join table
    op.create_table(
        "location_files",
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column(
            "added_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["files.id"],
            name=op.f("fk_location_files_file_id_files"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["user_locations.id"],
            name=op.f("fk_location_files_location_id_user_locations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "location_id", "file_id", name=op.f("pk_location_files")
        ),
    )

    # Create scouting_files join table
    op.create_table(
        "scouting_files",
        sa.Column("scouting_id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column(
            "added_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["files.id"],
            name=op.f("fk_scouting_files_file_id_files"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scouting_id"],
            ["scoutings.id"],
            name=op.f("fk_scouting_files_scouting_id_scoutings"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "scouting_id", "file_id", name=op.f("pk_scouting_files")
        ),
    )


def downgrade() -> None:
    op.drop_table("scouting_files")
    op.drop_table("location_files")
    op.drop_index(op.f("ix_files_uploaded_by_id"), table_name="files")
    op.drop_table("files")

    # Recreate old files table
    op.create_table(
        "files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("scouting_id", sa.Uuid(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["user_locations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["scouting_id"], ["scoutings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_files_location_id", "files", ["location_id"], unique=False)
    op.create_index("ix_files_scouting_id", "files", ["scouting_id"], unique=False)
