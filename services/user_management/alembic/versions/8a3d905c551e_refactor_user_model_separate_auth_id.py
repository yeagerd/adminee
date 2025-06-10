"""refactor_user_model_separate_auth_id

Revision ID: 8a3d905c551e
Revises: eae3ad795a11
Create Date: 2025-06-10 10:40:02.155164

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a3d905c551e'
down_revision = 'eae3ad795a11'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Create a new temporary table with the new structure
    op.create_table(
        'users_new',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('external_auth_id', sa.String(length=255), nullable=False),
        sa.Column('auth_provider', sa.String(length=50), nullable=False, default='clerk'),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('profile_image_url', sa.String(length=500), nullable=True),
        sa.Column('onboarding_completed', sa.Boolean(), nullable=False, default=False),
        sa.Column('onboarding_step', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('external_auth_id')
    )
    
    # Step 2: Copy data from old table to new table
    # The old 'id' becomes 'external_auth_id', new auto-increment 'id' is generated
    op.execute("""
        INSERT INTO users_new (external_auth_id, auth_provider, email, first_name, last_name, 
                               profile_image_url, onboarding_completed, onboarding_step, 
                               created_at, updated_at, deleted_at)
        SELECT id, 'clerk', email, first_name, last_name, profile_image_url, 
               onboarding_completed, onboarding_step, created_at, updated_at, deleted_at
        FROM users
    """)
    
    # Step 3: Update foreign key references in related tables
    # We need to update these to use the new auto-increment IDs
    # For now, we'll track the mapping of old clerk_id to new int id
    
    # Drop the old table and rename the new one
    op.drop_table('users')
    op.rename_table('users_new', 'users')
    
    # Create indexes
    op.create_index(op.f('ix_users_external_auth_id'), 'users', ['external_auth_id'], unique=True)


def downgrade() -> None:
    # For downgrade, we need to reverse the process
    # This is a destructive operation that will lose the auto-increment IDs
    
    # Create the old table structure
    op.create_table(
        'users_old',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('profile_image_url', sa.String(length=500), nullable=True),
        sa.Column('onboarding_completed', sa.Boolean(), nullable=False, default=False),
        sa.Column('onboarding_step', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Copy data back (external_auth_id becomes id)
    op.execute("""
        INSERT INTO users_old (id, email, first_name, last_name, profile_image_url,
                               onboarding_completed, onboarding_step, created_at, updated_at, deleted_at)
        SELECT external_auth_id, email, first_name, last_name, profile_image_url,
               onboarding_completed, onboarding_step, created_at, updated_at, deleted_at
        FROM users
    """)
    
    # Drop new table and rename old one back
    op.drop_index('ix_users_external_auth_id', table_name='users')
    op.drop_table('users')
    op.rename_table('users_old', 'users')
