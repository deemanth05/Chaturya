"use client";
import { useState } from "react";
import {
  BookOpen,
  ChevronRight,
  Code2,
  FileText,
  PenLine,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { api, date, Event, Job, User } from "../lib/api";
import { Badge, Busy, Markdown, Modal } from "./ui";
import { modes } from "./Composer";
import { ThinkingOrbCanvas } from "./ThinkingOrb";
export function Run({
  job,
  events,
  user,
  fail,
  onInspect,
  onRetry,
  onReview,
}: {
  job: Job;
  events: Event[];
  user: User;
  fail: (e: unknown) => void;
  onInspect: (tab: string) => void;
  onRetry: (job: Job) => void;
  onReview: () => void;
}) {
  const [review, setReview] = useState(false),
    [note, setNote] = useState(""),
    [busy, setBusy] = useState(false);
  const result = job.state?.result,
    running = ["queued", "running"].includes(job.status);
  const step = events.filter((e) => e.kind === "step.started").at(-1)
    ?.payload.step;
  return (
    <article className="run">
      <div className="run-meta">
        <Badge
          tone={
            job.status === "completed"
              ? "green"
              : job.status === "failed" || job.status === "interrupted"
                ? "rose"
                : "blue"
          }
        >
          {job.status}
        </Badge>
        <span>
          {modes.find((m) => m.id === job.workflow)?.name || job.workflow}
        </span>
        <time>{date(job.created)}</time>
      </div>
      <div className="request">
        <span className="eyebrow">YOUR REQUEST</span>
        <h1>{job.state?.prompt || job.name}</h1>
        <div className="row wrap">
          <Badge>
            {job.state?.grounding?.replaceAll("_", " ") || "Sandbox"}
          </Badge>
          {job.state?.language && <Badge>{job.state.language}</Badge>}
        </div>
      </div>
      {running && (
        <div className="working">
          <ThinkingOrbCanvas size={44} />
          <div>
            <strong>
              {job.status === "queued"
                ? "Waiting for an available worker"
                : "Working with your local tools"}
            </strong>
            <p>
              {step
                ? `Current recorded step: ${String(step)}`
                : "The activity panel shows events as they arrive."}
            </p>
            <button
              className="inline-link"
              onClick={() => onInspect("activity")}
            >
              Follow live activity
              <ChevronRight size={13} />
            </button>
          </div>
        </div>
      )}
      {job.error && (
        <div className="error run-error" role="alert">
          {job.error}
        </div>
      )}
      {["failed", "interrupted"].includes(job.status) && (
        <button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              onRetry(
                await api<Job>(`/jobs/${job.id}/retry`, { method: "POST" }),
              );
            } catch (e) {
              fail(e);
            } finally {
              setBusy(false);
            }
          }}
        >
          <RefreshCw size={14} />
          {busy ? "Creating retry…" : "Retry as a new run"}
        </button>
      )}
      {result && (
        <div className="answer">
          <div className="answer-heading">
            <span className="brand-mark">
              <Sparkles size={16} />
            </span>
            <span>Chaturya</span>
            <Badge tone="amber">Review draft</Badge>
            <button className="inline-link" onClick={() => onInspect("files")}>
              <FileText size={13} />
              Files
            </button>
          </div>
          <h2>{result.title}</h2>
          {result.status === "insufficient_evidence" && (
            <p className="notice">
              The available evidence is insufficient. This run does not
              establish a college rule or decision.
            </p>
          )}
          {result.basis && <p className="muted">{result.basis}</p>}
          {result.warnings?.map((w, i) => (
            <p className="notice" key={i}>
              {w}
            </p>
          ))}
          {result.sections.map((s, i) => (
            <section className="answer-section" key={i}>
              <h3>{s.heading}</h3>
              <Markdown text={s.text} />
              {s.evidence?.length > 0 && (
                <details className="evidence">
                  <summary>Source evidence · {s.evidence.length}</summary>
                  {s.evidence.map((e, k) => {
                    const source = (
                      result.sources ||
                      job.state?.retrieval?.sources ||
                      []
                    ).find((x) => x.id === e.source_id);
                    return (
                      <div key={k}>
                        <button
                          className="inline-link"
                          onClick={() => onInspect("sources")}
                        >
                          {source?.name || "Source"}
                          {source?.page
                            ? ` · page ${source.page}`
                            : source?.section
                              ? ` · ${source.section}`
                              : ""}
                        </button>
                        <blockquote>{e.quote}</blockquote>
                      </div>
                    );
                  })}
                </details>
              )}
            </section>
          ))}
          {!!result.missing_information?.length && (
            <div className="notice">
              <strong>Information still needed</strong>
              <ul>
                {result.missing_information.map((x, i) => (
                  <li key={i}>{x}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="answer-actions">
            <button onClick={() => onInspect("sources")}>
              <BookOpen size={14} />
              Inspect evidence
            </button>
            <button onClick={() => onInspect("files")}>
              <FileText size={14} />
              Download draft
            </button>
            {["admin", "faculty", "staff"].includes(user.role) && (
              <button onClick={() => setReview(true)}>
                <PenLine size={14} />
                Record review
              </button>
            )}
          </div>
        </div>
      )}
      {job.workflow === "code" && job.state?.attempts && (
        <div className="answer">
          <h2>Sandbox execution</h2>
          <p className="notice">
            {job.state.verification === "passed_supplied_cases"
              ? "Passed the supplied test cases. This is limited to the cases you provided."
              : job.state.verification === "executed_without_correctness_tests"
                ? "Executed without correctness tests. Correctness has not been verified."
                : "Inspect each recorded attempt below."}
          </p>
          {job.state.attempts.map((a) => (
            <details
              className="code-attempt"
              key={a.attempt}
              open={a.status === "passed"}
            >
              <summary>
                Attempt {a.attempt}
                <Badge tone={a.status === "passed" ? "green" : "rose"}>
                  {a.status}
                </Badge>
              </summary>
              {a.error && <pre>{a.error}</pre>}
              {a.checks?.map((c, i) => (
                <div key={i}>
                  <span className="eyebrow">
                    CASE {c.case} · {c.latency_ms} ms
                  </span>
                  <pre>{JSON.stringify(c.output, null, 2)}</pre>
                </div>
              ))}
            </details>
          ))}
          {job.status === "completed" && (
            <button onClick={() => onInspect("files")}>
              <Code2 size={14} />
              Download Python source
            </button>
          )}
        </div>
      )}
      {job.reviews?.map((r, i) => (
        <div className="review-note" key={r.id || i}>
          <span className="eyebrow">
            REVIEW NOTE · {r.username} · {date(r.time)}
          </span>
          <p>{r.note}</p>
        </div>
      ))}
      {review && (
        <Modal title="Record a human review" onClose={() => setReview(false)}>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              try {
                await api(`/jobs/${job.id}/reviews`, {
                  method: "POST",
                  body: JSON.stringify({ note }),
                });
                setReview(false);
                setNote("");
                onReview();
              } catch (e) {
                fail(e);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Review note
              <textarea
                required
                minLength={5}
                maxLength={4000}
                rows={6}
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </label>
            <p className="notice">
              This records your comments in the audit history. It does not issue
              an approval or electronic signature.
            </p>
            <button className="primary" disabled={busy}>
              {busy ? <Busy /> : "Record review note"}
            </button>
          </form>
        </Modal>
      )}
    </article>
  );
}
