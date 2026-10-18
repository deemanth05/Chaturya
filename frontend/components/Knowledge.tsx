"use client";
import { useEffect, useState } from "react";
import {
  Upload,
  Search,
  FileText,
  Download,
  Settings2,
  RefreshCw,
  BookOpen,
} from "lucide-react";
import { api, date, Doc, message, User } from "../lib/api";
import { Badge, Busy, Empty, Modal } from "./ui";
export function DocumentText({
  doc,
  onClose,
}: {
  doc: Doc;
  onClose: () => void;
}) {
  const [chunks, setChunks] = useState<
    { id: string; page: number; section: string; text: string }[] | null
  >(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api<{ id: string; page: number; section: string; text: string }[]>(
      `/knowledge/${doc.id}/chunks`,
    )
      .then((data) => {
        if (active) setChunks(data);
      })
      .catch((e) => {
        if (active) setError(message(e));
      });
    return () => {
      active = false;
    };
  }, [doc.id]);
  return (
    <Modal title={doc.name} onClose={onClose} wide>
      <div className="row wrap">
        <Badge>{doc.status}</Badge>
        <Badge>{doc.extraction}</Badge>
        <a className="button" href={`/api/knowledge/${doc.id}/download`}>
          <Download size={14} />
          Original file
        </a>
      </div>
      <p className="muted">
        Indexed transcript · Check scans against the original before publishing
        or relying on extracted values.
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!chunks && !error && <Busy />}
      {chunks?.map((c) => (
        <article className="transcript" key={c.id}>
          <span className="eyebrow">
            {c.page > 0 ? `Page ${c.page}` : c.section || "Unpaginated source"}
          </span>
          <pre>{c.text}</pre>
        </article>
      ))}
    </Modal>
  );
}
export function UploadDialog({
  onClose,
  onUploaded,
}: {
  onClose: () => void;
  onUploaded: (doc: Doc) => void;
}) {
  const [file, setFile] = useState<File | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [version, setVersion] = useState(""),
    [language, setLanguage] = useState("");
  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    if (file.size > 20 * 1024 * 1024) {
      setError("Choose a file smaller than 20 MB.");
      return;
    }
    setBusy(true);
    setError("");
    const body = new FormData();
    body.append("file", file);
    body.append(
      "metadata",
      JSON.stringify({
        audience: "private",
        status: "draft",
        version,
        language,
      }),
    );
    try {
      onUploaded(await api<Doc>("/knowledge", { method: "POST", body }));
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title="Add a college document"
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <form onSubmit={upload}>
        <label className="dropzone">
          <Upload size={28} />
          <strong>{file?.name || "Choose a real document"}</strong>
          <span>PDF, Word, text, Markdown or an image · up to 20 MB</span>
          <input
            type="file"
            required
            accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg"
            disabled={busy}
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </label>
        <div className="form-grid">
          <label>
            Version{" "}
            <input
              value={version}
              maxLength={100}
              onChange={(e) => setVersion(e.target.value)}
            />
          </label>
          <label>
            Document language{" "}
            <input
              value={language}
              maxLength={80}
              onChange={(e) => setLanguage(e.target.value)}
            />
          </label>
        </div>
        <p className="notice">
          Uploaded documents start as private drafts. Scanned pages use the
          local vision model and require transcript review before publication.
        </p>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="primary" disabled={busy || !file}>
          {busy ? <Busy>Extracting and indexing…</Busy> : "Upload and index"}
        </button>
        {busy && (
          <p className="muted">
            Keep this dialog open. Processing time depends on the document and
            model queue.
          </p>
        )}
      </form>
    </Modal>
  );
}
function AccessDialog({
  doc,
  onClose,
  onSaved,
}: {
  doc: Doc;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [meta, setMeta] = useState({
    audience: doc.audience,
    status: doc.status,
    department: doc.department || "",
    course: doc.course || "",
    version: doc.version || "",
    language: doc.language || "",
    transcript_verified: false,
  });
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <Modal title="Document access & publication" onClose={onClose}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            await api(`/knowledge/${doc.id}`, {
              method: "PATCH",
              body: JSON.stringify(meta),
            });
            onSaved();
            onClose();
          } catch (e) {
            setError(message(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        <p className="muted">{doc.name}</p>
        <div className="form-grid">
          <label>
            Audience
            <select
              value={meta.audience}
              onChange={(e) => setMeta({ ...meta, audience: e.target.value })}
            >
              {["private", "college", "faculty", "staff", "student"].map(
                (x) => (
                  <option key={x}>{x}</option>
                ),
              )}
            </select>
          </label>
          <label>
            Status
            <select
              value={meta.status}
              onChange={(e) => setMeta({ ...meta, status: e.target.value })}
            >
              {["draft", "published", "archived"].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          {(["department", "course", "version", "language"] as const).map(
            (key) => (
              <label key={key}>
                {key}
                <input
                  maxLength={key === "language" ? 80 : 100}
                  value={meta[key]}
                  onChange={(e) => setMeta({ ...meta, [key]: e.target.value })}
                />
              </label>
            ),
          )}
        </div>
        <p className="muted">
          Department and course restrictions require matching account
          memberships. Private documents remain visible only to their owner and
          administrators.
        </p>
        {doc.extraction === "vision_unverified" && (
          <label className="check">
            <input
              type="checkbox"
              checked={meta.transcript_verified}
              onChange={(e) =>
                setMeta({ ...meta, transcript_verified: e.target.checked })
              }
            />
            I compared the indexed transcript with the original and verified it.
          </label>
        )}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="primary" disabled={busy}>
          {busy ? <Busy /> : "Save access settings"}
        </button>
      </form>
    </Modal>
  );
}
export function Knowledge({
  docs,
  user,
  refresh,
  fail,
}: {
  docs: Doc[] | null;
  user: User;
  refresh: () => void;
  fail: (e: unknown) => void;
}) {
  const [search, setSearch] = useState(""),
    [upload, setUpload] = useState(false),
    [view, setView] = useState<Doc | null>(null),
    [edit, setEdit] = useState<Doc | null>(null),
    [busy, setBusy] = useState(false);
  const filtered = docs?.filter((d) =>
    `${d.name} ${d.department} ${d.course}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  return (
    <section className="page-content">
      <div className="section-heading">
        <div>
          <span className="eyebrow">YOUR LOCAL KNOWLEDGE</span>
          <h1>Knowledge library</h1>
          <p>Real sources, controlled access, traceable answers.</p>
        </div>
        {user.role !== "student" && (
          <button className="primary" onClick={() => setUpload(true)}>
            <Upload size={15} />
            Add document
          </button>
        )}
      </div>
      <div className="row wrap library-toolbar">
        <div className="search">
          <Search size={15} />
          <input
            aria-label="Search library"
            placeholder="Search documents, departments or courses"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        {user.role === "admin" && (
          <button
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                const result = await api("/knowledge/reindex-dense", {
                  method: "POST",
                });
                void result;
                refresh();
              } catch (e) {
                fail(e);
              } finally {
                setBusy(false);
              }
            }}
          >
            <RefreshCw size={14} className={busy ? "spin" : ""} />
            {busy ? "Indexing…" : "Rebuild dense index"}
          </button>
        )}
      </div>
      {docs === null ? (
        <Busy>Loading accessible documents…</Busy>
      ) : !filtered?.length ? (
        <Empty
          title={
            search
              ? "No matching documents"
              : "Your library is ready for real sources"
          }
        >
          Upload handbooks, syllabi, notices or course material. Nothing is
          prefilled.
        </Empty>
      ) : (
        <div className="document-grid">
          {filtered.map((d) => (
            <article className="document-card" key={d.id}>
              <div className="row spread">
                <span className="file-icon">
                  <FileText size={20} />
                </span>
                <Badge tone={d.status === "published" ? "green" : "amber"}>
                  {d.status}
                </Badge>
              </div>
              <h3>{d.name}</h3>
              <p>
                {[d.department, d.course, d.version && `v${d.version}`]
                  .filter(Boolean)
                  .join(" · ") || "No department or course specified"}
              </p>
              <div className="row wrap">
                <Badge>{d.audience}</Badge>
                <Badge>{d.chunks} indexed chunks</Badge>
                {d.extraction.startsWith("vision") && (
                  <Badge tone="amber">
                    {d.extraction === "vision_unverified"
                      ? "Transcript review needed"
                      : "Transcript reviewed"}
                  </Badge>
                )}
              </div>
              <span className="small muted">Added {date(d.created)}</span>
              <div className="card-actions">
                <button onClick={() => setView(d)}>
                  <BookOpen size={14} />
                  Read transcript
                </button>
                <a
                  className="icon-button"
                  title="Download original"
                  aria-label={`Download ${d.name}`}
                  href={`/api/knowledge/${d.id}/download`}
                >
                  <Download size={15} />
                </a>
                {user.role === "admin" && (
                  <button
                    className="icon-button"
                    aria-label={`Manage ${d.name}`}
                    onClick={() => setEdit(d)}
                  >
                    <Settings2 size={15} />
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
      {upload && (
        <UploadDialog
          onClose={() => setUpload(false)}
          onUploaded={() => {
            setUpload(false);
            refresh();
          }}
        />
      )}
      {view && <DocumentText doc={view} onClose={() => setView(null)} />}
      {edit && (
        <AccessDialog
          doc={edit}
          onClose={() => setEdit(null)}
          onSaved={refresh}
        />
      )}
    </section>
  );
}
