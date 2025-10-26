#!/usr/bin/env python3
"""
Test script for Google ID token verification endpoint
This helps debug issues with the /api/auth/google/verify endpoint
"""
import requests
import json
import sys

BASE_URL = "http://localhost:3000"

def test_google_verify(id_token):
    """Test the Google ID token verification endpoint"""
    print("=" * 70)
    print("Testing /api/auth/google/verify endpoint")
    print("=" * 70)
    
    endpoint = f"{BASE_URL}/api/auth/google/verify"
    
    payload = {
        "id_token": id_token
    }
    
    print(f"\nEndpoint: {endpoint}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("\nSending request...")
    
    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"\nResponse Body:")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 200:
            print("\n✅ SUCCESS! Token verified and JWT generated")
            data = response.json()
            if 'token' in data:
                print(f"\nJWT Token: {data['token'][:50]}...")
                print(f"User: {data.get('user', {})}")
        else:
            print("\n❌ FAILED! Check the error message above")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to the API")
        print("Make sure Docker container is running: docker-compose up -d")
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request timed out")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")

def check_logs():
    """Instructions to check Docker logs"""
    print("\n" + "=" * 70)
    print("To see detailed server logs, run:")
    print("=" * 70)
    print("docker-compose logs -f app")
    print("\nOr to see just the last 50 lines:")
    print("docker-compose logs --tail=50 app")

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Google ID Token Verification Test")
    print("=" * 70)
    
    if len(sys.argv) > 1:
        id_token = sys.argv[1]
        test_google_verify(id_token)
    else:
        print("\nUsage: python3 test_google_verify.py <id_token>")
        print("\nExample:")
        print("python3 test_google_verify.py eyJhbGciOiJSUzI1NiIsImtpZCI6...")
        print("\nTo get an ID token:")
        print("1. Use Google Sign-In in your mobile app")
        print("2. Print/log the id_token you receive")
        print("3. Pass it to this script")
        print("\nCommon issues:")
        print("- ID token expired (tokens expire after 1 hour)")
        print("- Wrong GOOGLE_CLIENT_ID in .env file")
        print("- ID token was issued for a different client ID")
        print("- Network issues preventing Google API calls")
    
    check_logs()
    print()
