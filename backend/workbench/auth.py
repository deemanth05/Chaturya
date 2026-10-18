import hashlib
import hmac
import secrets
import time
import uuid

ITERATIONS = 600_000


def password_hash(password):
    if len(password) < 12 or len(password) > 256:
        raise ValueError("Use a password between 12 and 256 characters")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def verify_password(password, encoded):
    if len(password) > 256:
        return False
    _, iterations, salt, expected = encoded.split("$")
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
    return hmac.compare_digest(actual, expected)


def create_user(store, username, password, role="student"):
    username = username.strip().lower()
    if not 3 <= len(username) <= 64 or not all(c.isalnum() or c in "._-" for c in username):
        raise ValueError("Username must have 3-64 letters, digits, dots, underscores or hyphens")
    if role not in {"admin", "faculty", "staff", "student", "inspector", "reviewer"}:
        raise ValueError("Unknown role")
    user_id = str(uuid.uuid4())
    # The legacy role column retains its original CHECK constraint; college_role
    # is the authoritative role for new accounts and keeps upgrades additive.
    legacy = role if role in {"admin", "inspector", "reviewer"} else "inspector"
    store.execute("INSERT INTO users(id,username,password,role,created,college_role) VALUES(?,?,?,?,?,?)",
                  (user_id, username, password_hash(password), legacy, time.time(), role))
    store.event("account.created", {"username": username, "role": role}, actor=user_id)
    return {"id": user_id, "username": username, "role": role}


def session_token(store, user_id):
    token = secrets.token_urlsafe(40)
    store.execute("DELETE FROM sessions WHERE expires<?", (time.time(),))
    store.execute("INSERT INTO sessions VALUES(?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user_id, time.time() + 8 * 3600))
    return token


def session_user(store, token):
    if not token:
        return None
    return store.one("SELECT users.id,username,COALESCE(college_role,CASE role WHEN 'inspector' THEN 'staff' WHEN 'reviewer' THEN 'faculty' ELSE role END) AS role FROM sessions JOIN users ON users.id=sessions.user_id WHERE active=1 AND token=? AND expires>?",
                     (hashlib.sha256(token.encode()).hexdigest(), time.time()))

