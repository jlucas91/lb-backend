#!/usr/bin/env python
"""Create a new user in the database.

Usage (inside Docker):
    docker compose run --rm --user root -e PYTHONPATH=/app app \
        python scripts/create_user.py --email user@example.com --display-name "Jane Doe"

You will be prompted for a password (min 8 characters).
"""

import argparse
import asyncio
import getpass
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.controllers.user import create_user
from app.core.config import get_settings
from app.schemas.user import UserCreate


async def main(email: str, display_name: str, password: str) -> None:
    engine = create_async_engine(get_settings().database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        data = UserCreate(email=email, display_name=display_name, password=password)
        user = await create_user(session, data)
        await session.commit()
        print(f"Created user: {user.email} (id={user.id})")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new user")
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument("--display-name", required=True, help="Display name")
    parser.add_argument(
        "--password",
        default=None,
        help="Password (prompted interactively if omitted)",
    )
    args = parser.parse_args()

    password = args.password
    if password is None:
        password = getpass.getpass("Password (min 8 chars): ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(main(args.email, args.display_name, password))
