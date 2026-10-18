"use client";
import { useEffect, useState } from "react";
import { UserPlus, Users, Settings2 } from "lucide-react";
import { api, date, message, User } from "../lib/api";
import { Badge, Busy, Empty, Modal } from "./ui";
export function People({
  current,
  fail,
}: {
  current: User;
  fail: (e: unknown) => void;
}) {
  const [accounts, setAccounts] = useState<User[] | null>(null),
    [create, setCreate] = useState(false),
    [selected, setSelected] = useState<User | null>(null),
    [busy, setBusy] = useState(false);
  const [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [role, setRole] = useState("student"),
    [error, setError] = useState("");
  const [departments, setDepartments] = useState(""),
    [courses, setCourses] = useState(""),
    [membershipLoading, setMembershipLoading] = useState(false),
    [membershipLoaded, setMembershipLoaded] = useState(false);
  async function refresh() {
    try {
      setAccounts(await api<User[]>("/accounts"));
    } catch (e) {
      fail(e);
    }
  }
  useEffect(() => {
    void refresh();
  }, []); // Mount is restricted to administrators by the parent.
  async function manage(user: User) {
    setSelected(user);
    setMembershipLoading(true);
    setMembershipLoaded(false);
    setError("");
    setDepartments("");
    setCourses("");
    try {
      const values = await api<{ kind: string; value: string }[]>(
        `/accounts/${user.id}/memberships`,
      );
      setDepartments(
        values
          .filter((x) => x.kind === "department")
          .map((x) => x.value)
          .join("\n"),
      );
      setCourses(
        values
          .filter((x) => x.kind === "course")
          .map((x) => x.value)
          .join("\n"),
      );
      setMembershipLoaded(true);
    } catch (e) {
      setError(message(e));
    } finally {
      setMembershipLoading(false);
    }
  }
  return (
    <section className="page-content">
      <div className="section-heading">
        <div>
          <span className="eyebrow">COLLEGE ACCESS</span>
          <h1>People & permissions</h1>
          <p>Local accounts with role, department and course access.</p>
        </div>
        <button
          className="primary"
          onClick={() => {
            setError("");
            setCreate(true);
          }}
        >
          <UserPlus size={15} />
          Create account
        </button>
      </div>
      {accounts === null ? (
        <Busy />
      ) : !accounts.length ? (
        <Empty title="No accounts available" />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Account</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {accounts.map((u) => (
                <tr key={u.id}>
                  <td>
                    <span className="row">
                      <span className="avatar">
                        <Users size={15} />
                      </span>
                      {u.username}
                      {u.id === current.id && <Badge>You</Badge>}
                    </span>
                  </td>
                  <td>{u.role}</td>
                  <td>
                    <Badge tone={u.active ? "green" : "amber"}>
                      {u.active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td>{date(u.created)}</td>
                  <td>
                    <button onClick={() => void manage(u)}>
                      <Settings2 size={14} />
                      Manage
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="notice">
        Students use published sources shared with their memberships. Faculty
        and staff can maintain private drafts. Administrators control
        publication and account access.
      </p>
      {create && (
        <Modal
          title="Create a local account"
          onClose={() => {
            if (!busy) setCreate(false);
          }}
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              try {
                await api("/accounts", {
                  method: "POST",
                  body: JSON.stringify({ username, password, role }),
                });
                setPassword("");
                setUsername("");
                setCreate(false);
                await refresh();
              } catch (e) {
                setError(message(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Username
              <input
                autoComplete="off"
                required
                minLength={3}
                maxLength={64}
                pattern="[A-Za-z0-9._-]+"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                required
                minLength={12}
                maxLength={256}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <span className="muted small">
                At least 12 characters. Share credentials securely.
              </span>
            </label>
            <label>
              Role
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                {["student", "faculty", "staff", "admin"].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <button className="primary" disabled={busy}>
              {busy ? <Busy /> : "Create account"}
            </button>
          </form>
        </Modal>
      )}
      {selected && (
        <Modal
          title={`Manage ${selected.username}`}
          onClose={() => {
            if (!busy) setSelected(null);
          }}
        >
          {membershipLoading ? (
            <Busy />
          ) : (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setBusy(true);
                setError("");
                try {
                  await api(`/accounts/${selected.id}/memberships`, {
                    method: "PUT",
                    body: JSON.stringify({
                      departments: departments
                        .split("\n")
                        .map((x) => x.trim())
                        .filter(Boolean),
                      courses: courses
                        .split("\n")
                        .map((x) => x.trim())
                        .filter(Boolean),
                    }),
                  });
                  setSelected(null);
                  await refresh();
                } catch (e) {
                  setError(message(e));
                } finally {
                  setBusy(false);
                }
              }}
            >
              <label>
                Departments
                <textarea
                  rows={3}
                  value={departments}
                  onChange={(e) => setDepartments(e.target.value)}
                />
              </label>
              <label>
                Courses
                <textarea
                  rows={4}
                  value={courses}
                  onChange={(e) => setCourses(e.target.value)}
                />
              </label>
              <p className="muted">
                One exact membership per line, matching the document’s metadata.
                Saving replaces existing memberships.
              </p>
              {error && (
                <p role="alert" className="error">
                  {error}
                </p>
              )}
              <div className="row wrap">
                <button
                  className="primary"
                  disabled={busy || !membershipLoaded}
                >
                  {busy ? <Busy /> : "Save memberships"}
                </button>
                {selected.id !== current.id && (
                  <button
                    className={selected.active ? "danger" : ""}
                    type="button"
                    disabled={busy}
                    onClick={async () => {
                      setBusy(true);
                      try {
                        await api(`/accounts/${selected.id}`, {
                          method: "PATCH",
                          body: JSON.stringify({ active: !selected.active }),
                        });
                        setSelected(null);
                        await refresh();
                      } catch (e) {
                        setError(message(e));
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    {selected.active
                      ? "Deactivate & revoke sessions"
                      : "Reactivate account"}
                  </button>
                )}
              </div>
            </form>
          )}
        </Modal>
      )}
    </section>
  );
}
