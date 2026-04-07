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
        sa.Column(
            "role",
            sa.Enum("user", "manager", name="userrole", create_type=False),
            nullable=False,
            server_default="user",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "groups",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "card_lists",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "cards",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("card_list_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["card_list_id"], ["card_lists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_group",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("role_in_group", sa.String(), nullable=False, server_default="member"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "group_id"),
    )

    op.create_table(
        'files',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_key', sa.String(), nullable=False),
        sa.Column('mime_type', sa.String(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('card_list_id', sa.String(), nullable=True),
        sa.Column('card_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['card_list_id'], ['card_lists.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['card_id'], ['cards.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_key')
    )

    op.create_index("ix_card_lists_user_id", "card_lists", ["user_id"])
    op.create_index("ix_card_lists_group_id", "card_lists", ["group_id"])
    op.create_index("ix_groups_created_by", "groups", ["created_by"])
    op.create_index("ix_user_group_group_id", "user_group", ["group_id"])
    op.create_index("ix_user_group_user_id", "user_group", ["user_id"])
    op.create_index('ix_files_card_list_id', 'files', ['card_list_id'])
    op.create_index('ix_files_card_id', 'files', ['card_id'])
    op.create_index('ix_files_user_id', 'files', ['user_id'])


def downgrade() -> None:

    op.drop_index("ix_user_group_user_id")
    op.drop_index("ix_user_group_group_id")
    op.drop_index("ix_groups_created_by")
    op.drop_index("ix_card_lists_group_id")
    op.drop_index("ix_card_lists_user_id")

    op.drop_table("user_group")
    op.drop_table("cards")
    op.drop_table("card_lists")
    op.drop_table("groups")
    op.drop_table("users")
    op.drop_table('files')

    op.execute("DROP TYPE IF EXISTS userrole")