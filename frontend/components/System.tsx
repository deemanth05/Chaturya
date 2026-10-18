"use client";
import { useEffect, useState } from "react";
import { ShieldCheck, Server, Activity, Ban, RefreshCw } from "lucide-react";
import { api, date, Event, System as SystemData, User } from "../lib/api";
import { Badge, Busy, Empty } from "./ui";
export function SystemPanel({
  system,
  user,
  refresh,
  fail,
}: {
  system: SystemData | null;
  user: User;
  refresh: () => void;
  fail: (e: unknown) => void;
}) {
  const [events, setEvents] = useState<Event[] | null>(null),
    [busy, setBusy] = useState(""),
    [probe, setProbe] = useState<Record<string, string>>({}),
    [check, setCheck] = useState(""),
    [auditLoading, setAuditLoading] = useState(false),
    [moreAudit, setMoreAudit] = useState(false);
  async function audit() {
    if (user.role === "admin") {
      try {
        setAuditLoading(true);
        const after = events?.at(-1)?.id || 0;
        const batch = await api<Event[]>(`/audit?after=${after}`);
        setEvents((previous) => [
          ...(previous || []),
          ...batch.filter(
            (item) => !previous?.some((old) => old.id === item.id),
          ),
        ]);
        setMoreAudit(batch.length === 500);
      } catch (e) {
        fail(e);
      } finally {
        setAuditLoading(false);
      }
    }
  }
  useEffect(() => {
    void audit();
  }, []);
  if (!system)
    return (
      <div className="page-content">
        <Busy>Loading local system…</Busy>
      </div>
    );
  const monitor = system.monitor;
  return (
    <section className="page-content">
      <div className="section-heading">
        <div>
          <span className="eyebrow">LOCAL OPERATIONS</span>
          <h1>System & audit</h1>
          <p>Live application observations and declared model configuration.</p>
        </div>
        <button
          onClick={() => {
            refresh();
            void audit();
          }}
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>
      <div className="stats-grid">
        <article className="stat">
          <Activity size={18} />
          <strong>{monitor.local_calls}</strong>
          <span>Recorded local calls</span>
        </article>
        <article className="stat">
          <Ban size={18} />
          <strong>{monitor.blocked_attempts}</strong>
          <span>Policy blocks recorded</span>
        </article>
        <article className="stat">
          <Server size={18} />
          <strong>
            {system.worker_limit} / {system.model_concurrency}
          </strong>
          <span>Job / model concurrency</span>
        </article>
      </div>
      <article className="panel">
        <div className="row spread">
          <h2>
            <ShieldCheck size={17} />
            Network observations
          </h2>
          <Badge>{monitor.visibility.replaceAll("_", " ")}</Badge>
        </div>
        <dl>
          <dt>External bytes</dt>
          <dd>
            {monitor.external_bytes === null
              ? "Not measured"
              : `${monitor.external_bytes} B`}
          </dd>
          <dt>Observation scope</dt>
          <dd>{monitor.scope.replaceAll("_", " ")}</dd>
          <dt>Enforcement</dt>
          <dd>{monitor.enforcement.replaceAll("_", " ")}</dd>
          <dt>Last sample</dt>
          <dd>{date(monitor.sampled_at)}</dd>
          <dt>Allowed model destinations</dt>
          <dd>
            {system.allowed_origins.map((x) => (
              <code key={x}>
                {x}
                <br />
              </code>
            ))}
          </dd>
        </dl>
        <p className="notice">{monitor.note}</p>
        {monitor.unexpected_connections.length > 0 && (
          <div className="error">
            Unexpected sampled connections:
            <pre>{JSON.stringify(monitor.unexpected_connections, null, 2)}</pre>
          </div>
        )}
        {user.role === "admin" && (
          <button
            disabled={busy === "check"}
            onClick={async () => {
              setBusy("check");
              try {
                const result = await api<{
                  blocked: boolean;
                  layer: string;
                  socket_attempted: boolean;
                  os_firewall_verified: boolean;
                }>("/system/blocked-check", { method: "POST" });
                setCheck(
                  result.blocked && !result.socket_attempted
                    ? "Blocked by application policy before any socket was opened. Operating-system firewall isolation was not tested."
                    : JSON.stringify(result),
                );
                refresh();
                await audit();
              } catch (e) {
                fail(e);
              } finally {
                setBusy("");
              }
            }}
          >
            <Ban size={14} />
            {busy === "check" ? "Checking…" : "Run blocked-call check"}
          </button>
        )}
        {check && <p role="status">{check}</p>}
      </article>
      <div className="section-heading compact">
        <div>
          <h2>Model configuration</h2>
          <p>
            Availability is checked on request. Registry entries do not confirm
            a model is loaded.
          </p>
        </div>
        <Badge>
          Laya {system.laya_configured ? "configured" : "not configured"}
        </Badge>
      </div>
      <div className="document-grid">
        {system.models.map((model) => (
          <article className="document-card" key={model.id}>
            <div className="row spread">
              <Server size={19} />
              <Badge tone={model.enabled ? "green" : ""}>
                {model.enabled ? "Enabled" : "Disabled"}
              </Badge>
            </div>
            <h3>{model.id}</h3>
            <div className="row wrap">
              {model.modalities.map((x) => (
                <Badge key={x}>{x}</Badge>
              ))}
            </div>
            {user.role === "admin" && model.enabled && (
              <button
                disabled={busy === model.id}
                onClick={async () => {
                  setBusy(model.id);
                  try {
                    const result = await api("/models/probe", {
                      method: "POST",
                      body: JSON.stringify({
                        model_id: model.id,
                        image: false,
                      }),
                    });
                    setProbe((p) => ({
                      ...p,
                      [model.id]: JSON.stringify(result),
                    }));
                    refresh();
                  } catch (e) {
                    fail(e);
                  } finally {
                    setBusy("");
                  }
                }}
              >
                {busy === model.id ? <Busy /> : "Check local availability"}
              </button>
            )}
            {probe[model.id] && <pre className="small">{probe[model.id]}</pre>}
          </article>
        ))}
      </div>
      {user.role === "admin" && (
        <article className="panel">
          <div className="row spread">
            <h2>Audit log</h2>
            <Badge>
              {events === null ? "Loading" : `${events.length} events returned`}
            </Badge>
          </div>
          <p className="muted">
            Retained application events, loaded in batches of up to 500. Load
            newer records or refresh to retrieve subsequent events. These counts
            describe loaded records, not the total audit history.
          </p>
          <button disabled={auditLoading} onClick={() => void audit()}>
            {auditLoading ? (
              <Busy />
            ) : moreAudit ? (
              "Load newer audit events"
            ) : (
              "Check for new audit events"
            )}
          </button>
          {events === null ? (
            <Busy />
          ) : events.length === 0 ? (
            <Empty title="No audit events" />
          ) : (
            <div className="audit-list">
              {events
                .slice()
                .reverse()
                .map((e) => (
                  <details key={e.id}>
                    <summary>
                      <span className="mono">#{e.id}</span>
                      <strong>{e.kind}</strong>
                      <time>{date(e.time)}</time>
                    </summary>
                    <pre>{JSON.stringify(e.payload, null, 2)}</pre>
                  </details>
                ))}
            </div>
          )}
        </article>
      )}
    </section>
  );
}
