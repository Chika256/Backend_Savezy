"""Add expense type column."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f23f5b3f5ade"
down_revision = "b9d8b79f3df7"
branch_labels = None
depends_on = None

expense_type_enum = sa.Enum("investment", "wants", "need", name="expensetype")


def upgrade() -> None:
    expense_type_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "expenses",
        sa.Column(
            "type",
            expense_type_enum,
            nullable=False,
            server_default="need",
        ),
    )


def downgrade() -> None:
    op.drop_column("expenses", "type")
    expense_type_enum.drop(op.get_bind(), checkfirst=True)
