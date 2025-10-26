#!/usr/bin/env python3
"""
Test script to verify X-API-Key and JWT authentication for /api/expenses endpoint.
This script will:
1. Create a test user
2. Generate an API key for that user
3. Test creating an expense with X-API-Key
4. Generate a JWT token
5. Test creating an expense with JWT
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User, APIKey, Card, Category
from app.utils.keys_helper import generate_api_key
from app.utils.jwt_helper import generate_jwt
from datetime import datetime, timezone
import requests
import json


def setup_test_data(app):
    """Create test user, card, and category."""
    with app.app_context():
        # Clean up existing test data
        test_user = User.query.filter_by(email="test@example.com").first()
        if test_user:
            db.session.delete(test_user)
            db.session.commit()

        # Create test user
        user = User(
            email="test@example.com",
            name="Test User"
        )
        db.session.add(user)
        db.session.commit()

        # Create test card
        card = Card(
            user_id=user.id,
            name="Test Card",
            brand="Visa",
            last_four="1234"
        )
        db.session.add(card)
        db.session.commit()

        # Ensure categories exist
        need_cat = Category.query.filter_by(slug="need").first()
        if not need_cat:
            need_cat = Category(name="Need", slug="need", description="Essential expenses")
            db.session.add(need_cat)
            db.session.commit()

        # Generate API key
        api_key = generate_api_key()
        api_key_record = APIKey(
            key=api_key,
            user_id=user.id,
            created_at=datetime.now(timezone.utc),
            is_active=True
        )
        db.session.add(api_key_record)
        db.session.commit()

        # Generate JWT
        jwt_token = generate_jwt(user.id, user.email)

        return {
            "user_id": user.id,
            "card_id": card.id,
            "api_key": api_key,
            "jwt_token": jwt_token,
            "email": user.email
        }


def test_apikey_auth(base_url, api_key, card_id):
    """Test creating expense with X-API-Key authentication."""
    print("\n" + "="*70)
    print("TEST 1: X-API-Key Authentication")
    print("="*70)

    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "title": "Test Expense (API Key)",
        "amount": 25.50,
        "category": "need",
        "card_id": card_id,
        "description": "Testing X-API-Key authentication"
    }

    print(f"\n📤 Request:")
    print(f"   URL: {base_url}/api/expenses")
    print(f"   Headers: X-Api-Key: {api_key[:20]}...")
    print(f"   Body: {json.dumps(payload, indent=6)}")

    try:
        response = requests.post(
            f"{base_url}/api/expenses",
            headers=headers,
            json=payload
        )

        print(f"\n📥 Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Body: {json.dumps(response.json(), indent=6)}")

        if response.status_code == 201:
            print(f"\n✅ SUCCESS: Expense created with X-API-Key authentication")
            return True
        else:
            print(f"\n❌ FAILED: Expected 201, got {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"\n❌ ERROR: Could not connect to {base_url}")
        print(f"   Make sure the Flask app is running!")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False


def test_jwt_auth(base_url, jwt_token, card_id):
    """Test creating expense with JWT authentication."""
    print("\n" + "="*70)
    print("TEST 2: JWT (Bearer Token) Authentication")
    print("="*70)

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "title": "Test Expense (JWT)",
        "amount": 15.75,
        "category": "need",
        "card_id": card_id,
        "description": "Testing JWT Bearer token authentication"
    }

    print(f"\n📤 Request:")
    print(f"   URL: {base_url}/api/expenses")
    print(f"   Headers: Authorization: Bearer {jwt_token[:30]}...")
    print(f"   Body: {json.dumps(payload, indent=6)}")

    try:
        response = requests.post(
            f"{base_url}/api/expenses",
            headers=headers,
            json=payload
        )

        print(f"\n📥 Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Body: {json.dumps(response.json(), indent=6)}")

        if response.status_code == 201:
            print(f"\n✅ SUCCESS: Expense created with JWT authentication")
            return True
        else:
            print(f"\n❌ FAILED: Expected 201, got {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"\n❌ ERROR: Could not connect to {base_url}")
        print(f"   Make sure the Flask app is running!")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False


def main():
    """Main test execution."""
    print("\n🧪 API Authentication Test Suite")
    print("="*70)

    # Create Flask app
    app = create_app()

    # Setup test data
    print("\n📋 Setting up test data...")
    test_data = setup_test_data(app)

    print(f"\n✅ Test data created:")
    print(f"   User ID: {test_data['user_id']}")
    print(f"   Email: {test_data['email']}")
    print(f"   Card ID: {test_data['card_id']}")
    print(f"   API Key: {test_data['api_key'][:30]}...")
    print(f"   JWT Token: {test_data['jwt_token'][:40]}...")

    # Base URL (update if your app runs on different port)
    base_url = "http://localhost:5001"

    print(f"\n🌐 Testing against: {base_url}")

    # Run tests
    apikey_result = test_apikey_auth(base_url, test_data['api_key'], test_data['card_id'])
    jwt_result = test_jwt_auth(base_url, test_data['jwt_token'], test_data['card_id'])

    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"   X-API-Key Auth: {'✅ PASSED' if apikey_result else '❌ FAILED'}")
    print(f"   JWT Auth:       {'✅ PASSED' if jwt_result else '❌ FAILED'}")
    print("="*70)

    if apikey_result and jwt_result:
        print("\n🎉 All tests passed! Both authentication methods work correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()