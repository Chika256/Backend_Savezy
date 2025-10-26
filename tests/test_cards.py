"""Integration tests for the cards CRUD API."""

import os
import unittest

os.environ.setdefault("JWT_SECRET_KEY", "dev-jwt-secret-key")

from app import create_app
from app.extensions import db
from app.models import Card, CardType, Category, Expense, User
from app.utils.jwt_helper import generate_jwt


class CardsApiTestCase(unittest.TestCase):
    """Covers CRUD operations and validation for cards endpoints."""

    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

        self.user = User(id=1, email="cardtester@example.com", name="Card Tester")
        db.session.add(self.user)
        db.session.commit()

        # Supporting categories for expense deletion test.
        need_category = Category(slug="need", name="Need")
        db.session.add(need_category)
        db.session.commit()
        self.need_category = need_category

        self.client = self.app.test_client()
        token = generate_jwt(user_id=self.user.id, email=self.user.email)
        self.auth_header = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        db_path = os.path.join(self.app.instance_path, "test.db")
        if os.path.exists(db_path):
            os.remove(db_path)

    def _create_card(self, **kwargs):
        defaults = {
            "user_id": self.user.id,
            "name": "Daily Debit",
            "type": CardType.DEBIT,
            "last_four": "0000",
        }
        defaults.update(kwargs)
        card = Card(**defaults)
        db.session.add(card)
        db.session.commit()
        return card

    def test_create_credit_card_requires_limit(self):
        payload = {"name": "Rewards", "type": "credit"}
        response = self.client.post(
            "/api/cards", json=payload, headers=self.auth_header
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("limit is required for credit cards.", data["data"]["errors"])

        payload["limit"] = "5000"
        payload["last_four"] = "4242"
        response = self.client.post(
            "/api/cards", json=payload, headers=self.auth_header
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["data"]["card"]["name"], "Rewards")
        self.assertEqual(data["data"]["card"]["limit"], 5000.0)
        self.assertEqual(data["data"]["card"]["last_four"], "4242")

    def test_create_prepaid_card_validation(self):
        payload = {"name": "Travel Wallet", "type": "prepaid", "total_balance": "200"}
        response = self.client.post(
            "/api/cards", json=payload, headers=self.auth_header
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("balance_left is required for prepaid cards.", data["data"]["errors"])

        payload["balance_left"] = "250"
        response = self.client.post(
            "/api/cards", json=payload, headers=self.auth_header
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("balance_left cannot exceed total_balance.", data["data"]["errors"])

        payload["balance_left"] = "150"
        response = self.client.post(
            "/api/cards", json=payload, headers=self.auth_header
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["data"]["card"]["type"], "prepaid")
        self.assertEqual(data["data"]["card"]["total_balance"], 200.0)
        self.assertEqual(data["data"]["card"]["balance_left"], 150.0)

    def test_list_cards_with_filtering(self):
        self._create_card(name="Debit A")
        self._create_card(
            name="Premium Credit",
            type=CardType.CREDIT,
            credit_limit=8000,
        )
        self._create_card(
            name="Travel Wallet",
            type=CardType.PREPAID,
            total_balance=600,
            balance_left=400,
            last_four="5678",
        )

        response = self.client.get(
            "/api/cards?type=credit&sort=name&order=asc",
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["data"]["items"]), 1)
        self.assertEqual(data["data"]["items"][0]["name"], "Premium Credit")
        self.assertEqual(data["data"]["filters"]["type"], "credit")
        self.assertIn("last_four", data["data"]["items"][0])
        self.assertNotIn("brand", data["data"]["items"][0])

    def test_update_card_to_prepaid(self):
        card = self._create_card(name="Flex", type=CardType.DEBIT)

        payload = {
            "type": "prepaid",
            "total_balance": "300",
            "balance_left": "180",
        }
        response = self.client.patch(
            f"/api/cards/{card.id}", json=payload, headers=self.auth_header
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["data"]["card"]["type"], "prepaid")
        self.assertEqual(data["data"]["card"]["total_balance"], 300.0)
        self.assertEqual(data["data"]["card"]["balance_left"], 180.0)
        self.assertIsNone(data["data"]["card"]["limit"])

    def test_delete_card_blocked_when_expenses_exist(self):
        card = self._create_card(name="Household", type=CardType.DEBIT)
        expense = Expense(
            user_id=self.user.id,
            title="Groceries",
            amount=50,
            category=self.need_category,
            type=Expense.ExpenseType.NEED,
            card=card,
        )
        db.session.add(expense)
        db.session.commit()

        response = self.client.delete(
            f"/api/cards/{card.id}", headers=self.auth_header
        )
        self.assertEqual(response.status_code, 409)

        # Remove expense then delete should work.
        db.session.delete(expense)
        db.session.commit()
        response = self.client.delete(
            f"/api/cards/{card.id}", headers=self.auth_header
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["data"]["card_id"], card.id)


if __name__ == "__main__":
    unittest.main()
