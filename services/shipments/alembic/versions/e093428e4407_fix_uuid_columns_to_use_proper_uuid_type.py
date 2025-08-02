"""fix_uuid_columns_to_use_proper_uuid_type

Revision ID: e093428e4407
Revises: 8867599ddb51
Create Date: 2025-08-01 23:11:08.392243

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e093428e4407"
down_revision: Union[str, Sequence[str], None] = "8867599ddb51"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Convert String(36) columns to proper UUID columns
    # This is needed because the previous migration used String(36) for SQLite compatibility
    # but we're using PostgreSQL which supports native UUID types

    # First, we need to drop foreign key constraints
    try:
        op.drop_constraint(
            "trackingevent_package_id_fkey", "trackingevent", type_="foreignkey"
        )
    except Exception:
        pass  # Constraint might not exist

    try:
        op.drop_constraint(
            "packagelabel_package_id_fkey", "packagelabel", type_="foreignkey"
        )
    except Exception:
        pass  # Constraint might not exist

    try:
        op.drop_constraint(
            "packagelabel_label_id_fkey", "packagelabel", type_="foreignkey"
        )
    except Exception:
        pass  # Constraint might not exist

    # Drop primary key constraints
    try:
        op.drop_constraint("package_pkey", "package", type_="primary")
    except Exception:
        pass

    try:
        op.drop_constraint("label_pkey", "label", type_="primary")
    except Exception:
        pass

    try:
        op.drop_constraint("trackingevent_pkey", "trackingevent", type_="primary")
    except Exception:
        pass

    try:
        op.drop_constraint("packagelabel_pkey", "packagelabel", type_="primary")
    except Exception:
        pass

    try:
        op.drop_constraint("carrierconfig_pkey", "carrierconfig", type_="primary")
    except Exception:
        pass

    # Convert String columns to UUID columns
    # We need to use raw SQL for this conversion
    connection = op.get_bind()

    # Convert package.id
    connection.execute(
        sa.text("ALTER TABLE package ALTER COLUMN id TYPE UUID USING id::UUID")
    )

    # Convert label.id
    connection.execute(
        sa.text("ALTER TABLE label ALTER COLUMN id TYPE UUID USING id::UUID")
    )

    # Convert trackingevent.id
    connection.execute(
        sa.text("ALTER TABLE trackingevent ALTER COLUMN id TYPE UUID USING id::UUID")
    )

    # Convert trackingevent.package_id
    connection.execute(
        sa.text(
            "ALTER TABLE trackingevent ALTER COLUMN package_id TYPE UUID USING package_id::UUID"
        )
    )

    # Convert packagelabel.id
    connection.execute(
        sa.text("ALTER TABLE packagelabel ALTER COLUMN id TYPE UUID USING id::UUID")
    )

    # Convert packagelabel.package_id
    connection.execute(
        sa.text(
            "ALTER TABLE packagelabel ALTER COLUMN package_id TYPE UUID USING package_id::UUID"
        )
    )

    # Convert packagelabel.label_id
    connection.execute(
        sa.text(
            "ALTER TABLE packagelabel ALTER COLUMN label_id TYPE UUID USING label_id::UUID"
        )
    )

    # Convert carrierconfig.id
    connection.execute(
        sa.text("ALTER TABLE carrierconfig ALTER COLUMN id TYPE UUID USING id::UUID")
    )

    # Recreate primary key constraints
    op.create_primary_key("package_pkey", "package", ["id"])
    op.create_primary_key("label_pkey", "label", ["id"])
    op.create_primary_key("trackingevent_pkey", "trackingevent", ["id"])
    op.create_primary_key("packagelabel_pkey", "packagelabel", ["id"])
    op.create_primary_key("carrierconfig_pkey", "carrierconfig", ["id"])

    # Recreate foreign key constraints
    op.create_foreign_key(
        "trackingevent_package_id_fkey",
        "trackingevent",
        "package",
        ["package_id"],
        ["id"],
    )
    op.create_foreign_key(
        "packagelabel_package_id_fkey",
        "packagelabel",
        "package",
        ["package_id"],
        ["id"],
    )
    op.create_foreign_key(
        "packagelabel_label_id_fkey", "packagelabel", "label", ["label_id"], ["id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Convert UUID columns back to String(36) columns
    # This is the reverse of the upgrade process

    # Drop foreign key constraints
    try:
        op.drop_constraint(
            "trackingevent_package_id_fkey", "trackingevent", type_="foreignkey"
        )
    except Exception:
        pass

    try:
        op.drop_constraint(
            "packagelabel_package_id_fkey", "packagelabel", type_="foreignkey"
        )
    except Exception:
        pass

    try:
        op.drop_constraint(
            "packagelabel_label_id_fkey", "packagelabel", type_="foreignkey"
        )
    except Exception:
        pass

    # Drop primary key constraints
    try:
        op.drop_constraint("package_pkey", "package", type_="primary")
    except Exception:
        pass

    try:
        op.drop_constraint("label_pkey", "label", type_="primary")
    except Exception:
        pass

    try:
        op.drop_constraint("trackingevent_pkey", "trackingevent", type_="primary")
    except Exception:
        pass

    try:
        op.drop_constraint("packagelabel_pkey", "packagelabel", type_="primary")
    except Exception:
        pass

    try:
        op.drop_constraint("carrierconfig_pkey", "carrierconfig", type_="primary")
    except Exception:
        pass

    # Convert UUID columns back to String columns
    connection = op.get_bind()

    # Convert package.id
    connection.execute(sa.text("ALTER TABLE package ALTER COLUMN id TYPE VARCHAR(36)"))

    # Convert label.id
    connection.execute(sa.text("ALTER TABLE label ALTER COLUMN id TYPE VARCHAR(36)"))

    # Convert trackingevent.id
    connection.execute(
        sa.text("ALTER TABLE trackingevent ALTER COLUMN id TYPE VARCHAR(36)")
    )

    # Convert trackingevent.package_id
    connection.execute(
        sa.text("ALTER TABLE trackingevent ALTER COLUMN package_id TYPE VARCHAR(36)")
    )

    # Convert packagelabel.id
    connection.execute(
        sa.text("ALTER TABLE packagelabel ALTER COLUMN id TYPE VARCHAR(36)")
    )

    # Convert packagelabel.package_id
    connection.execute(
        sa.text("ALTER TABLE packagelabel ALTER COLUMN package_id TYPE VARCHAR(36)")
    )

    # Convert packagelabel.label_id
    connection.execute(
        sa.text("ALTER TABLE packagelabel ALTER COLUMN label_id TYPE VARCHAR(36)")
    )

    # Convert carrierconfig.id
    connection.execute(
        sa.text("ALTER TABLE carrierconfig ALTER COLUMN id TYPE VARCHAR(36)")
    )

    # Recreate primary key constraints
    op.create_primary_key("package_pkey", "package", ["id"])
    op.create_primary_key("label_pkey", "label", ["id"])
    op.create_primary_key("trackingevent_pkey", "trackingevent", ["id"])
    op.create_primary_key("packagelabel_pkey", "packagelabel", ["id"])
    op.create_primary_key("carrierconfig_pkey", "carrierconfig", ["id"])

    # Recreate foreign key constraints
    op.create_foreign_key(
        "trackingevent_package_id_fkey",
        "trackingevent",
        "package",
        ["package_id"],
        ["id"],
    )
    op.create_foreign_key(
        "packagelabel_package_id_fkey",
        "packagelabel",
        "package",
        ["package_id"],
        ["id"],
    )
    op.create_foreign_key(
        "packagelabel_label_id_fkey", "packagelabel", "label", ["label_id"], ["id"]
    )
