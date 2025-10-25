"""Unit tests covering the Expense and User models."""

import os
import unittest
from datetime import datetime

from app import create_app, db
from app.models import Card, Category, Expense, User


class ModelsTestCase(unittest.TestCase):
    """Ensure model defaults, relationships, and serializers behave correctly."""

    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()
        slug_name_pairs = [
            ("investment", "Investment"),
            ("wants", "Wants"),
            ("need", "Need"),
        ]
        for slug, name in slug_name_pairs:
            db.session.add(Category(slug=slug, name=name))
        db.session.commit()
        self.category_map = {
            category.slug: category for category in Category.query.all()
        }
        self.card = Card(user_id=1, name="Primary", brand="Visa", last_four="4242")
        # Ensure user exists ahead of card creation
        user = User(id=1, email="model@example.com", name="Model User")
        db.session.add(user)
        db.session.add(self.card)
        db.session.commit()
        self.user = user

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        db_path = os.path.join(self.app.instance_path, "test.db")
        if os.path.exists(db_path):
            os.remove(db_path)

    def test_expense_defaults_and_serialization(self):
        """Expense gets automatic timestamp and serializes cleanly."""
        expense = Expense(
            user_id=self.user.id,
            title="Monthly rent",
            amount=1200.0,
            category=self.category_map["need"],
            card=self.card,
            description="Apartment rent",
        )
        db.session.add(expense)
        db.session.commit()

        self.assertIsNotNone(expense.id)
        self.assertIsNotNone(expense.date)
        self.assertIsInstance(expense.date, datetime)

        serialized = expense.to_dict()
        self.assertEqual(serialized["title"], "Monthly rent")
        self.assertEqual(serialized["amount"], 1200.0)
        self.assertEqual(serialized["category"], "need")
        self.assertEqual(serialized["category_name"], "Need")
        self.assertEqual(serialized["description"], "Apartment rent")
        self.assertEqual(serialized["user_id"], self.user.id)
        self.assertEqual(serialized["date"], expense.date.isoformat())
        self.assertEqual(serialized["card"]["id"], self.card.id)
        self.assertEqual(serialized["card"]["name"], "Primary")

    def test_user_expense_relationship_and_cascade(self):
        """Deleting a user should cascade to their expenses."""
        first = Expense(
            user_id=self.user.id,
            title="Index fund",
            amount=300.0,
            category=self.category_map["investment"],
            card=self.card,
        )
        second = Expense(
            user_id=self.user.id,
            title="Gym membership",
            amount=45.0,
            category=self.category_map["wants"],
            card=self.card,
        )
        db.session.add_all([first, second])
        db.session.commit()

        self.assertEqual(self.user.expenses.count(), 2)
        self.assertSetEqual(
            {expense.title for expense in self.user.expenses.all()},
            {"Index fund", "Gym membership"},
        )

        db.session.delete(self.user)
        db.session.commit()

        self.assertEqual(Expense.query.count(), 0)

    def test_category_serialization(self):
        """Category serialization exposes slug and human name."""
        investment = self.category_map["investment"]
        serialized = investment.to_dict()

        self.assertEqual(serialized["slug"], "investment")
        self.assertEqual(serialized["name"], "Investment")
        self.assertIsNone(serialized["description"])

    def test_card_serialization(self):
        """Card serialization returns core identifiers."""
        serialized = self.card.to_dict()
        self.assertEqual(serialized["id"], self.card.id)
        self.assertEqual(serialized["name"], "Primary")
        self.assertEqual(serialized["brand"], "Visa")


if __name__ == "__main__":
    unittest.main()
