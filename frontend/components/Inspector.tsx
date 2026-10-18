"use client";
import { useState } from "react";
import {
  Download,
  Files,
  Activity,
  Quote,
  Cpu,
  X,
  ArrowUpRight,
} from "lucide-react";
import { date, Doc, Event, Job, Source } from "../lib/api";
import { Badge, Empty, IconButton } from "./ui";
import { DocumentText } from "./Knowledge";
export function Inspector({
  job,
  events,
  docs,
  tab,
  setTab,
  close,
}: {
  job: Job | null;
  events: Event[];
  docs: Doc[] | null;
  tab: string;
  setTab: (tab: string) => void;
  close: () => void;
}) {
  const [view, setView] = useState<Doc | null>(null);
  const sources: Source[] =
    job?.state?.result?.sources || job?.state?.retrieval?.sources || [];
  return (
    <>
      <div className="inspector-heading">
        <strong>Inspector</strong>
        <IconButton label="Close inspector" onClick={close}>
          <X size={16} />
        </IconButton>
      </div>
      <nav className="inspector-tabs" aria-label="Inspector tabs">
        {[
          {
            id: "sources",
            label: "Sources",
            icon: Quote,
            count: sources.length,
          },
          {
            id: "files",
            label: "Files",
            icon: Files,
            count: job?.status === "completed" && job.state?.artifact ? 1 : 0,
          },
          {
            id: "activity",
            label: "Activity",
            icon: Activity,
            count: events.length,
          },
        ].map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? "selected" : ""}
            onClick={() => setTab(t.id)}
          >
            <t.icon size={13} />
            {t.label}
            <span>{t.count}</span>
          </button>
        ))}
      </nav>
      <div className="inspector-body">
        {!job ? (
          <Empty title="Your work, in view">
            Select a run to inspect its sources, generated files and actual
            execution steps.
          </Empty>
        ) : tab === "sources" ? (
          <>
            {sources.length === 0 ? (
              <Empty title="No retrieved sources">
                {job.state?.grounding === "general"
                  ? "This run uses general study knowledge."
                  : job.state?.grounding === "provided_facts"
                    ? "This draft uses the facts supplied in the request."
                    : "Sources appear after the retrieval step."}
              </Empty>
            ) : (
              sources.map((s, i) => (
                <article className="source-card" key={s.id}>
                  <span className="eyebrow">SOURCE {i + 1}</span>
                  <h3>{s.name}</h3>
                  <p>
                    {s.page > 0
                      ? `Page ${s.page}`
                      : s.section || "Unpaginated source"}
                  </p>
                  <div className="row wrap">
                    <Badge>{s.status || "Source"}</Badge>
                    {s.version && <Badge>v{s.version}</Badge>}
                  </div>
                  <blockquote>{s.text}</blockquote>
                  <div className="row wrap">
                    <a
                      className="inline-link"
                      href={`/api/knowledge/${s.document_id}/download`}
                    >
                      Original
                      <ArrowUpRight size={12} />
                    </a>
                    {docs?.find((d) => d.id === s.document_id) && (
                      <button
                        className="inline-link"
                        onClick={() =>
                          setView(docs.find((d) => d.id === s.document_id)!)
                        }
                      >
                        Indexed text
                      </button>
                    )}
                  </div>
                </article>
              ))
            )}
          </>
        ) : tab === "files" ? (
          job.status === "completed" && job.state?.artifact ? (
            <article className="source-card">
              <Files size={24} />
              <h3>{job.state.artifact}</h3>
              <p>
                {job.workflow === "code"
                  ? "Generated Python source"
                  : "Human review required · no approval verdict"}
              </p>
              <div className="download-stack">
                {(job.workflow === "code"
                  ? ["py"]
                  : ["docx", "md", "json"]
                ).map((format) => (
                  <a
                    className="button"
                    key={format}
                    href={`/api/jobs/${job.id}/download?format=${format === "py" ? "docx" : format}`}
                  >
                    <Download size={14} />
                    Download .{format}
                  </a>
                ))}
              </div>
            </article>
          ) : (
            <Empty title="No generated files yet">
              Files become available when a run completes successfully.
            </Empty>
          )
        ) : (
          <>
            {job.state?.route && (
              <article className="source-card">
                <span className="eyebrow">ROUTING DECISION</span>
                <h3>
                  <Cpu size={14} />
                  {job.state.route.model}
                </h3>
                <Badge>{job.state.route.method}</Badge>
                <p>{job.state.route.reason}</p>
                {job.state.route.probabilities && (
                  <pre>
                    {JSON.stringify(job.state.route.probabilities, null, 2)}
                  </pre>
                )}
              </article>
            )}
            {events.length === 0 ? (
              <Empty title="Waiting for events" />
            ) : (
              <ol className="trace">
                {events.map((e) => (
                  <li key={e.id}>
                    <span
                      className={`trace-dot ${e.kind.includes("failed") ? "failed" : ""}`}
                    />
                    <div>
                      <strong>
                        {e.kind.replaceAll(".", " · ").replaceAll("_", " ")}
                      </strong>
                      <time>{date(e.time)}</time>
                      <details>
                        <summary>Event details</summary>
                        <pre>{JSON.stringify(e.payload, null, 2)}</pre>
                      </details>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
      </div>
      {view && <DocumentText doc={view} onClose={() => setView(null)} />}
    </>
  );
}
