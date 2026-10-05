"""
Design tokens, CSS themes, and HTML styling components for the RAG Assistant Frontend.
"""
import textwrap

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg-main: #0B0F17;
    --bg-card: #131B2A;
    --bg-card-hover: #1E293B;
    --border-subtle: rgba(255, 255, 255, 0.08);
    --border-active: rgba(99, 102, 241, 0.4);
    --primary: #6366F1;
    --primary-gradient: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #EC4899 100%);
    --cyan-accent: #06B6D4;
    --text-main: #F8FAFC;
    --text-muted: #94A3B8;
    --success: #10B981;
    --warning: #F59E0B;
    --danger: #EF4444;
}

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--text-main);
}

.block-container {
    padding-top: 1.25rem !important;
    padding-bottom: 2rem !important;
    max-width: 1250px !important;
}

.rag-header {
    background: linear-gradient(180deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.4) 100%);
    border: 1px solid var(--border-subtle);
    backdrop-filter: blur(12px);
    border-radius: 14px;
    padding: 1.1rem 1.5rem;
    margin-bottom: 1.25rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
}

.rag-title {
    font-size: 1.4rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: var(--primary-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.rag-subtitle {
    font-size: 0.82rem;
    color: var(--text-muted);
    margin-top: 0.15rem;
    font-weight: 500;
}

.doc-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    transition: all 0.2s ease;
}
.doc-card:hover {
    border-color: rgba(99, 102, 241, 0.3);
    background: var(--bg-card-hover);
}

.kpi-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 0.85rem 1rem;
    transition: all 0.2s ease;
}
.kpi-card:hover {
    border-color: var(--border-active);
}
.kpi-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    font-weight: 600;
}
.kpi-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-main);
    margin-top: 0.2rem;
}

.badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.6rem;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.badge-green {
    background: rgba(16, 185, 129, 0.12);
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.25);
}
.badge-blue {
    background: rgba(99, 102, 241, 0.12);
    color: #818CF8;
    border: 1px solid rgba(99, 102, 241, 0.25);
}
.badge-amber {
    background: rgba(245, 158, 11, 0.12);
    color: #FBBF24;
    border: 1px solid rgba(245, 158, 11, 0.25);
}
.badge-red {
    background: rgba(239, 68, 68, 0.12);
    color: #F87171;
    border: 1px solid rgba(239, 68, 68, 0.25);
}

.citation-card {
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-left: 3px solid var(--primary);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-top: 0.4rem;
    margin-bottom: 0.4rem;
    font-size: 0.85rem;
}
.citation-card:hover {
    border-left-color: var(--cyan-accent);
    background: rgba(30, 41, 59, 0.8);
}
.citation-title {
    font-weight: 600;
    color: #A5B4FC;
    font-size: 0.8rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.35rem;
}
.citation-snippet {
    color: #CBD5E1;
    font-size: 0.78rem;
    line-height: 1.45;
    font-family: 'JetBrains Mono', monospace;
    white-space: pre-wrap;
    background: rgba(0, 0, 0, 0.3);
    padding: 0.45rem 0.65rem;
    border-radius: 4px;
}

.grounded-box {
    border-radius: 8px;
    padding: 0.55rem 0.8rem;
    font-size: 0.78rem;
    margin-top: 0.4rem;
    display: flex;
    align-items: center;
    gap: 0.45rem;
}
.grounded-supported {
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.2);
    color: #34D399;
}
.grounded-unsupported {
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.2);
    color: #F87171;
}

.sidebar-nav-header {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748B;
    font-weight: 700;
    margin-top: 1rem;
    margin-bottom: 0.35rem;
}

button[kind="primary"] {
    background: var(--primary-gradient) !important;
    border: none !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3) !important;
    transition: all 0.2s ease !important;
}
button[kind="primary"]:hover {
    box-shadow: 0 6px 18px rgba(99, 102, 241, 0.45) !important;
    transform: translateY(-1px) !important;
}
button[kind="secondary"] {
    background: rgba(30, 41, 59, 0.4) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    color: #CBD5E1 !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
}
button[kind="secondary"]:hover {
    background: rgba(99, 102, 241, 0.12) !important;
    border-color: rgba(99, 102, 241, 0.3) !important;
    color: #F8FAFC !important;
}
</style>
"""


def render_header(
    app_name: str = "Production RAG Assistant",
    subtitle: str = "Chat with your documents",
    workspace_name: str | None = None,
    backend_status: str = "ok",
    mode_label: str = "Connected",
) -> str:
    status_badge = (
        f'<span class="badge badge-green">● {mode_label}</span>'
        if backend_status == "ok"
        else '<span class="badge badge-amber">● Connecting...</span>'
    )
    ws_badge = f'<span class="badge badge-blue">📁 {workspace_name}</span>' if workspace_name else ""

    html = f"""<div class="rag-header">
<div>
<div class="rag-title">⚡ {app_name}</div>
<div class="rag-subtitle">{subtitle}</div>
</div>
<div style="display: flex; align-items: center; gap: 0.6rem;">
{ws_badge}
{status_badge}
</div>
</div>"""
    return textwrap.dedent(html)


def render_groundedness_badge(groundedness: dict) -> str:
    if not groundedness:
        return ""
    supported = groundedness.get("supported", False)
    method = groundedness.get("method", "lexical_overlap")
    unsupported = groundedness.get("unsupported_sentences", [])

    if supported:
        html = f"""<div class="grounded-box grounded-supported">
<span>🛡️</span>
<div><b>100% Citation Grounded</b> — Verified against context ({method})</div>
</div>"""
    else:
        unsupported_html = ""
        if unsupported:
            unsupported_html = "<br><small>Flagged: " + " | ".join(unsupported[:2]) + "</small>"
        html = f"""<div class="grounded-box grounded-unsupported">
<span>⚠️</span>
<div><b>Potential Hallucination Detected</b> — Some claims lack direct context support ({method}){unsupported_html}</div>
</div>"""
    return textwrap.dedent(html)


def render_citation_card(idx: int, citation: dict) -> str:
    filename = citation.get("filename", "document")
    score = citation.get("score", 0.0)
    score_pct = f"{score * 100:.1f}%" if score <= 1.0 else f"{score:.2f}"
    snippet = citation.get("snippet", "")
    chunk_id = str(citation.get("chunk_id", ""))[:8]

    html = f"""<div class="citation-card">
<div class="citation-title">
<span>[{idx}] 📄 <b>{filename}</b> (chunk: <code>{chunk_id}</code>)</span>
<span class="badge badge-blue">Relevance: {score_pct}</span>
</div>
<div class="citation-snippet">{snippet}</div>
</div>"""
    return textwrap.dedent(html)
