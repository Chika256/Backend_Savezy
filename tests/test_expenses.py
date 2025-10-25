"""Integration tests for the expenses CRUD API using unittest."""

import os
import sys
import unittest
from functools import wraps
from types import SimpleNamespace
from unittest.mock import patch

from flask import request

from app import create_app, db
from app.models import Expense, User


class ExpensesApiTestCase(unittest.TestCase):
    """Covers core CRUD operations and validation paths."""

    def setUp(self):
        def _test_auth_required(fn):
            @wraps(fn)
            def _wrapped(*args, **kwargs):
                auth_header = request.headers.get("Authorization", "")
                user_id = 1
                email = None
                name = None
                if auth_header.startswith("Bearer "):
                    token = auth_header.removeprefix("Bearer ").strip()
                    if token:
                        parts = token.split("|")
                        try:
                            user_id = int(parts[0])
                        except (TypeError, ValueError):
                            user_id = 1
                        if len(parts) > 1:
                            email = parts[1]
                        if len(parts) > 2:
                            name = parts[2]
                request.user = SimpleNamespace(id=user_id, email=email, name=name)
                return fn(*args, **kwargs)

            return _wrapped

        self.auth_patcher = patch(
            "app.auth.middleware.auth_required",
            new=_test_auth_required,
        )
        self.auth_patcher.start()
        sys.modules.pop("app.routes.expenses", None)

        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Seed a mock authenticated user (id must match Authorization header).
        user = User(id=1, email="user@example.com", name="Test User")
        db.session.add(user)
        db.session.commit()

        self.client = self.app.test_client()
        self.auth_header = {"Authorization": "Bearer 1|user@example.com|Test User"}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        self.auth_patcher.stop()
        db_path = os.path.join(self.app.instance_path, "test.db")
        if os.path.exists(db_path):
            os.remove(db_path)

    def _create_expense(self, **kwargs):
        defaults = {
            "user_id": 1,
            "title": "Coffee",
            "amount": 5.0,
            "category": "Food",
            "description": "Morning coffee",
        }
        defaults.update(kwargs)
        expense = Expense(**defaults)
        db.session.add(expense)
        db.session.commit()
        return expense

    def test_create_expense_success(self):
        payload = {
            "title": "Lunch",
            "amount": 12.5,
            "category": "Food",
            "description": "Team lunch",
        }
        response = self.client.post("/api/expenses", json=payload, headers=self.auth_header)

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["message"], "Expense created successfully.")
        self.assertEqual(data["data"]["expense"]["title"], "Lunch")

    def test_create_expense_validation_error(self):
        payload = {"title": "", "amount": "invalid", "category": ""}
        response = self.client.post("/api/expenses", json=payload, headers=self.auth_header)

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("errors", data["data"])

    def test_list_expenses_with_filtering_and_pagination(self):
        self._create_expense(title="Breakfast", category="Food", amount=8)
        self._create_expense(title="Bus Ticket", category="Transport", amount=2.5)
        self._create_expense(title="Dinner", category="Food", amount=20)

        response = self.client.get(
            "/api/expenses?category=Food&sort=amount&order=asc&limit=2&page=1",
            headers=self.auth_header,
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        items = data["data"]["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["title"], "Breakfast")
        self.assertEqual(data["data"]["filters"]["category"], "Food")

    def test_get_single_expense(self):
        expense = self._create_expense(title="Gym", category="Health", amount=30)

        response = self.client.get(f"/api/expenses/{expense.id}", headers=self.auth_header)

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["data"]["expense"]["title"], "Gym")

    def test_get_expense_not_found(self):
        response = self.client.get("/api/expenses/999", headers=self.auth_header)

        self.assertEqual(response.status_code, 404)

    def test_update_expense(self):
        expense = self._create_expense(title="Snacks", category="Food", amount=3)
        payload = {"amount": 4, "description": "Evening snack"}

        response = self.client.patch(
            f"/api/expenses/{expense.id}", json=payload, headers=self.auth_header
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["data"]["expense"]["amount"], 4.0)
        self.assertEqual(data["data"]["expense"]["description"], "Evening snack")

    def test_delete_expense(self):
        expense = self._create_expense(title="Taxi", category="Transport", amount=15)

        response = self.client.delete(f"/api/expenses/{expense.id}", headers=self.auth_header)

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["data"]["expense_id"], expense.id)

        verify = self.client.get(f"/api/expenses/{expense.id}", headers=self.auth_header)
        self.assertEqual(verify.status_code, 404)


if __name__ == "__main__":
    unittest.main()
