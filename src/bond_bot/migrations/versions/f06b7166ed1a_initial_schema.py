from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = 'f06b7166ed1a'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('themes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('owner_id', sa.BigInteger(), nullable=True),
    sa.Column('is_builtin', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('owner_id', 'name', name='uq_theme_owner_name')
    )
    with op.batch_alter_table('themes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_themes_owner_id'), ['owner_id'], unique=False)

    op.create_table('words',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('theme_id', sa.Integer(), nullable=False),
    sa.Column('text', sa.String(length=64), nullable=False),
    sa.ForeignKeyConstraint(['theme_id'], ['themes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('theme_id', 'text', name='uq_word_theme_text')
    )
    with op.batch_alter_table('words', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_words_theme_id'), ['theme_id'], unique=False)

    op.create_table('similar_words',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('word_id', sa.Integer(), nullable=False),
    sa.Column('text', sa.String(length=64), nullable=False),
    sa.ForeignKeyConstraint(['word_id'], ['words.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('word_id', 'text', name='uq_similar_word_text')
    )
    with op.batch_alter_table('similar_words', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_similar_words_word_id'), ['word_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('similar_words', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_similar_words_word_id'))

    op.drop_table('similar_words')
    with op.batch_alter_table('words', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_words_theme_id'))

    op.drop_table('words')
    with op.batch_alter_table('themes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_themes_owner_id'))

    op.drop_table('themes')
