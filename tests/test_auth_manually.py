#!/usr/bin/env python3
"""
Manual Authentication Testing Script

This script helps you test the authentication flow without needing
to set up Google OAuth. It creates a test user and generates JWT tokens.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User
from app.utils.jwt_helper import generate_jwt, decode_jwt, refresh_jwt


def print_separator():
    print("\n" + "=" * 60 + "\n")


def test_jwt_flow():
    """Test JWT generation, verification, and refresh."""

    print("🧪 Starting Manual Authentication Tests...")
    print_separator()

    # Create app context
    app = create_app('development')

    with app.app_context():
        # Clean up existing test user
        existing_user = User.query.filter_by(email='test@example.com').first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()
            print("🗑️  Cleaned up existing test user")

        # Step 1: Create test user
        print("📝 Step 1: Creating test user...")
        user = User(email='test@example.com', name='Test User')
        db.session.add(user)
        db.session.commit()
        print(f"✅ Created user: {user}")
        print(f"   - ID: {user.id}")
        print(f"   - Email: {user.email}")
        print(f"   - Name: {user.name}")

        print_separator()

        # Step 2: Generate JWT token
        print("🔐 Step 2: Generating JWT token...")
        token = generate_jwt(user_id=user.id, email=user.email)
        print(f"✅ Generated token:")
        print(f"\n{token}\n")
        print("📋 Copy this token to use in your API requests!")

        print_separator()

        # Step 3: Verify token
        print("🔍 Step 3: Verifying JWT token...")
        payload = decode_jwt(token)
        if payload:
            print("✅ Token is valid!")
            print(f"   - user_id: {payload.get('user_id')}")
            print(f"   - email: {payload.get('email')}")
            print(f"   - issued_at: {payload.get('iat')}")
            print(f"   - expires_at: {payload.get('exp')}")
        else:
            print("❌ Token verification failed!")

        print_separator()

        # Step 4: Refresh token
        print("🔄 Step 4: Refreshing JWT token...")
        import time
        time.sleep(1)  # Wait to ensure different timestamp
        new_token = refresh_jwt(token)
        if new_token:
            print("✅ Token refreshed successfully!")
            print(f"\n{new_token}\n")
            print(f"🔄 Old token != New token: {token != new_token}")
        else:
            print("❌ Token refresh failed!")

        print_separator()

        # Step 5: Test commands
        print("🚀 Next Steps - Test with curl:")
        print("\n1. Test token verification:")
        print(f'''
curl -X POST http://localhost:5000/api/auth/token/verify \\
  -H "Content-Type: application/json" \\
  -d '{{"token": "{token}"}}'
        ''')

        print("\n2. Create an expense (protected endpoint):")
        print(f'''
curl -X POST http://localhost:5000/api/expenses \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer {token}" \\
  -d '{{
    "title": "Test Expense",
    "amount": 10.50,
    "category": "Food",
    "type": "need",
    "description": "Testing authentication"
  }}'
        ''')

        print("\n3. List expenses:")
        print(f'''
curl -X GET http://localhost:5000/api/expenses \\
  -H "Authorization: Bearer {token}"
        ''')

        print_separator()
        print("✅ All tests completed successfully!")
        print("\n💡 Tips:")
        print("   - Use the generated token in Postman/Insomnia")
        print("   - Token is valid for 24 hours")
        print("   - Import Savezy_Auth_API.postman_collection.json to Postman")
        print_separator()


if __name__ == "__main__":
    try:
        test_jwt_flow()
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
