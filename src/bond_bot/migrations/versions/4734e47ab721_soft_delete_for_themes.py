from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = '4734e47ab721'
down_revision: str | Sequence[str] | None = '91e3e93f43de'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table('retired_themes')
    with op.batch_alter_table('themes', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.create_index(batch_op.f('ix_themes_is_deleted'), ['is_deleted'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('themes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_themes_is_deleted'))
        batch_op.drop_column('is_deleted')

    op.create_table('retired_themes',
    sa.Column('source_name', sa.VARCHAR(length=64), nullable=False),
    sa.Column('retired_at', sa.DATETIME(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('source_name')
    )
