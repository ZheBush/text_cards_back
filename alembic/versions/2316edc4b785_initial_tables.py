from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2316edc4b785"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "card_lists",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cards",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("card_list_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["card_list_id"],
            ["card_lists.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute("CREATE TYPE userrole AS ENUM ('USER', 'MANAGER')")
    op.add_column('users', sa.Column('role', sa.Enum('USER', 'MANAGER', name='userrole'),
                                     nullable=False, server_default='USER'))

    op.create_table('groups',
                    sa.Column('id', sa.String(), nullable=False),
                    sa.Column('name', sa.String(), nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('created_by', sa.String(), nullable=False),
                    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )

    op.create_table('user_group',
                    sa.Column('user_id', sa.String(), nullable=False),
                    sa.Column('group_id', sa.String(), nullable=False),
                    sa.Column('role_in_group', sa.String(), nullable=True),
                    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('user_id', 'group_id')
                    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("cards")
    op.drop_table("card_lists")
    op.drop_table("users")