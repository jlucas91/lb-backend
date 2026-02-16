"""rename locations to user_locations and add project_locations

Revision ID: b5bf6597608c
Revises: 509d6147e1a1
Create Date: 2026-02-15 20:55:49.600230

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5bf6597608c"
down_revision: Union[str, None] = "509d6147e1a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename locations -> user_locations
    op.rename_table("locations", "user_locations")

    # Rename PK constraint
    op.execute(
        "ALTER TABLE user_locations RENAME CONSTRAINT pk_locations TO pk_user_locations"
    )

    # Rename index
    op.execute(
        "ALTER INDEX ix_locations_owner_id RENAME TO ix_user_locations_owner_id"
    )

    # Rename FK constraint on user_locations itself
    op.execute(
        "ALTER TABLE user_locations RENAME CONSTRAINT "
        "fk_locations_owner_id_users TO fk_user_locations_owner_id_users"
    )

    # 2. Update FK constraints on referencing tables to point to user_locations
    # files
    op.drop_constraint("fk_files_location_id_locations", "files", type_="foreignkey")
    op.create_foreign_key(
        op.f("fk_files_location_id_user_locations"),
        "files",
        "user_locations",
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # location_shares
    op.drop_constraint(
        "fk_location_shares_location_id_locations",
        "location_shares",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_location_shares_location_id_user_locations"),
        "location_shares",
        "user_locations",
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # production_locations
    op.drop_constraint(
        "fk_production_locations_location_id_locations",
        "production_locations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_production_locations_location_id_user_locations"),
        "production_locations",
        "user_locations",
        ["location_id"],
        ["id"],
    )

    # scoutings
    op.drop_constraint(
        "fk_scoutings_location_id_locations", "scoutings", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_scoutings_location_id_user_locations"),
        "scoutings",
        "user_locations",
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 3. Create project_locations table
    op.create_table(
        "project_locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("added_by_id", sa.Uuid(), nullable=False),
        sa.Column("source_location_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("location_type", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["added_by_id"],
            ["users.id"],
            name=op.f("fk_project_locations_added_by_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_locations_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_location_id"],
            ["user_locations.id"],
            name=op.f(
                "fk_project_locations_source_location_id_user_locations"
            ),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_locations")),
    )
    op.create_index(
        op.f("ix_project_locations_project_id"),
        "project_locations",
        ["project_id"],
        unique=False,
    )

    # 4. Update scripted_location_locations: replace location_id with project_location_id
    # Delete existing rows (they reference user locations, no longer valid)
    op.execute("DELETE FROM scripted_location_locations")

    # Drop old PK, FK, and column
    op.drop_constraint(
        "pk_scripted_location_locations",
        "scripted_location_locations",
        type_="primary",
    )
    op.drop_constraint(
        "fk_scripted_location_locations_location_id_locations",
        "scripted_location_locations",
        type_="foreignkey",
    )
    op.drop_column("scripted_location_locations", "location_id")

    # Add new column and constraints
    op.add_column(
        "scripted_location_locations",
        sa.Column("project_location_id", sa.Uuid(), nullable=False),
    )
    op.create_primary_key(
        op.f("pk_scripted_location_locations"),
        "scripted_location_locations",
        ["scripted_location_id", "project_location_id"],
    )
    op.create_foreign_key(
        op.f(
            "fk_scripted_location_locations_project_location_id_project_locations"
        ),
        "scripted_location_locations",
        "project_locations",
        ["project_location_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Reverse scripted_location_locations changes
    op.execute("DELETE FROM scripted_location_locations")
    op.drop_constraint(
        op.f(
            "fk_scripted_location_locations_project_location_id_project_locations"
        ),
        "scripted_location_locations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "pk_scripted_location_locations",
        "scripted_location_locations",
        type_="primary",
    )
    op.drop_column("scripted_location_locations", "project_location_id")
    op.add_column(
        "scripted_location_locations",
        sa.Column("location_id", sa.UUID(), nullable=False),
    )
    op.create_primary_key(
        "pk_scripted_location_locations",
        "scripted_location_locations",
        ["scripted_location_id", "location_id"],
    )
    op.create_foreign_key(
        "fk_scripted_location_locations_location_id_locations",
        "scripted_location_locations",
        "locations",
        ["location_id"],
        ["id"],
    )

    # Drop project_locations
    op.drop_index(
        op.f("ix_project_locations_project_id"), table_name="project_locations"
    )
    op.drop_table("project_locations")

    # Reverse FK constraints
    op.drop_constraint(
        op.f("fk_scoutings_location_id_user_locations"),
        "scoutings",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_scoutings_location_id_locations",
        "scoutings",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        op.f("fk_production_locations_location_id_user_locations"),
        "production_locations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_production_locations_location_id_locations",
        "production_locations",
        "locations",
        ["location_id"],
        ["id"],
    )

    op.drop_constraint(
        op.f("fk_location_shares_location_id_user_locations"),
        "location_shares",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_location_shares_location_id_locations",
        "location_shares",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        op.f("fk_files_location_id_user_locations"), "files", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_files_location_id_locations",
        "files",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Rename back
    op.execute(
        "ALTER TABLE user_locations RENAME CONSTRAINT "
        "fk_user_locations_owner_id_users TO fk_locations_owner_id_users"
    )
    op.execute(
        "ALTER INDEX ix_user_locations_owner_id RENAME TO ix_locations_owner_id"
    )
    op.execute(
        "ALTER TABLE user_locations RENAME CONSTRAINT "
        "pk_user_locations TO pk_locations"
    )
    op.rename_table("user_locations", "locations")
