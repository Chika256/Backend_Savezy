"""Integration tests for the expenses CRUD API using unittest."""

import os
import unittest

os.environ.setdefault("JWT_SECRET_KEY", "dev-jwt-secret-key")

from app import create_app
from app.extensions import db
from app.models import Card, Category, Expense, User
from app.utils.jwt_helper import generate_jwt


class ExpensesApiTestCase(unittest.TestCase):
    """Covers core CRUD operations and validation paths."""

    def setUp(self):
        self.app = create_app("testing")

        self.app_context = self.app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()

        # Seed canonical categories expected by the API.
        slug_name_pairs = [
            ("investment", "Investment"),
            ("wants", "Wants"),
            ("need", "Need"),
        ]
        for slug, name in slug_name_pairs:
            category = Category(slug=slug, name=name)
            db.session.add(category)
        db.session.commit()
        self.category_map = {
            category.slug: category for category in Category.query.all()
        }

        # Seed a mock authenticated user (id must match Authorization header).
        user = User(id=1, email="user@example.com", name="Test User")
        db.session.add(user)
        db.session.commit()

        # Seed default cards for the user.
        self.primary_card = Card(
            user_id=user.id,
            name="Primary Card",
            brand="Visa",
            last_four="4242",
        )
        self.secondary_card = Card(
            user_id=user.id,
            name="Backup Card",
            brand="Mastercard",
            last_four="1111",
        )
        db.session.add_all([self.primary_card, self.secondary_card])
        db.session.commit()

        self.client = self.app.test_client()
        token = generate_jwt(user_id=1, email="user@example.com")
        self.auth_header = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        db_path = os.path.join(self.app.instance_path, "test.db")
        if os.path.exists(db_path):
            os.remove(db_path)

    def _create_expense(self, **kwargs):
        defaults = {
            "user_id": 1,
            "title": "Coffee",
            "amount": 5.0,
            "category": "need",
            "description": "Morning coffee",
            "card": self.primary_card,
        }
        defaults.update(kwargs)
        category_slug = defaults.pop("category")
        category = self.category_map[category_slug]
        card = defaults.pop("card")
        expense = Expense(category=category, card=card, **defaults)
        db.session.add(expense)
        db.session.commit()
        return expense

    def test_create_expense_success(self):
        payload = {
            "title": "Lunch",
            "amount": 12.5,
            "category": "need",
            "description": "Team lunch",
            "card_id": self.primary_card.id,
        }
        response = self.client.post("/api/expenses", json=payload, headers=self.auth_header)

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["message"], "Expense created successfully.")
        self.assertEqual(data["data"]["expense"]["title"], "Lunch")
        self.assertEqual(data["data"]["expense"]["category"], "need")
        self.assertEqual(data["data"]["expense"]["category_name"], "Need")
        self.assertEqual(data["data"]["expense"]["card"]["id"], self.primary_card.id)

    def test_create_expense_validation_error(self):
        payload = {"title": "", "amount": "invalid", "category": ""}
        response = self.client.post("/api/expenses", json=payload, headers=self.auth_header)

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("errors", data["data"])

    def test_create_expense_invalid_category(self):
        payload = {
            "title": "Movie night",
            "amount": 15,
            "category": "entertainment",
            "card_id": self.primary_card.id,
        }
        response = self.client.post("/api/expenses", json=payload, headers=self.auth_header)

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("Category must be one of", data["data"]["errors"][0])

    def test_create_expense_invalid_card(self):
        payload = {
            "title": "Dinner",
            "amount": 30,
            "category": "need",
            "card_id": 999,
        }
        response = self.client.post("/api/expenses", json=payload, headers=self.auth_header)

        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn("Card not found", data["message"])

    def test_list_expenses_with_filtering_and_pagination(self):
        self._create_expense(title="Breakfast", category="need", amount=8)
        self._create_expense(title="Groceries", category="need", amount=25)
        self._create_expense(title="Brokerage", category="investment", amount=50)
        self._create_expense(title="Concert", category="wants", amount=120)

        response = self.client.get(
            "/api/expenses?category=need&sort=amount&order=asc&limit=2&page=1",
            headers=self.auth_header,
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        items = data["data"]["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["title"], "Breakfast")
        self.assertEqual(data["data"]["filters"]["category"], "need")

    def test_get_single_expense(self):
        expense = self._create_expense(title="Gym", category="wants", amount=30)

        response = self.client.get(f"/api/expenses/{expense.id}", headers=self.auth_header)

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["data"]["expense"]["title"], "Gym")
        self.assertEqual(data["data"]["expense"]["category"], "wants")
        self.assertEqual(data["data"]["expense"]["card"]["id"], self.primary_card.id)

    def test_get_expense_not_found(self):
        response = self.client.get("/api/expenses/999", headers=self.auth_header)

        self.assertEqual(response.status_code, 404)

    def test_update_expense(self):
        expense = self._create_expense(title="Snacks", category="need", amount=3)
        payload = {"amount": 4, "description": "Evening snack"}

        response = self.client.patch(
            f"/api/expenses/{expense.id}", json=payload, headers=self.auth_header
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["data"]["expense"]["amount"], 4.0)
        self.assertEqual(data["data"]["expense"]["description"], "Evening snack")
        self.assertEqual(data["data"]["expense"]["category"], "need")

    def test_update_expense_category_change(self):
        expense = self._create_expense(title="Utilities", category="need", amount=90)
        payload = {"category": "investment"}

        response = self.client.patch(
            f"/api/expenses/{expense.id}", json=payload, headers=self.auth_header
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["data"]["expense"]["category"], "investment")
        self.assertEqual(data["data"]["expense"]["category_name"], "Investment")

    def test_update_expense_card_change(self):
        expense = self._create_expense(title="Groceries", category="need", amount=45)
        payload = {"card_id": self.secondary_card.id}

        response = self.client.patch(
            f"/api/expenses/{expense.id}", json=payload, headers=self.auth_header
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["data"]["expense"]["card"]["id"], self.secondary_card.id)
        self.assertEqual(data["data"]["expense"]["card"]["name"], "Backup Card")

    def test_delete_expense(self):
        expense = self._create_expense(title="Taxi", category="wants", amount=15)

        response = self.client.delete(f"/api/expenses/{expense.id}", headers=self.auth_header)

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["data"]["expense_id"], expense.id)

        verify = self.client.get(f"/api/expenses/{expense.id}", headers=self.auth_header)
        self.assertEqual(verify.status_code, 404)


if __name__ == "__main__":
    unittest.main()
