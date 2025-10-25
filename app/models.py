"""Database models for the Savezy backend."""

from datetime import datetime

from app import db


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

    def to_dict(self):
        """Serialize the user for JSON responses."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
        }

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User id={self.id} email={self.email!r}>"


class Expense(db.Model):
    """Expense entry tracked per user."""

    __tablename__ = "expenses"
    __table_args__ = (
        db.Index("ix_expenses_user_category", "user_id", "category"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    description = db.Column(db.String(255))

    user = db.relationship("User", back_populates="expenses")

    def to_dict(self):
        """Serialize the expense for JSON responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "amount": self.amount,
            "category": self.category,
            "date": self.date.isoformat() if self.date else None,
            "description": self.description,
        }

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Expense id={self.id} title={self.title!r} amount={self.amount}>"

