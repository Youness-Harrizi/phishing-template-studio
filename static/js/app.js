/* =============================================================
   Phishing Template Studio — Single-Page Application
   ============================================================= */

'use strict';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const State = {
  view: 'dashboard',
  personas: [],
  templates: [],
  currentTemplate: null,
  currentPersona: null,
  editorMode: 'html',          // 'html' | 'text'
  previewMode: 'desktop',      // 'desktop' | 'mobile' | 'plain' | 'dark'
  scoreData: null,
  pretext: null,
  selectedTemplates: new Set(),
  debounceTimer: null,
  tokenValues: {               // sample values for preview substitution
    first_name: 'Sarah',
    last_name: 'Mitchell',
    company: 'Acme Corp',
    department: 'Finance',
    sender_name: 'John Davies',
    sender_title: 'IT Security Manager',
    link: 'https://portal.corp-secure.com/verify?token=abc123',
    deadline: 'Friday, 25 April 2026 at 17:00',
    ticket_number: 'INC-48291',
    attachment: 'Q1_Report.pdf',
  },
};

const KNOWN_TOKENS = [
  'first_name','last_name','company','department','sender_name',
  'sender_title','link','deadline','ticket_number','attachment',
  'position','manager_name','portal_url','expiry_date',
];

const CATEGORIES = [
  { id: 'it_helpdesk',             label: 'IT / Helpdesk',             badge: 'badge-it' },
  { id: 'hr_payroll',              label: 'HR / Payroll',              badge: 'badge-hr' },
  { id: 'finance_accounting',      label: 'Finance / Accounting',      badge: 'badge-finance' },
  { id: 'executive_impersonation', label: 'Executive Impersonation',   badge: 'badge-exec' },
  { id: 'vendor_supplier',         label: 'Vendor / Supplier',         badge: 'badge-vendor' },
  { id: 'security_alert',          label: 'Security Alert',            badge: 'badge-security' },
  { id: 'collaboration_platform',  label: 'Collaboration Platform',    badge: 'badge-collab' },
  { id: 'custom',                  label: 'Custom',                    badge: 'badge-custom' },
];

const EXPORT_FORMATS = [
  { id: 'gophish',      name: 'GoPhish JSON',       desc: 'GoPhish API-compatible campaign template' },
  { id: 'king_phisher', name: 'King Phisher',        desc: 'King Phisher compatible JSON format' },
  { id: 'evilginx',     name: 'Evilginx2 Companion', desc: 'Companion email for Evilginx2 phishlets' },
  { id: 'eml',          name: 'EML File',             desc: 'RFC 2822 .eml — load in Thunderbird/Outlook' },
  { id: 'raw_html',     name: 'Raw HTML',             desc: 'Self-contained HTML with inline styles' },
  { id: 'plain_text',   name: 'Plain Text',           desc: 'Plaintext .txt for simple delivery' },
  { id: 'pdf',          name: 'PDF Report',           desc: 'Printable PDF for client documentation' },
  { id: 'zip',          name: 'Full ZIP Archive',     desc: 'All formats bundled for engagement handoff' },
];

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------
const API = {
  async get(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async post(url, body) {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async put(url, body) {
    const r = await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async del(url) {
    const r = await fetch(url, { method: 'DELETE' });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async download(url, body, filename) {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r.ok) { toast('Export failed: ' + await r.text(), 'error'); return; }
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  },
};

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
function $(sel, ctx = document) { return ctx.querySelector(sel); }
function $$(sel, ctx = document) { return [...ctx.querySelectorAll(sel)]; }
function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const c of children) {
    if (c == null) continue;
    e.append(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return e;
}

function toast(msg, type = 'info', duration = 3000) {
  const t = el('div', { class: `toast toast-${type}` }, msg);
  $('#toasts').appendChild(t);
  setTimeout(() => t.remove(), duration);
}

function formatDate(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }); }
  catch { return iso.slice(0, 10); }
}

function scoreColor(score) {
  if (score >= 7) return '#4caf81';
  if (score >= 4) return '#f5a623';
  return '#e84d4d';
}

function categoryBadge(catId) {
  const cat = CATEGORIES.find(c => c.id === catId) || CATEGORIES[CATEGORIES.length - 1];
  return `<span class="badge ${cat.badge}">${cat.label}</span>`;
}

function substituteTokens(text) {
  return text.replace(/\{\{(\w+)\}\}/g, (_, token) => State.tokenValues[token] || `{{${token}}}`);
}

function buildGauge(score, size = 60, stroke = 5) {
  const r = (size / 2) - stroke;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 10) * circ;
  const color = scoreColor(score);
  return `
    <div class="gauge-ring" style="width:${size}px;height:${size}px">
      <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
        <circle class="gauge-bg" cx="${size/2}" cy="${size/2}" r="${r}"/>
        <circle class="gauge-fill" cx="${size/2}" cy="${size/2}" r="${r}"
          stroke="${color}"
          stroke-dasharray="${circ}"
          stroke-dashoffset="${offset}"/>
      </svg>
      <div class="gauge-number" style="color:${color}">${score.toFixed(1)}</div>
    </div>`;
}

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------
function navigate(view, opts = {}) {
  $$('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.view === view));
  $$('.view').forEach(v => v.classList.add('hidden'));
  $(`#view-${view}`).classList.remove('hidden');
  State.view = view;
  if (view === 'dashboard') renderDashboard();
  else if (view === 'editor')   renderEditor(opts.template);
  else if (view === 'library')  renderLibrary();
  else if (view === 'personas') renderPersonas();
}

document.addEventListener('DOMContentLoaded', () => {
  // Nav
  $$('.nav-item').forEach(n => n.addEventListener('click', e => {
    e.preventDefault();
    navigate(n.dataset.view);
  }));

  // Modal close
  $('#modal-overlay').addEventListener('click', e => {
    if (e.target === $('#modal-overlay')) closeModal();
  });

  loadAll().then(() => navigate('dashboard'));
});

async function loadAll() {
  [State.personas, State.templates] = await Promise.all([
    API.get('/api/personas'),
    API.get('/api/templates'),
  ]);
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------
function openModal(htmlContent) {
  $('#modal-box').innerHTML = htmlContent;
  $('#modal-overlay').classList.remove('hidden');
}
function closeModal() {
  $('#modal-overlay').classList.add('hidden');
  $('#modal-box').innerHTML = '';
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
async function renderDashboard() {
  const view = $('#view-dashboard');
  view.innerHTML = '<div class="muted small">Loading…</div>';
  const stats = await API.get('/api/stats');
  State.templates = await API.get('/api/templates');

  view.innerHTML = `
    <div class="section-header">
      <h1 class="page-title">Dashboard</h1>
      <button class="btn btn-primary" id="dash-new-btn">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        New Template
      </button>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value stat-accent">${stats.total_templates}</div>
        <div class="stat-label">Templates</div>
      </div>
      <div class="stat-card">
        <div class="stat-value stat-blue">${stats.total_personas}</div>
        <div class="stat-label">Personas</div>
      </div>
      <div class="stat-card">
        <div class="stat-value stat-green">${stats.total_campaigns}</div>
        <div class="stat-label">Exports</div>
      </div>
      <div class="stat-card">
        <div class="stat-value stat-yellow">${stats.avg_score || '—'}</div>
        <div class="stat-label">Avg Persuasion Score</div>
      </div>
    </div>

    <div class="dashboard-grid">
      <div class="card">
        <div class="card-header">
          <h2>Recent Templates</h2>
          <button class="btn btn-ghost btn-sm" id="dash-view-all">View All</button>
        </div>
        <div class="recent-list" id="recent-list"></div>
      </div>
      <div class="card">
        <div class="card-header"><h2>Quick Start</h2></div>
        <p class="muted small" style="margin-bottom:16px">Red team workflow: build a persona → generate pretext → compose → score → export.</p>
        <div style="display:flex;flex-direction:column;gap:8px">
          <button class="btn btn-secondary" id="qs-persona">① Create Persona</button>
          <button class="btn btn-secondary" id="qs-template">② New Template from Persona</button>
          <button class="btn btn-secondary" id="qs-library">③ Browse Template Library</button>
        </div>
        <div class="roe-panel mt-16">
          <div class="roe-panel-title">⚠ Rules of Engagement</div>
          <p style="font-size:12px;color:#8892a4;line-height:1.6">
            This tool is for <strong style="color:#e2e8f0">authorised red team and social engineering assessments only</strong>.
            Engagement context metadata is mandatory on all exports. Ensure written authorisation is in place before conducting any campaign.
          </p>
        </div>
      </div>
    </div>
  `;

  // Recent list
  const rl = $('#recent-list');
  if (!stats.recent_templates.length) {
    rl.innerHTML = '<div class="empty-state"><p>No templates yet. Create your first template to get started.</p></div>';
  } else {
    stats.recent_templates.forEach(t => {
      const item = el('div', { class: 'recent-item', onclick: () => navigate('editor', { template: t }) });
      item.innerHTML = `
        <div>
          <div class="recent-name">${escHtml(t.name)}</div>
          <div class="recent-meta">${categoryBadge(t.category)} &nbsp; Updated ${formatDate(t.updated_at)}</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px">
          ${buildGauge(t.persuasion_score || 0, 44, 4)}
        </div>`;
      rl.appendChild(item);
    });
  }

  $('#dash-new-btn').onclick = () => openNewTemplateModal();
  $('#dash-view-all').onclick = () => navigate('library');
  $('#qs-persona').onclick = () => navigate('personas');
  $('#qs-template').onclick = () => openNewTemplateModal();
  $('#qs-library').onclick = () => navigate('library');
}

function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ---------------------------------------------------------------------------
// New Template Modal
// ---------------------------------------------------------------------------
function openNewTemplateModal() {
  const personaOptions = State.personas.map(p =>
    `<option value="${p.id}">${escHtml(p.name)} — ${escHtml(p.job_title)}</option>`
  ).join('');
  const catOptions = CATEGORIES.map(c =>
    `<option value="${c.id}">${c.label}</option>`
  ).join('');

  openModal(`
    <div class="modal-header">
      <span class="modal-title">New Template</span>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <label class="form-label">Template Name</label>
        <input id="nt-name" placeholder="e.g. Office 365 MFA Reset">
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Category</label>
          <select id="nt-cat">${catOptions}</select>
        </div>
        <div class="form-group">
          <label class="form-label">Target Persona</label>
          <select id="nt-persona">
            <option value="">— None —</option>
            ${personaOptions}
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Description</label>
        <input id="nt-desc" placeholder="Brief scenario description…">
      </div>
      <div class="form-group">
        <label class="form-label">Tags (comma-separated)</label>
        <input id="nt-tags" placeholder="mfa, o365, helpdesk">
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" id="nt-create">Create & Open Editor</button>
    </div>
  `);

  $('#nt-create').onclick = async () => {
    const name = $('#nt-name').value.trim() || 'Untitled Template';
    const tags = $('#nt-tags').value.split(',').map(s => s.trim()).filter(Boolean);
    try {
      const t = await API.post('/api/templates', {
        name,
        description: $('#nt-desc').value.trim(),
        category: $('#nt-cat').value,
        persona_id: $('#nt-persona').value,
        tags,
        subject_line: '',
        body_html: '',
        body_text: '',
      });
      State.templates.unshift(t);
      closeModal();
      navigate('editor', { template: t });
    } catch (err) { toast('Failed to create: ' + err.message, 'error'); }
  };
}

// ---------------------------------------------------------------------------
// Editor
// ---------------------------------------------------------------------------
async function renderEditor(templateData) {
  const view = $('#view-editor');
  view.innerHTML = '';

  // Load full template if we only have summary
  let t = templateData;
  if (t && t.id) {
    try { t = await API.get(`/api/templates/${t.id}`); } catch {}
  } else {
    t = { id: null, name: 'Untitled', subject_line: '', body_html: '', body_text: '',
           signature_block: '', tags: [], category: 'custom', persona_id: '',
           engagement_context: {}, persuasion_score: 0, red_flags: [] };
  }
  State.currentTemplate = t;

  const personaOptions = State.personas.map(p =>
    `<option value="${p.id}" ${t.persona_id === p.id ? 'selected' : ''}>${escHtml(p.name)}</option>`
  ).join('');
  const catOptions = CATEGORIES.map(c =>
    `<option value="${c.id}" ${t.category === c.id ? 'selected' : ''}>${c.label}</option>`
  ).join('');

  view.innerHTML = `
    <div class="editor-layout">
      <!-- LEFT PANEL -->
      <div class="editor-left" id="editor-left">

        <!-- Template meta -->
        <div>
          <h3 class="mb-8">Template</h3>
          <div class="form-group mb-8">
            <label class="form-label">Name</label>
            <input id="ed-name" value="${escHtml(t.name)}">
          </div>
          <div class="form-group mb-8">
            <label class="form-label">Category</label>
            <select id="ed-cat">${catOptions}</select>
          </div>
          <div class="form-group mb-8">
            <label class="form-label">Persona</label>
            <select id="ed-persona">
              <option value="">— None —</option>
              ${personaOptions}
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Tags</label>
            <input id="ed-tags" value="${escHtml((t.tags || []).join(', '))}">
          </div>
        </div>

        <!-- Pretext generator -->
        <div>
          <h3 class="mb-8">Pretext Generator</h3>
          <button class="btn btn-secondary" style="width:100%" id="gen-pretext-btn">Generate Pretext</button>
          <div id="pretext-result" class="mt-8"></div>
        </div>

        <!-- Token reference -->
        <div>
          <h3 class="mb-8">Available Tokens</h3>
          <div class="token-list" id="token-list">
            ${KNOWN_TOKENS.map(tk => `<span class="token-chip" onclick="insertToken('${tk}')">{{${tk}}}</span>`).join('')}
          </div>
        </div>

        <!-- Token preview values -->
        <div>
          <h3 class="mb-8">Preview Token Values</h3>
          <div id="token-values-panel" style="display:flex;flex-direction:column;gap:6px">
            ${Object.entries(State.tokenValues).map(([k,v]) => `
              <div class="form-group">
                <label class="form-label">{{${k}}}</label>
                <input class="token-val-input" data-token="${k}" value="${escHtml(v)}" style="font-size:11px">
              </div>`).join('')}
          </div>
        </div>

        <!-- Signature block -->
        <div>
          <h3 class="mb-8">Signature Block</h3>
          <textarea id="ed-sig" rows="4" placeholder="Best regards,&#10;{{sender_name}}&#10;{{sender_title}}&#10;{{company}}">${escHtml(t.signature_block || '')}</textarea>
          <button class="btn btn-ghost btn-sm mt-4" id="insert-sig-btn">Insert into Body</button>
        </div>

        <!-- Engagement context -->
        <div>
          <h3 class="mb-8">Engagement Context</h3>
          <div class="roe-panel">
            <div class="roe-panel-title">⚠ Required for Export</div>
            <div style="display:flex;flex-direction:column;gap:6px;margin-top:8px">
              ${[
                ['engagement_name', 'Engagement Name'],
                ['reference_id', 'Reference ID'],
                ['client_name', 'Client Name'],
                ['authorized_by', 'Authorised By'],
                ['authorization_date', 'Authorisation Date'],
                ['scope_notes', 'Scope Notes'],
              ].map(([k,lbl]) => `
                <div class="form-group">
                  <label class="form-label">${lbl}</label>
                  <input class="ctx-input" data-key="${k}" value="${escHtml((t.engagement_context||{})[k]||'')}">
                </div>`).join('')}
              <div class="form-group">
                <label class="form-label">Assessment Type</label>
                <select class="ctx-input" data-key="assessment_type">
                  ${['Internal Phishing Simulation','Red Team','Awareness Training'].map(v =>
                    `<option ${((t.engagement_context||{}).assessment_type||'')=== v?'selected':''}>${v}</option>`
                  ).join('')}
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div style="display:flex;flex-direction:column;gap:8px">
          <button class="btn btn-primary" id="ed-save-btn">Save Template</button>
          <button class="btn btn-ghost btn-sm" id="ed-version-btn">Save Version Snapshot</button>
          <button class="btn btn-ghost btn-sm" id="ed-history-btn">View Version History</button>
          <button class="btn btn-blue btn-sm" id="ed-export-btn">Export…</button>
          <button class="btn btn-secondary btn-sm" id="ed-variants-btn">Generate A/B Variants</button>
          ${t.id ? `<button class="btn btn-danger btn-sm" id="ed-delete-btn">Delete Template</button>` : ''}
        </div>

      </div>

      <!-- CENTER: Editor -->
      <div class="editor-center">
        <div class="editor-toolbar">
          <button class="toolbar-btn ${State.editorMode==='html'?'active':''}" id="tb-html">HTML</button>
          <button class="toolbar-btn ${State.editorMode==='text'?'active':''}" id="tb-text">Plain Text</button>
          <div class="toolbar-sep"></div>
          <button class="toolbar-btn" title="Bold" onclick="wrapSel('<strong>','</strong>')"><b>B</b></button>
          <button class="toolbar-btn" title="Italic" onclick="wrapSel('<em>','</em>')"><i>I</i></button>
          <button class="toolbar-btn" title="Underline" onclick="wrapSel('<u>','</u>')"><u>U</u></button>
          <button class="toolbar-btn" title="Bullet list" onclick="insertBulletList()">≡</button>
          <button class="toolbar-btn" title="Insert link" onclick="insertLink()">🔗</button>
          <button class="toolbar-btn" title="Insert token" onclick="openTokenPicker()">{{ }}</button>
          <div class="toolbar-sep"></div>
          <span id="ed-save-status" class="muted small" style="margin-left:4px"></span>
        </div>

        <div class="editor-body">
          <div class="editor-subject">
            <input id="ed-subject" placeholder="Subject line…" value="${escHtml(t.subject_line||'')}">
          </div>
          <div class="editor-area" id="editor-area">
            <textarea id="editor-html" class="${State.editorMode!=='html'?'hidden':''}"
              placeholder="Compose your email body HTML here…">${escHtml(t.body_html||'')}</textarea>
            <textarea id="editor-text" class="${State.editorMode!=='text'?'hidden':''}"
              placeholder="Plain text version…">${escHtml(t.body_text||'')}</textarea>
          </div>
          <div class="editor-counts">
            <span id="count-words">0 words</span>
            <span id="count-chars">0 chars</span>
            <span id="fk-score" style="color:#4caf81">FK: —</span>
          </div>
        </div>
      </div>

      <!-- RIGHT: Preview + Scores -->
      <div class="editor-right">
        <div class="preview-tabs">
          ${['desktop','mobile','plain','dark'].map(m => `
            <div class="preview-tab ${State.previewMode===m?'active':''}" data-mode="${m}">
              ${m.charAt(0).toUpperCase()+m.slice(1)}
            </div>`).join('')}
        </div>

        <div id="preview-frame" class="preview-frame ${State.previewMode==='dark'?'dark':''} ${State.previewMode==='mobile'?'mobile':''} ${State.previewMode==='plain'?'plain':''}"></div>

        <!-- Scores -->
        <div class="score-panel" id="score-panel">
          <h3>Persuasion Score</h3>
          <div style="display:flex;align-items:center;gap:12px">
            <div id="overall-gauge">${buildGauge(t.persuasion_score||0,60,5)}</div>
            <div style="flex:1" id="dim-bars"></div>
          </div>
          <div id="score-suggestions"></div>

          <h3 class="mt-8">Red Flags</h3>
          <div class="redflags-list" id="redflag-list"></div>

          <h3 class="mt-8">Readability</h3>
          <div id="readability-panel"></div>
        </div>
      </div>

    </div>
  `;

  // Bind events
  bindEditorEvents(t);
  updatePreview();
  if (t.persuasion_details) renderScores(t.persuasion_details, t.red_flags || [], t.readability || {});
  else triggerScore();
}

function bindEditorEvents(t) {
  // Mode toggle
  $('#tb-html').onclick = () => switchEditorMode('html');
  $('#tb-text').onclick = () => switchEditorMode('text');

  // Preview tabs
  $$('.preview-tab').forEach(tab => tab.onclick = () => {
    $$('.preview-tab').forEach(t2 => t2.classList.remove('active'));
    tab.classList.add('active');
    State.previewMode = tab.dataset.mode;
    const frame = $('#preview-frame');
    frame.className = `preview-frame${State.previewMode==='dark'?' dark':''}${State.previewMode==='mobile'?' mobile':''}${State.previewMode==='plain'?' plain':''}`;
    updatePreview();
  });

  // Editor input → debounced score + preview
  ['editor-html','editor-text','ed-subject'].forEach(id => {
    const el2 = $(`#${id}`);
    if (el2) el2.addEventListener('input', () => {
      updateCounts();
      updatePreview();
      clearTimeout(State.debounceTimer);
      State.debounceTimer = setTimeout(triggerScore, 600);
      markUnsaved();
    });
  });

  // Token value inputs → re-preview
  $$('.token-val-input').forEach(inp => inp.addEventListener('input', () => {
    State.tokenValues[inp.dataset.token] = inp.value;
    updatePreview();
  }));

  // Token autocomplete in editor
  $('#editor-html').addEventListener('keyup', handleTokenAutocomplete);
  $('#editor-text').addEventListener('keyup', handleTokenAutocomplete);

  // Save button
  $('#ed-save-btn').onclick = saveTemplate;

  // Signature insert
  $('#insert-sig-btn').onclick = () => {
    const sig = $('#ed-sig').value;
    if (!sig) { toast('No signature content', 'info'); return; }
    const sigHtml = `<br><br><p>${sig.replace(/\n/g,'<br>')}</p>`;
    const htmlTA = $('#editor-html');
    htmlTA.value += sigHtml;
    updatePreview(); markUnsaved();
  };

  // Generate pretext
  $('#gen-pretext-btn').onclick = generatePretext;

  // Version buttons
  $('#ed-version-btn').onclick = saveVersionSnapshot;
  $('#ed-history-btn').onclick = openVersionHistory;

  // Export
  $('#ed-export-btn').onclick = () => openExportModal();

  // A/B Variants
  $('#ed-variants-btn').onclick = generateVariants;

  // Delete
  const delBtn = $('#ed-delete-btn');
  if (delBtn) delBtn.onclick = deleteCurrentTemplate;

  updateCounts();
}

function switchEditorMode(mode) {
  State.editorMode = mode;
  $('#tb-html').classList.toggle('active', mode === 'html');
  $('#tb-text').classList.toggle('active', mode === 'text');
  $('#editor-html').classList.toggle('hidden', mode !== 'html');
  $('#editor-text').classList.toggle('hidden', mode !== 'text');
}

function markUnsaved() {
  const s = $('#ed-save-status');
  if (s) s.textContent = '● Unsaved';
}

function markSaved() {
  const s = $('#ed-save-status');
  if (s) { s.textContent = '✓ Saved'; setTimeout(() => { if(s) s.textContent=''; }, 2000); }
}

function getEditorValues() {
  const ctx = {};
  $$('.ctx-input').forEach(inp => { ctx[inp.dataset.key] = inp.value; });
  return {
    name: $('#ed-name')?.value || 'Untitled',
    category: $('#ed-cat')?.value || 'custom',
    persona_id: $('#ed-persona')?.value || '',
    subject_line: $('#ed-subject')?.value || '',
    body_html: $('#editor-html')?.value || '',
    body_text: $('#editor-text')?.value || '',
    signature_block: $('#ed-sig')?.value || '',
    tags: ($('#ed-tags')?.value || '').split(',').map(s=>s.trim()).filter(Boolean),
    engagement_context: ctx,
  };
}

async function saveTemplate() {
  const payload = getEditorValues();
  try {
    let saved;
    if (State.currentTemplate?.id) {
      saved = await API.put(`/api/templates/${State.currentTemplate.id}`, payload);
    } else {
      saved = await API.post('/api/templates', payload);
    }
    State.currentTemplate = saved;
    markSaved();
    toast('Template saved', 'success');
    if (saved.persuasion_details) renderScores(saved.persuasion_details, saved.red_flags || [], saved.readability || {});
  } catch (err) { toast('Save failed: ' + err.message, 'error'); }
}

// ---------------------------------------------------------------------------
// Preview
// ---------------------------------------------------------------------------
function updatePreview() {
  const frame = $('#preview-frame');
  if (!frame) return;
  const subjectRaw = $('#ed-subject')?.value || '';
  const htmlRaw = ($('#editor-html')?.value || '') + ($('#ed-sig')?.value ? `<br><p>${($('#ed-sig')?.value||'').replace(/\n/g,'<br>')}</p>` : '');
  const textRaw = $('#editor-text')?.value || '';
  const subject = substituteTokens(subjectRaw);
  const html = substituteTokens(htmlRaw);
  const text = substituteTokens(textRaw);

  if (State.previewMode === 'plain') {
    frame.textContent = `Subject: ${subject}\n\n${text}`;
    return;
  }

  frame.innerHTML = `
    <div class="email-preview-wrap">
      <div class="email-preview-header">
        <div class="email-preview-from">From: ${escHtml(State.tokenValues.sender_name)} &lt;helpdesk@corp.com&gt;</div>
        <div class="email-preview-subject">${escHtml(subject)}</div>
        <div class="email-preview-meta">To: ${escHtml(State.tokenValues.first_name)} ${escHtml(State.tokenValues.last_name)} · ${new Date().toLocaleString()}</div>
      </div>
      <div class="email-body-content">${html || '<p style="color:#999;font-style:italic">Start typing in the editor to see a preview…</p>'}</div>
    </div>`;
}

// ---------------------------------------------------------------------------
// Word / char counts
// ---------------------------------------------------------------------------
function updateCounts() {
  const text = ($('#editor-html')?.value || '') + ' ' + ($('#editor-text')?.value || '');
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  const chars = text.length;
  if ($('#count-words')) $('#count-words').textContent = `${words} words`;
  if ($('#count-chars')) $('#count-chars').textContent = `${chars} chars`;
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------
async function triggerScore() {
  const html = $('#editor-html')?.value || '';
  const text = $('#editor-text')?.value || '';
  const subject = $('#ed-subject')?.value || '';
  try {
    const data = await API.post('/api/score', { body_html: html, body_text: text, subject_line: subject });
    renderScores(data.persuasion, data.red_flags, data.readability);
  } catch {}
}

function renderScores(ps, redFlags, readability) {
  if (!ps) return;

  // Overall gauge
  const og = $('#overall-gauge');
  if (og) og.innerHTML = buildGauge(ps.overall || 0, 60, 5);

  // Dim bars
  const db = $('#dim-bars');
  if (db && ps.dimensions) {
    db.innerHTML = Object.entries(ps.dimensions).map(([dim, data]) => {
      const color = scoreColor(data.score);
      const pct = (data.score / 10 * 100).toFixed(0);
      return `<div class="dim-bar">
        <span class="dim-name">${dim.replace('_',' ')}</span>
        <div class="dim-track"><div class="dim-fill" style="width:${pct}%;background:${color}"></div></div>
        <span class="dim-score" style="color:${color}">${data.score.toFixed(1)}</span>
      </div>`;
    }).join('');
  }

  // Suggestions
  const ss = $('#score-suggestions');
  if (ss && ps.suggestions && ps.suggestions.length) {
    ss.innerHTML = `<div style="font-size:11px;color:#8892a4;margin-top:8px"><strong style="color:#f5a623">Improvements:</strong><br>${
      ps.suggestions.map(s => `• <strong>${s.dimension.replace('_',' ')}</strong>: ${escHtml(s.suggestion)}`).join('<br>')
    }</div>`;
  } else if (ss) ss.innerHTML = '';

  // Red flags
  const rfl = $('#redflag-list');
  if (rfl) {
    if (!redFlags || !redFlags.length) {
      rfl.innerHTML = '<span style="font-size:12px;color:#4caf81">✓ No red flags detected</span>';
    } else {
      rfl.innerHTML = redFlags.map(f => `
        <div class="redflag-item ${f.severity === 'high' ? 'sev-high' : f.severity === 'medium' ? 'sev-medium' : 'sev-low'}">
          <div class="redflag-header">
            <span class="redflag-name">${escHtml(f.check)}</span>
            <span class="badge ${f.severity === 'high' ? 'sev-high' : f.severity === 'medium' ? 'sev-medium' : 'sev-low'}">${f.severity}</span>
          </div>
          <div>${escHtml(f.detail)}</div>
          <div class="redflag-fix">Fix: ${escHtml(f.fix)}</div>
        </div>`).join('');
    }
  }

  // Readability
  const rp = $('#readability-panel');
  if (rp && readability && readability.score !== undefined) {
    const fk = readability.score;
    const color = fk >= 60 && fk <= 70 ? '#4caf81' : fk >= 40 ? '#f5a623' : '#e84d4d';
    const pct = Math.min(100, fk);
    if ($('#fk-score')) $('#fk-score').innerHTML = `FK: <span style="color:${color}">${fk}</span>`;
    rp.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;font-size:12px">
        <span>${escHtml(readability.grade)} — ${escHtml(readability.assessment)}</span>
        <span style="color:${color};font-weight:700">${fk}</span>
      </div>
      <div class="readability-bar">
        <div class="readability-fill" style="width:${pct}%;background:${color}"></div>
      </div>
      <div style="font-size:11px;color:#5a6278;margin-top:4px">
        ${readability.word_count} words · ${readability.sentence_count} sentences · ${readability.avg_words_per_sentence} avg words/sentence
        &nbsp;|&nbsp; Optimal: 60–70
      </div>`;
  }
}

// ---------------------------------------------------------------------------
// Token autocomplete
// ---------------------------------------------------------------------------
let tokenDropdown = null;
function handleTokenAutocomplete(e) {
  const ta = e.target;
  const pos = ta.selectionStart;
  const text = ta.value.substring(0, pos);
  const m = text.match(/\{\{(\w*)$/);
  removeTokenDropdown();
  if (!m) return;
  const prefix = m[1].toLowerCase();
  const matches = KNOWN_TOKENS.filter(t2 => t2.startsWith(prefix));
  if (!matches.length) return;

  tokenDropdown = el('div', { class: 'token-dropdown' });
  const rect = ta.getBoundingClientRect();
  tokenDropdown.style.cssText = `position:fixed;top:${rect.top+20}px;left:${rect.left+20}px`;
  matches.forEach((tk, i) => {
    const opt = el('div', { class: 'token-option' + (i===0?' selected':'') }, `{{${tk}}}`);
    opt.onmousedown = (ev) => {
      ev.preventDefault();
      const before = ta.value.substring(0, pos - m[0].length);
      const after  = ta.value.substring(pos);
      ta.value = before + `{{${tk}}}` + after;
      ta.selectionStart = ta.selectionEnd = before.length + tk.length + 4;
      removeTokenDropdown();
      updatePreview(); markUnsaved();
    };
    tokenDropdown.appendChild(opt);
  });
  document.body.appendChild(tokenDropdown);
}

function removeTokenDropdown() {
  if (tokenDropdown) { tokenDropdown.remove(); tokenDropdown = null; }
}
document.addEventListener('click', removeTokenDropdown);

function insertToken(token) {
  const ta = State.editorMode === 'html' ? $('#editor-html') : $('#editor-text');
  if (!ta) return;
  const s = ta.selectionStart, e2 = ta.selectionEnd;
  ta.value = ta.value.slice(0, s) + `{{${token}}}` + ta.value.slice(e2);
  ta.selectionStart = ta.selectionEnd = s + token.length + 4;
  ta.focus();
  updatePreview(); markUnsaved();
}

function openTokenPicker() {
  openModal(`
    <div class="modal-header">
      <span class="modal-title">Insert Token</span>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="token-list">
        ${KNOWN_TOKENS.map(tk => `<span class="token-chip" onclick="insertToken('${tk}');closeModal()">{{${tk}}}</span>`).join('')}
      </div>
      <div class="form-group mt-16">
        <label class="form-label">Custom Token Name</label>
        <div style="display:flex;gap:8px">
          <input id="custom-token-input" placeholder="my_custom_token">
          <button class="btn btn-primary" onclick="insertToken($('#custom-token-input').value.replace(/[^\\w]/g,'_'));closeModal()">Insert</button>
        </div>
      </div>
    </div>
  `);
}

// ---------------------------------------------------------------------------
// Toolbar helpers
// ---------------------------------------------------------------------------
function wrapSel(before, after) {
  const ta = $('#editor-html');
  if (!ta) return;
  const s = ta.selectionStart, e2 = ta.selectionEnd;
  const sel = ta.value.slice(s, e2);
  ta.value = ta.value.slice(0, s) + before + sel + after + ta.value.slice(e2);
  ta.selectionStart = s + before.length;
  ta.selectionEnd = s + before.length + sel.length;
  ta.focus(); updatePreview(); markUnsaved();
}

function insertBulletList() {
  const ta = $('#editor-html');
  if (!ta) return;
  const s = ta.selectionStart;
  const insert = '\n<ul>\n  <li>Item 1</li>\n  <li>Item 2</li>\n  <li>Item 3</li>\n</ul>\n';
  ta.value = ta.value.slice(0, s) + insert + ta.value.slice(s);
  ta.focus(); updatePreview(); markUnsaved();
}

function insertLink() {
  const text = prompt('Link text:', 'Click here to verify');
  if (text === null) return;
  const url = prompt('URL or token:', '{{link}}');
  if (url === null) return;
  wrapSel(`<a href="${url}">`, `${text}</a>`);
}

// ---------------------------------------------------------------------------
// Pretext generator
// ---------------------------------------------------------------------------
async function generatePretext() {
  const cat = $('#ed-cat')?.value || 'custom';
  const personaId = $('#ed-persona')?.value || '';
  try {
    const p = await API.post('/api/pretext/generate', { category: cat, persona_id: personaId });
    State.pretext = p;
    const r = $('#pretext-result');
    if (!r) return;
    const ul = p.urgency_level;
    r.innerHTML = `
      <div class="pretext-card">
        <div style="display:flex;align-items:center;justify-content:space-between">
          <strong style="font-size:12px">Pretext Generated</strong>
          <span class="urgency-badge urgency-${ul}">${ul}</span>
        </div>
        <div style="font-size:11px;color:#8892a4">${escHtml(p.summary)}</div>
        <div>
          <div class="form-label mb-4">Sender</div>
          <div style="font-size:11px">${escHtml(p.sender_name)} &lt;${escHtml(p.sender_display)}&gt;</div>
        </div>
        <div>
          <div class="form-label mb-4">Subject Variants (click to use)</div>
          <div class="pretext-subject-variants">
            ${Object.entries(p.subjects).map(([type, subj]) => `
              <div class="subject-variant" onclick="useSubjectVariant('${escHtml(subj).replace(/'/g,"\\'")}')">
                <span>${escHtml(subj)}</span>
                <span class="label">${type}</span>
              </div>`).join('')}
          </div>
        </div>
        <div>
          <div class="form-label mb-4">CTA</div>
          <div style="font-size:11px">${escHtml(p.cta)}</div>
        </div>
        <button class="btn btn-secondary btn-sm mt-4" onclick="applyPretext()">Apply to Template</button>
      </div>`;
  } catch (err) { toast('Pretext generation failed: ' + err.message, 'error'); }
}

function useSubjectVariant(subj) {
  const inp = $('#ed-subject');
  if (inp) { inp.value = subj; updatePreview(); markUnsaved(); }
}

function applyPretext() {
  if (!State.pretext) return;
  const p = State.pretext;
  // Apply neutral subject if empty
  const subjInp = $('#ed-subject');
  if (subjInp && !subjInp.value) subjInp.value = p.subjects.neutral;
  // Seed body
  const htmlTA = $('#editor-html');
  const textTA = $('#editor-text');
  if (htmlTA && !htmlTA.value) {
    htmlTA.value = `<p>Dear {{first_name}},</p>
<p>${escHtml(p.summary)}</p>
<p>${escHtml(p.cta)}</p>
<p><a href="{{link}}">Click here to proceed</a></p>
<p>This action is required by <strong>{{deadline}}</strong>.</p>
<br>
<p>Best regards,<br>
{{sender_name}}<br>
{{sender_title}}</p>`;
  }
  if (textTA && !textTA.value) {
    textTA.value = `Dear {{first_name}},\n\n${p.summary}\n\n${p.cta}\n\n{{link}}\n\nThis action is required by {{deadline}}.\n\nBest regards,\n{{sender_name}}\n{{sender_title}}`;
  }
  updatePreview();
  markUnsaved();
  toast('Pretext applied to template', 'success');
}

// ---------------------------------------------------------------------------
// Version history
// ---------------------------------------------------------------------------
async function saveVersionSnapshot() {
  if (!State.currentTemplate?.id) { toast('Save template first', 'info'); return; }
  const note = prompt('Version note (optional):', '');
  if (note === null) return;
  // Save current state first
  await saveTemplate();
  try {
    await API.post(`/api/templates/${State.currentTemplate.id}/versions`, { note: note || 'Snapshot' });
    toast('Version snapshot saved', 'success');
  } catch (err) { toast('Failed: ' + err.message, 'error'); }
}

async function openVersionHistory() {
  if (!State.currentTemplate?.id) { toast('Save template first', 'info'); return; }
  const versions = await API.get(`/api/templates/${State.currentTemplate.id}/versions`);
  openModal(`
    <div class="modal-header">
      <span class="modal-title">Version History — ${escHtml(State.currentTemplate.name)}</span>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      ${!versions.length
        ? '<div class="empty-state"><p>No saved versions yet.</p></div>'
        : `<div class="version-list">${versions.map(v => `
          <div class="version-item">
            <div>
              <div class="version-note">${escHtml(v.note || 'Snapshot')}</div>
              <div class="version-date">${formatDate(v.saved_at)} &nbsp; Subject: ${escHtml(v.subject_line || '—')}</div>
            </div>
            <button class="btn btn-ghost btn-sm" onclick="restoreVersion('${v.id}')">Restore</button>
          </div>`).join('')}</div>`}
    </div>
  `);
}

async function restoreVersion(vid) {
  if (!State.currentTemplate?.id) return;
  if (!confirm('Restore this version? Your current unsaved changes will be lost.')) return;
  try {
    const restored = await API.put ? await API.post(
      `/api/templates/${State.currentTemplate.id}/versions/${vid}/restore`, {}
    ) : null;
    closeModal();
    await renderEditor(State.currentTemplate);
    toast('Version restored', 'success');
  } catch (err) { toast('Restore failed: ' + err.message, 'error'); }
}

// ---------------------------------------------------------------------------
// A/B Variants
// ---------------------------------------------------------------------------
async function generateVariants() {
  if (!State.currentTemplate?.id) { toast('Save template first', 'info'); return; }
  try {
    await saveTemplate();
    const variants = await API.post(`/api/templates/${State.currentTemplate.id}/variants`, {});
    openModal(`
      <div class="modal-header">
        <span class="modal-title">A/B Variants</span>
        <button class="modal-close" onclick="closeModal()">✕</button>
      </div>
      <div class="modal-body">
        <p class="muted small mb-16">Three variants generated from your base template. Click <em>Save as new</em> to create each as an independent template.</p>
        ${variants.map((v, i) => `
          <div class="card card-sm mb-8">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
              <strong>${escHtml(v.name)}</strong>
              <button class="btn btn-primary btn-sm" onclick="saveVariant(${i})">Save as New</button>
            </div>
            <div class="small muted">Subject: ${escHtml(v.subject_line)}</div>
          </div>`).join('')}
      </div>
    `);
    window._variantsCache = variants;
  } catch (err) { toast('Failed: ' + err.message, 'error'); }
}

async function saveVariant(idx) {
  const v = window._variantsCache?.[idx];
  if (!v) return;
  try {
    const saved = await API.post('/api/templates', {
      name: v.name, description: v.description, category: v.category,
      persona_id: v.persona_id, subject_line: v.subject_line,
      body_html: v.body_html, body_text: v.body_text,
      tags: v.tags, engagement_context: v.engagement_context,
    });
    toast(`Saved: ${saved.name}`, 'success');
  } catch (err) { toast('Failed: ' + err.message, 'error'); }
}

// ---------------------------------------------------------------------------
// Export modal
// ---------------------------------------------------------------------------
function openExportModal() {
  let selectedFormat = 'gophish';
  let step = 1;

  function renderStep() {
    const content = step === 1 ? renderFormatStep() : step === 2 ? renderContextStep() : renderConfirmStep();
    $('#modal-box').innerHTML = `
      <div class="modal-header">
        <span class="modal-title">Export Template</span>
        <button class="modal-close" onclick="closeModal()">✕</button>
      </div>
      <div class="modal-body">
        <div class="export-steps">
          ${['Format','Metadata','Confirm'].map((s,i) => `<div class="export-step ${step===i+1?'active':step>i+1?'done':''}">${i+1}. ${s}</div>`).join('')}
        </div>
        ${content}
      </div>
      <div class="modal-footer" id="export-modal-footer"></div>`;
    bindStepFooter();
  }

  function renderFormatStep() {
    return `<div class="format-grid">${EXPORT_FORMATS.map(f => `
      <div class="format-option ${f.id===selectedFormat?'selected':''}" data-fmt="${f.id}">
        <div class="format-option-name">${f.name}</div>
        <div class="format-option-desc">${f.desc}</div>
      </div>`).join('')}</div>`;
  }

  function renderContextStep() {
    const ctx = State.currentTemplate?.engagement_context || {};
    return `
      <p class="muted small mb-16">Engagement metadata is embedded in all exports as an audit trail.</p>
      ${[['engagement_name','Engagement Name'],['reference_id','Reference ID'],
         ['client_name','Client Name'],['authorized_by','Authorised By'],
         ['authorization_date','Authorisation Date'],['scope_notes','Scope / Notes']].map(([k,l]) => `
        <div class="form-group mb-8">
          <label class="form-label">${l}</label>
          <input class="exp-ctx" data-key="${k}" value="${escHtml(ctx[k]||'')}">
        </div>`).join('')}
      <div class="form-group">
        <label class="form-label">Assessment Type</label>
        <select class="exp-ctx" data-key="assessment_type">
          ${['Internal Phishing Simulation','Red Team','Awareness Training'].map(v =>
            `<option ${(ctx.assessment_type||'')=== v?'selected':''}>${v}</option>`).join('')}
        </select>
      </div>`;
  }

  function renderConfirmStep() {
    const fmt = EXPORT_FORMATS.find(f => f.id === selectedFormat);
    return `
      <div style="display:flex;flex-direction:column;gap:12px">
        <div class="card card-sm">
          <div class="form-label mb-4">Export Format</div>
          <strong>${fmt?.name}</strong> — ${fmt?.desc}
        </div>
        <div class="card card-sm">
          <div class="form-label mb-4">Template</div>
          <strong>${escHtml(State.currentTemplate?.name||'')}</strong>
        </div>
        ${['eml','zip'].includes(selectedFormat) ? `
          <div class="form-group">
            <label class="form-label">Sender Name</label>
            <input id="exp-sender-name" value="${escHtml(State.tokenValues.sender_name||'IT Helpdesk')}">
          </div>
          <div class="form-group">
            <label class="form-label">Sender Email</label>
            <input id="exp-sender-email" value="helpdesk@corp.com">
          </div>` : ''}
        <div class="roe-panel">
          <div class="roe-panel-title">⚠ Authorised Use Only</div>
          <p style="font-size:12px;color:#8892a4">By exporting you confirm this campaign is conducted under written authorisation within an agreed scope.</p>
        </div>
      </div>`;
  }

  function bindStepFooter() {
    const footer = $('#export-modal-footer');
    if (!footer) return;
    footer.innerHTML = `
      ${step > 1 ? '<button class="btn btn-ghost" id="exp-back">← Back</button>' : ''}
      <span style="flex:1"></span>
      ${step < 3
        ? `<button class="btn btn-primary" id="exp-next">Next →</button>`
        : `<button class="btn btn-primary" id="exp-download">⬇ Download</button>`}`;

    // Format selection bindings (step 1)
    if (step === 1) {
      $$('.format-option').forEach(opt => opt.onclick = () => {
        $$('.format-option').forEach(o => o.classList.remove('selected'));
        opt.classList.add('selected');
        selectedFormat = opt.dataset.fmt;
      });
    }

    $('#exp-back')?.addEventListener('click', () => { step--; renderStep(); });
    $('#exp-next')?.addEventListener('click', () => { step++; renderStep(); });
    $('#exp-download')?.addEventListener('click', doExport);
  }

  async function doExport() {
    const ctx = {};
    $$('.exp-ctx').forEach(inp => { ctx[inp.dataset.key] = inp.value; });
    const senderName  = $('#exp-sender-name')?.value  || State.tokenValues.sender_name;
    const senderEmail = $('#exp-sender-email')?.value || 'helpdesk@corp.com';
    const tid = State.currentTemplate?.id;
    if (!tid) { toast('Template not saved', 'error'); return; }
    const ext = { gophish:'json', king_phisher:'json', eml:'eml', raw_html:'html',
                  plain_text:'txt', evilginx:'txt', pdf:'pdf', zip:'zip' };
    const filename = `${(State.currentTemplate.name||'export').replace(/[^a-z0-9]/gi,'_')}.${ext[selectedFormat]||'txt'}`;
    await API.download(`/api/export/${tid}`,
      { format: selectedFormat, sender_name: senderName, sender_email: senderEmail, engagement_context: ctx },
      filename);
    closeModal();
    toast('Export complete', 'success');
  }

  openModal('');
  renderStep();
}

// ---------------------------------------------------------------------------
// Delete template
// ---------------------------------------------------------------------------
async function deleteCurrentTemplate() {
  if (!State.currentTemplate?.id) return;
  if (!confirm(`Delete "${State.currentTemplate.name}"? This cannot be undone.`)) return;
  try {
    await API.del(`/api/templates/${State.currentTemplate.id}`);
    State.templates = State.templates.filter(t => t.id !== State.currentTemplate.id);
    State.currentTemplate = null;
    toast('Template deleted', 'success');
    navigate('library');
  } catch (err) { toast('Delete failed: ' + err.message, 'error'); }
}

// ---------------------------------------------------------------------------
// Library
// ---------------------------------------------------------------------------
async function renderLibrary() {
  const view = $('#view-library');
  view.innerHTML = `
    <div class="section-header">
      <h1 class="page-title">Template Library</h1>
      <div style="display:flex;gap:8px">
        <button class="btn btn-danger btn-sm hidden" id="bulk-delete-btn">Delete Selected</button>
        <button class="btn btn-ghost btn-sm hidden" id="bulk-export-btn">Export Selected</button>
        <button class="btn btn-primary" id="lib-new-btn">+ New Template</button>
      </div>
    </div>

    <div class="library-controls">
      <div class="search-input-wrap">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input id="lib-search" placeholder="Search templates, tags, body…">
      </div>
      <select id="lib-cat-filter" style="width:180px">
        <option value="">All Categories</option>
        ${CATEGORIES.map(c=>`<option value="${c.id}">${c.label}</option>`).join('')}
      </select>
      <select id="lib-sort" style="width:150px">
        <option value="updated_at">Last Modified</option>
        <option value="score">Persuasion Score</option>
        <option value="name">Name</option>
        <option value="created_at">Created</option>
      </select>
    </div>

    <div class="template-grid" id="template-grid"></div>
  `;

  State.selectedTemplates.clear();
  await refreshLibraryGrid();

  $('#lib-new-btn').onclick = () => openNewTemplateModal();
  $('#lib-search').oninput = debounce(refreshLibraryGrid, 300);
  $('#lib-cat-filter').onchange = refreshLibraryGrid;
  $('#lib-sort').onchange = refreshLibraryGrid;

  $('#bulk-delete-btn').onclick = bulkDelete;
  $('#bulk-export-btn').onclick = openBulkExportModal;
}

async function refreshLibraryGrid() {
  const q = $('#lib-search')?.value || '';
  const cat = $('#lib-cat-filter')?.value || '';
  const sort = $('#lib-sort')?.value || 'updated_at';
  const params = new URLSearchParams({ q, category: cat, sort });
  const templates = await API.get(`/api/templates?${params}`);
  State.templates = templates;
  const grid = $('#template-grid');
  if (!grid) return;

  if (!templates.length) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
      <p>No templates found. Create your first template to get started.</p>
      <button class="btn btn-primary" onclick="openNewTemplateModal()">Create Template</button>
    </div>`;
    return;
  }

  grid.innerHTML = templates.map(t => `
    <div class="template-card ${State.selectedTemplates.has(t.id)?'selected':''}" data-id="${t.id}">
      <div class="tc-header">
        <div>
          <div class="tc-name">${escHtml(t.name)}</div>
          <div style="margin-top:4px">${categoryBadge(t.category)} ${t.is_favorite?'⭐':''}</div>
        </div>
        ${buildGauge(t.persuasion_score||0, 44, 4)}
      </div>
      <div class="tc-desc">${escHtml(t.description||t.subject_line||'No description')}</div>
      <div style="display:flex;flex-wrap:wrap;gap:3px">
        ${(t.tags||[]).map(tag=>`<span class="tag">${escHtml(tag)}</span>`).join('')}
      </div>
      <div class="tc-footer">
        <span class="tc-meta">${formatDate(t.updated_at)}</span>
        <div class="tc-actions">
          <button class="btn btn-ghost btn-sm" title="Edit" onclick="event.stopPropagation();navigate('editor',{template:${JSON.stringify({id:t.id})}})">✎</button>
          <button class="btn btn-ghost btn-sm" title="Duplicate" onclick="event.stopPropagation();duplicateTemplate('${t.id}')">⎘</button>
          <button class="btn btn-ghost btn-sm" title="Toggle Favourite" onclick="event.stopPropagation();toggleFav('${t.id}',this)">⭐</button>
          <button class="btn btn-danger btn-sm" title="Delete" onclick="event.stopPropagation();deleteTemplate('${t.id}')">✕</button>
        </div>
      </div>
    </div>`).join('');

  $$('.template-card').forEach(card => {
    card.onclick = () => {
      const id = card.dataset.id;
      if (State.selectedTemplates.has(id)) {
        State.selectedTemplates.delete(id);
        card.classList.remove('selected');
      } else {
        navigate('editor', { template: { id } });
      }
      updateBulkButtons();
    };
  });
}

function updateBulkButtons() {
  const has = State.selectedTemplates.size > 0;
  $('#bulk-delete-btn')?.classList.toggle('hidden', !has);
  $('#bulk-export-btn')?.classList.toggle('hidden', !has);
}

async function toggleFav(id, btn) {
  const r = await API.post(`/api/templates/${id}/favorite`, {});
  btn.style.opacity = r.is_favorite ? '1' : '0.4';
  toast(r.is_favorite ? 'Added to favourites' : 'Removed from favourites', 'info');
}

async function duplicateTemplate(id) {
  const t = await API.post(`/api/templates/${id}/duplicate`, {});
  toast(`Duplicated as "${t.name}"`, 'success');
  await refreshLibraryGrid();
}

async function deleteTemplate(id) {
  if (!confirm('Delete this template?')) return;
  await API.del(`/api/templates/${id}`);
  toast('Deleted', 'success');
  await refreshLibraryGrid();
}

async function bulkDelete() {
  if (!State.selectedTemplates.size) return;
  if (!confirm(`Delete ${State.selectedTemplates.size} selected template(s)?`)) return;
  await Promise.all([...State.selectedTemplates].map(id => API.del(`/api/templates/${id}`)));
  State.selectedTemplates.clear();
  toast('Deleted selected templates', 'success');
  await refreshLibraryGrid();
}

function openBulkExportModal() {
  const ids = [...State.selectedTemplates];
  openModal(`
    <div class="modal-header">
      <span class="modal-title">Bulk Export (${ids.length} templates)</span>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <label class="form-label">Export Format</label>
        <select id="bulk-fmt">
          <option value="raw_html">Raw HTML</option>
          <option value="gophish">GoPhish JSON</option>
          <option value="plain_text">Plain Text</option>
          <option value="eml">EML Files</option>
        </select>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" id="bulk-dl-btn">Download ZIP</button>
    </div>
  `);
  $('#bulk-dl-btn').onclick = async () => {
    const fmt = $('#bulk-fmt').value;
    await API.download('/api/export/bulk', { ids, format: fmt }, 'bulk_export.zip');
    closeModal();
    toast('Bulk export complete', 'success');
  };
}

// ---------------------------------------------------------------------------
// Personas
// ---------------------------------------------------------------------------
async function renderPersonas() {
  const view = $('#view-personas');
  view.innerHTML = `
    <div class="section-header">
      <h1 class="page-title">Persona Manager</h1>
      <button class="btn btn-primary" id="new-persona-btn">+ New Persona</button>
    </div>
    <div class="persona-grid" id="persona-grid"></div>
  `;
  await refreshPersonaGrid();
  $('#new-persona-btn').onclick = () => openPersonaModal(null);
}

async function refreshPersonaGrid() {
  State.personas = await API.get('/api/personas');
  const grid = $('#persona-grid');
  if (!grid) return;

  if (!State.personas.length) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
      <p>No personas yet. Create one to enable richer pretext generation.</p>
      <button class="btn btn-primary" onclick="openPersonaModal(null)">Create Persona</button>
    </div>`;
    return;
  }

  grid.innerHTML = State.personas.map(p => {
    const initials = (p.name || 'P').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase();
    const linked = State.templates.filter(t => t.persona_id === p.id).length;
    return `
      <div class="persona-card">
        <div style="display:flex;align-items:center;gap:12px">
          <div class="persona-avatar">${initials}</div>
          <div>
            <div class="persona-name">${escHtml(p.name)}</div>
            <div class="persona-title">${escHtml(p.job_title||'')} ${p.department?`· ${escHtml(p.department)}`:''}</div>
          </div>
        </div>
        <div class="persona-tags">
          <span class="tag">${escHtml(p.industry||'—')}</span>
          <span class="tag">${escHtml(p.seniority||'mid')}</span>
          <span class="tag">${escHtml(p.communication_style||'semi-formal')}</span>
          <span class="tag">${escHtml(p.locale||'en-US')}</span>
        </div>
        ${p.known_platforms?.length ? `<div class="persona-tags">${p.known_platforms.map(pl=>`<span class="tag" style="color:#6db8ff;border-color:rgba(74,144,217,.3)">${escHtml(pl)}</span>`).join('')}</div>` : ''}
        <div style="font-size:11px;color:#5a6278">${linked} linked template${linked!==1?'s':''} · Created ${formatDate(p.created_at)}</div>
        <div style="display:flex;gap:6px">
          <button class="btn btn-ghost btn-sm" onclick="openPersonaModal('${p.id}')">Edit</button>
          <button class="btn btn-secondary btn-sm" onclick="navigate('editor');openNewTemplateModalWithPersona('${p.id}')">Use in Template</button>
          <button class="btn btn-danger btn-sm" onclick="deletePersona('${p.id}')">Delete</button>
        </div>
      </div>`;
  }).join('');
}

function openNewTemplateModalWithPersona(personaId) {
  openNewTemplateModal();
  setTimeout(() => {
    const sel = $('#nt-persona');
    if (sel) sel.value = personaId;
  }, 50);
}

function openPersonaModal(personaId) {
  const p = personaId ? State.personas.find(x => x.id === personaId) : null;
  const platforms = ['Office 365','Workday','ServiceNow','Slack','Teams','Zoom',
                     'SharePoint','OneDrive','Okta','Salesforce','Jira','Google Workspace'];
  const selectedPlats = p?.known_platforms || [];

  openModal(`
    <div class="modal-header">
      <span class="modal-title">${p ? 'Edit' : 'New'} Persona</span>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Persona Name</label>
          <input id="p-name" value="${escHtml(p?.name||'')}">
        </div>
        <div class="form-group">
          <label class="form-label">Job Title</label>
          <input id="p-title" value="${escHtml(p?.job_title||'')}">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Department</label>
          <input id="p-dept" value="${escHtml(p?.department||'')}">
        </div>
        <div class="form-group">
          <label class="form-label">Industry</label>
          <input id="p-industry" value="${escHtml(p?.industry||'')}">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Seniority</label>
          <select id="p-seniority">
            ${['junior','mid','senior','executive'].map(s=>`<option ${p?.seniority===s?'selected':''}>${s}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Communication Style</label>
          <select id="p-style">
            ${['formal','semi-formal','casual'].map(s=>`<option ${p?.communication_style===s?'selected':''}>${s}</option>`).join('')}
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Language</label>
          <input id="p-lang" value="${escHtml(p?.language||'en')}">
        </div>
        <div class="form-group">
          <label class="form-label">Locale</label>
          <input id="p-locale" value="${escHtml(p?.locale||'en-US')}">
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Known Platforms / Tools</label>
        <div style="display:flex;flex-wrap:wrap;gap:6px">
          ${platforms.map(pl=>`
            <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer">
              <input type="checkbox" class="plat-cb" value="${pl}" ${selectedPlats.includes(pl)?'checked':''}> ${pl}
            </label>`).join('')}
        </div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" id="p-save-btn">${p ? 'Save Changes' : 'Create Persona'}</button>
    </div>
  `);

  $('#p-save-btn').onclick = async () => {
    const platforms = $$('.plat-cb').filter(cb => cb.checked).map(cb => cb.value);
    const payload = {
      name: $('#p-name').value.trim() || 'Unnamed',
      job_title: $('#p-title').value.trim(),
      department: $('#p-dept').value.trim(),
      industry: $('#p-industry').value.trim(),
      seniority: $('#p-seniority').value,
      communication_style: $('#p-style').value,
      language: $('#p-lang').value.trim() || 'en',
      locale: $('#p-locale').value.trim() || 'en-US',
      known_platforms: platforms,
    };
    try {
      if (p) await API.put(`/api/personas/${p.id}`, payload);
      else await API.post('/api/personas', payload);
      closeModal();
      toast(p ? 'Persona updated' : 'Persona created', 'success');
      await refreshPersonaGrid();
    } catch (err) { toast('Failed: ' + err.message, 'error'); }
  };
}

async function deletePersona(id) {
  if (!confirm('Delete this persona?')) return;
  await API.del(`/api/personas/${id}`);
  toast('Persona deleted', 'success');
  await refreshPersonaGrid();
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// Expose globals needed by inline handlers
Object.assign(window, {
  navigate, closeModal, insertToken, openTokenPicker,
  openPersonaModal, deletePersona, openNewTemplateModal,
  openNewTemplateModalWithPersona, duplicateTemplate,
  deleteTemplate, toggleFav, restoreVersion, saveVariant,
  generateVariants, wrapSel, insertBulletList, insertLink,
  useSubjectVariant, applyPretext, generatePretext,
});
