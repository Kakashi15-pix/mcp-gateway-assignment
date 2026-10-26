import os

from sqlalchemy import select

from auth import hash_password
from db import SessionLocal
from models import User


def main() -> None:
    email = os.environ["ADMIN_EMAIL"].strip().lower()
    password = os.environ["ADMIN_PASSWORD"]
    password_hash = hash_password(password)

    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == email)).first()
        if user is None:
            user = User(
                email=email,
                display_name="Admin",
                role="admin",
                password_hash=password_hash,
            )
            db.add(user)
        else:
            user.role = "admin"
            user.is_active = True
            user.password_hash = password_hash
        db.commit()

    print(f"admin ready: {email}")


if __name__ == "__main__":
    main()
