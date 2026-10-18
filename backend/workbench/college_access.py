"""Authorization shared by listing, retrieval, and source downloads."""
import yaml


def load_config(path):
    result = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    allowed = {"question", "study", "teaching", "letter", "code"}
    if not set(result.get("workflows", [])).issubset(allowed):
        raise ValueError("Unknown college workflow in configuration")
    if not 1 <= result.get("max_sources", 6) <= 10:
        raise ValueError("max_sources must be between 1 and 10")
    for key in ("teaching_roles", "letter_roles"):
        if not set(result.get(key, [])).issubset({"admin", "faculty", "staff", "student"}):
            raise ValueError("Unknown college role in configuration")
    return result


def memberships(store, user_id):
    rows = store.rows("SELECT kind,value FROM memberships WHERE user_id=?", (user_id,))
    return {kind: {row["value"] for row in rows if row["kind"] == kind} for kind in ("department", "course")}


def visible(document, current, grants):
    if document["synthetic"]:
        return False
    if current["role"] == "admin":
        return True
    if document["status"] == "archived":
        return False
    if document["owner_id"] == current["id"]:
        return True
    if document["status"] != "published" or document["audience"] == "private":
        return False
    if document["audience"] != "college" and document["audience"] != current["role"]:
        return False
    return all(not document[kind] or document[kind] in grants[kind] for kind in ("department", "course"))


def visible_documents(store, current):
    grants = memberships(store, current["id"])
    return [d for d in store.rows("SELECT documents.*,COUNT(chunks.id) AS chunks FROM documents LEFT JOIN chunks ON chunks.document_id=documents.id GROUP BY documents.id ORDER BY created DESC")
            if visible(d, current, grants)]


def current_user(store, user_id):
    return store.one("SELECT id,username,COALESCE(college_role,CASE role WHEN 'inspector' THEN 'staff' WHEN 'reviewer' THEN 'faculty' ELSE role END) AS role FROM users WHERE id=? AND active=1", (user_id,))
