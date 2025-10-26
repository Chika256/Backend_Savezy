"""Integration tests for the categories CRUD API."""

import os
import unittest

os.environ.setdefault("JWT_SECRET_KEY", "dev-jwt-secret-key")

from app import create_app
from app.extensions import db
from app.models import Card, CardType, Category, Expense, User
from app.utils.jwt_helper import generate_jwt


class CategoriesApiTestCase(unittest.TestCase):
    """Exercise category creation, listing, update, and deletion."""

    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

        self.user = User(id=1, email="cat@example.com", name="Category User")
        db.session.add(self.user)
        db.session.commit()

        self.client = self.app.test_client()
        token = generate_jwt(user_id=self.user.id, email=self.user.email)
        self.auth_header = {"Authorization": f"Bearer {token}"}

        # Pre-seed a card and expense helpers for delete tests.
        self.card = Card(
            user_id=self.user.id,
            name="Primary Card",
            type=CardType.DEBIT,
            last_four="4242",
        )
        db.session.add(self.card)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        db_path = os.path.join(self.app.instance_path, "test.db")
        if os.path.exists(db_path):
            os.remove(db_path)

    def test_create_category_success(self):
        payload = {"name": "Home Office", "description": "Remote work supplies"}
        response = self.client.post(
            "/api/categories", json=payload, headers=self.auth_header
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        category = data["data"]["category"]
        self.assertEqual(category["name"], "Home Office")
        self.assertEqual(category["slug"], "home-office")
        self.assertEqual(category["description"], "Remote work supplies")

    def test_duplicate_category_name_rejected(self):
        db.session.add(Category(name="Travel", slug="travel"))
        db.session.commit()
        payload = {"name": "Travel"}
        response = self.client.post(
            "/api/categories", json=payload, headers=self.auth_header
        )
        self.assertEqual(response.status_code, 400)

    def test_list_categories_with_search(self):
        db.session.add(Category(name="Food & Dining", slug="food-dining"))
        db.session.add(Category(name="Entertainment", slug="entertainment"))
        db.session.commit()

        response = self.client.get(
            "/api/categories?search=food", headers=self.auth_header
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["data"]["items"]), 1)
        self.assertEqual(data["data"]["items"][0]["slug"], "food-dining")
        self.assertEqual(data["data"]["filters"]["search"], "food")

    def test_get_category(self):
        category = Category(name="Subscriptions", slug="subscriptions")
        db.session.add(category)
        db.session.commit()

        response = self.client.get(
            f"/api/categories/{category.id}", headers=self.auth_header
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["data"]["category"]["name"], "Subscriptions")

    def test_update_category(self):
        category = Category(name="Education", slug="education")
        db.session.add(category)
        db.session.commit()

        payload = {"name": "Continuing Education"}
        response = self.client.patch(
            f"/api/categories/{category.id}", json=payload, headers=self.auth_header
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["data"]["category"]["slug"], "continuing-education")

    def test_delete_category_blocked_when_in_use(self):
        category = Category(name="Food & Dining", slug="food-dining")
        db.session.add(category)
        db.session.commit()

        expense = Expense(
            user_id=self.user.id,
            title="Groceries",
            amount=80,
            type=Expense.ExpenseType.NEED,
            category=category,
            card=self.card,
        )
        db.session.add(expense)
        db.session.commit()

        response = self.client.delete(
            f"/api/categories/{category.id}", headers=self.auth_header
        )
        self.assertEqual(response.status_code, 409)

        db.session.delete(expense)
        db.session.commit()
        response = self.client.delete(
            f"/api/categories/{category.id}", headers=self.auth_header
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["category_id"], category.id)


if __name__ == "__main__":
    unittest.main()
