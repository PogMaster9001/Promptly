"""Introduce organization tables and script mapping

Revision ID: 3bf1d8e235e4
Revises: 0ec7bea7a1f4
Create Date: 2025-12-12 01:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3bf1d8e235e4'
down_revision = '0ec7bea7a1f4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('slug', sa.String(length=120), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )

    op.create_table(
        'organization_memberships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='member'),
        sa.Column('joined_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'user_id', name='uq_membership')
    )

    op.create_table(
        'organization_invites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='member'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_organization_invites_code'), 'organization_invites', ['code'], unique=True)

    with op.batch_alter_table('scripts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_scripts_organization_id', ['organization_id'], unique=False)
        batch_op.create_foreign_key('fk_scripts_organization_id', 'organizations', ['organization_id'], ['id'], ondelete='SET NULL')

    with op.batch_alter_table('organization_memberships', schema=None) as batch_op:
        batch_op.alter_column('role', server_default=None)

    with op.batch_alter_table('organization_invites', schema=None) as batch_op:
        batch_op.alter_column('role', server_default=None)


def downgrade():
    with op.batch_alter_table('scripts', schema=None) as batch_op:
        batch_op.drop_constraint('fk_scripts_organization_id', type_='foreignkey')
        batch_op.drop_index('ix_scripts_organization_id')
        batch_op.drop_column('organization_id')

    op.drop_index(op.f('ix_organization_invites_code'), table_name='organization_invites')
    op.drop_table('organization_invites')
    op.drop_table('organization_memberships')
    op.drop_table('organizations')
