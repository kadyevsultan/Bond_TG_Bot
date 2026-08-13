from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = '91e3e93f43de'
down_revision: str | Sequence[str] | None = 'f06b7166ed1a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('retired_themes',
    sa.Column('source_name', sa.String(length=64), nullable=False),
    sa.Column('retired_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('source_name')
    )
    with op.batch_alter_table('themes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_name', sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column(
                'is_customized',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.create_index(batch_op.f('ix_themes_source_name'), ['source_name'], unique=False)

    op.execute("UPDATE themes SET source_name = name WHERE is_builtin = 1")



def downgrade() -> None:
    with op.batch_alter_table('themes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_themes_source_name'))
        batch_op.drop_column('is_customized')
        batch_op.drop_column('source_name')

    op.drop_table('retired_themes')
