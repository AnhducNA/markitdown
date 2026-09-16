/* ─────────────────────────────────────────
   MOFA MarkItDown — Frontend Logic
   Bộ Ngoại Giao Việt Nam
───────────────────────────────────────── */

const API_BASE = '';

/* ── DOM refs ── */
const $ = id => document.getElementById(id);
const uploadZone     = $('uploadZone');
const fileInput      = $('fileInput');
const browseBtn      = $('browseBtn');
const fileSelectedInfo = $('fileSelectedInfo');
const fileExtLabel   = $('fileExtLabel');
const selectedFileName = $('selectedFileName');
const selectedFileSize = $('selectedFileSize');
const fileClearBtn   = $('fileClearBtn');
const convertBtn     = $('convertBtn');
const departmentInput = $('departmentInput');
const categoryInput  = $('categoryInput');
const authorInput    = $('authorInput');
const dateInput      = $('dateInput');
const descriptionInput = $('descriptionInput');
const tagsInput      = $('tagsInput');
const heroSection    = $('heroSection');
const progressSection = $('progressSection');
const progressBar    = $('progressBar');
const progressLabel  = $('progressLabel');
const errorSection   = $('errorSection');
const errorMessage   = $('errorMessage');
const errorRetryBtn  = $('errorRetryBtn');
const resultSection  = $('resultSection');
const resultTitle    = $('resultTitle');
const resultStats    = $('resultStats');
const rawView        = $('rawView');
const rawCode        = $('rawCode');
const previewView    = $('previewView');
const rawViewBtn     = $('rawViewBtn');
const previewViewBtn = $('previewViewBtn');
const copyBtn        = $('copyBtn');
const downloadBtn    = $('downloadBtn');
const newConvertBtn  = $('newConvertBtn');
const serverStatus   = $('serverStatus');
const currentDateTime = $('currentDateTime');

let currentFile = null;
let currentMarkdown = '';
let currentFilename = '';

/* ══════════════════════════════
   DATE / TIME
══════════════════════════════ */
function updateClock() {
  const now = new Date();
  const opts = { weekday:'long', day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12: false };
  currentDateTime.textContent = now.toLocaleString('vi-VN', opts);
}
updateClock();
setInterval(updateClock, 1000);

/* ══════════════════════════════
   SERVER HEALTH CHECK
══════════════════════════════ */
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(4000) });
    if (res.ok) {
      serverStatus.className = 'status-pill online';
      serverStatus.querySelector('.status-text').textContent = 'Máy chủ sẵn sàng';
    } else { setOffline(); }
  } catch { setOffline(); }
}
function setOffline() {
  serverStatus.className = 'status-pill offline';
  serverStatus.querySelector('.status-text').textContent = 'Mất kết nối';
}
checkHealth();
setInterval(checkHealth, 15000);

/* ══════════════════════════════
   PARTICLES
══════════════════════════════ */
(function initParticles() {
  const container = $('particles');
  for (let i = 0; i < 18; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    const size = Math.random() * 3 + 1;
    p.style.cssText = `
      width:${size}px; height:${size}px;
      left:${Math.random()*100}%;
      top:${Math.random()*100}%;
      animation-duration:${8 + Math.random()*14}s;
      animation-delay:${Math.random()*10}s;
      opacity:0;
    `;
    container.appendChild(p);
  }
})();

/* ══════════════════════════════
   FILE HELPERS
══════════════════════════════ */
function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

function getExtColor(ext) {
  const map = {
    pdf: '#e53e3e', docx: '#2b6cb0', doc: '#2b6cb0',
    xlsx: '#276749', xls: '#276749', pptx: '#c05621', ppt: '#c05621',
    txt: '#4a5568', csv: '#276749', html: '#c05621',
    jpg: '#6b46c1', jpeg: '#6b46c1', png: '#6b46c1', gif: '#6b46c1',
    mp3: '#d69e2e', wav: '#d69e2e', epub: '#2c7a7b',
  };
  return map[ext.toLowerCase()] || '#4a5568';
}

function showFileSelected(file) {
  currentFile = file;
  const ext = file.name.split('.').pop().toUpperCase();
  fileExtLabel.textContent = ext.length > 4 ? ext.slice(0, 4) : ext;
  $('fileIconWrap').style.background = `linear-gradient(135deg, ${getExtColor(ext.toLowerCase())} 0%, #111 100%)`;
  selectedFileName.textContent = file.name;
  selectedFileSize.textContent = formatBytes(file.size);
  uploadZone.style.display = 'none';
  fileSelectedInfo.hidden = false;
}

function resetUI() {
  currentFile = null;
  currentMarkdown = '';
  fileInput.value = '';
  departmentInput.value = '';
  categoryInput.value = '';
  authorInput.value = '';
  dateInput.value = '';
  descriptionInput.value = '';
  tagsInput.value = '';
  uploadZone.style.display = '';
  fileSelectedInfo.hidden = true;
  progressSection.hidden = true;
  errorSection.hidden = true;
  resultSection.hidden = true;
  heroSection.hidden = false;
}

/* ══════════════════════════════
   DRAG & DROP
══════════════════════════════ */
uploadZone.addEventListener('dragover', e => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});
['dragleave', 'dragend'].forEach(ev =>
  uploadZone.addEventListener(ev, () => uploadZone.classList.remove('drag-over'))
);
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) showFileSelected(file);
});
uploadZone.addEventListener('keydown', e => {
  if (e.key === 'Enter' || e.key === ' ') fileInput.click();
});

browseBtn.addEventListener('click', e => { e.stopPropagation(); fileInput.click(); });
fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) showFileSelected(fileInput.files[0]);
});
fileClearBtn.addEventListener('click', resetUI);
errorRetryBtn.addEventListener('click', resetUI);
newConvertBtn.addEventListener('click', resetUI);

/* ══════════════════════════════
   PROGRESS ANIMATION
══════════════════════════════ */
// Scanning PDFs can take minutes — we loop the animation and show elapsed time
const progressSteps = [
  [15, 900,  'Đang tải tài liệu lên máy chủ...'],
  [30, 1200, 'Đang phân tích cấu trúc PDF...'],
  [50, 1000, 'Đang nhận dạng văn bản (OCR)...'],
  [70, 1000, 'Đang xử lý các trang ảnh scan...'],
  [85, 800,  'Đang chuyển đổi sang Markdown...'],
  [92, 600,  'Đang hoàn thiện kết quả...'],
];

let _progressStopped = false;

async function animateProgressLoop(startTime) {
  _progressStopped = false;
  let stepIdx = 0;
  // First pass: run all steps once
  for (const [pct, delay, label] of progressSteps) {
    if (_progressStopped) return;
    progressBar.style.width = pct + '%';
    progressLabel.textContent = label;
    await new Promise(r => setTimeout(r, delay));
  }
  // Loop: keep cycling OCR steps with elapsed timer so the user knows it's working
  const ocrSteps = [
    [72, 'Đang nhận dạng văn bản (OCR)... '],
    [78, 'Đang xử lý trang scan... '],
    [84, 'Đang trích xuất nội dung... '],
    [90, 'Đang chuyển đổi sang Markdown... '],
  ];
  let loopIdx = 0;
  while (!_progressStopped) {
    const [pct, label] = ocrSteps[loopIdx % ocrSteps.length];
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const mins = Math.floor(elapsed / 60);
    const secs = String(elapsed % 60).padStart(2, '0');
    const timeStr = mins > 0 ? `${mins}:${secs}` : `${elapsed}s`;
    progressBar.style.width = pct + '%';
    progressLabel.textContent = label + `(${timeStr})`;
    loopIdx++;
    await new Promise(r => setTimeout(r, 1200));
  }
}

/* ══════════════════════════════
   CONVERT
══════════════════════════════ */
convertBtn.addEventListener('click', async () => {
  if (!currentFile) return;

  // Show progress
  fileSelectedInfo.hidden = true;
  heroSection.hidden = true;
  progressSection.hidden = false;
  errorSection.hidden = true;
  resultSection.hidden = true;
  progressBar.style.width = '0%';
  progressLabel.textContent = 'Đang chuẩn bị...';

  const startTime = Date.now();
  animateProgressLoop(startTime); // fire-and-forget — loops until we stop it

  const formData = new FormData();
  formData.append('file', currentFile);
  formData.append('department', departmentInput.value.trim());
  formData.append('category', categoryInput.value.trim());
  formData.append('author', authorInput.value.trim());
  formData.append('created_at', dateInput.value);
  formData.append('description', descriptionInput.value.trim());
  formData.append('tags', tagsInput.value.trim());
  
  const ocrEngine = document.querySelector('input[name="ocr_engine"]:checked')?.value || 'rapid';
  formData.append('ocr_engine', ocrEngine);

  try {
    const res = await fetch(`${API_BASE}/api/convert`, { method: 'POST', body: formData });

    _progressStopped = true;
    progressBar.style.width = '100%';
    progressLabel.textContent = 'Hoàn thành!';
    await new Promise(r => setTimeout(r, 350));

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || `Lỗi máy chủ (${res.status})`);
    }

    showResult(data);

  } catch (err) {
    _progressStopped = true;
    progressSection.hidden = true;
    errorSection.hidden = false;
    errorMessage.textContent = err.message || 'Đã xảy ra lỗi không xác định.';
  }
});

/* ══════════════════════════════
   SHOW RESULT
══════════════════════════════ */
function showResult(data) {
  progressSection.hidden = true;
  resultSection.hidden = false;

  currentMarkdown = data.markdown || '';
  currentFilename = (data.filename || 'document').replace(/\.[^.]+$/, '') + '.md';

  resultTitle.textContent = data.title || data.filename || 'Tài liệu';

  const lines = currentMarkdown.split('\n').length;
  const words = currentMarkdown.split(/\s+/).filter(Boolean).length;
  const chars = currentMarkdown.length;
  resultStats.textContent = `${lines.toLocaleString('vi')} dòng · ${words.toLocaleString('vi')} từ · ${chars.toLocaleString('vi')} ký tự`;

  rawCode.textContent = currentMarkdown;

  // Default: raw view
  setView('raw');
}

/* ══════════════════════════════
   VIEW TOGGLE
══════════════════════════════ */
function setView(mode) {
  if (mode === 'raw') {
    rawView.hidden = false;
    previewView.hidden = true;
    rawViewBtn.className = 'toggle-btn toggle-btn--active';
    previewViewBtn.className = 'toggle-btn';
  } else {
    rawView.hidden = true;
    previewView.hidden = false;
    rawViewBtn.className = 'toggle-btn';
    previewViewBtn.className = 'toggle-btn toggle-btn--active';

    // Render markdown
    marked.setOptions({ breaks: true, gfm: true });
    previewView.innerHTML = marked.parse(currentMarkdown);

    // Syntax highlight code blocks
    previewView.querySelectorAll('pre code').forEach(el => {
      try { hljs.highlightElement(el); } catch {}
    });
  }
}
rawViewBtn.addEventListener('click', () => setView('raw'));
previewViewBtn.addEventListener('click', () => setView('preview'));

/* ══════════════════════════════
   COPY
══════════════════════════════ */
copyBtn.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(currentMarkdown);
    copyBtn.classList.add('copied');
    const orig = copyBtn.innerHTML;
    copyBtn.innerHTML = `<svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg> Đã sao chép!`;
    setTimeout(() => { copyBtn.innerHTML = orig; copyBtn.classList.remove('copied'); }, 2000);
  } catch {
    alert('Không thể sao chép. Vui lòng chọn thủ công.');
  }
});

/* ══════════════════════════════
   DOWNLOAD
══════════════════════════════ */
downloadBtn.addEventListener('click', () => {
  const blob = new Blob([currentMarkdown], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = currentFilename;
  a.click();
  URL.revokeObjectURL(url);
});
