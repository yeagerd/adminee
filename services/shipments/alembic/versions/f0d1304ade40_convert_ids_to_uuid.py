"""convert_ids_to_uuid

Revision ID: f0d1304ade40
Revises: 746a3beff9c9
Create Date: 2025-07-31 15:20:38.756839

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f0d1304ade40'
down_revision: Union[str, Sequence[str], None] = '746a3beff9c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add UUID columns to all tables
    op.add_column('package', sa.Column('uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('label', sa.Column('uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('trackingevent', sa.Column('uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('packagelabel', sa.Column('uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('carrierconfig', sa.Column('uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add UUID foreign key columns
    op.add_column('trackingevent', sa.Column('package_uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('packagelabel', sa.Column('package_uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('packagelabel', sa.Column('label_uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Create a mapping table to store old_id -> new_uuid mappings
    op.create_table(
        'id_mapping',
        sa.Column('table_name', sa.String(), nullable=False),
        sa.Column('old_id', sa.Integer(), nullable=False),
        sa.Column('new_uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('table_name', 'old_id')
    )
    
    # Generate UUIDs for existing data and store mappings
    connection = op.get_bind()
    
    # Generate UUIDs for packages
    packages = connection.execute(sa.text('SELECT id FROM package')).fetchall()
    for package in packages:
        new_uuid = uuid.uuid4()
        connection.execute(
            sa.text('UPDATE package SET uuid_id = :uuid WHERE id = :id'),
            {'uuid': new_uuid, 'id': package[0]}
        )
        connection.execute(
            sa.text('INSERT INTO id_mapping (table_name, old_id, new_uuid) VALUES (:table, :old_id, :new_uuid)'),
            {'table': 'package', 'old_id': package[0], 'new_uuid': new_uuid}
        )
    
    # Generate UUIDs for labels
    labels = connection.execute(sa.text('SELECT id FROM label')).fetchall()
    for label in labels:
        new_uuid = uuid.uuid4()
        connection.execute(
            sa.text('UPDATE label SET uuid_id = :uuid WHERE id = :id'),
            {'uuid': new_uuid, 'id': label[0]}
        )
        connection.execute(
            sa.text('INSERT INTO id_mapping (table_name, old_id, new_uuid) VALUES (:table, :old_id, :new_uuid)'),
            {'table': 'label', 'old_id': label[0], 'new_uuid': new_uuid}
        )
    
    # Generate UUIDs for tracking events
    events = connection.execute(sa.text('SELECT id FROM trackingevent')).fetchall()
    for event in events:
        new_uuid = uuid.uuid4()
        connection.execute(
            sa.text('UPDATE trackingevent SET uuid_id = :uuid WHERE id = :id'),
            {'uuid': new_uuid, 'id': event[0]}
        )
        connection.execute(
            sa.text('INSERT INTO id_mapping (table_name, old_id, new_uuid) VALUES (:table, :old_id, :new_uuid)'),
            {'table': 'trackingevent', 'old_id': event[0], 'new_uuid': new_uuid}
        )
    
    # Generate UUIDs for package labels
    package_labels = connection.execute(sa.text('SELECT id FROM packagelabel')).fetchall()
    for package_label in package_labels:
        new_uuid = uuid.uuid4()
        connection.execute(
            sa.text('UPDATE packagelabel SET uuid_id = :uuid WHERE id = :id'),
            {'uuid': new_uuid, 'id': package_label[0]}
        )
        connection.execute(
            sa.text('INSERT INTO id_mapping (table_name, old_id, new_uuid) VALUES (:table, :old_id, :new_uuid)'),
            {'table': 'packagelabel', 'old_id': package_label[0], 'new_uuid': new_uuid}
        )
    
    # Generate UUIDs for carrier configs
    carrier_configs = connection.execute(sa.text('SELECT id FROM carrierconfig')).fetchall()
    for carrier_config in carrier_configs:
        new_uuid = uuid.uuid4()
        connection.execute(
            sa.text('UPDATE carrierconfig SET uuid_id = :uuid WHERE id = :id'),
            {'uuid': new_uuid, 'id': carrier_config[0]}
        )
        connection.execute(
            sa.text('INSERT INTO id_mapping (table_name, old_id, new_uuid) VALUES (:table, :old_id, :new_uuid)'),
            {'table': 'carrierconfig', 'old_id': carrier_config[0], 'new_uuid': new_uuid}
        )
    
    # Update foreign key references using the mapping table
    # Update trackingevent.package_uuid_id
    tracking_events = connection.execute(sa.text('SELECT id, package_id FROM trackingevent')).fetchall()
    for event in tracking_events:
        package_uuid = connection.execute(
            sa.text('SELECT new_uuid FROM id_mapping WHERE table_name = :table AND old_id = :old_id'),
            {'table': 'package', 'old_id': event[1]}
        ).fetchone()
        if package_uuid:
            connection.execute(
                sa.text('UPDATE trackingevent SET package_uuid_id = :uuid WHERE id = :id'),
                {'uuid': package_uuid[0], 'id': event[0]}
            )
    
    # Update packagelabel.package_uuid_id and packagelabel.label_uuid_id
    package_labels = connection.execute(sa.text('SELECT id, package_id, label_id FROM packagelabel')).fetchall()
    for package_label in package_labels:
        package_uuid = connection.execute(
            sa.text('SELECT new_uuid FROM id_mapping WHERE table_name = :table AND old_id = :old_id'),
            {'table': 'package', 'old_id': package_label[1]}
        ).fetchone()
        label_uuid = connection.execute(
            sa.text('SELECT new_uuid FROM id_mapping WHERE table_name = :table AND old_id = :old_id'),
            {'table': 'label', 'old_id': package_label[2]}
        ).fetchone()
        
        if package_uuid and label_uuid:
            connection.execute(
                sa.text('UPDATE packagelabel SET package_uuid_id = :package_uuid, label_uuid_id = :label_uuid WHERE id = :id'),
                {'package_uuid': package_uuid[0], 'label_uuid': label_uuid[0], 'id': package_label[0]}
            )
    
    # Drop old foreign key constraints
    op.drop_constraint('trackingevent_package_id_fkey', 'trackingevent', type_='foreignkey')
    op.drop_constraint('packagelabel_package_id_fkey', 'packagelabel', type_='foreignkey')
    op.drop_constraint('packagelabel_label_id_fkey', 'packagelabel', type_='foreignkey')
    
    # Drop old integer columns
    op.drop_column('trackingevent', 'package_id')
    op.drop_column('packagelabel', 'package_id')
    op.drop_column('packagelabel', 'label_id')
    
    # Rename UUID columns to be the primary columns
    op.alter_column('package', 'uuid_id', new_column_name='id')
    op.alter_column('label', 'uuid_id', new_column_name='id')
    op.alter_column('trackingevent', 'uuid_id', new_column_name='id')
    op.alter_column('packagelabel', 'uuid_id', new_column_name='id')
    op.alter_column('carrierconfig', 'uuid_id', new_column_name='id')
    
    # Rename foreign key columns
    op.alter_column('trackingevent', 'package_uuid_id', new_column_name='package_id')
    op.alter_column('packagelabel', 'package_uuid_id', new_column_name='package_id')
    op.alter_column('packagelabel', 'label_uuid_id', new_column_name='label_id')
    
    # Make UUID columns NOT NULL
    op.alter_column('package', 'id', nullable=False)
    op.alter_column('label', 'id', nullable=False)
    op.alter_column('trackingevent', 'id', nullable=False)
    op.alter_column('packagelabel', 'id', nullable=False)
    op.alter_column('carrierconfig', 'id', nullable=False)
    op.alter_column('trackingevent', 'package_id', nullable=False)
    op.alter_column('packagelabel', 'package_id', nullable=False)
    op.alter_column('packagelabel', 'label_id', nullable=False)
    
    # Add new foreign key constraints
    op.create_foreign_key('trackingevent_package_id_fkey', 'trackingevent', 'package', ['package_id'], ['id'])
    op.create_foreign_key('packagelabel_package_id_fkey', 'packagelabel', 'package', ['package_id'], ['id'])
    op.create_foreign_key('packagelabel_label_id_fkey', 'packagelabel', 'label', ['label_id'], ['id'])
    
    # Drop the mapping table
    op.drop_table('id_mapping')


def downgrade() -> None:
    """Downgrade schema."""
    # This is a complex migration that would require significant effort to reverse
    # For now, we'll raise an exception to prevent accidental downgrades
    raise Exception("UUID migration cannot be automatically downgraded. Manual intervention required.")
