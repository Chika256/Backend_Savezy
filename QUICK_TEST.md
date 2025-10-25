# 🚀 Quick Authentication Test - 3 Steps

## Step 1: Generate Token (10 seconds)

```bash
python test_auth_manually.py
```

## Step 2: Copy Token from Output

Look for this section:
```
✅ Generated token:

eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Step 3: Test API (Copy/Paste)

Replace `YOUR_TOKEN` below with the token from Step 2:

```bash
# Test 1: Verify token works
curl -X POST http://localhost:5000/api/auth/token/verify \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_TOKEN"}'

# Test 2: Create expense (protected)
curl -X POST http://localhost:5000/api/expenses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"title": "Coffee", "amount": 4.50, "category": "Food"}'

# Test 3: List expenses
curl -X GET http://localhost:5000/api/expenses \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## ✅ Expected Results

**Test 1:** `{"valid": true, "payload": {...}}`
**Test 2:** `{"message": "Expense created successfully.", ...}`
**Test 3:** `{"message": "Expenses retrieved successfully.", "data": {"items": [...]}}`

---

## 🧪 Run All Automated Tests

```bash
python -m unittest discover tests -v
```

Expected: `Ran 19 tests ... OK`

---

## 📱 For Mobile App Testing

Use Postman collection:
1. Import `Savezy_Auth_API.postman_collection.json`
2. Set `jwt_token` variable to your token
3. Test all endpoints

---

## ❓ Having Issues?

See `TESTING_GUIDE.md` for detailed troubleshooting.
