"use client";
import { useRef, useState } from "react";
import {
  ArrowUp,
  Plus,
  Files,
  SlidersHorizontal,
  X,
  Cpu,
  ChevronDown,
} from "lucide-react";
import { api, College, Doc, Job, message, User } from "../lib/api";
import { Badge, Busy, Modal } from "./ui";
import { UploadDialog } from "./Knowledge";
export const modes = [
  {
    id: "question",
    name: "Ask documents",
    description: "Answers with local source evidence",
  },
  {
    id: "study",
    name: "Study support",
    description: "Understand concepts and practise",
  },
  {
    id: "teaching",
    name: "Teaching material",
    description: "Draft from selected course sources",
  },
  {
    id: "letter",
    name: "Office drafts",
    description: "Letters from your supplied facts",
  },
  {
    id: "code",
    name: "Code lab",
    description: "Execute Python in the local sandbox",
  },
];
export function permitted(mode: string, user: User, college: College | null) {
  return (
    !!college?.workflows.includes(mode) &&
    (mode !== "teaching" || college.teaching_roles.includes(user.role)) &&
    (mode !== "letter" || college.letter_roles.includes(user.role))
  );
}
export function Composer({
  mode,
  setMode,
  user,
  college,
  docs,
  onCreated,
  refresh,
  model,
}: {
  mode: string;
  setMode: (x: string) => void;
  user: User;
  college: College | null;
  docs: Doc[] | null;
  onCreated: (job: Job) => void;
  refresh: () => void;
  model?: string;
}) {
  const [prompt, setPrompt] = useState(""),
    [expanded, setExpanded] = useState(false),
    [settings, setSettings] = useState(false),
    [picker, setPicker] = useState(false),
    [upload, setUpload] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [ids, setIds] = useState<string[]>([]),
    [grounding, setGrounding] = useState("local"),
    [language, setLanguage] = useState("English"),
    [cases, setCases] = useState("[]");
  const [facts, setFacts] = useState({
      recipient: "",
      subject: "",
      purpose: "",
    }),
    [additional, setAdditional] = useState("");
  const input = useRef<HTMLTextAreaElement>(null);
  const actualGrounding =
    mode === "study"
      ? grounding === "general"
        ? "general"
        : "local"
      : mode === "letter"
        ? grounding === "provided_facts"
          ? "provided_facts"
          : "local"
        : "local";
  const selected =
    docs?.filter((d) => ids.includes(d.id) && d.status !== "archived") || [];
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (prompt.trim().length < 10) {
      setError("Describe the task in at least 10 characters.");
      return;
    }
    if (mode === "teaching" && selected.length === 0) {
      setError("Select at least one course document for teaching material.");
      return;
    }
    setBusy(true);
    try {
      let body;
      if (mode === "code") {
        const parsed = JSON.parse(cases);
        if (
          !Array.isArray(parsed) ||
          parsed.length > 10 ||
          parsed.some(
            (c) =>
              !c ||
              typeof c.input !== "object" ||
              Array.isArray(c.input) ||
              c.input === null ||
              !Object.hasOwn(c, "expected"),
          )
        )
          throw new Error(
            "Supply a JSON array of up to 10 cases, each with an input object and expected output.",
          );
        body = { prompt: prompt.trim(), cases: parsed };
      } else {
        if (mode === "letter" && Object.values(facts).some((x) => !x.trim()))
          throw new Error(
            "Provide the recipient, subject and purpose in Task settings.",
          );
        body = {
          workflow: mode,
          prompt: prompt.trim(),
          grounding: actualGrounding,
          language,
          document_ids: selected.map((d) => d.id),
          facts:
            mode === "letter"
              ? {
                  ...facts,
                  ...(additional.trim()
                    ? { additional_facts: additional.trim() }
                    : {}),
                }
              : {},
        };
      }
      onCreated(
        await api<Job>(mode === "code" ? "/jobs/code" : "/jobs/college", {
          method: "POST",
          body: JSON.stringify(body),
        }),
      );
      setPrompt("");
      refresh();
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  const full =
    expanded ||
    !!prompt ||
    mode === "letter" ||
    mode === "code" ||
    selected.length > 0;
  return (
    <div className="composer-area">
      <form
        className={`composer ${full ? "expanded" : "collapsed"}`}
        onSubmit={submit}
        onFocus={() => setExpanded(true)}
        onBlur={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node))
            setExpanded(false);
        }}
      >
        <div className="composer-input">
          <textarea
            ref={input}
            aria-label="Describe your task"
            placeholder={
              mode === "code"
                ? "Describe the Python task and expected behavior…"
                : "Ask, learn, draft — using your local AI…"
            }
            maxLength={12000}
            rows={full ? 3 : 1}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                e.preventDefault();
                e.currentTarget.form?.requestSubmit();
              }
            }}
          />
          {!full && (
            <button
              className="send"
              disabled={busy || !college}
              aria-label="Run task"
            >
              <ArrowUp size={19} />
            </button>
          )}
        </div>
        {full && (
          <>
            <div className="selected-chips">
              {selected.map((d) => (
                <span className="source-chip" key={d.id}>
                  {d.name}
                  <button
                    type="button"
                    aria-label={`Remove ${d.name}`}
                    onClick={() => setIds(ids.filter((x) => x !== d.id))}
                  >
                    <X size={12} />
                  </button>
                </span>
              ))}
            </div>
            <div className="composer-tools">
              <div className="row">
                <button
                  className="tool-button"
                  type="button"
                  title="Upload a document"
                  aria-label="Upload a document"
                  disabled={user.role === "student"}
                  onClick={() => setUpload(true)}
                >
                  <Plus size={18} />
                </button>
                <button
                  className="tool-button"
                  type="button"
                  onClick={() => setPicker(true)}
                >
                  <Files size={15} />
                  <span>
                    Sources{selected.length ? ` · ${selected.length}` : ""}
                  </span>
                </button>
                <button
                  className="tool-button"
                  type="button"
                  onClick={() => setSettings(true)}
                >
                  <SlidersHorizontal size={15} />
                  <span>Settings</span>
                </button>
              </div>
              <div className="row">
                <select
                  className="mode-select"
                  aria-label="Workflow"
                  value={mode}
                  onChange={(e) => setMode(e.target.value)}
                >
                  {modes
                    .filter((m) => permitted(m.id, user, college))
                    .map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                </select>
                <button
                  className="send"
                  disabled={busy || !college}
                  aria-label="Run task"
                >
                  {busy ? <Busy /> : <ArrowUp size={19} />}
                </button>
              </div>
            </div>
          </>
        )}
      </form>
      <div className="composer-caption">
        <span>
          <Cpu size={11} />
          {mode === "code"
            ? "Isolated Python execution"
            : actualGrounding === "general"
              ? "General study knowledge · no college claims"
              : actualGrounding === "provided_facts"
                ? "Your supplied facts · draft only"
                : "Grounded in accessible local documents"}
        </span>
        <span title={model || "Configured when connected"}>
          {model ? "Local model · automatic routing" : "Awaiting configuration"}
        </span>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {mode === "letter" && (
        <button className="inline-link" onClick={() => setSettings(true)}>
          Set recipient, subject and purpose <ChevronDown size={12} />
        </button>
      )}
      {mode === "code" && (
        <button className="inline-link" onClick={() => setSettings(true)}>
          Configure correctness tests ·{" "}
          {cases.trim() === "[]" ? "none supplied" : "custom cases"}
        </button>
      )}
      {picker && (
        <Modal title="Choose local sources" onClose={() => setPicker(false)}>
          <p className="muted">
            With no selection, the workbench searches all your accessible
            sources. Teaching tasks require a selection.
          </p>
          {docs === null ? (
            <Busy />
          ) : docs.filter((d) => d.status !== "archived").length === 0 ? (
            <p>
              No accessible documents. Ask an administrator to publish course
              material.
            </p>
          ) : (
            <div className="source-picker">
              {docs
                .filter((d) => d.status !== "archived")
                .map((d) => (
                  <label className="check source-choice" key={d.id}>
                    <input
                      type="checkbox"
                      checked={ids.includes(d.id)}
                      disabled={!ids.includes(d.id) && ids.length >= 20}
                      onChange={(e) =>
                        setIds(
                          e.target.checked
                            ? [...ids, d.id]
                            : ids.filter((x) => x !== d.id),
                        )
                      }
                    />
                    <span>
                      <strong>{d.name}</strong>
                      <small>
                        {d.status} · {d.audience}
                        {d.course ? ` · ${d.course}` : ""}
                      </small>
                    </span>
                  </label>
                ))}
            </div>
          )}
          <button className="primary" onClick={() => setPicker(false)}>
            Use selected sources
          </button>
        </Modal>
      )}
      {settings && (
        <Modal title="Task settings" onClose={() => setSettings(false)}>
          <label>
            Workflow
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              {modes
                .filter((m) => permitted(m.id, user, college))
                .map((m) => (
                  <option value={m.id} key={m.id}>
                    {m.name}
                  </option>
                ))}
            </select>
          </label>
          {mode !== "code" && (
            <label>
              Output language
              <input
                value={language}
                minLength={2}
                maxLength={80}
                onChange={(e) => setLanguage(e.target.value)}
              />
            </label>
          )}
          {(mode === "study" || mode === "letter") && (
            <label>
              Evidence basis
              <select
                value={actualGrounding}
                onChange={(e) => setGrounding(e.target.value)}
              >
                <option value="local">Local documents</option>
                {mode === "study" ? (
                  <option value="general">General educational knowledge</option>
                ) : (
                  <option value="provided_facts">Only facts I provide</option>
                )}
              </select>
            </label>
          )}
          {mode === "letter" && (
            <>
              {(["recipient", "subject", "purpose"] as const).map((key) => (
                <label key={key}>
                  {key}
                  <input
                    value={facts[key]}
                    onChange={(e) =>
                      setFacts({ ...facts, [key]: e.target.value })
                    }
                  />
                </label>
              ))}
              <label>
                Additional verified facts
                <textarea
                  rows={4}
                  value={additional}
                  onChange={(e) => setAdditional(e.target.value)}
                />
              </label>
              <p className="notice">
                Supply actual names, dates and context. The system drafts a
                letter for human review; it does not issue an official letter or
                signature.
              </p>
            </>
          )}
          {mode === "code" && (
            <>
              <label>
                Test cases (JSON)
                <textarea
                  className="mono"
                  rows={8}
                  value={cases}
                  onChange={(e) => setCases(e.target.value)}
                  spellCheck={false}
                />
              </label>
              <p className="muted">
                Each case needs an <code>input</code> object and{" "}
                <code>expected</code> JSON value. Use [] to execute without
                correctness tests. Passing supplied cases does not prove general
                correctness.
              </p>
            </>
          )}
          <button className="primary" onClick={() => setSettings(false)}>
            Done
          </button>
        </Modal>
      )}
      {upload && (
        <UploadDialog
          onClose={() => setUpload(false)}
          onUploaded={(d) => {
            setIds((x) => [...x, d.id].slice(0, 20));
            setUpload(false);
            refresh();
          }}
        />
      )}
    </div>
  );
}
