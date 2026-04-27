'use strict';

let _pending        = null;
let _messages       = [];
let _docId          = null;
let _isLoading      = false;

// Generate once per page session so every request — including the first —
// carries the same conversation_id. This makes the backend in-flight check
// work even before the server has responded with its own conversation_id.
let _conversationId = crypto.randomUUID();

// ── View switching ──────────────────────────────────────────────────────────

function showView(id) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

function showLanding() {
  _pending        = null;
  _conversationId = crypto.randomUUID(); // fresh conversation for new session
  _messages       = [];
  document.getElementById('input-landing').value = '';
  showView('view-landing');
}

function showProcessing() {
  renderChatMessages();
  setInfoBtnReady(_pending !== null);
  showView('view-processing');
}

// ── Chat rendering ──────────────────────────────────────────────────────────

function _esc(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function renderChatMessages() {
  const container = document.getElementById('chat-messages');
  container.innerHTML = '';

  _messages.forEach((msg, i) => {
    const isLast = i === _messages.length - 1;

    if (msg.role === 'user') {
      const el = document.createElement('div');
      el.className = 'chat-bubble-user';
      el.textContent = msg.content;
      container.appendChild(el);
      return;
    }

    // Bot card with internal header
    const card = document.createElement('div');
    card.className = 'chat-card-bot';

    const infoBtn = isLast
      ? `<button id="processing-info-btn" class="processing-info-btn" onclick="goToResults()" disabled>
           <span class="info-spinner"></span>
           <span class="info-icon">ℹ</span>
         </button>`
      : '';

    if (msg.content === '__typing__') {
      card.innerHTML = `
        <div class="chat-card-inner-header">
          <div class="brand-inline">
            <img src="/static/logo.png" class="brand-logo-sm" alt="spoon" />
            <span class="brand-name-sm">spoon</span>
          </div>
          ${infoBtn}
        </div>
        <div class="chat-card-body">
          <div class="typing-indicator"><span></span><span></span><span></span></div>
        </div>`;
    } else {
      card.innerHTML = `
        <div class="chat-card-inner-header">
          <div class="brand-inline">
            <img src="/static/logo.png" class="brand-logo-sm" alt="spoon" />
            <span class="brand-name-sm">spoon</span>
          </div>
          ${infoBtn}
        </div>
        <div class="chat-card-body">
          <p class="bot-answer">${_esc(msg.content)}</p>
        </div>`;
    }

    container.appendChild(card);
  });

  // Auto-scroll to latest message
  const area = document.getElementById('chat-area');
  area.scrollTop = area.scrollHeight;
}

// ── Input handling ──────────────────────────────────────────────────────────

const INPUT_IDS = {
  landing:    'input-landing',
  processing: 'input-processing',
};

function handleKey(e, source) {
  if (e.key === 'Enter' && !_isLoading) submitQuery(source);
}

function setSendDisabled(disabled) {
  document.querySelectorAll('.send-btn').forEach(btn => {
    btn.disabled = disabled;
    btn.style.opacity = disabled ? '0.4' : '1';
    btn.style.cursor  = disabled ? 'not-allowed' : 'pointer';
  });
}

// ── Query submission ────────────────────────────────────────────────────────

async function submitQuery(source) {
  if (_isLoading) return;
  const inputEl = document.getElementById(INPUT_IDS[source]);
  if (!inputEl) { console.error('No input for source:', source); return; }
  const query = inputEl.value.trim();
  if (!query) return;

  inputEl.value = '';
  _pending   = null;
  _isLoading = true;
  setSendDisabled(true);

  // Append user bubble + typing placeholder, then render
  _messages.push({ role: 'user',      content: query });
  _messages.push({ role: 'assistant', content: '__typing__' });
  try { renderChatMessages(); } catch(e) { console.error('renderChatMessages error:', e); }
  showView('view-processing');

  try {
    const body = { query };
    if (_conversationId) body.conversation_id = _conversationId;
    if (_docId)          body.doc_id          = _docId;

    const res = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    // Handle 409 in-flight conflict
    if (res.status === 409) {
      const err = await res.json().catch(() => ({}));
      _messages.pop();
      _messages[_messages.length - 1] = {
        role: 'assistant',
        content: err.detail || 'A response is already in progress. Please wait.',
      };
      renderChatMessages();
      return;
    }

    // Handle 400 unsafe prompt — show refusal in chat
    if (res.status === 400) {
      const err = await res.json().catch(() => ({}));
      const detail = err.detail || {};
      const msg = detail.error === 'unsafe_prompt'
        ? (detail.message || `This prompt was blocked (${detail.category || 'policy violation'}). ${detail.reason || ''}`)
        : 'This request could not be processed.';
      _messages.pop(); // remove typing placeholder
      _messages[_messages.length - 1] = { role: 'assistant', content: msg };
      renderChatMessages();
      return;
    }

    if (!res.ok) throw new Error(`Server error: ${res.status}`);
    const data = await res.json();

    if (data.conversation_id) _conversationId = data.conversation_id;

    // Replace typing placeholder with actual answer
    _messages[_messages.length - 1].content = data.final_answer;
    _pending = { query, data };
    renderChatMessages();
    setInfoBtnReady(true);
  } catch (err) {
    console.error(err);
    _messages.pop(); // remove typing placeholder
    _messages.pop(); // remove user bubble
    renderChatMessages();
    alert('Something went wrong. Please try again.');
    if (_messages.length === 0) showLanding();
  } finally {
    _isLoading = false;
    setSendDisabled(false);
  }
}

// ── ℹ button state ──────────────────────────────────────────────────────────

function setInfoBtnReady(ready) {
  const btn = document.getElementById('processing-info-btn');
  if (!btn) return;
  btn.disabled = !ready;
  btn.classList.toggle('ready', ready);
}

// ── Navigate processing → results ───────────────────────────────────────────

function goToResults() {
  if (!_pending) return;
  renderResults(_pending.query, _pending.data);
}

// ── Render results ──────────────────────────────────────────────────────────

function renderResults(query, data) {
  document.getElementById('results-query').textContent = `"${query}"`;
  document.getElementById('results-answer').textContent = data.final_answer;
  document.getElementById('results-analysis').textContent = data.analysis;

  const r = data.original_responses || [];
  document.getElementById('content-gpt').textContent    = r[0]?.answer ?? '';
  document.getElementById('content-claude').textContent  = r[1]?.answer ?? '';
  document.getElementById('content-gemini').textContent  = r[2]?.answer ?? '';

  ['gpt', 'claude', 'gemini'].forEach(id => {
    document.getElementById(`content-${id}`).classList.remove('open');
    document.getElementById(`chevron-${id}`).classList.remove('open');
  });

  showView('view-results');
}

// ── Expanders ───────────────────────────────────────────────────────────────

function toggleExpander(id) {
  document.getElementById(`content-${id}`).classList.toggle('open');
  document.getElementById(`chevron-${id}`).classList.toggle('open');
}

// ── Document upload ──────────────────────────────────────────────────────────

async function uploadFile() {
  const input = document.getElementById('file-input');
  const file  = input.files[0];
  if (!file) return;

  const form = new FormData();
  form.append('file', file);

  try {
    const res = await fetch('/api/upload', { method: 'POST', body: form });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Upload failed: ${err.detail || res.status}`);
      return;
    }
    const data = await res.json();
    _docId = data.doc_id;

    const pill  = document.getElementById('doc-pill');
    const label = document.getElementById('doc-pill-label');
    label.textContent = `${data.filename} (${data.chunks} chunks)`;
    pill.classList.remove('hidden');
  } catch (err) {
    console.error(err);
    alert('Upload failed. Please try again.');
  } finally {
    input.value = '';   // allow re-uploading same file
  }
}

function clearDocument() {
  _docId = null;
  document.getElementById('doc-pill').classList.add('hidden');
  document.getElementById('doc-pill-label').textContent = '';
}
