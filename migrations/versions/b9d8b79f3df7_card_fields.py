"""Add extended fields to cards table."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b9d8b79f3df7"
down_revision = "ddfaa1be93c4"
branch_labels = None
depends_on = None


card_type_enum = sa.Enum("credit", "debit", "prepaid", name="cardtype")


def upgrade() -> None:
    card_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("cards", sa.Column("apple_slug", sa.String(length=100), nullable=True))
    op.add_column(
        "cards",
        sa.Column(
            "type",
            card_type_enum,
            nullable=False,
            server_default="debit",
        ),
    )
    op.add_column(
        "cards",
        sa.Column("credit_limit", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "cards",
        sa.Column("total_balance", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "cards",
        sa.Column("balance_left", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cards", "balance_left")
    op.drop_column("cards", "total_balance")
    op.drop_column("cards", "credit_limit")
    op.drop_column("cards", "type")
    op.drop_column("cards", "apple_slug")

    card_type_enum.drop(op.get_bind(), checkfirst=True)
