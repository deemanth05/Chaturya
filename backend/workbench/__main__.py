import argparse
import getpass

from .auth import create_user, password_hash
from .settings import Settings
from .store import Store


def main():
    parser = argparse.ArgumentParser(description="Manage the local workbench")
    sub = parser.add_subparsers(dest="command", required=True)
    bootstrap = sub.add_parser("create-admin")
    bootstrap.add_argument("username")
    reset = sub.add_parser("reset-password")
    reset.add_argument("username")
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.command in {"create-admin", "reset-password"}:
        settings = Settings()
        settings.prepare()
        password = getpass.getpass("Password (12+ characters): ")
        if password != getpass.getpass("Repeat password: "):
            raise SystemExit("Passwords differ")
        store = Store(settings.data)
        if args.command == "create-admin":
            create_user(store, args.username, password, "admin")
            print("Administrator created. No default credentials exist.")
        else:
            user = store.one("SELECT id FROM users WHERE username=?", (args.username.strip().lower(),))
            if not user:
                raise SystemExit("Account not found")
            store.execute("UPDATE users SET password=? WHERE id=?", (password_hash(password), user["id"]))
            store.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
            store.event("account.password_reset", {"method": "local_operator"}, actor=user["id"])
            print("Password reset. Existing sessions revoked.")
    else:
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(), host=args.host, port=args.port, proxy_headers=False)


if __name__ == "__main__":
    main()
