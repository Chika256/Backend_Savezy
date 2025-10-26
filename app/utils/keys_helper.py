import secrets
import hashlib

def generate_api_key():
    """Generate a random API key."""
    return f"sk_{secrets.token_urlsafe(32)}"

def hash_api_key(api_key):
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()