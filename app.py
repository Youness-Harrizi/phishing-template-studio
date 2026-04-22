import os
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory, render_template, Response

from scorer import PersuasionScorer, ReadabilityScorer, RedFlagDetector
import exporter as exp
from pretext import generate_pretext

app = Flask(__name__, static_folder="static", template_folder="templates")
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "phishing_studio.db")

_persuasion = PersuasionScorer()
_readability = ReadabilityScorer()
_redflags = RedFlagDetector()

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS personas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    job_title TEXT DEFAULT '',
    department TEXT DEFAULT '',
    industry TEXT DEFAULT '',
    seniority TEXT DEFAULT 'mid',
    communication_style TEXT DEFAULT 'semi-formal',
    language TEXT DEFAULT 'en',
    locale TEXT DEFAULT 'en-US',
    known_platforms TEXT DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'custom',
    persona_id TEXT DEFAULT '',
    subject_line TEXT DEFAULT '',
    body_html TEXT DEFAULT '',
    body_text TEXT DEFAULT '',
    signature_block TEXT DEFAULT '',
    tokens_used TEXT DEFAULT '[]',
    persuasion_score REAL DEFAULT 0,
    red_flags TEXT DEFAULT '[]',
    tags TEXT DEFAULT '[]',
    engagement_context TEXT DEFAULT '{}',
    is_favorite INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS versions (
    id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL,
    body_html TEXT DEFAULT '',
    body_text TEXT DEFAULT '',
    subject_line TEXT DEFAULT '',
    note TEXT DEFAULT '',
    saved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL,
    export_format TEXT NOT NULL,
    exported_at TEXT NOT NULL,
    engagement_context TEXT DEFAULT '{}'
);
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript(DDL)
    conn.commit()
    conn.close()


def row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    for key in ("known_platforms", "tokens_used", "red_flags", "tags"):
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                d[key] = []
    for key in ("engagement_context",):
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                d[key] = {}
    if "is_favorite" in d:
        d["is_favorite"] = bool(d["is_favorite"])
    return d


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def new_id():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_tokens(html: str, text: str) -> list:
    import re
    found = set(re.findall(r"\{\{(\w+)\}\}", html + " " + text))
    return sorted(found)


def score_template(body_html: str, body_text: str, subject: str) -> tuple:
    combined = f"{subject} {body_text}"
    ps = _persuasion.score(combined)
    rs = _readability.score(body_text)
    rf = _redflags.detect(subject, body_html, body_text)
    return ps, rs, rf


# ---------------------------------------------------------------------------
# Routes — SPA
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Personas API
# ---------------------------------------------------------------------------

@app.route("/api/personas", methods=["GET"])
def list_personas():
    conn = get_db()
    rows = conn.execute("SELECT * FROM personas ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/api/personas", methods=["POST"])
def create_persona():
    data = request.get_json(force=True)
    pid = new_id()
    now = now_iso()
    conn = get_db()
    conn.execute(
        """INSERT INTO personas
           (id,name,job_title,department,industry,seniority,communication_style,
            language,locale,known_platforms,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            pid,
            data.get("name", "Unnamed Persona"),
            data.get("job_title", ""),
            data.get("department", ""),
            data.get("industry", ""),
            data.get("seniority", "mid"),
            data.get("communication_style", "semi-formal"),
            data.get("language", "en"),
            data.get("locale", "en-US"),
            json.dumps(data.get("known_platforms", [])),
            now,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM personas WHERE id=?", (pid,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row)), 201


@app.route("/api/personas/<pid>", methods=["GET"])
def get_persona(pid):
    conn = get_db()
    row = conn.execute("SELECT * FROM personas WHERE id=?", (pid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(row_to_dict(row))


@app.route("/api/personas/<pid>", methods=["PUT"])
def update_persona(pid):
    data = request.get_json(force=True)
    conn = get_db()
    conn.execute(
        """UPDATE personas SET
           name=?,job_title=?,department=?,industry=?,seniority=?,
           communication_style=?,language=?,locale=?,known_platforms=?
           WHERE id=?""",
        (
            data.get("name", ""),
            data.get("job_title", ""),
            data.get("department", ""),
            data.get("industry", ""),
            data.get("seniority", "mid"),
            data.get("communication_style", "semi-formal"),
            data.get("language", "en"),
            data.get("locale", "en-US"),
            json.dumps(data.get("known_platforms", [])),
            pid,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM personas WHERE id=?", (pid,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row))


@app.route("/api/personas/<pid>", methods=["DELETE"])
def delete_persona(pid):
    conn = get_db()
    conn.execute("DELETE FROM personas WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": pid})


# ---------------------------------------------------------------------------
# Templates API
# ---------------------------------------------------------------------------

@app.route("/api/templates", methods=["GET"])
def list_templates():
    q = request.args.get("q", "").lower()
    category = request.args.get("category", "")
    sort = request.args.get("sort", "updated_at")
    sort_map = {"updated_at": "updated_at", "created_at": "created_at",
                "score": "persuasion_score", "name": "name"}
    order_col = sort_map.get(sort, "updated_at")
    conn = get_db()
    rows = conn.execute(
        f"SELECT * FROM templates ORDER BY {order_col} DESC"
    ).fetchall()
    conn.close()
    result = [row_to_dict(r) for r in rows]
    if q:
        result = [
            r for r in result
            if q in r.get("name", "").lower()
            or q in r.get("description", "").lower()
            or any(q in t.lower() for t in r.get("tags", []))
            or q in r.get("body_text", "").lower()
        ]
    if category:
        result = [r for r in result if r.get("category") == category]
    return jsonify(result)


@app.route("/api/templates", methods=["POST"])
def create_template():
    data = request.get_json(force=True)
    tid = new_id()
    now = now_iso()
    body_html = data.get("body_html", "")
    body_text = data.get("body_text", "")
    subject = data.get("subject_line", "")
    ps, rs, rf = score_template(body_html, body_text, subject)
    tokens = extract_tokens(body_html, body_text)
    conn = get_db()
    conn.execute(
        """INSERT INTO templates
           (id,name,description,category,persona_id,subject_line,body_html,body_text,
            signature_block,tokens_used,persuasion_score,red_flags,tags,
            engagement_context,is_favorite,created_at,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            tid,
            data.get("name", "Untitled Template"),
            data.get("description", ""),
            data.get("category", "custom"),
            data.get("persona_id", ""),
            subject,
            body_html,
            body_text,
            data.get("signature_block", ""),
            json.dumps(tokens),
            ps["overall"],
            json.dumps(rf),
            json.dumps(data.get("tags", [])),
            json.dumps(data.get("engagement_context", {})),
            0,
            now,
            now,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM templates WHERE id=?", (tid,)).fetchone()
    conn.close()
    d = row_to_dict(row)
    d["persuasion_details"] = ps
    d["readability"] = rs
    return jsonify(d), 201


@app.route("/api/templates/<tid>", methods=["GET"])
def get_template(tid):
    conn = get_db()
    row = conn.execute("SELECT * FROM templates WHERE id=?", (tid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    d = row_to_dict(row)
    ps, rs, rf = score_template(d["body_html"], d["body_text"], d["subject_line"])
    d["persuasion_details"] = ps
    d["readability"] = rs
    return jsonify(d)


@app.route("/api/templates/<tid>", methods=["PUT"])
def update_template(tid):
    data = request.get_json(force=True)
    now = now_iso()
    body_html = data.get("body_html", "")
    body_text = data.get("body_text", "")
    subject = data.get("subject_line", "")
    ps, rs, rf = score_template(body_html, body_text, subject)
    tokens = extract_tokens(body_html, body_text)
    conn = get_db()
    conn.execute(
        """UPDATE templates SET
           name=?,description=?,category=?,persona_id=?,subject_line=?,
           body_html=?,body_text=?,signature_block=?,tokens_used=?,
           persuasion_score=?,red_flags=?,tags=?,engagement_context=?,updated_at=?
           WHERE id=?""",
        (
            data.get("name", ""),
            data.get("description", ""),
            data.get("category", "custom"),
            data.get("persona_id", ""),
            subject,
            body_html,
            body_text,
            data.get("signature_block", ""),
            json.dumps(tokens),
            ps["overall"],
            json.dumps(rf),
            json.dumps(data.get("tags", [])),
            json.dumps(data.get("engagement_context", {})),
            now,
            tid,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM templates WHERE id=?", (tid,)).fetchone()
    conn.close()
    d = row_to_dict(row)
    d["persuasion_details"] = ps
    d["readability"] = rs
    return jsonify(d)


@app.route("/api/templates/<tid>", methods=["DELETE"])
def delete_template(tid):
    conn = get_db()
    conn.execute("DELETE FROM templates WHERE id=?", (tid,))
    conn.execute("DELETE FROM versions WHERE template_id=?", (tid,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": tid})


@app.route("/api/templates/<tid>/favorite", methods=["POST"])
def toggle_favorite(tid):
    conn = get_db()
    row = conn.execute("SELECT is_favorite FROM templates WHERE id=?", (tid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Not found"}), 404
    new_val = 0 if row["is_favorite"] else 1
    conn.execute("UPDATE templates SET is_favorite=? WHERE id=?", (new_val, tid))
    conn.commit()
    conn.close()
    return jsonify({"is_favorite": bool(new_val)})


@app.route("/api/templates/<tid>/duplicate", methods=["POST"])
def duplicate_template(tid):
    conn = get_db()
    row = conn.execute("SELECT * FROM templates WHERE id=?", (tid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Not found"}), 404
    d = row_to_dict(row)
    new_tid = new_id()
    now = now_iso()
    conn.execute(
        """INSERT INTO templates
           (id,name,description,category,persona_id,subject_line,body_html,body_text,
            signature_block,tokens_used,persuasion_score,red_flags,tags,
            engagement_context,is_favorite,created_at,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            new_tid,
            d["name"] + " (Copy)",
            d.get("description", ""),
            d.get("category", "custom"),
            d.get("persona_id", ""),
            d.get("subject_line", ""),
            d.get("body_html", ""),
            d.get("body_text", ""),
            d.get("signature_block", ""),
            json.dumps(d.get("tokens_used", [])),
            d.get("persuasion_score", 0),
            json.dumps(d.get("red_flags", [])),
            json.dumps(d.get("tags", [])),
            json.dumps(d.get("engagement_context", {})),
            0,
            now,
            now,
        ),
    )
    conn.commit()
    new_row = conn.execute("SELECT * FROM templates WHERE id=?", (new_tid,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(new_row)), 201


# ---------------------------------------------------------------------------
# Version history
# ---------------------------------------------------------------------------

@app.route("/api/templates/<tid>/versions", methods=["GET"])
def list_versions(tid):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM versions WHERE template_id=? ORDER BY saved_at DESC", (tid,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/templates/<tid>/versions", methods=["POST"])
def save_version(tid):
    data = request.get_json(force=True)
    conn = get_db()
    row = conn.execute("SELECT * FROM templates WHERE id=?", (tid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Template not found"}), 404
    t = row_to_dict(row)
    vid = new_id()
    conn.execute(
        "INSERT INTO versions (id,template_id,body_html,body_text,subject_line,note,saved_at) VALUES (?,?,?,?,?,?,?)",
        (
            vid, tid,
            t.get("body_html", ""),
            t.get("body_text", ""),
            t.get("subject_line", ""),
            data.get("note", ""),
            now_iso(),
        ),
    )
    conn.commit()
    ver = conn.execute("SELECT * FROM versions WHERE id=?", (vid,)).fetchone()
    conn.close()
    return jsonify(dict(ver)), 201


@app.route("/api/templates/<tid>/versions/<vid>/restore", methods=["POST"])
def restore_version(tid, vid):
    conn = get_db()
    ver = conn.execute("SELECT * FROM versions WHERE id=? AND template_id=?", (vid, tid)).fetchone()
    if not ver:
        conn.close()
        return jsonify({"error": "Version not found"}), 404
    v = dict(ver)
    now = now_iso()
    conn.execute(
        "UPDATE templates SET body_html=?,body_text=?,subject_line=?,updated_at=? WHERE id=?",
        (v["body_html"], v["body_text"], v["subject_line"], now, tid),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM templates WHERE id=?", (tid,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row))


# ---------------------------------------------------------------------------
# Scoring API
# ---------------------------------------------------------------------------

@app.route("/api/score", methods=["POST"])
def score_endpoint():
    data = request.get_json(force=True)
    body_html = data.get("body_html", "")
    body_text = data.get("body_text", "")
    subject = data.get("subject_line", "")
    ps = _persuasion.score(f"{subject} {body_text}")
    rs = _readability.score(body_text)
    rf = _redflags.detect(subject, body_html, body_text)
    return jsonify({"persuasion": ps, "readability": rs, "red_flags": rf})


# ---------------------------------------------------------------------------
# Pretext generator
# ---------------------------------------------------------------------------

@app.route("/api/pretext/generate", methods=["POST"])
def gen_pretext():
    data = request.get_json(force=True)
    category = data.get("category", "custom")
    persona_id = data.get("persona_id", "")
    custom_desc = data.get("custom_description", "")
    persona = {}
    if persona_id:
        conn = get_db()
        row = conn.execute("SELECT * FROM personas WHERE id=?", (persona_id,)).fetchone()
        conn.close()
        if row:
            persona = row_to_dict(row)
    result = generate_pretext(category, persona, custom_desc)
    return jsonify(result)


# ---------------------------------------------------------------------------
# A/B variants
# ---------------------------------------------------------------------------

@app.route("/api/templates/<tid>/variants", methods=["POST"])
def generate_variants(tid):
    conn = get_db()
    row = conn.execute("SELECT * FROM templates WHERE id=?", (tid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    t = row_to_dict(row)

    variants = []

    # Variant 1: Swap subject only — high urgency
    v1 = dict(t)
    v1["name"] = t["name"] + " [Variant: Urgent Subject]"
    v1["subject_line"] = "URGENT: " + t["subject_line"]
    v1["id"] = None
    variants.append(v1)

    # Variant 2: Short body (first 50 words)
    words = t.get("body_text", "").split()
    short_body = " ".join(words[:50]) + ("\n\n{{link}}" if len(words) > 50 else "")
    v2 = dict(t)
    v2["name"] = t["name"] + " [Variant: Short Version]"
    v2["body_text"] = short_body
    v2["body_html"] = f"<p>{short_body.replace(chr(10), '</p><p>')}</p>"
    v2["id"] = None
    variants.append(v2)

    # Variant 3: Authority-first rewrite (prepend authority line)
    authority_line = "<p><strong>This is a mandatory communication from the IT Security Team.</strong></p>\n"
    v3 = dict(t)
    v3["name"] = t["name"] + " [Variant: Authority-First]"
    v3["body_html"] = authority_line + t.get("body_html", "")
    v3["body_text"] = "This is a mandatory communication from the IT Security Team.\n\n" + t.get("body_text", "")
    v3["id"] = None
    variants.append(v3)

    return jsonify(variants)


# ---------------------------------------------------------------------------
# Export API
# ---------------------------------------------------------------------------

@app.route("/api/export/<tid>", methods=["POST"])
def export_template(tid):
    data = request.get_json(force=True)
    fmt = data.get("format", "raw_html")
    sender_name = data.get("sender_name", "IT Helpdesk")
    sender_email = data.get("sender_email", "helpdesk@corp.com")
    recipient = data.get("recipient", "test@example.com")

    conn = get_db()
    row = conn.execute("SELECT * FROM templates WHERE id=?", (tid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Not found"}), 404

    t = row_to_dict(row)
    ctx = t.get("engagement_context", {})
    if not isinstance(ctx, dict):
        ctx = {}

    # Merge override context from request
    ctx.update(data.get("engagement_context", {}))

    # Record campaign
    conn = get_db()
    conn.execute(
        "INSERT INTO campaigns (id,template_id,export_format,exported_at,engagement_context) VALUES (?,?,?,?,?)",
        (new_id(), tid, fmt, now_iso(), json.dumps(ctx)),
    )
    conn.commit()
    conn.close()

    dispatch = {
        "gophish": (exp.export_gophish, "application/json", f"{t['name']}_gophish.json"),
        "king_phisher": (exp.export_king_phisher, "application/json", f"{t['name']}_kingphisher.json"),
        "eml": (None, "message/rfc822", f"{t['name']}.eml"),
        "raw_html": (exp.export_raw_html, "text/html", f"{t['name']}.html"),
        "plain_text": (exp.export_plain_text, "text/plain", f"{t['name']}.txt"),
        "evilginx": (exp.export_evilginx, "text/plain", f"{t['name']}_evilginx.txt"),
        "pdf": (None, "application/pdf", f"{t['name']}_report.pdf"),
        "zip": (None, "application/zip", f"{t['name']}_export.zip"),
    }

    if fmt not in dispatch:
        return jsonify({"error": f"Unknown format: {fmt}"}), 400

    fn, mime, filename = dispatch[fmt]

    if fmt == "eml":
        content = exp.export_eml(t, ctx, sender_name, sender_email, recipient)
        return Response(content, mimetype=mime,
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    elif fmt == "pdf":
        content = exp.export_pdf(t, ctx)
        return Response(content, mimetype=mime,
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    elif fmt == "zip":
        content = exp.export_zip(t, ctx, sender_name, sender_email)
        return Response(content, mimetype=mime,
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    else:
        content = fn(t, ctx)
        return Response(content, mimetype=mime,
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@app.route("/api/stats", methods=["GET"])
def stats():
    conn = get_db()
    total_templates = conn.execute("SELECT COUNT(*) FROM templates").fetchone()[0]
    total_personas = conn.execute("SELECT COUNT(*) FROM personas").fetchone()[0]
    total_campaigns = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    avg_score = conn.execute(
        "SELECT AVG(persuasion_score) FROM templates"
    ).fetchone()[0] or 0
    recent = conn.execute(
        "SELECT id,name,category,persuasion_score,updated_at FROM templates ORDER BY updated_at DESC LIMIT 5"
    ).fetchall()
    conn.close()
    return jsonify({
        "total_templates": total_templates,
        "total_personas": total_personas,
        "total_campaigns": total_campaigns,
        "avg_score": round(avg_score, 1),
        "recent_templates": [dict(r) for r in recent],
    })


# ---------------------------------------------------------------------------
# Bulk export
# ---------------------------------------------------------------------------

@app.route("/api/export/bulk", methods=["POST"])
def bulk_export():
    import zipfile, io as _io
    data = request.get_json(force=True)
    ids = data.get("ids", [])
    fmt = data.get("format", "raw_html")
    ctx = data.get("engagement_context", {})

    conn = get_db()
    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for tid in ids:
            row = conn.execute("SELECT * FROM templates WHERE id=?", (tid,)).fetchone()
            if not row:
                continue
            t = row_to_dict(row)
            tctx = {**t.get("engagement_context", {}), **ctx}
            if fmt == "gophish":
                zf.writestr(f"{t['name']}_gophish.json", exp.export_gophish(t, tctx))
            elif fmt == "eml":
                zf.writestr(f"{t['name']}.eml", exp.export_eml(t, tctx, "Sender", "sender@corp.com"))
            elif fmt == "raw_html":
                zf.writestr(f"{t['name']}.html", exp.export_raw_html(t, tctx))
            else:
                zf.writestr(f"{t['name']}.txt", exp.export_plain_text(t, tctx))
    conn.close()
    return Response(buf.getvalue(), mimetype="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="bulk_export.zip"'})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    print("Phishing Template Studio — http://127.0.0.1:5000")
    print("For authorised red team engagements only.")
    app.run(debug=True, host="127.0.0.1", port=5000)
