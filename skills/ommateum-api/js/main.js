/* ============================================================
   Ommateum Frontend v2 — RESTful API Client
   ============================================================ */

/* ============================================================
   Splash Screen — 复眼 (Compound Eye) Canvas 动画
   ============================================================ */
(function initSplash() {
  const splash = document.getElementById('splashScreen');
  const canvas = document.getElementById('splashCanvas');
  const brand = document.getElementById('splashBrand');
  if (!splash || !canvas) return;

  const ctx = canvas.getContext('2d');
  let animId = null;

  function resize() {
    const dpr = window.devicePixelRatio || 1;
    canvas.width = window.innerWidth * dpr;
    canvas.height = window.innerHeight * dpr;
    canvas.style.width = window.innerWidth + 'px';
    canvas.style.height = window.innerHeight + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  resize();
  window.addEventListener('resize', resize);

  // ---- 六边形 (ommatidium) 绘制 ----
  function drawHex(ctx, x, y, r, fill, stroke, lw) {
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const a = (Math.PI / 3) * i - Math.PI / 6;
      const px = x + r * Math.cos(a);
      const py = y + r * Math.sin(a);
      i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
    }
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw || 1; ctx.stroke(); }
  }

  const hexR = 18;
  const hexW = Math.sqrt(3) * hexR;
  const hexH = 2 * hexR;
  const hGap = hexW;
  const vGap = hexH * 0.78;

  let startTs = null;
  const TOTAL = 3800; // 总动画时长 (ms)
  const BRAND_SHOW = 2200; // 品牌文字出现时间点

  function frame(ts) {
    if (!startTs) startTs = ts;
    const elapsed = ts - startTs;
    const t = Math.min(elapsed / TOTAL, 1);

    const w = window.innerWidth;
    const h = window.innerHeight;
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2;
    const maxD = Math.sqrt(cx * cx + cy * cy);

    const breath = 1 + 0.06 * Math.sin(elapsed * 0.0018);
    // 眼睛"转动"效果：中心点缓慢偏移
    const lookX = cx + Math.sin(elapsed * 0.0004) * w * 0.06;
    const lookY = cy + Math.cos(elapsed * 0.00055) * h * 0.06;

    const cols = Math.ceil(w / hGap) + 3;
    const rows = Math.ceil(h / vGap) + 3;

    for (let row = -1; row < rows; row++) {
      for (let col = -1; col < cols; col++) {
        const ox = (row % 2 === 0) ? hGap / 2 : 0;
        const x = col * hGap + ox;
        const y = row * vGap;

        const dx = x - lookX;
        const dy = y - lookY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const dNorm = Math.min(dist / maxD, 1);

        const r = hexR * (1.3 - 0.55 * dNorm) * breath;
        if (r < 2.5) continue;

        // 溶解效果：入/出
        const dissolveIn  = Math.min(t * 2.5, 1);
        const dissolveOut = t > 0.7 ? Math.max(1 - (t - 0.7) / 0.3, 0) : 1;
        const dissolve = dissolveIn * dissolveOut;

        const hue = 195 + dNorm * 40;
        const sat = 55 + dNorm * 20;
        const light = 22 + dNorm * 50;

        // 主体填充
        const fillAlpha = (0.85 + 0.1 * (1 - dNorm)) * dissolve;
        ctx.globalAlpha = fillAlpha;
        drawHex(ctx, x, y, r, `hsl(${hue}, ${sat}%, ${light}%)`, null, 0);

        // 边框
        ctx.globalAlpha = 0.22 * dissolve;
        drawHex(ctx, x, y, r, null, `hsla(${hue + 20}, ${sat}%, ${light + 20}%, 0.5)`, 0.7);

        // 透镜高光 (内层小六边形)
        const hlR = r * 0.42;
        const hl = ctx.createRadialGradient(x - r * 0.1, y - r * 0.15, 0, x, y, hlR);
        hl.addColorStop(0, `hsla(${hue}, 70%, 90%, ${(0.55 + 0.3 * (1 - dNorm)) * dissolve})`);
        hl.addColorStop(0.5, `hsla(${hue}, 60%, 70%, ${0.25 * dissolve})`);
        hl.addColorStop(1, 'transparent');
        ctx.globalAlpha = 1;
        drawHex(ctx, x, y, hlR, hl, null, 0);

        // 每个小眼的次级暗环
        if (r > 8) {
          const ringR = r * 0.7;
          ctx.globalAlpha = 0.08 * dissolve;
          drawHex(ctx, x, y, ringR, null, `hsla(${hue}, 30%, 40%, 0.5)`, 0.5);
        }
      }
    }

    // 整体暗角
    const vignette = ctx.createRadialGradient(cx, cy, w * 0.25, cx, cy, w * 0.85);
    vignette.addColorStop(0, 'transparent');
    vignette.addColorStop(0.5, 'rgba(6, 13, 24, 0.2)');
    vignette.addColorStop(1, 'rgba(6, 13, 24, 0.75)');
    ctx.globalAlpha = 1;
    ctx.fillStyle = vignette;
    ctx.fillRect(0, 0, w, h);

    // 中心"瞳孔"区域
    const pupilGrad = ctx.createRadialGradient(lookX, lookY, hexR * 1.5, lookX, lookY, hexR * 6);
    pupilGrad.addColorStop(0, 'rgba(6, 13, 24, 0.35)');
    pupilGrad.addColorStop(1, 'transparent');
    ctx.fillStyle = pupilGrad;
    ctx.fillRect(0, 0, w, h);

    // 品牌文字淡入
    if (elapsed > BRAND_SHOW) {
      const brandAlpha = Math.min((elapsed - BRAND_SHOW) / 600, 1);
      brand.style.opacity = brandAlpha;
      brand.style.transform = brandAlpha >= 0.99 ? 'none' : `translateY(${(1 - brandAlpha) * 14}px)`;
    }

    if (t < 1) {
      animId = requestAnimationFrame(frame);
    } else {
      // 动画完成 → 渐隐 splash
      splash.classList.add('fade-out');
      setTimeout(function () { splash.style.display = 'none'; }, 950);
    }
  }

  animId = requestAnimationFrame(frame);
})();


const API = (function() {
  const base = '/api';
  async function req(path, opts = {}) {
    const url = base + path;
    const config = { headers: {}, ...opts };
    if (config.body && !(config.body instanceof FormData)) {
      config.headers['Content-Type'] = 'application/json';
      config.body = JSON.stringify(config.body);
    }
    const res = await fetch(url, config);
    if (!res.ok) {
      const err = new Error(`API ${res.status}: ${res.statusText}`);
      err.status = res.status;
      try { err.body = await res.json(); } catch(_) {}
      throw err;
    }
    const ct = res.headers.get('content-type') || '';
    return ct.includes('application/json') ? res.json() : res.text();
  }
  return {
    health:     () => req('/health'),
    models:     () => req('/models'),
    weights:    (modelId) => req('/weights?model=' + encodeURIComponent(modelId)),
    stats:      () => req('/stats'),
    images:     (type) => req('/images' + (type ? '?type=' + type : '')),
    upload:     (formData) => req('/images', { method: 'POST', body: formData }),
    deleteImg:  (id) => req('/images/' + encodeURIComponent(id), { method: 'DELETE' }),
    predict:    (payload) => req('/predict', { method: 'POST', body: payload }),
    task:       (id) => req('/tasks/' + encodeURIComponent(id)),
    train:      (payload) => req('/train', { method: 'POST', body: payload }),
    trainStatus:(id) => req('/train/' + encodeURIComponent(id)),
    trainHistory: () => req('/training-history'),
    exportUrl:  (id) => base + '/export/' + encodeURIComponent(id),
  };
})();

/* ---- State ---- */
const state = {
  models: [],
  selectedModel: null,
  weights: [],
  selectedWeight: null,
  images: [],
  galleryFilter: 'all',
  results: null,
  online: false,
  trainingTaskId: null,
  trainingPollTimer: null,
  trainedHistory: [],
  advParams: {},
  // Inference page
  infModels: [], infSelectedModel: null, infWeights: [], infSelectedWeight: null,
  infImages: [], infResults: null,
};

/* ---- DOM helpers ---- */
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
const el = (tag, cls, html) => { const e = document.createElement(tag); if(cls) e.className = cls; if(html!=null) e.innerHTML = html; return e; };

/* ---- Card hover tilt (transitions-dev 19) ---- */
function makeTilt(wrapper) {
  const card = wrapper.querySelector('.t-tilt-card');
  if (!card) return;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  const MAX = 10; // 峰值倾斜角度（度）
  function reset() {
    wrapper.classList.remove('is-hover');
    card.classList.remove('is-tilting');
    card.style.setProperty('--tilt-rx', '0deg');
    card.style.setProperty('--tilt-ry', '0deg');
  }
  function track(e) {
    if (reduce.matches) return;
    const r = wrapper.getBoundingClientRect();
    const px = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
    const py = Math.min(1, Math.max(0, (e.clientY - r.top) / r.height));
    wrapper.classList.add('is-hover');
    card.classList.add('is-tilting');
    card.style.setProperty('--tilt-ry', ((px - 0.5) * MAX).toFixed(2) + 'deg');
    card.style.setProperty('--tilt-rx', ((0.5 - py) * MAX).toFixed(2) + 'deg');
    card.style.setProperty('--tilt-gx', (px * 100).toFixed(1) + '%');
    card.style.setProperty('--tilt-gy', (py * 100).toFixed(1) + '%');
  }
  wrapper.addEventListener('pointermove', track);
  wrapper.addEventListener('pointerup', reset);
  wrapper.addEventListener('pointercancel', reset);
  wrapper.addEventListener('pointerleave', (e) => { if (e.pointerType === 'mouse') reset(); });
  wrapper.addEventListener('pointerdown', (e) => { if (e.pointerType !== 'mouse') { try { wrapper.setPointerCapture(e.pointerId); } catch (_) {} } });
}

/* ---- Toast ---- */
function toast(msg, type = 'info') {
  const t = el('div', 'toast ' + type);
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
  const color = type === 'success' ? 'normal-dark' : type === 'error' ? 'severe' : 'accent-dark';
  t.innerHTML = `<span style="font-weight:700;color:var(--${color})">${icon}</span><span>${msg}</span>`;
  $('#toastContainer').appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(40px)'; t.style.transition = 'all 300ms'; setTimeout(()=>t.remove(), 300); }, 3500);
}

/* ---- API status ---- */
async function checkApiStatus() {
  const badge = $('#apiStatus'); const text = $('#apiStatusText');
  try {
    const data = await API.health();
    state.online = true;
    badge.classList.add('online'); badge.classList.remove('offline');
    text.textContent = 'API 在线 · v' + (data.version || '2');
    return true;
  } catch (e) {
    state.online = false;
    badge.classList.add('offline'); badge.classList.remove('online');
    text.textContent = 'API 离线';
    return false;
  }
}

/* ---- Models ---- */
async function loadModels() {
  try {
    const data = await API.models();
    state.models = data.data?.models || data.models || [];
    $('#statModels').textContent = state.models.length;
    $('#modelHint').textContent = state.models.length + ' 个可用';
    renderModels();
  } catch (e) {
    $('#modelHint').textContent = '加载失败';
    toast('模型列表加载失败：' + e.message, 'error');
  }
}
function renderModels() {
  const grid = $('#modelGrid'); grid.innerHTML = '';
  state.models.forEach((m) => {
    const wrap = el('div', 't-tilt');
    const card = el('div', 'model-card t-tilt-card' + (state.selectedModel === m.id ? ' active' : ''));
    const abbr = (m.name || m.id).slice(0, 2).toUpperCase();
    card.innerHTML = `<div class="mc-icon">${abbr}</div><div class="mc-body"><div class="mc-name">${m.name}</div><div class="mc-desc">${m.description || m.architecture || ''}</div></div><div class="mc-check"></div><div class="t-tilt-glare"></div>`;
    card.addEventListener('click', () => selectModel(m.id));
    wrap.appendChild(card); grid.appendChild(wrap); makeTilt(wrap);
  });
}
async function selectModel(modelId) {
  if (state.selectedModel === modelId) {
    // 再次点击：取消选择
    state.selectedModel = null;
    state.selectedWeight = null;
    renderModels();
    await loadWeights(null);
    checkReady();
    return;
  }
  state.selectedModel = modelId;
  state.selectedWeight = null;
  renderModels();
  await loadWeights(modelId);
  checkReady();
}

/* ---- Weights ---- */
async function loadWeights(modelId) {
  if (!modelId) {
    state.weights = [];
    state.selectedWeight = null;
    $('#weightHint').textContent = '请先选择模型';
    $('#weightList').innerHTML = '<div class="weight-empty">请先选择模型</div>';
    renderWeights();
    checkReady();
    return;
  }
  $('#weightHint').textContent = '加载中…';
  $('#weightList').innerHTML = '<div class="weight-empty">加载中…</div>';
  try {
    const data = await API.weights(modelId);
    state.weights = data.data?.weights || data.weights || [];
    $('#weightHint').textContent = state.weights.length + ' 个权重';
    renderWeights();
    if (state.weights.length > 0 && !state.selectedWeight) selectWeight(state.weights[0].id);
  } catch (e) {
    $('#weightHint').textContent = '加载失败';
    $('#weightList').innerHTML = '<div class="weight-empty">权重加载失败</div>';
    toast('权重列表加载失败：' + e.message, 'error');
  }
}
function renderWeights() {
  const list = $('#weightList'); list.innerHTML = '';
  if (state.weights.length === 0) { list.innerHTML = '<div class="weight-empty">该模型暂无可用权重</div>'; return; }
  state.weights.forEach((w) => {
    const item = el('div', 'weight-item' + (state.selectedWeight === w.id ? ' active' : '') + (w.trained ? ' trained' : ''));
    const size = w.size_mb ? w.size_mb.toFixed(1) + ' MB' : '';
    const badge = w.trained ? '<span class="wi-badge">训练</span>' : '';
    item.innerHTML = `<div class="wi-radio"></div><span class="wi-name">${w.name}</span>${badge}<span class="wi-meta">${size}</span>`;
    item.addEventListener('click', () => selectWeight(w.id));
    list.appendChild(item);
  });
}
function selectWeight(weightId) {
  if (state.selectedWeight === weightId) {
    // 再次点击：取消选择
    state.selectedWeight = null;
    renderWeights();
    checkReady();
    return;
  }
  state.selectedWeight = weightId; renderWeights(); checkReady();
}

/* ---- Ready check ---- */
function checkReady() {
  const btn = $('#predictBtn');
  const ready = state.selectedModel && state.selectedWeight && state.images.length > 0 && state.online;
  btn.disabled = !ready;
}

/* ---- Upload ---- */
function setupUpload(zoneId, inputId, type) {
  const zone = $('#' + zoneId); const input = $('#' + inputId);
  zone.addEventListener('click', () => input.click());
  input.addEventListener('change', () => { if (input.files.length) handleFiles(input.files, type); input.value = ''; });
  ['dragenter','dragover'].forEach(ev => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add('dragover'); }));
  ['dragleave','drop'].forEach(ev => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove('dragover'); }));
  zone.addEventListener('drop', (e) => { if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files, type); });
}
async function handleFiles(files, type) {
  const imgFiles = Array.from(files).filter(f => f.type.startsWith('image/'));
  if (imgFiles.length === 0) { toast('请选择图片文件', 'error'); return; }
  for (const file of imgFiles) {
    const fd = new FormData();
    fd.append('file', file); fd.append('type', type);
    if (state.selectedModel) fd.append('model', state.selectedModel);
    if (state.selectedWeight) fd.append('weight', state.selectedWeight);
    try { const result = await API.upload(fd); state.images.push(result.data?.image || result.image || result); }
    catch (e) { toast(`上传失败：${file.name} — ${e.message}`, 'error'); }
  }
  toast(`成功上传 ${imgFiles.length} 张${type === 'normal' ? '正确' : '缺陷'}图片`, 'success');
  renderGallery(); updateStats(); updateTrainSummary(); checkReady();
}

/* ---- Gallery ---- */
function renderGallery() {
  const gallery = $('#gallery'); gallery.innerHTML = '';
  const filtered = state.galleryFilter === 'all' ? state.images : state.images.filter(i => i.type === state.galleryFilter);
  $('#cntAll').textContent = state.images.length;
  $('#cntNormalTab').textContent = state.images.filter(i => i.type === 'normal').length;
  $('#cntDefectTab').textContent = state.images.filter(i => i.type === 'defect').length;
  if (filtered.length === 0) { gallery.innerHTML = '<div class="gallery-empty">该分类下暂无样本</div>'; return; }
  filtered.forEach((img) => {
    const wrap = el('div', 't-tilt');
    const card = el('div', 'img-card t-tilt-card');
    const isDefect = img.type === 'defect';
    let resultBadge = '';
    if (img.result) {
      const v = img.result;
      if (v.verdict === 'defect') resultBadge = `<div class="img-result ${v.severity === 'critical' ? 'crit' : 'warn'}">缺陷 ${(v.confidence*100).toFixed(0)}%</div>`;
      else resultBadge = `<div class="img-result ok">正常 ${(v.confidence*100).toFixed(0)}%</div>`;
    }
    const confText = img.result ? (img.result.confidence*100).toFixed(1)+'%' : img.size_kb ? img.size_kb+'KB' : '';
    const confClass = img.result ? (img.result.confidence > 0.85 ? 'high' : 'mid') : '';
    card.innerHTML = `
      <div class="img-thumb">
        ${img.url ? `<img src="${img.url}" alt="${img.name}" loading="lazy">` : `<span class="placeholder">${img.name}</span>`}
        <span class="img-badge ${img.type}">${isDefect ? '缺陷' : '正常'}</span>
        ${resultBadge}
        <div class="img-del" title="删除"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></div>
      </div>
      <div class="img-meta"><span>${img.name && img.name.length > 16 ? img.name.slice(0,14)+'…' : (img.name||'')}</span><span class="conf ${confClass}">${confText}</span></div>`;
    card.querySelector('.img-del').addEventListener('click', async (e) => { e.stopPropagation(); await deleteImage(img.id); });
    wrap.appendChild(card); gallery.appendChild(wrap); makeTilt(wrap);
  });
}
async function deleteImage(id) {
  const prev = [...state.images];
  state.images = state.images.filter(i => i.id !== id);
  renderGallery(); updateStats(); updateTrainSummary(); checkReady();
  try { await API.deleteImg(id); toast('已删除图片', 'info'); }
  catch (e) { state.images = prev; renderGallery(); updateStats(); updateTrainSummary(); checkReady(); toast('删除失败：' + e.message, 'error'); }
}
function setupGalleryTabs() {
  $$('.gtab').forEach(tab => tab.addEventListener('click', () => {
    $$('.gtab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active'); state.galleryFilter = tab.dataset.filter; renderGallery();
  }));
}

/* ---- Stats ---- */
async function updateStats() {
  const normalCount = state.images.filter(i => i.type === 'normal').length;
  const defectCount = state.images.filter(i => i.type === 'defect').length;
  $('#statNormal').textContent = normalCount;
  $('#statDefect').textContent = defectCount;
  if (state.results && state.results.length > 0) {
    const correct = state.results.filter(r => r.expected_verdict === r.verdict).length;
    $('#statAccuracy').textContent = (correct / state.results.length * 100).toFixed(1) + '%';
  }
}

/* ---- Predict ---- */
async function runPredict() {
  if (!state.selectedModel || !state.selectedWeight) { toast('请先选择模型和权重', 'error'); return; }
  if (state.images.length === 0) { toast('请先上传样本图片', 'error'); return; }
  const overlay = $('#scanOverlay');
  const modelObj = state.models.find(m => m.id === state.selectedModel);
  const weightObj = state.weights.find(w => w.id === state.selectedWeight);
  $('#scanLabel').textContent = '正在执行缺陷检测…';
  $('#scanSub').textContent = `model: ${modelObj ? modelObj.name : state.selectedModel} · weight: ${weightObj ? weightObj.name : state.selectedWeight}`;
  overlay.classList.add('show');
  try {
    const payload = { model: state.selectedModel, weight: state.selectedWeight, image_ids: state.images.map(i => i.id) };
    const taskData = await API.predict(payload);
    const d = taskData.data || taskData;
    let result = d;
    if (taskData.task_id && taskData.status !== 'done' && taskData.status !== 'completed') {
      const polled = await pollTask(taskData.task_id);
      result = polled.data || polled;
    }
    state.results = result.results || [];
    if (state.results && state.results.length) {
      const resultMap = {}; state.results.forEach(r => { resultMap[r.image_id] = r; });
      state.images.forEach(img => { if (resultMap[img.id]) img.result = resultMap[img.id]; });
    }
    renderResults(); renderGallery(); updateStats();
    toast(`检测完成，共 ${state.results.length} 项结果`, 'success');
  } catch (e) { toast('检测失败：' + e.message, 'error'); }
  finally { overlay.classList.remove('show'); }
}
async function pollTask(taskId) {
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 1000));
    const t = await API.task(taskId);
    if (t.status === 'done' || t.status === 'completed' || t.status === 'success') return t;
    if (t.status === 'failed' || t.status === 'error') throw new Error(t.error || '检测任务失败');
    $('#scanLabel').textContent = '检测中… ' + Math.round((i+1)/60*100) + '%';
  }
  throw new Error('检测超时');
}

/* ---- Results ---- */
function renderResults() {
  const body = $('#resultsBody'); body.innerHTML = '';
  if (!state.results || state.results.length === 0) { body.innerHTML = '<div class="results-empty"><div>未获取到检测结果</div></div>'; return; }
  state.results.forEach((r) => {
    const row = el('div', 'result-row');
    const verdict = r.verdict || 'normal';
    const conf = r.confidence || 0;
    const sevClass = r.severity === 'critical' ? 'crit' : verdict === 'defect' ? 'warn' : 'ok';
    const vTag = verdict === 'defect' ? (r.severity === 'critical' ? '严重缺陷' : '缺陷') : '正常';
    const confPct = (conf * 100).toFixed(1);
    const img = state.images.find(i => i.id === r.image_id);
    row.innerHTML = `
      <div class="result-thumb">${img && img.url ? `<img src="${img.url}" alt="">` : ''}</div>
      <div class="result-info"><div class="ri-name">${r.image_name || (img ? img.name : r.image_id)}</div><div class="ri-detail">${r.defect_type ? '类型: ' + r.defect_type + ' · ' : ''}置信度 ${confPct}%${r.processing_ms ? ' · ' + r.processing_ms + 'ms' : ''}</div></div>
      <div class="result-verdict"><div class="conf-bar"><div class="fill ${sevClass}" style="width:${confPct}%"></div></div><span class="verdict-tag ${sevClass}">${vTag}</span></div>`;
    body.appendChild(row);
  });
}

/* ============================================================
   Training & Export
   ============================================================ */
// train.py 中 parse_args() 的参数定义（名称/类型/默认/分组/帮助）
const TRAIN_PARAMS = [
  // YOLO
  { name: 'yolo_epochs',        type: 'int',    def: 50,   group: 'yolo', help: 'YOLO 训练轮数' },
  { name: 'imgsz',              type: 'int',    def: 640,  group: 'yolo', help: '输入图像尺寸' },
  { name: 'yolo_batch_size',    type: 'int',    def: 16,   group: 'yolo', help: 'YOLO 批大小' },
  { name: 'workers',            type: 'int',    def: 4,    group: 'yolo', help: '数据加载线程数' },
  { name: 'patience',           type: 'int',    def: 10,   group: 'yolo', help: '早停耐心值' },
  { name: 'freeze',             type: 'int',    def: 20,   group: 'yolo', help: '冻结主干前 N 层（0=全量微调）' },
  { name: 'yolo_lr',            type: 'float',  def: 0.001,group: 'yolo', help: 'YOLO 初始学习率' },
  { name: 'lrf',                type: 'float',  def: 0.1,  group: 'yolo', help: '最终学习率因子 (final=lr0*lrf)' },
  { name: 'cos_lr',             type: 'bool',   def: true,  group: 'yolo', help: '使用 cosine 学习率衰减' },
  { name: 'full_train',         type: 'flag',   def: false, group: 'yolo', help: '全量训练模式（不冻结 backbone）' },
  // SAM2
  { name: 'sam2_epochs',        type: 'int',    def: 8,    group: 'sam2', help: 'SAM2 训练轮数' },
  { name: 'sam2_batch_size',    type: 'int',    def: 8,    group: 'sam2', help: 'SAM2 批大小' },
  { name: 'lora_rank',          type: 'int',    def: 16,   group: 'sam2', help: 'LoRA rank' },
  { name: 'use_dora',           type: 'bool',   def: true,  group: 'sam2', help: '是否使用 DoRA' },
  { name: 'sam2_lr',            type: 'float',  def: 0.0002,group: 'sam2', help: 'SAM2 学习率' },
  { name: 'weight_decay',       type: 'float',  def: 0.01,  group: 'sam2', help: '权重衰减' },
];
const _TRAIN_DEFAULTS = Object.fromEntries(TRAIN_PARAMS.map(p => [p.name, p.def]));

function _advFieldHtml(p) {
  const id = 'adv_' + p.name;
  const val = state.advParams[p.name] !== undefined ? state.advParams[p.name] : p.def;
  if (p.type === 'bool' || p.type === 'flag') {
    const checked = val ? 'checked' : '';
    return `<div class="adv-field${p.auto ? ' full' : ''}">
      <label class="chk"><input type="checkbox" id="${id}" ${checked}> ${p.name}${p.auto ? '（自动）' : ''}</label>
      <span class="help">${p.help}</span>
    </div>`;
  }
  const full = p.auto ? ' full' : '';
  const disp = p.auto ? '（自动生成，可覆盖）' : '';
  return `<div class="adv-field${full}">
    <label>${p.name}<span class="dv">默认 ${p.def}</span></label>
    <input type="${p.type === 'int' || p.type === 'float' ? 'number' : 'text'}" id="${id}"
      ${p.type === 'int' ? 'step="1"' : ''}${p.type === 'float' ? 'step="any"' : ''}
      value="${val}">
    <span class="help">${p.help}${disp}</span>
  </div>`;
}

function populateAdvFields() {
  const groups = { yolo: $('#advFieldsYolo'), sam2: $('#advFieldsSam2') };
  for (const k in groups) groups[k].innerHTML = '';
  TRAIN_PARAMS.forEach(p => {
    const host = groups[p.group];
    if (host) host.insertAdjacentHTML('beforeend', _advFieldHtml(p));
  });
}

function collectAdvParams() {
  const out = {};
  TRAIN_PARAMS.forEach(p => {
    const id = 'adv_' + p.name;
    const node = document.getElementById(id);
    if (!node) return;
    let v;
    if (p.type === 'bool' || p.type === 'flag') {
      v = node.checked;
    } else if (p.type === 'int') {
      v = node.value === '' ? p.def : parseInt(node.value, 10);
    } else if (p.type === 'float') {
      v = node.value === '' ? p.def : parseFloat(node.value);
    } else {
      v = node.value;
    }
    // 仅保留与被自动默认值不同的用户修改；auto 字段（路径类）始终保留用户输入（含空=用后端自动值）
    if (p.auto) {
      if (node.value !== '') out[p.name] = v; // 用户覆盖了自动路径才发送
    } else if (String(v) !== String(p.def)) {
      out[p.name] = v;
    }
  });
  return out;
}

let advCloseTimer = null;
function openAdvModal() {
  populateAdvFields();
  const m = $('#advModal');
  if (advCloseTimer) { clearTimeout(advCloseTimer); advCloseTimer = null; }
  m.style.display = 'flex';
  const modal = m.querySelector('.t-modal');
  modal.classList.remove('is-closing');
  requestAnimationFrame(() => modal.classList.add('is-open'));
}
function closeAdvModal() {
  const m = $('#advModal');
  const modal = m.querySelector('.t-modal');
  const closeMs = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--modal-close-dur')) || 150;
  modal.classList.remove('is-open');
  modal.classList.add('is-closing');
  advCloseTimer = setTimeout(() => { modal.classList.remove('is-closing'); m.style.display = 'none'; advCloseTimer = null; }, closeMs);
}

function updateTrainSummary() {
  const n = state.images.filter(i => i.type === 'normal').length;
  const d = state.images.filter(i => i.type === 'defect').length;
  $('#tdsNormal').textContent = n + ' 张';
  $('#tdsDefect').textContent = d + ' 张';
  $('#tdsTotal').textContent = (n + d) + ' 张';
  const yoloEpochs = state.advParams.yolo_epochs || _TRAIN_DEFAULTS.yolo_epochs;
  const sam2Epochs = state.advParams.sam2_epochs || _TRAIN_DEFAULTS.sam2_epochs;
  $('#tdsEstimate').textContent = '~' + (yoloEpochs * 0.4 + sam2Epochs * 0.4).toFixed(1) + 's';
  const hasData = (n + d) > 0;
  $('#trainBtn').disabled = !hasData || !state.online || !!state.trainingTaskId;
  const changed = Object.keys(state.advParams).length > 0;
  $('#advHint').textContent = changed ? `已自定义 ${Object.keys(state.advParams).length} 项参数` : '默认参数 · 点击可修改';
}

function setupTrainingControls() {
  $('#advOptionsBtn').addEventListener('click', openAdvModal);
  $('#advClose').addEventListener('click', closeAdvModal);
  $('#advModal').addEventListener('click', (e) => { if (e.target === $('#advModal')) closeAdvModal(); });
  $('#advReset').addEventListener('click', () => { state.advParams = {}; populateAdvFields(); });
  $('#advConfirm').addEventListener('click', () => {
    state.advParams = collectAdvParams();
    closeAdvModal();
    updateTrainSummary();
  });
  // Train button
  $('#trainBtn').addEventListener('click', startTraining);
}

async function startTraining() {
  const normalIds = state.images.filter(i => i.type === 'normal').map(i => i.id);
  const defectIds = state.images.filter(i => i.type === 'defect').map(i => i.id);
  if (normalIds.length === 0 && defectIds.length === 0) { toast('请先上传训练图片', 'error'); return; }

  $('#trainBtn').disabled = true;
  $('#trainProgress').classList.add('show');
  $('#tpTotalEpoch').textContent = state.advParams.yolo_epochs || _TRAIN_DEFAULTS.yolo_epochs;
  $('#tpEpoch').textContent = '0';
  $('#tpPct').textContent = '0%';
  $('#tpFill').style.width = '0%';
  $('#tpLoss').textContent = '—';
  $('#tpValLoss').textContent = '—';
  $('#tpAcc').textContent = '—';
  $('#tpStage').textContent = '准备中';

  try {
    const payload = {
      params: state.advParams,
      normal_image_ids: normalIds,
      defect_image_ids: defectIds,
    };
    const data = await API.train(payload);
    const d = data.data || data;
    state.trainingTaskId = d.task_id;
    toast('训练已启动，预计 ' + d.estimated_seconds + 's', 'info');
    pollTraining(d.task_id);
  } catch (e) {
    toast('训练启动失败：' + e.message, 'error');
    $('#trainProgress').classList.remove('show');
    $('#trainBtn').disabled = false;
  }
}

async function pollTraining(taskId) {
  if (state.trainingPollTimer) clearInterval(state.trainingPollTimer);
  state.trainingPollTimer = setInterval(async () => {
    try {
      const resp = await API.trainStatus(taskId);
      const t = resp.data || resp;
      // Update progress UI
      const pct = Math.round((t.progress || 0) * 100);
      $('#tpEpoch').textContent = t.current_epoch || 0;
      $('#tpStage').textContent = t.stage || (t.status === 'training' ? '训练中' : t.status);
      $('#tpPct').textContent = pct + '%';
      $('#tpFill').style.width = pct + '%';
      if (t.loss != null) $('#tpLoss').textContent = t.loss.toFixed(4);
      if (t.val_loss != null) $('#tpValLoss').textContent = t.val_loss.toFixed(4);
      if (t.accuracy != null) $('#tpAcc').textContent = (t.accuracy * 100).toFixed(1) + '%';

      if (t.status === 'error') {
        clearInterval(state.trainingPollTimer);
        state.trainingPollTimer = null;
        state.trainingTaskId = null;
        $('#trainBtn').disabled = false;
        toast('训练失败：' + (t.error || '未知错误'), 'error');
        return;
      }

      if (t.status === 'done') {
        clearInterval(state.trainingPollTimer);
        state.trainingPollTimer = null;
        state.trainingTaskId = null;
        $('#trainBtn').disabled = false;
        const acc = (t.final_accuracy * 100).toFixed(1);
        toast(`训练完成！准确率 ${acc}%`, 'success');
        // Refresh weights to include the new trained weight
        if (state.selectedModel) await loadWeights(state.selectedModel);
        await loadTrainingHistory();
        await loadStats();
        updateTrainSummary();
      }
    } catch (e) {
      clearInterval(state.trainingPollTimer);
      state.trainingPollTimer = null;
      state.trainingTaskId = null;
      $('#trainBtn').disabled = false;
      toast('训练状态查询失败：' + e.message, 'error');
    }
  }, 800);
}

async function loadTrainingHistory() {
  try {
    const data = await API.trainHistory();
    state.trainedHistory = data.tasks || [];
    renderTrainedList();
    $('#statTrained').textContent = state.trainedHistory.filter(t => t.status === 'done').length;
  } catch (e) { /* silent */ }
}

function renderTrainedList() {
  const container = $('#trainedItems');
  const empty = $('#trainedEmpty');
  container.innerHTML = '';
  const done = state.trainedHistory.filter(t => t.status === 'done');
  if (done.length === 0) { empty.style.display = 'block'; return; }
  empty.style.display = 'none';

  done.forEach((t) => {
    const modelObj = state.models.find(m => m.id === t.model);
    const modelName = modelObj ? modelObj.name : t.model;
    const acc = (t.accuracy * 100).toFixed(1);
    const item = el('div', 'trained-item');
    item.innerHTML = `
      <div class="ti-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg></div>
      <div class="ti-info">
        <div class="ti-name">${modelName} · 训练权重</div>
        <div class="ti-meta">准确率 ${acc}% · ${t.epochs} epoch · ${t.normal_count}正常+${t.defect_count}缺陷 · ${t.weight_id || ''}</div>
      </div>
      <div class="ti-actions">
        <button class="btn btn-ghost btn-sm" data-action="use" data-model="${t.model}" data-weight="${t.weight_id}">在线使用</button>
        <a class="btn btn-ghost btn-sm" href="${API.exportUrl(t.id)}" download>导出模型</a>
      </div>`;
    item.querySelector('[data-action="use"]').addEventListener('click', () => useTrainedModel(t.model, t.weight_id));
    container.appendChild(item);
  });
}

async function useTrainedModel(modelId, weightId) {
  // Select the model and weight
  if (state.selectedModel !== modelId) {
    await selectModel(modelId);
  }
  // Wait for weights to load then select
  setTimeout(() => {
    selectWeight(weightId);
    toast('已切换至训练模型，可直接执行检测', 'success');
    // Scroll to config
    $('.workspace').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, state.selectedModel !== modelId ? 500 : 0);
}

/* ============================================================
   Inference page (screen 3) — Model/Weight select + upload + detect
   ============================================================ */
async function loadInfModels() {
  try {
    const data = await API.models();
    state.infModels = data.data?.models || data.models || [];
    renderInfModels();
  } catch (e) { toast('模型列表加载失败', 'error'); }
}
function renderInfModels() {
  const grid = $('#infModelGrid'); grid.innerHTML = '';
  state.infModels.forEach((m) => {
    const wrap = el('div', 't-tilt');
    const card = el('div', 'model-card t-tilt-card' + (state.infSelectedModel === m.id ? ' active' : ''));
    card.innerHTML = `<div class="mc-icon">${(m.name||'').slice(0,2).toUpperCase()}</div><div class="mc-body"><div class="mc-name">${m.name}</div><div class="mc-desc">${m.description||''}</div></div><div class="mc-check"></div><div class="t-tilt-glare"></div>`;
    card.addEventListener('click', () => selectInfModel(m.id));
    wrap.appendChild(card); grid.appendChild(wrap); makeTilt(wrap);
  });
}
async function selectInfModel(modelId) {
  if (state.infSelectedModel === modelId) { state.infSelectedModel = null; state.infSelectedWeight = null; renderInfModels(); await loadInfWeights(null); infCheckReady(); return; }
  state.infSelectedModel = modelId; state.infSelectedWeight = null; renderInfModels(); await loadInfWeights(modelId); infCheckReady();
}
async function loadInfWeights(modelId) {
  if (!modelId) { state.infWeights = []; state.infSelectedWeight = null; $('#infWeightHint').textContent = '请先选择模型'; $('#infWeightList').innerHTML = '<div class="weight-empty">请先选择模型</div>'; infCheckReady(); return; }
  $('#infWeightHint').textContent = '加载中…';
  try {
    const data = await API.weights(modelId);
    state.infWeights = data.data?.weights || data.weights || [];
    renderInfWeights();
    if (state.infWeights.length > 0 && !state.infSelectedWeight) selectInfWeight(state.infWeights[0].id);
  } catch (e) { toast('权重加载失败', 'error'); }
}
function renderInfWeights() {
  const list = $('#infWeightList'); list.innerHTML = '';
  if (state.infWeights.length === 0) { list.innerHTML = '<div class="weight-empty">暂无可用权重</div>'; return; }
  state.infWeights.forEach((w) => {
    const item = el('div', 'weight-item' + (state.infSelectedWeight === w.id ? ' active' : ''));
    item.innerHTML = `<div class="wi-radio"></div><span class="wi-name">${w.name}</span><span class="wi-meta">${w.size_mb||''} MB</span>`;
    item.addEventListener('click', () => selectInfWeight(w.id));
    list.appendChild(item);
  });
}
function selectInfWeight(wid) {
  if (state.infSelectedWeight === wid) { state.infSelectedWeight = null; renderInfWeights(); infCheckReady(); return; }
  state.infSelectedWeight = wid; renderInfWeights(); infCheckReady();
}
function infCheckReady() {
  $('#infPredictBtn').disabled = !(state.infSelectedModel && state.infSelectedWeight && state.infImages.length > 0 && state.online);
}

/* Inference upload */
function setupInfUpload() {
  const zone = $('#zoneInference'); const input = $('#inputInference');
  zone.addEventListener('click', () => input.click());
  input.addEventListener('change', () => { if (input.files.length) handleInfFiles(input.files); input.value = ''; });
  ['dragenter','dragover'].forEach(ev => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add('dragover'); }));
  ['dragleave','drop'].forEach(ev => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove('dragover'); }));
  zone.addEventListener('drop', (e) => { if (e.dataTransfer.files.length) handleInfFiles(e.dataTransfer.files); });
}
async function handleInfFiles(files) {
  const imgFiles = Array.from(files).filter(f => f.type.startsWith('image/'));
  if (imgFiles.length === 0) { toast('请选择图片文件', 'error'); return; }
  for (const file of imgFiles) {
    const fd = new FormData(); fd.append('file', file); fd.append('type', 'normal');
    try {
      const resp = await API.upload(fd);
      const img = resp.data?.image || resp.image || resp;
      state.infImages.push(img);
    } catch (e) { toast(`上传失败: ${file.name}`, 'error'); }
  }
  toast(`成功上传 ${imgFiles.length} 张图片`, 'success');
  infCheckReady();
}

/* Inference predict */
async function runInfPredict() {
  if (!state.infSelectedModel || !state.infSelectedWeight) { toast('请先选择模型和权重', 'error'); return; }
  if (state.infImages.length === 0) { toast('请先上传待检测图片', 'error'); return; }
  const overlay = $('#scanOverlay');
  $('#scanLabel').textContent = '正在执行缺陷检测…';
  overlay.classList.add('show');
  try {
    const payload = { model: state.infSelectedModel, weight: state.infSelectedWeight, image_ids: state.infImages.map(i => i.id) };
    const resp = await API.predict(payload);
    const task = resp.data || resp;
    state.infResults = task.results || [];
    renderInfResults();
    toast(`检测完成，共 ${state.infResults.length} 项结果`, 'success');
  } catch (e) { toast('检测失败: ' + e.message, 'error'); }
  finally { overlay.classList.remove('show'); }
}
function renderInfResults() {
  const body = $('#infResultsBody'); body.innerHTML = '';
  if (!state.infResults || state.infResults.length === 0) { body.innerHTML = '<div class="results-empty"><div>未获取到检测结果</div></div>'; return; }
  state.infResults.forEach((r) => {
    const row = el('div', 'result-row');
    const verdict = r.verdict || 'normal';
    const conf = r.confidence || 0;
    const sevClass = r.severity === 'critical' ? 'crit' : verdict === 'defect' ? 'warn' : 'ok';
    const vTag = verdict === 'defect' ? (r.severity === 'critical' ? '严重缺陷' : '缺陷') : '正常';
    const img = state.infImages.find(i => i.id === r.image_id);
    row.innerHTML = `
      <div class="result-thumb">${img && img.url ? `<img src="${img.url}" alt="">` : ''}</div>
      <div class="result-info"><div class="ri-name">${r.image_name || (img ? img.name : '')}</div><div class="ri-detail">${r.defect_type ? '类型: '+r.defect_type+' · ' : ''}置信度 ${(conf*100).toFixed(1)}%</div></div>
      <div class="result-verdict"><div class="conf-bar"><div class="fill ${sevClass}" style="width:${(conf*100).toFixed(1)}%"></div></div><span class="verdict-tag ${sevClass}">${vTag}</span></div>`;
    body.appendChild(row);
  });
}

/* ---- Stats from API ---- */
async function loadStats() {
  try {
    const data = await API.stats();
    if (data.recent_accuracy != null && data.recent_accuracy > 0) {
      $('#statAccuracy').textContent = (data.recent_accuracy * 100).toFixed(1) + '%';
    }
    if (data.trained_weights != null) $('#statTrained').textContent = data.trained_weights;
  } catch (e) { /* silent */ }
}

/* ---- Scroll reveal ---- */
function setupReveal() {
  const items = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window)) { items.forEach(i => i.classList.add('in')); return; }
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
  }, { threshold: 0.12 });
  items.forEach(i => io.observe(i));
}

/* ---- Multi-screen scroll jumps (3 screens) ---- */
function setupMultiScreenScroll() {
  const hero = document.getElementById('heroLanding');
  const ws = document.getElementById('workspace');
  const inf = document.getElementById('heroInference');
  const upCue = document.getElementById('scrollUp');
  const upCueInf = document.getElementById('scrollUpInf');
  if (!hero || !ws || !inf) return;

  // 顶栏在滚动后隐藏（body.scrolled），故第二、三屏锚点落在其真实顶部（不再扣 71px），
  // 避免落在上一屏的 71px 余量上从而露出上一屏。首屏落在文档顶端（顶栏可见）。
  const ANCHORS = [hero, ws, inf];
  const anchorTops = () => ANCHORS.map((elm, i) => {
    const top = Math.round(elm.getBoundingClientRect().top + window.scrollY);
    return i === 0 ? 0 : top;
  });
  const currentIndex = () => {
    const sy = window.scrollY;
    const tops = anchorTops();
    let idx = 0, best = Infinity;
    tops.forEach((y, i) => { const d = Math.abs(sy - y); if (d < best) { best = d; idx = i; } });
    return idx;
  };
  let jumpLock = false;
  const jumpTo = (i) => {
    jumpLock = true;
    window.scrollTo({ top: anchorTops()[i], behavior: 'smooth' });
    setTimeout(() => { jumpLock = false; }, 700); // 防连跳：一次手势只切一屏
  };

  // 进入视口时重放屏幕切换过渡（transitions-dev page switch）
  // 用双 rAF 分离「加 is-entering」与「移除」，确保过渡起点被浏览器采纳
  const _screenIO = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (en.isIntersecting && en.intersectionRatio >= 0.55) {
        const t = en.target;
        t.classList.add('is-entering');
        requestAnimationFrame(() => requestAnimationFrame(() => t.classList.remove('is-entering')));
      }
    });
  }, { threshold: [0, 0.55, 1] });
  ANCHORS.forEach((a) => _screenIO.observe(a));

  // 是否处于可滚动内部容器（面板 body）且仍有滚动余量：是则放行原生滚动，不劫持
  const inInnerScroll = (e) => {
    let node = e.target;
    while (node && node !== document.body) {
      const oy = getComputedStyle(node).overflowY;
      if ((oy === 'auto' || oy === 'scroll') && node.scrollHeight > node.clientHeight + 1) {
        if (e.deltaY > 0 && node.scrollTop + node.clientHeight < node.scrollHeight - 1) return true;
        if (e.deltaY < 0 && node.scrollTop > 1) return true;
      }
      node = node.parentElement;
    }
    return false;
  };

  // 滚轮：以「当前所在屏」为准，整屏吸附跳转到相邻屏
  window.addEventListener('wheel', (e) => {
    if (jumpLock) { e.preventDefault(); return; }
    if (inInnerScroll(e)) return;
    const idx = currentIndex();
    if (e.deltaY > 0 && idx < ANCHORS.length - 1) {
      e.preventDefault(); jumpTo(idx + 1); return;
    }
    if (e.deltaY < 0 && idx > 0) {
      e.preventDefault(); jumpTo(idx - 1); return;
    }
  }, { passive: false });

  // 键盘：方向键 / 翻页 / 空格 在屏间跳转
  window.addEventListener('keydown', (e) => {
    const tag = (document.activeElement && document.activeElement.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    const idx = currentIndex();
    if ((e.key === 'ArrowDown' || e.key === 'PageDown' || e.key === ' ') && idx < ANCHORS.length - 1) {
      e.preventDefault(); jumpTo(idx + 1);
    } else if ((e.key === 'ArrowUp' || e.key === 'PageUp') && idx > 0) {
      e.preventDefault(); jumpTo(idx - 1);
    }
  });

  if (upCue) upCue.addEventListener('click', (e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }); });
  if (upCueInf) upCueInf.addEventListener('click', (e) => { e.preventDefault(); jumpTo(1); });

  function onScroll() {
    const scrolled = window.scrollY > 2;
    document.body.classList.toggle('scrolled', scrolled);
    if (upCue) upCue.classList.toggle('show', scrolled);
    if (upCueInf) upCueInf.classList.toggle('show', currentIndex() === 2); // 仅第三屏显示「回到工作区」
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

/* ---- Typewriter title ---- */
function startTypewriter() {
  const target = $('#typewriterText');
  if (!target) return;

  const text = '视觉缺陷检测 训练与推理平台';
  const hlStart = 7;
  let i = 0;

  function type() {
    if (i < text.length) {
      const ch = text.charAt(i);
      if (i < hlStart) {
        target.textContent += ch;
      } else {
        if (i === hlStart) {
          const hl = document.createElement('span');
          hl.className = 'hl';
          hl.textContent = ch;
          target.appendChild(hl);
        } else {
          const hl = target.querySelector('.hl');
          if (hl) hl.textContent += ch;
        }
      }
      i++;
      setTimeout(type, 80 + Math.random() * 60);
    }
  }

  setTimeout(type, 500);
}

/* ---- Init ---- */
async function init() {
  setupUpload('zoneNormal', 'inputNormal', 'normal');
  setupUpload('zoneDefect', 'inputDefect', 'defect');
  setupGalleryTabs();
  setupTrainingControls();
  setupReveal();
  setupMultiScreenScroll();
  $('#predictBtn').addEventListener('click', runPredict);

  // Inference page setup
  setupInfUpload();
  $('#infPredictBtn').addEventListener('click', runInfPredict);

  // 入场动画结束后启动打字机效果
  setTimeout(startTypewriter, 4300);

  const online = await checkApiStatus();
  if (online) {
    await Promise.all([loadModels(), refreshImages(), loadTrainingHistory(), loadStats(), loadInfModels()]);
  } else {
    toast('API 后端未连接，请启动后端服务', 'error');
    $('#modelHint').textContent = '离线';
  }
  checkReady();
  updateTrainSummary();
  setInterval(checkApiStatus, 30000);
}

async function refreshImages() {
  try {
    const data = await API.images();
    state.images = data.data?.images || data.images || [];
    renderGallery(); updateStats(); updateTrainSummary(); checkReady();
  } catch (e) { /* silent */ }
}

document.addEventListener('DOMContentLoaded', init);