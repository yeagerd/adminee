"""
Drop allow_anonymous_responses column from meeting_polls table
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'drop_allow_anonymous_responses'
down_revision = 'add_response_token_to_poll_participants'
branch_labels = None
depends_on = None

def upgrade():
    op.drop_column('meeting_polls', 'allow_anonymous_responses')

def downgrade():
    op.add_column('meeting_polls', sa.Column('allow_anonymous_responses', sa.Boolean(), server_default=sa.false(), nullable=True)) 