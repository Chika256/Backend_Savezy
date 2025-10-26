"""Seed default categories with descriptions."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "88a0f25c3a1f"
down_revision = "f23f5b3f5ade"
branch_labels = None
depends_on = None


CATEGORIES = [
    ("Others", "others", "Miscellaneous expenses"),
    ("Gifts & Donations", "gifts-donations", "Presents, charity, and contributions"),
    ("Subscriptions", "subscriptions", "Streaming services, memberships, and recurring payments"),
    ("Personal Care", "personal-care", "Haircuts, cosmetics, and personal grooming"),
    ("Travel", "travel", "Flights, hotels, and vacation expenses"),
    ("Education", "education", "Tuition, books, courses, and learning materials"),
    ("Healthcare", "healthcare", "Medical expenses, pharmacy, and health insurance"),
    ("Bills & Utilities", "bills-utilities", "Rent, electricity, water, internet, and phone bills"),
    ("Entertainment", "entertainment", "Movies, games, hobbies, and leisure activities"),
    ("Shopping", "shopping", "Clothing, electronics, and general retail"),
    ("Transportation", "transportation", "Gas, public transit, ride-sharing, and vehicle maintenance"),
    ("Food & Dining", "food-dining", "Groceries, restaurants, and food delivery"),
]


def upgrade() -> None:
    connection = op.get_bind()
    categories_table = sa.table(
        "categories",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("description", sa.String),
    )

    existing = {
        row.slug for row in connection.execute(sa.select(categories_table.c.slug))
    }

    for name, slug, description in CATEGORIES:
        if slug not in existing:
            connection.execute(
                categories_table.insert().values(
                    name=name,
                    slug=slug,
                    description=description,
                )
            )
        else:
            connection.execute(
                categories_table.update()
                .where(categories_table.c.slug == slug)
                .values(
                    name=name,
                    description=description,
                )
            )


def downgrade() -> None:
    connection = op.get_bind()
    categories_table = sa.table(
        "categories",
        sa.column("slug", sa.String),
    )

    connection.execute(
        categories_table.delete().where(
            categories_table.c.slug.in_([slug for _, slug, _ in CATEGORIES])
        )
    )
