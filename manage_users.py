import argparse
import getpass
import hashlib
import secrets
from pathlib import Path
from typing import Any

import yaml


USERS_FILE = Path("config/users.yaml")
ROUNDS = 600000


def load_users() -> dict[str, Any]:
    if not USERS_FILE.exists():
        return {"users": {}}
    with USERS_FILE.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {"users": {}}


def save_users(data: dict[str, Any]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with USERS_FILE.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), ROUNDS)
    return f"pbkdf2_sha256${ROUNDS}${salt}${digest.hex()}"


def set_password(args: argparse.Namespace) -> None:
    data = load_users()
    users = data.setdefault("users", {})
    user = users.setdefault(
        args.username,
        {
            "display_name": args.username,
            "role": "technician",
            "permissions": {
                "use_smart_model": False,
                "use_web_search": False,
                "view_diagrams": True,
                "manage_users": False,
                "upload_images": True,
            },
        },
    )
    password = args.password or getpass.getpass("Password: ")
    user["password_hash"] = hash_password(password)
    save_users(data)
    print(f"Password updated for {args.username}")


def set_permission(args: argparse.Namespace) -> None:
    data = load_users()
    users = data.setdefault("users", {})
    if args.username not in users:
        raise SystemExit(f"Unknown user: {args.username}")
    users[args.username].setdefault("permissions", {})[args.permission] = args.value == "true"
    save_users(data)
    print(f"{args.permission} set to {args.value} for {args.username}")


def add_user(args: argparse.Namespace) -> None:
    data = load_users()
    users = data.setdefault("users", {})
    if args.username in users:
        raise SystemExit(f"User already exists: {args.username}")
    password = args.password or getpass.getpass("Password: ")
    users[args.username] = {
        "password_hash": hash_password(password),
        "display_name": args.display_name or args.username,
        "role": args.role,
        "permissions": {
            "use_smart_model": args.role == "admin",
            "use_web_search": args.role == "admin",
            "view_diagrams": True,
            "manage_users": args.role == "admin",
            "upload_images": True,
        },
    }
    save_users(data)
    print(f"Added {args.username}")


def list_users(_: argparse.Namespace) -> None:
    data = load_users()
    for username, user in data.get("users", {}).items():
        permissions = ", ".join(
            f"{key}={value}" for key, value in sorted(user.get("permissions", {}).items())
        )
        print(f"{username}\trole={user.get('role', 'user')}\t{permissions}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Manage FEVCOM AI users and permissions.")
    sub = root.add_subparsers(required=True)

    add = sub.add_parser("add-user")
    add.add_argument("username")
    add.add_argument("--password")
    add.add_argument("--display-name")
    add.add_argument("--role", default="technician")
    add.set_defaults(func=add_user)

    password = sub.add_parser("set-password")
    password.add_argument("username")
    password.add_argument("password", nargs="?")
    password.set_defaults(func=set_password)

    permission = sub.add_parser("set-permission")
    permission.add_argument("username")
    permission.add_argument("permission")
    permission.add_argument("value", choices=["true", "false"])
    permission.set_defaults(func=set_permission)

    users = sub.add_parser("list-users")
    users.set_defaults(func=list_users)
    return root


if __name__ == "__main__":
    arguments = parser().parse_args()
    arguments.func(arguments)
