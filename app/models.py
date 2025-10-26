"""Database models for the Savezy backend."""

from datetime import datetime, timezone
from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


def utc_now():
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class User(db.Model):
    """Application user authenticated via Google OAuth."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255))

    expenses = db.relationship(
        "Expense",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    cards = db.relationship(
        "Card",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    api_keys = db.relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def to_dict(self):
        """Serialize the user for JSON responses."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
        }

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User id={self.id} email={self.email!r}>"


class CardType(str, Enum):
    """Enumerated card types supported by the system."""

    CREDIT = "credit"
    DEBIT = "debit"
    PREPAID = "prepaid"


class Card(db.Model):
    """Spending card used when logging expenses."""

    __tablename__ = "cards"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(100), nullable=False)
    apple_slug = db.Column(db.String(100))
    brand = db.Column(db.String(50))
    last_four = db.Column(db.String(4))
    type = db.Column(db.Enum(CardType), nullable=False, default=CardType.DEBIT)
    credit_limit = db.Column(db.Numeric(12, 2))
    total_balance = db.Column(db.Numeric(12, 2))
    balance_left = db.Column(db.Numeric(12, 2))

    user = db.relationship("User", back_populates="cards")
    expenses = db.relationship(
        "Expense",
        back_populates="card",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def to_dict(self):
        """Serialize the card for JSON responses."""
        serialized = {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "type": self.type.value if isinstance(self.type, CardType) else self.type,
            "apple_slug": self.apple_slug,
            "brand": self.brand,
            "last_four": self.last_four,
            "limit": float(self.credit_limit) if self.credit_limit is not None else None,
            "total_balance": float(self.total_balance) if self.total_balance is not None else None,
            "balance_left": float(self.balance_left) if self.balance_left is not None else None,
        }
        return serialized

    def __repr__(self) -> str:  # pragma: no cover
        card_type = self.type.value if isinstance(self.type, CardType) else self.type
        return f"<Card id={self.id} name={self.name!r} type={card_type}>"


class Category(db.Model):
    """Expense category definitions with unique slug identifiers."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255))

    expenses = db.relationship(
        "Expense",
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def to_dict(self):
        """Serialize the category for JSON responses."""
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
        }

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Category id={self.id} slug={self.slug!r}>"


class Expense(db.Model):
    """Expense entry tracked per user."""

    __tablename__ = "expenses"
    __table_args__ = (
        db.Index("ix_expenses_user_category", "user_id", "category_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    card_id = db.Column(
        db.Integer,
        db.ForeignKey("cards.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=utc_now, nullable=False)
    description = db.Column(db.String(255))

    user = db.relationship("User", back_populates="expenses")
    category = db.relationship("Category", back_populates="expenses")
    card = db.relationship("Card", back_populates="expenses")

    def to_dict(self):
        """Serialize the expense for JSON responses."""
        serialized = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "amount": self.amount,
            "date": self.date.isoformat() if self.date else None,
            "description": self.description,
        }
        if self.category:
            serialized["category"] = self.category.slug
            serialized["category_name"] = self.category.name
        else:
            serialized["category"] = None
        if self.card:
            serialized["card"] = self.card.to_dict()
        else:
            serialized["card"] = None
        return serialized

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Expense id={self.id} title={self.title!r} amount={self.amount}>"

class APIKey(db.Model):
    """API key for shortcut's request."""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user = db.relationship("User", back_populates="api_keys")
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    last_used_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
