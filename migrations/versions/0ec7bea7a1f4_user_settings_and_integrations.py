"""Add user settings fields and integration table

Revision ID: 0ec7bea7a1f4
Revises: c5f68f97cdbd
Create Date: 2025-12-12 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0ec7bea7a1f4'
down_revision = 'c5f68f97cdbd'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('theme_preference', sa.String(length=20), nullable=False, server_default='light'))
        batch_op.add_column(sa.Column('nextcloud_base_url', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('nextcloud_username', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('nextcloud_app_password', sa.String(length=255), nullable=True))

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('theme_preference', server_default=None)

    op.create_table(
        'user_integrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('credentials_json', sa.Text(), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'provider', name='uq_user_provider')
    )
    op.create_index(op.f('ix_user_integrations_provider'), 'user_integrations', ['provider'], unique=False)

    # Align timestamps with application defaults for existing rows
    op.execute("UPDATE user_integrations SET updated_at = created_at")


def downgrade():
    op.drop_index(op.f('ix_user_integrations_provider'), table_name='user_integrations')
    op.drop_table('user_integrations')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('nextcloud_app_password')
        batch_op.drop_column('nextcloud_username')
        batch_op.drop_column('nextcloud_base_url')
        batch_op.drop_column('theme_preference')
