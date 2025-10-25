#!/usr/bin/env python3
"""
Test script to generate and verify JWT tokens
Usage: python3 test_token.py
"""
import requests
import json

BASE_URL = "http://localhost:3000"

def test_token_generation():
    """Test generating a token via Google OAuth flow"""
    print("=" * 60)
    print("JWT Token Test")
    print("=" * 60)
    
    # Note: You need to complete the Google OAuth flow to get a valid token
    # This is just a demonstration of how to verify a token
    
    print("\n1. To get a valid token, you need to:")
    print("   - Call /api/auth/google/init with your redirect_uri")
    print("   - Complete the Google OAuth flow")
    print("   - Call /api/auth/google/callback with the code")
    print("   - You'll receive a JWT token in the response")
    
    print("\n2. Or use Google Sign-In SDK directly:")
    print("   - Get ID token from Google Sign-In")
    print("   - POST to /api/auth/google/verify with the id_token")
    
    # Test with a dummy token (will fail as expected)
    print("\n" + "=" * 60)
    print("Testing token verification with invalid token...")
    print("=" * 60)
    
    test_token = "invalid.token.here"
    
    response = requests.post(
        f"{BASE_URL}/api/auth/token/verify",
        json={"token": test_token},
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 401:
        print("\n✓ Expected result: Invalid token was rejected")
    
    print("\n" + "=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. Complete the Google OAuth flow to get a valid token")
    print("2. The token must be generated AFTER the container restart")
    print("3. Old tokens generated with the old JWT_SECRET_KEY will not work")
    print("\nThe JWT_SECRET_KEY has been updated. Any tokens generated")
    print("before the container restart are now invalid and need to be")
    print("regenerated through the authentication flow.")

if __name__ == "__main__":
    try:
        test_token_generation()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API at http://localhost:3000")
        print("Make sure the Docker container is running: docker-compose up -d")
    except Exception as e:
        print(f"Error: {e}")
