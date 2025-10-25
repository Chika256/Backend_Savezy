# 🧪 Authentication Testing Guide

## Quick Start

### Method 1: Automated Tests (Fastest) ✅

```bash
# Run all authentication tests
python -m unittest tests.test_auth -v

# Run all tests (auth + expenses)
python -m unittest discover tests -v
```

**Results:** All 19 tests passing ✅

---

## Method 2: Manual Testing with Script (Recommended for Development)

### Step 1: Generate Test Token

```bash
python test_auth_manually.py
```

This script will:
- ✅ Create a test user
- ✅ Generate a JWT token
- ✅ Verify the token
- ✅ Refresh the token
- ✅ Provide ready-to-use curl commands

### Step 2: Copy the Token

The script outputs a JWT token like:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJpYXQiOjE3NjE0MTQ4OTQsImV4cCI6MTc2MTUwMTI5NH0.s8NJeMwBpoO3xZKTcaByHM-UC0Qb1Gbb3sQPiqeSanc
```

### Step 3: Test Protected Endpoints

Use the provided curl commands or test manually:

```bash
# Verify token
curl -X POST http://localhost:5000/api/auth/token/verify \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_TOKEN_HERE"}'

# Create expense
curl -X POST http://localhost:5000/api/expenses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "title": "Lunch",
    "amount": 15.50,
    "category": "Food"
  }'

# List expenses
curl -X GET http://localhost:5000/api/expenses \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## Method 3: Using Postman/Insomnia

### Import Collection

1. Open Postman
2. Click **Import**
3. Select `Savezy_Auth_API.postman_collection.json`
4. Set environment variables:
   - `base_url`: `http://localhost:5000`
   - `jwt_token`: (paste token from script)

### Test Requests

The collection includes:
- ✅ Google OAuth Init
- ✅ Google OAuth Callback
- ✅ Verify JWT Token
- ✅ Refresh JWT Token
- ✅ Create Expense (Protected)
- ✅ List Expenses (Protected)

---

## Method 4: Full OAuth Testing with Real Google Credentials

### Prerequisites

1. **Google Cloud Console Setup:**
   - Visit: https://console.cloud.google.com
   - Create/select project
   - Enable "Google+ API" or "People API"
   - Create OAuth 2.0 credentials
   - Add redirect URIs:
     - `http://localhost:5000/api/auth/google/callback`
     - `myapp://auth/callback` (for mobile)

2. **Update `.env` file:**
   ```bash
   GOOGLE_CLIENT_ID=your_actual_client_id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_actual_secret
   GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/google/callback
   ALLOWED_MOBILE_REDIRECT_URIS=myapp://auth/callback,savezy://auth/callback
   ```

### Testing Flow

**Step 1: Start Server**
```bash
flask run
# or
python run.py
```

**Step 2: Initialize OAuth**
```bash
curl "http://localhost:5000/api/auth/google/init?redirect_uri=myapp://auth/callback"
```

Response:
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&state=..."
}
```

**Step 3: Authorize with Google**
1. Copy the `auth_url`
2. Paste in browser
3. Sign in with Google
4. Google redirects to: `http://localhost:5000/api/auth/google/callback?code=...&state=...`
5. Extract `code` and `state` from URL

**Step 4: Exchange Code for JWT**
```bash
curl -X POST http://localhost:5000/api/auth/google/callback \
  -H "Content-Type: application/json" \
  -d '{
    "code": "PASTE_CODE_HERE",
    "state": "PASTE_STATE_HERE",
    "redirect_uri": "myapp://auth/callback"
  }'
```

Response:
```json
{
  "success": true,
  "token": "eyJhbGc...",
  "user": {
    "id": 1,
    "email": "your@gmail.com",
    "name": "Your Name",
    "picture": "https://..."
  }
}
```

**Step 5: Use JWT Token**
```bash
curl -X GET http://localhost:5000/api/expenses \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Testing Checklist

### Authentication Endpoints

- [ ] `GET /api/auth/google/init`
  - [ ] With valid redirect_uri
  - [ ] Without redirect_uri (should fail)
  - [ ] With invalid redirect_uri (should fail)

- [ ] `POST /api/auth/google/callback`
  - [ ] With valid code and state
  - [ ] Without state (should fail)
  - [ ] With invalid state (should fail)
  - [ ] Creates new user
  - [ ] Updates existing user

- [ ] `POST /api/auth/token/verify`
  - [ ] With valid token
  - [ ] With expired token
  - [ ] With invalid token
  - [ ] Using Authorization header

- [ ] `POST /api/auth/token/refresh`
  - [ ] With valid token
  - [ ] With invalid token

### Protected Endpoints

- [ ] All `/api/expenses` endpoints require JWT
- [ ] Invalid JWT returns 401
- [ ] Valid JWT allows access
- [ ] User can only access their own expenses

### Security Features

- [ ] State validation prevents CSRF
- [ ] Rate limiting works (10/min, 5/min, 20/min)
- [ ] JWT expires after 24 hours
- [ ] Tokens can be refreshed
- [ ] Redirect URI whitelist enforced

---

## Common Issues & Solutions

### Issue: "Token is invalid or expired"
**Solution:** Generate a new token using `test_auth_manually.py`

### Issue: "Invalid redirect_uri"
**Solution:** Add your redirect URI to `ALLOWED_MOBILE_REDIRECT_URIS` in `.env`

### Issue: "Failed to exchange authorization code"
**Solution:**
- Check Google OAuth credentials are correct
- Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`
- Ensure redirect URI matches in Google Console

### Issue: Rate limit exceeded
**Solution:** Wait 1 minute or restart server to reset rate limits

### Issue: Database error
**Solution:**
```bash
flask db upgrade
# or
python -c "from app import create_app; from app.extensions import db; app=create_app(); app.app_context().push(); db.create_all()"
```

---

## Test Results Summary

```bash
# Expected output from automated tests:
Ran 19 tests in 1.134s
OK

# Breakdown:
- 12 authentication tests ✅
- 7 expense CRUD tests ✅
```

---

## API Response Examples

### Successful Token Verification
```json
{
  "valid": true,
  "payload": {
    "user_id": 1,
    "email": "test@example.com",
    "iat": 1761414894,
    "exp": 1761501294
  }
}
```

### Failed Authentication
```json
{
  "error": "Token is missing"
}
```

### Successful Expense Creation
```json
{
  "message": "Expense created successfully.",
  "data": {
    "expense": {
      "id": 1,
      "user_id": 1,
      "title": "Lunch",
      "amount": 15.50,
      "category": "Food",
      "date": "2025-10-25T18:54:55",
      "description": null
    }
  }
}
```

---

## Mobile App Testing Notes

For mobile app developers testing the OAuth flow:

1. **Deep Link Setup:** Ensure `myapp://auth/callback` is registered as a deep link
2. **State Management:** Store the `state` token from `/init` response
3. **Code Extraction:** Extract `code` and `state` from redirect URL
4. **Token Storage:** Securely store JWT token in device keychain/keystore
5. **Auto-Refresh:** Implement token refresh before expiration (24h)

### Example Mobile Flow

```javascript
// 1. Get auth URL
const initResponse = await fetch(
  'http://localhost:5000/api/auth/google/init?redirect_uri=myapp://auth/callback'
);
const { auth_url } = await initResponse.json();

// 2. Open browser for Google sign-in
openBrowser(auth_url);

// 3. Handle redirect (in deep link handler)
function handleDeepLink(url) {
  const code = extractParam(url, 'code');
  const state = extractParam(url, 'state');

  // 4. Exchange for JWT
  const callbackResponse = await fetch(
    'http://localhost:5000/api/auth/google/callback',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, state, redirect_uri: 'myapp://auth/callback' })
    }
  );

  const { token, user } = await callbackResponse.json();

  // 5. Store token
  await secureStorage.set('jwt_token', token);
  await secureStorage.set('user', JSON.stringify(user));
}
```

---

## Next Steps

1. ✅ Run automated tests: `python -m unittest discover tests -v`
2. ✅ Generate test token: `python test_auth_manually.py`
3. ✅ Test with Postman/curl
4. ⚠️ Set up real Google OAuth credentials
5. ⚠️ Test full OAuth flow with browser
6. ⚠️ Integrate with mobile app

---

## Support

If you encounter issues:
1. Check logs in terminal
2. Verify `.env` configuration
3. Run automated tests to isolate the problem
4. Check `TESTING_GUIDE.md` (this file)

Good luck testing! 🚀
