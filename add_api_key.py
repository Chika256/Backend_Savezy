import argparse
from datetime import datetime, timezone

from app import create_app
from app.extensions import db
from app.models import User, APIKey


def upsert_user(email: str) -> User:
    user = User.query.filter_by(email=email).first()
    if user:
        return user
    user = User(email=email, name=email.split("@")[0])
    db.session.add(user)
    db.session.commit()
    return user


def insert_api_key(user: User, key: str) -> APIKey:
    existing = APIKey.query.filter_by(key=key).first()
    if existing:
        return existing
    rec = APIKey(
        key=key,
        user_id=user.id,
        created_at=datetime.now(timezone.utc),
        is_active=True,
    )
    db.session.add(rec)
    db.session.commit()
    return rec


def main():
    parser = argparse.ArgumentParser(description="Insert an API key into the database")
    parser.add_argument("--email", default="shortcut-user@example.com", help="User email to associate with the API key (will be created if missing)")
    parser.add_argument("--key", required=True, help="The API key value to insert (e.g., sk_...)")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        user = upsert_user(args.email)
        rec = insert_api_key(user, args.key)
        print("API key record:")
        print(f"  id: {rec.id}")
        print(f"  key: {rec.key}")
        print(f"  user_id: {rec.user_id}")
        print(f"  is_active: {rec.is_active}")
        print("Done.")


if __name__ == "__main__":
    main()
