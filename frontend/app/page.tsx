"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronRight,
  Code2,
  GraduationCap,
  History,
  Library,
  LogOut,
  Menu,
  MessageSquare,
  PanelRight,
  PenLine,
  Plus,
  Search,
  Shield,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import {
  api,
  ApiError,
  College,
  Doc,
  Event,
  Job,
  message,
  System,
  User,
} from "../lib/api";
import { Busy, IconButton, Modal } from "../components/ui";
import { Composer, modes, permitted } from "../components/Composer";
import { Inspector } from "../components/Inspector";
import { Knowledge } from "../components/Knowledge";
import { People } from "../components/People";
import { SystemPanel } from "../components/System";
import { Run } from "../components/Run";
const workflowIcons = {
  question: MessageSquare,
  study: GraduationCap,
  teaching: BookOpen,
  letter: PenLine,
  code: Code2,
};
function Brand() {
  return (
    <span className="brand">
      <span className="brand-mark">
        <Sparkles size={17} />
      </span>
      <strong>Chaturya</strong>
      <span className="campus-label">CAMPUS</span>
    </span>
  );
}
function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [initialized, setInitialized] = useState<boolean | null>(null);
  useEffect(() => {
    api<{ accounts_initialized: boolean }>("/health")
      .then((v) => setInitialized(v.accounts_initialized))
      .catch((e) => setError(message(e)));
  }, []);
  return (
    <main className="login-page">
      <div className="login-brand">
        <Brand />
      </div>
      <div className="login-card">
        <span className="hero-emblem">
          <GraduationCap size={30} />
        </span>
        <span className="eyebrow">YOUR COLLEGE. YOUR LOCAL AI.</span>
        <h1>A space for better work.</h1>
        <p>Learn, teach and create with your college’s own knowledge.</p>
        {initialized === false ? (
          <div className="notice">
            An administrator must initialize the first local account using the
            setup instructions before sign-in is available.
          </div>
        ) : (
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              try {
                onLogin(
                  await api<User>("/auth/login", {
                    method: "POST",
                    body: JSON.stringify({ username, password }),
                  }),
                );
                setPassword("");
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
                autoComplete="username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <button className="primary" disabled={busy || initialized === null}>
              {busy ? (
                <Busy>Signing in…</Busy>
              ) : (
                <>
                  Enter your workspace
                  <ArrowUpRight size={15} />
                </>
              )}
            </button>
          </form>
        )}
        <div className="login-note">
          <Shield size={13} />
          Account access is managed by your local administrator.
        </div>
      </div>
      <footer>Local knowledge. Thoughtful assistance. Human decisions.</footer>
    </main>
  );
}
export default function Workbench() {
  const [user, setUser] = useState<User | null>(null),
    [authLoading, setAuthLoading] = useState(true),
    [authError, setAuthError] = useState("");
  const [jobs, setJobs] = useState<Job[] | null>(null),
    [docs, setDocs] = useState<Doc[] | null>(null),
    [system, setSystem] = useState<System | null>(null),
    [college, setCollege] = useState<College | null>(null);
  const [page, setPage] = useState("workspace"),
    [mode, setMode] = useState("question"),
    [selected, setSelected] = useState<string | null>(null),
    [job, setJob] = useState<Job | null>(null),
    [events, setEvents] = useState<Event[]>([]);
  const [sidebar, setSidebar] = useState(false),
    [inspector, setInspector] = useState(false),
    [tab, setTab] = useState("sources"),
    [search, setSearch] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [help, setHelp] = useState(false),
    [loadingJob, setLoadingJob] = useState(false);
  const lastEvent = useRef(0),
    refreshJob = useRef<() => void>(() => {});
  const session = useRef<string | null>(null);
  session.current = user?.id || null;
  const logoutState = useCallback(() => {
    session.current = null;
    setUser(null);
    setJobs(null);
    setDocs(null);
    setSystem(null);
    setCollege(null);
    setJob(null);
    setSelected(null);
    setEvents([]);
    setError("");
    setNotice("");
    setPage("workspace");
    setMode("question");
  }, []);
  const fail = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError && e.status === 401) logoutState();
      else setError(message(e));
    },
    [logoutState],
  );
  const refresh = useCallback(async () => {
    const requestedFor = session.current;
    const results = await Promise.allSettled([
      api<Job[]>("/jobs"),
      api<Doc[]>("/knowledge"),
      api<System>("/system"),
      api<College>("/college"),
    ]);
    if (!requestedFor || session.current !== requestedFor) return;
    if (
      results.some(
        (r) =>
          r.status === "rejected" &&
          r.reason instanceof ApiError &&
          r.reason.status === 401,
      )
    ) {
      logoutState();
      return;
    }
    results.forEach((r, i) => {
      if (r.status === "rejected") {
        if (i === 2) setSystem(null);
        fail(r.reason);
      } else {
        if (i === 0) setJobs(r.value as Job[]);
        if (i === 1) setDocs(r.value as Doc[]);
        if (i === 2) setSystem(r.value as System);
        if (i === 3) setCollege(r.value as College);
      }
    });
  }, [fail, logoutState]);
  useEffect(() => {
    window.addEventListener("workbench:session-expired", logoutState);
    return () =>
      window.removeEventListener("workbench:session-expired", logoutState);
  }, [logoutState]);
  useEffect(() => {
    let active = true;
    api<User>("/auth/me")
      .then((u) => {
        if (active) setUser(u);
      })
      .catch((e) => {
        if (active && (!(e instanceof ApiError) || e.status !== 401))
          setAuthError(message(e));
      })
      .finally(() => {
        if (active) setAuthLoading(false);
      });
    setSidebar(window.innerWidth >= 980);
    setInspector(window.innerWidth >= 1440);
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (!user) return;
    void refresh();
    const interval = setInterval(() => void refresh(), 15000);
    return () => clearInterval(interval);
  }, [user, refresh]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (window.innerWidth < 1440) setInspector(false);
        if (window.innerWidth < 980) setSidebar(false);
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSelected(null);
        setJob(null);
        setPage("workspace");
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  useEffect(() => {
    setJob(null);
    setEvents([]);
    lastEvent.current = 0;
    if (!selected || !user) {
      setLoadingJob(false);
      return;
    }
    let active = true,
      loading = false;
    setLoadingJob(true);
    const snapshot = async () => {
      if (!active || loading) return;
      loading = true;
      try {
        const result = await api<Job>(`/jobs/${selected}`);
        if (active) setJob(result);
      } catch (e) {
        if (active) {
          if (e instanceof ApiError && e.status === 404) {
            setJob(null);
            setEvents([]);
            setSelected(null);
          }
          fail(e);
        }
      } finally {
        loading = false;
        if (active) setLoadingJob(false);
      }
    };
    refreshJob.current = () => void snapshot();
    void snapshot();
    const accept = (items: Event[]) => {
      if (!active) return;
      const fresh = items.filter((e) => e.id > lastEvent.current);
      if (!fresh.length) return;
      lastEvent.current = Math.max(...fresh.map((e) => e.id));
      setEvents((old) => [...old, ...fresh].sort((a, b) => a.id - b.id));
      if (
        fresh.some(
          (e) =>
            e.kind === "step.completed" ||
            e.kind.startsWith("job.") ||
            e.kind === "router.selected" ||
            e.kind === "review.recorded",
        )
      )
        void snapshot();
    };
    const socket = new WebSocket(
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/jobs/${selected}/stream`,
    );
    socket.onmessage = (e) => {
      try {
        const item = JSON.parse(e.data);
        if (item.kind !== "heartbeat") accept([item]);
      } catch {
        /* HTTP polling reports service errors. */
      }
    };
    const poll = async () => {
      await snapshot();
      try {
        accept(
          await api<Event[]>(
            `/jobs/${selected}/events?after=${lastEvent.current}`,
          ),
        );
      } catch (e) {
        if (active) fail(e);
      }
    };
    const timer = setInterval(() => void poll(), 4000);
    return () => {
      active = false;
      socket.close();
      clearInterval(timer);
      refreshJob.current = () => {};
    };
  }, [selected, user, fail]);
  const openJob = (id: string) => {
    setSelected(id);
    setPage("workspace");
    setError("");
    if (window.innerWidth < 980) setSidebar(false);
  };
  const newTask = (workflow = mode) => {
    setSelected(null);
    setJob(null);
    setPage("workspace");
    setMode(workflow);
    setError("");
    if (window.innerWidth < 980) setSidebar(false);
  };
  if (authLoading)
    return (
      <main className="loading-page">
        <Brand />
        <Busy>Connecting to your workbench…</Busy>
      </main>
    );
  if (authError && !user)
    return (
      <main className="loading-page">
        <Brand />
        <p className="error">{authError}</p>
        <button onClick={() => location.reload()}>Reconnect</button>
      </main>
    );
  if (!user)
    return (
      <Login
        onLogin={(u) => {
          setAuthError("");
          setUser(u);
        }}
      />
    );
  const activeMode = modes.find((m) => m.id === mode)!;
  const generation = system?.models.find(
    (m) => m.enabled && m.modalities.includes("text"),
  );
  const running = job && ["queued", "running"].includes(job.status);
  return (
    <div
      className={`workbench ${sidebar ? "sidebar-open" : ""} ${inspector && page === "workspace" ? "inspector-open" : ""}`}
    >
      {sidebar && (
        <button
          className="panel-backdrop sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setSidebar(false)}
        />
      )}
      <aside className="sidebar" inert={!sidebar}>
        <div className="sidebar-brand">
          <Brand />
          <IconButton
            label="Close navigation"
            onClick={() => setSidebar(false)}
          >
            <Menu size={16} />
          </IconButton>
        </div>
        <button className="new-task" onClick={() => newTask()}>
          <Plus size={16} />
          New task<kbd>Ctrl K</kbd>
        </button>
        <nav className="main-nav" aria-label="Main navigation">
          {[
            { id: "workspace", name: "Workspace", icon: MessageSquare },
            { id: "library", name: "Knowledge library", icon: Library },
            ...(user.role === "admin"
              ? [{ id: "people", name: "People & access", icon: Users }]
              : []),
            { id: "system", name: "System & audit", icon: Shield },
          ].map((n) => (
            <button
              key={n.id}
              className={page === n.id ? "selected" : ""}
              onClick={() => {
                setPage(n.id);
                if (window.innerWidth < 980) setSidebar(false);
              }}
            >
              <n.icon size={16} />
              {n.name}
              {n.id === "library" && docs !== null && (
                <span className="nav-count">{docs.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-label">COLLEGE TOOLS</div>
        <nav className="workflow-nav" aria-label="College tools">
          {modes
            .filter((m) => permitted(m.id, user, college))
            .map((m) => {
              const Icon = workflowIcons[m.id as keyof typeof workflowIcons];
              return (
                <button
                  className={
                    mode === m.id && page === "workspace" && !selected
                      ? "chosen"
                      : ""
                  }
                  key={m.id}
                  onClick={() => newTask(m.id)}
                >
                  <Icon size={14} />
                  {m.name}
                </button>
              );
            })}
        </nav>
        <div className="sidebar-label history-heading">
          <span>RECENT RUNS</span>
          <History size={12} />
        </div>
        <div className="history-search">
          <Search size={12} />
          <input
            aria-label="Search run history"
            placeholder="Find a run…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="history-list">
          {jobs === null ? (
            <Busy />
          ) : jobs.filter((j) =>
              `${j.name} ${j.workflow}`
                .toLowerCase()
                .includes(search.toLowerCase()),
            ).length === 0 ? (
            <p className="sidebar-empty">
              {search ? "No matching runs." : "Your runs will appear here."}
            </p>
          ) : (
            jobs
              .filter((j) =>
                `${j.name} ${j.workflow}`
                  .toLowerCase()
                  .includes(search.toLowerCase()),
              )
              .map((j) => (
                <button
                  key={j.id}
                  className={selected === j.id ? "selected" : ""}
                  onClick={() => openJob(j.id)}
                  title={`${j.name} · ${j.status}`}
                >
                  <span className={`status-dot ${j.status}`} />
                  <span>{j.name}</span>
                  <ChevronRight size={12} />
                </button>
              ))
          )}
        </div>
        <div className="sidebar-bottom">
          <button className="local-status" onClick={() => setPage("system")}>
            <span className={`status-dot ${system ? "completed" : "queued"}`} />
            <span>
              {system ? "Local backend connected" : "Connecting to backend"}
              <small>{generation?.id || "Configuration unavailable"}</small>
            </span>
          </button>
          <div className="account-row">
            <span className="avatar">
              {user.username.slice(0, 2).toUpperCase()}
            </span>
            <span>
              <strong>{user.username}</strong>
              <small>{user.role}</small>
            </span>
            <IconButton
              label="Sign out"
              onClick={() => {
                api("/auth/logout", { method: "POST" })
                  .then(logoutState)
                  .catch(fail);
              }}
            >
              <LogOut size={15} />
            </IconButton>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="row">
            <IconButton
              label="Toggle navigation"
              active={sidebar}
              onClick={() => setSidebar(!sidebar)}
            >
              <Menu size={17} />
            </IconButton>
            <span className="topbar-path">
              Campus<span>/</span>
              <strong>
                {page === "workspace"
                  ? "Workspace"
                  : page === "library"
                    ? "Library"
                    : page === "people"
                      ? "People"
                      : "System"}
              </strong>
            </span>
          </div>
          <div className="row topbar-actions">
            <button className="help-button" onClick={() => setHelp(true)}>
              Quick guide
            </button>
            {page === "workspace" && (
              <IconButton
                label="Toggle inspector"
                active={inspector}
                onClick={() => setInspector(!inspector)}
              >
                <PanelRight size={17} />
              </IconButton>
            )}
          </div>
        </header>
        {error && (
          <div className="error-banner" role="alert">
            <span>{error}</span>
            <IconButton label="Dismiss error" onClick={() => setError("")}>
              <X size={14} />
            </IconButton>
          </div>
        )}
        {notice && (
          <div className="notice-banner" role="status">
            <Check size={14} />
            {notice}
            <IconButton
              label="Dismiss notification"
              onClick={() => setNotice("")}
            >
              <X size={14} />
            </IconButton>
          </div>
        )}
        <main className="main-content">
          {page === "library" ? (
            <Knowledge
              docs={docs}
              user={user}
              refresh={() => void refresh()}
              fail={fail}
            />
          ) : page === "people" && user.role === "admin" ? (
            <People current={user} fail={fail} />
          ) : page === "system" ? (
            <SystemPanel
              system={system}
              user={user}
              refresh={() => void refresh()}
              fail={fail}
            />
          ) : (
            <div className={`workspace-content ${selected ? "has-run" : ""}`}>
              <div className="workspace-switch">
                <button
                  className="selected"
                  onClick={() => setPage("workspace")}
                >
                  <MessageSquare size={13} />
                  Workspace
                </button>
                <button onClick={() => setPage("library")}>
                  <Library size={13} />
                  Library
                </button>
              </div>
              {loadingJob ? (
                <div className="run-loading">
                  <Busy>Opening run…</Busy>
                </div>
              ) : selected && job ? (
                <Run
                  key={job.id}
                  job={job}
                  events={events}
                  user={user}
                  fail={fail}
                  onInspect={(t) => {
                    setTab(t);
                    setInspector(true);
                  }}
                  onRetry={(j) => {
                    openJob(j.id);
                    void refresh();
                  }}
                  onReview={() => {
                    refreshJob.current();
                    setNotice(
                      "Review note recorded. This does not issue an approval.",
                    );
                  }}
                />
              ) : (
                <div className="hero">
                  <span className="hero-emblem">
                    <GraduationCap size={28} />
                  </span>
                  <span className="eyebrow">
                    A LITTLE CLARITY. A LOT OF POSSIBILITY.
                  </span>
                  <h1>What will you create today?</h1>
                  <p>
                    Your college knowledge. Your local AI.
                    <br />A thoughtful space to learn, teach and get work done.
                  </p>
                  <div className="workflow-chips">
                    {modes
                      .filter((m) => permitted(m.id, user, college))
                      .map((m) => {
                        const Icon =
                          workflowIcons[m.id as keyof typeof workflowIcons];
                        return (
                          <button
                            key={m.id}
                            className={mode === m.id ? "selected" : ""}
                            onClick={() => setMode(m.id)}
                            title={m.description}
                          >
                            <Icon size={14} />
                            {m.name}
                          </button>
                        );
                      })}
                  </div>
                  <div className="mode-description">
                    {activeMode.description}
                  </div>
                </div>
              )}
              {!selected && (
                <Composer
                  key={user.id}
                  mode={mode}
                  setMode={setMode}
                  user={user}
                  college={college}
                  docs={docs}
                  refresh={() => void refresh()}
                  model={generation?.id}
                  onCreated={(j) => {
                    openJob(j.id);
                    setTab("activity");
                    if (window.innerWidth >= 1440) setInspector(true);
                  }}
                />
              )}
              {selected && !running && (
                <div className="next-task">
                  <button onClick={() => newTask()}>
                    <Plus size={14} />
                    Start another task
                  </button>
                </div>
              )}
              <footer className="workspace-footer">
                <Shield size={11} />
                Local assistance · Outputs require human review
              </footer>
            </div>
          )}
        </main>
      </div>
      {inspector && page === "workspace" && (
        <>
          <button
            className="panel-backdrop inspector-backdrop"
            aria-label="Close inspector"
            onClick={() => setInspector(false)}
          />
          <aside className="inspector">
            <Inspector
              job={job}
              events={events}
              docs={docs}
              tab={tab}
              setTab={setTab}
              close={() => setInspector(false)}
            />
          </aside>
        </>
      )}
      {help && (
        <Modal
          title="Your college workbench"
          onClose={() => setHelp(false)}
          wide
        >
          <div className="guide-grid">
            {modes
              .filter((m) => permitted(m.id, user, college))
              .map((m) => (
                <article key={m.id}>
                  <h3>{m.name}</h3>
                  <p>{m.description}.</p>
                </article>
              ))}
          </div>
          <ol className="guide-steps">
            <li>
              Add actual handbooks, syllabi or notices to the library. Review
              scans and publish them with the intended access.
            </li>
            <li>
              Choose a tool, select sources when needed, and describe your task.
              Use Settings for language, letter facts or code tests.
            </li>
            <li>
              Inspect the source evidence and recorded workflow. Download
              completed drafts from the Files tab.
            </li>
            <li>
              Review every output before use. Missing evidence is reported;
              official decisions and signatures remain with people.
            </li>
          </ol>
          <p className="notice">
            An empty library cannot answer college-specific questions. Study
            support can explicitly use general educational knowledge. System
            observations cover the backend process; they do not certify
            whole-network isolation.
          </p>
        </Modal>
      )}
    </div>
  );
}
