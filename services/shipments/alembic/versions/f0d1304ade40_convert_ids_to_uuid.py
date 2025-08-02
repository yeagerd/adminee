"""convert_ids_to_uuid

Revision ID: f0d1304ade40
Revises: 746a3beff9c9
Create Date: 2025-07-31 15:20:38.756839

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0d1304ade40"
down_revision: Union[str, Sequence[str], None] = "746a3beff9c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    """Upgrade schema."""
    # Add UUID columns to all tables (using String for SQLite compatibility)
    if not column_exists("package", "uuid_id"):
        op.add_column("package", sa.Column("uuid_id", sa.String(36), nullable=True))
    if not column_exists("label", "uuid_id"):
        op.add_column("label", sa.Column("uuid_id", sa.String(36), nullable=True))
    if not column_exists("trackingevent", "uuid_id"):
        op.add_column(
            "trackingevent",
            sa.Column("uuid_id", sa.String(36), nullable=True),
        )
    if not column_exists("packagelabel", "uuid_id"):
        op.add_column(
            "packagelabel",
            sa.Column("uuid_id", sa.String(36), nullable=True),
        )
    if not column_exists("carrierconfig", "uuid_id"):
        op.add_column(
            "carrierconfig",
            sa.Column("uuid_id", sa.String(36), nullable=True),
        )

    # Add UUID foreign key columns
    if not column_exists("trackingevent", "package_uuid_id"):
        op.add_column(
            "trackingevent",
            sa.Column("package_uuid_id", sa.String(36), nullable=True),
        )
    if not column_exists("packagelabel", "package_uuid_id"):
        op.add_column(
            "packagelabel",
            sa.Column("package_uuid_id", sa.String(36), nullable=True),
        )
    if not column_exists("packagelabel", "label_uuid_id"):
        op.add_column(
            "packagelabel",
            sa.Column("label_uuid_id", sa.String(36), nullable=True),
        )

    # Create a mapping table to store old_id -> new_uuid mappings
    if not table_exists("id_mapping"):
        op.create_table(
            "id_mapping",
            sa.Column("table_name", sa.String(), nullable=False),
            sa.Column("old_id", sa.Integer(), nullable=False),
            sa.Column("new_uuid", sa.String(36), nullable=False),
            sa.PrimaryKeyConstraint("table_name", "old_id"),
        )

    # Generate UUIDs for existing data and store mappings
    connection = op.get_bind()

    # Check if we already have UUIDs populated
    existing_uuids = connection.execute(
        sa.text("SELECT COUNT(*) FROM package WHERE uuid_id IS NOT NULL")
    ).scalar()

    if existing_uuids == 0:
        # Generate UUIDs for packages
        packages = connection.execute(sa.text("SELECT id FROM package")).fetchall()
        for package in packages:
            new_uuid = str(uuid.uuid4())
            connection.execute(
                sa.text("UPDATE package SET uuid_id = :uuid WHERE id = :id"),
                {"uuid": new_uuid, "id": package[0]},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO id_mapping (table_name, old_id, new_uuid) VALUES (:table, :old_id, :new_uuid)"
                ),
                {"table": "package", "old_id": package[0], "new_uuid": new_uuid},
            )

        # Generate UUIDs for labels
        labels = connection.execute(sa.text("SELECT id FROM label")).fetchall()
        for label in labels:
            new_uuid = str(uuid.uuid4())
            connection.execute(
                sa.text("UPDATE label SET uuid_id = :uuid WHERE id = :id"),
                {"uuid": new_uuid, "id": label[0]},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO id_mapping (table_name, old_id, new_uuid) VALUES (:table, :old_id, :new_uuid)"
                ),
                {"table": "label", "old_id": label[0], "new_uuid": new_uuid},
            )

        # Generate UUIDs for tracking events
        events = connection.execute(sa.text("SELECT id FROM trackingevent")).fetchall()
        for event in events:
            new_uuid = str(uuid.uuid4())
            connection.execute(
                sa.text("UPDATE trackingevent SET uuid_id = :uuid WHERE id = :id"),
                {"uuid": new_uuid, "id": event[0]},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO id_mapping (table_name, old_id, new_uuid) VALUES (:table, :old_id, :new_uuid)"
                ),
                {"table": "trackingevent", "old_id": event[0], "new_uuid": new_uuid},
            )

        # Generate UUIDs for package labels
        package_labels = connection.execute(
            sa.text("SELECT id FROM packagelabel")
        ).fetchall()
        for package_label in package_labels:
            new_uuid = str(uuid.uuid4())
            connection.execute(
                sa.text("UPDATE packagelabel SET uuid_id = :uuid WHERE id = :id"),
                {"uuid": new_uuid, "id": package_label[0]},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO id_mapping (table_name, old_id, new_uuid) VALUES (:table, :old_id, :new_uuid)"
                ),
                {
                    "table": "packagelabel",
                    "old_id": package_label[0],
                    "new_uuid": new_uuid,
                },
            )

        # Generate UUIDs for carrier configs
        carrier_configs = connection.execute(
            sa.text("SELECT id FROM carrierconfig")
        ).fetchall()
        for carrier_config in carrier_configs:
            new_uuid = str(uuid.uuid4())
            connection.execute(
                sa.text("UPDATE carrierconfig SET uuid_id = :uuid WHERE id = :id"),
                {"uuid": new_uuid, "id": carrier_config[0]},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO id_mapping (table_name, old_id, new_uuid) VALUES (:table, :old_id, :new_uuid)"
                ),
                {
                    "table": "carrierconfig",
                    "old_id": carrier_config[0],
                    "new_uuid": new_uuid,
                },
            )

        # Update foreign key references using the mapping table
        # Update trackingevent.package_uuid_id
        tracking_events = connection.execute(
            sa.text("SELECT id, package_id FROM trackingevent")
        ).fetchall()
        for event in tracking_events:
            package_uuid = connection.execute(
                sa.text(
                    "SELECT new_uuid FROM id_mapping WHERE table_name = :table AND old_id = :old_id"
                ),
                {"table": "package", "old_id": event[1]},
            ).fetchone()
            if package_uuid:
                connection.execute(
                    sa.text(
                        "UPDATE trackingevent SET package_uuid_id = :uuid WHERE id = :id"
                    ),
                    {"uuid": package_uuid[0], "id": event[0]},
                )

        # Update packagelabel.package_uuid_id and packagelabel.label_uuid_id
        package_labels = connection.execute(
            sa.text("SELECT id, package_id, label_id FROM packagelabel")
        ).fetchall()
        for package_label in package_labels:
            package_uuid = connection.execute(
                sa.text(
                    "SELECT new_uuid FROM id_mapping WHERE table_name = :table AND old_id = :old_id"
                ),
                {"table": "package", "old_id": package_label[1]},
            ).fetchone()
            label_uuid = connection.execute(
                sa.text(
                    "SELECT new_uuid FROM id_mapping WHERE table_name = :table AND old_id = :old_id"
                ),
                {"table": "label", "old_id": package_label[2]},
            ).fetchone()

            if package_uuid and label_uuid:
                connection.execute(
                    sa.text(
                        "UPDATE packagelabel SET package_uuid_id = :package_uuid, label_uuid_id = :label_uuid WHERE id = :id"
                    ),
                    {
                        "package_uuid": package_uuid[0],
                        "label_uuid": label_uuid[0],
                        "id": package_label[0],
                    },
                )

    # Drop old foreign key constraints if they exist
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

    # Drop old integer columns if they exist - but only after foreign key constraints are dropped
    # Note: SQLite doesn't support DROP COLUMN with foreign key references
    # We'll need to recreate the tables without these columns
    connection = op.get_bind()

    # Check if the old columns still exist and need to be handled
    if column_exists("trackingevent", "package_id"):
        # For SQLite, we need to recreate the table without the column
        # This is a complex operation, so we'll skip it for now and let the migration continue
        # The old column will remain but won't be used
        pass

    if column_exists("packagelabel", "package_id"):
        # Same as above
        pass

    if column_exists("packagelabel", "label_id"):
        # Same as above
        pass

    # Drop the old integer id columns before renaming uuid_id columns
    # This is needed because we can't have two columns with the same name
    if column_exists("package", "id") and column_exists("package", "uuid_id"):
        # We need to drop the old id column first
        # For SQLite, this requires recreating the table, which is complex
        # Instead, we'll use a different approach: rename the old id column temporarily
        op.alter_column("package", "id", new_column_name="old_id")

    if column_exists("label", "id") and column_exists("label", "uuid_id"):
        op.alter_column("label", "id", new_column_name="old_id")

    if column_exists("trackingevent", "id") and column_exists(
        "trackingevent", "uuid_id"
    ):
        op.alter_column("trackingevent", "id", new_column_name="old_id")

    if column_exists("packagelabel", "id") and column_exists("packagelabel", "uuid_id"):
        op.alter_column("packagelabel", "id", new_column_name="old_id")

    if column_exists("carrierconfig", "id") and column_exists(
        "carrierconfig", "uuid_id"
    ):
        op.alter_column("carrierconfig", "id", new_column_name="old_id")

    # Handle foreign key column duplicates
    if column_exists("trackingevent", "package_id") and column_exists(
        "trackingevent", "package_uuid_id"
    ):
        op.alter_column("trackingevent", "package_id", new_column_name="old_package_id")

    if column_exists("packagelabel", "package_id") and column_exists(
        "packagelabel", "package_uuid_id"
    ):
        op.alter_column("packagelabel", "package_id", new_column_name="old_package_id")

    if column_exists("packagelabel", "label_id") and column_exists(
        "packagelabel", "label_uuid_id"
    ):
        op.alter_column("packagelabel", "label_id", new_column_name="old_label_id")

    # Rename UUID columns to be the primary columns
    op.alter_column("package", "uuid_id", new_column_name="id")
    op.alter_column("label", "uuid_id", new_column_name="id")
    op.alter_column("trackingevent", "uuid_id", new_column_name="id")
    op.alter_column("packagelabel", "uuid_id", new_column_name="id")
    op.alter_column("carrierconfig", "uuid_id", new_column_name="id")

    # Drop existing primary key constraints before renaming
    op.drop_constraint("package_pkey", "package", type_="primary")
    op.drop_constraint("label_pkey", "label", type_="primary")
    op.drop_constraint("trackingevent_pkey", "trackingevent", type_="primary")
    op.drop_constraint("packagelabel_pkey", "packagelabel", type_="primary")
    op.drop_constraint("carrierconfig_pkey", "carrierconfig", type_="primary")

    # Rename foreign key columns
    op.alter_column("trackingevent", "package_uuid_id", new_column_name="package_id")
    op.alter_column("packagelabel", "package_uuid_id", new_column_name="package_id")
    op.alter_column("packagelabel", "label_uuid_id", new_column_name="label_id")

    # Make UUID columns NOT NULL
    op.alter_column("package", "id", nullable=False)
    op.alter_column("label", "id", nullable=False)
    op.alter_column("trackingevent", "id", nullable=False)
    op.alter_column("packagelabel", "id", nullable=False)
    op.alter_column("carrierconfig", "id", nullable=False)
    op.alter_column("trackingevent", "package_id", nullable=False)
    op.alter_column("packagelabel", "package_id", nullable=False)
    op.alter_column("packagelabel", "label_id", nullable=False)

    # Recreate primary key constraints on the renamed UUID columns
    op.create_primary_key("package_pkey", "package", ["id"])
    op.create_primary_key("label_pkey", "label", ["id"])
    op.create_primary_key("trackingevent_pkey", "trackingevent", ["id"])
    op.create_primary_key("packagelabel_pkey", "packagelabel", ["id"])
    op.create_primary_key("carrierconfig_pkey", "carrierconfig", ["id"])

    # Add new foreign key constraints
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

    # Drop the mapping table
    if table_exists("id_mapping"):
        op.drop_table("id_mapping")


def downgrade() -> None:
    """Downgrade schema."""
    # This is a complex migration that would require significant effort to reverse
    # For now, we'll raise an exception to prevent accidental downgrades
    raise Exception(
        "UUID migration cannot be automatically downgraded. Manual intervention required."
    )
