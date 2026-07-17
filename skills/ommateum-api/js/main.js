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

  var HEX_VERT = [];
  for (var vi = 0; vi < 6; vi++) {
    var va = (Math.PI / 3) * vi - Math.PI / 6;
    HEX_VERT.push({ c: Math.cos(va), s: Math.sin(va) });
  }
  function drawHex(ctx, x, y, r, fill, stroke, lw) {
    ctx.beginPath();
    for (var i = 0; i < 6; i++) {
      var px = x + r * HEX_VERT[i].c;
      var py = y + r * HEX_VERT[i].s;
      i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
    }
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw || 1; ctx.stroke(); }
  }

  var hexR = 22, hexW = Math.sqrt(3) * hexR, hexH = 2 * hexR;
  var hGap = hexW, vGap = hexH * 0.78;
  let startTs = null;
  const TOTAL = 7000, BRAND_SHOW = 4200;

  function frame(ts) {
    if (!startTs) startTs = ts;
    const elapsed = ts - startTs, t = Math.min(elapsed / TOTAL, 1);
    const w = window.innerWidth, h = window.innerHeight;
    ctx.clearRect(0, 0, w, h);
    const cx = w / 2, cy = h / 2, maxD = Math.sqrt(cx * cx + cy * cy);
    const breath = 1 + 0.06 * Math.sin(elapsed * 0.0018);
    const lookX = cx + Math.sin(elapsed * 0.0004) * w * 0.06;
    const lookY = cy + Math.cos(elapsed * 0.00055) * h * 0.06;
    const cols = Math.ceil(w / hGap) + 3, rows = Math.ceil(h / vGap) + 3;

    for (let row = -1; row < rows; row++) {
      for (let col = -1; col < cols; col++) {
        const ox = (row % 2 === 0) ? hGap / 2 : 0;
        const x = col * hGap + ox, y = row * vGap;
        const dx = x - lookX, dy = y - lookY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const dNorm = Math.min(dist / maxD, 1);
        const r = hexR * (1.3 - 0.55 * dNorm) * breath;
        if (r < 2.5) continue;
        const dissolveIn = Math.min(t * 2.5, 1);
        const dissolveOut = t > 0.20 ? Math.max(1 - (t - 0.20) / 0.18, 0) : 1;
        const dissolve = dissolveIn * dissolveOut;
        const hue = 195 + dNorm * 40, sat = 55 + dNorm * 20, light = 45 + dNorm * 30;

        ctx.globalAlpha = (0.85 + 0.1 * (1 - dNorm)) * dissolve;
        drawHex(ctx, x, y, r, `hsl(${hue}, ${sat}%, ${light}%)`, null, 0);
        ctx.globalAlpha = 0.22 * dissolve;
        drawHex(ctx, x, y, r, null, `hsla(${hue+20},${sat}%,${light+20}%,0.5)`, 0.7);

        var hlR = r * 0.42;
        ctx.globalAlpha = (0.5 + 0.2 * (1 - dNorm)) * dissolve;
        drawHex(ctx, x, y, hlR, 'rgba(255,255,255,0.55)', null, 0);
        var dotR = hlR * 0.3;
        if (dotR > 2) {
          ctx.globalAlpha = 0.6 * dissolve;
          ctx.beginPath(); ctx.arc(x - r*0.08, y - r*0.12, dotR, 0, Math.PI*2);
          ctx.fillStyle = 'rgba(255,255,255,0.7)'; ctx.fill();
        }
        if (r > 8) {
          ctx.globalAlpha = 0.15 * dissolve;
          drawHex(ctx, x, y, r*0.7, null, `hsla(${hue+10},40%,70%,0.4)`, 0.5);
        }
      }
    }

    const vg = ctx.createRadialGradient(cx, cy, w*0.25, cx, cy, w*0.85);
    vg.addColorStop(0,'transparent'); vg.addColorStop(0.5,'rgba(14,165,233,0.08)'); vg.addColorStop(1,'rgba(14,165,233,0.18)');
    ctx.globalAlpha=1; ctx.fillStyle=vg; ctx.fillRect(0,0,w,h);
    const pg = ctx.createRadialGradient(lookX, lookY, hexR*1.5, lookX, lookY, hexR*6);
    pg.addColorStop(0,'rgba(14,165,233,0.15)'); pg.addColorStop(1,'transparent');
    ctx.fillStyle=pg; ctx.fillRect(0,0,w,h);

    if (elapsed > BRAND_SHOW) {
      const ba = Math.min((elapsed - BRAND_SHOW) / 600, 1);
      brand.style.opacity = ba; brand.style.transform = ba>=0.99?'none':`translateY(${(1-ba)*14}px)`;
    }
    if (t < 1) { animId = requestAnimationFrame(frame); }
    else {
      window.scrollTo({left:0,top:0,behavior:'instant'});
      document.body.classList.remove('scrolled');
      splash.classList.add('fade-out');
      setTimeout(function(){splash.style.display='none';},950);
    }
  }
  animId = requestAnimationFrame(frame);
})();

/* ============================================================
   动态粒子背景
   ============================================================ */
(function initBgParticles() {
  const canvas = document.getElementById('bgCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H, particles = [];
  let mouse = { x: -9999, y: -9999 };
  let isRunning = false;
  const COUNT = 80, MAX_DIST = 150, SPEED = 0.35, MOUSE_RADIUS = 200;

  function resize() {
    const dpr = window.devicePixelRatio || 1;
    W = window.innerWidth; H = window.innerHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  resize(); window.addEventListener('resize', resize);

  class Particle {
    constructor() { this.reset(true); }
    reset(init) {
      this.x = init ? Math.random()*W : (Math.random()<0.5?0:W);
      this.y = init ? Math.random()*H : Math.random()*H;
      this.vx = (Math.random()-0.5)*SPEED*2; this.vy = (Math.random()-0.5)*SPEED*2;
      this.r = Math.random()*2.2+1.0; this.hue = 195+Math.random()*30;
      this.sat = 60+Math.random()*30; this.light = 55+Math.random()*25;
      this.alpha = 0.35+Math.random()*0.35;
    }
    update() {
      this.x+=this.vx; this.y+=this.vy;
      if(this.x<-20||this.x>W+20)this.vx*=-1; if(this.y<-20||this.y>H+20)this.vy*=-1;
      this.x=Math.max(-20,Math.min(W+20,this.x)); this.y=Math.max(-20,Math.min(H+20,this.y));
    }
    draw() {
      ctx.beginPath(); ctx.arc(this.x,this.y,this.r,0,Math.PI*2);
      ctx.fillStyle=`hsla(${this.hue},${this.sat}%,${this.light}%,${this.alpha})`; ctx.fill();
    }
  }
  function init() { particles=[]; for(let i=0;i<COUNT;i++) particles.push(new Particle()); }
  init();
  function drawLines() {
    for(let i=0;i<particles.length;i++) for(let j=i+1;j<particles.length;j++) {
      const dx=particles[i].x-particles[j].x, dy=particles[i].y-particles[j].y, dist=Math.sqrt(dx*dx+dy*dy);
      if(dist<MAX_DIST) {
        ctx.beginPath(); ctx.moveTo(particles[i].x,particles[i].y); ctx.lineTo(particles[j].x,particles[j].y);
        ctx.strokeStyle=`hsla(205,70%,70%,${(1-dist/MAX_DIST)*0.30})`; ctx.lineWidth=0.6; ctx.stroke();
      }
    }
  }
  function handleMouse(e){mouse.x=e.clientX;mouse.y=e.clientY;}
  function handleLeave(){mouse.x=-9999;mouse.y=-9999;}
  function applyMouseInfluence() {
    for(const p of particles){
      const dx=p.x-mouse.x, dy=p.y-mouse.y, dist=Math.sqrt(dx*dx+dy*dy);
      if(dist<MOUSE_RADIUS&&dist>0){const force=(1-dist/MOUSE_RADIUS)*0.3;p.vx+=(dx/dist)*force;p.vy+=(dy/dist)*force;}
    }
  }
  document.addEventListener('mousemove',handleMouse); document.addEventListener('mouseleave',handleLeave);
  function animate() {
    ctx.fillStyle='rgba(238,243,248,0.25)'; ctx.fillRect(0,0,W,H);
    if(isRunning) applyMouseInfluence();
    for(const p of particles){p.update();p.draw();}
    drawLines(); requestAnimationFrame(animate);
  }
  isRunning=true; ctx.clearRect(0,0,W,H);
  setTimeout(()=>{canvas.classList.add('visible');},100);
  animate();
  const splash=document.getElementById('splashScreen');
  if(splash){const obs=new MutationObserver(function(){}); obs.observe(splash,{attributes:true,attributeFilter:['style']});}
  window.addEventListener('resize',function(){resize();for(const p of particles){p.x=Math.max(0,Math.min(W,p.x));p.y=Math.max(0,Math.min(H,p.y));}});
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
    const ct = res.headers.get('content-type') || '';
    let body;
    try { body = ct.includes('json') ? await res.json() : await res.text(); } catch(_) { body = null; }
    if (!res.ok) throw new Error((body && body.error) || `HTTP ${res.status}`);
    return (body && typeof body === 'object' && (body.status === 'ok' || body.status === 'processing') && body.data !== undefined) ? body.data : body;
  }
  return {
    health:     () => req('/health'),
    models:     () => req('/models'),
    weights:    (modelId) => req('/weights?model=' + encodeURIComponent(modelId)),
    stats:      () => req('/stats'),
    images:     (batchName) => req('/images?name=' + encodeURIComponent(batchName)),
    datasets:    () => req('/dataset'),
    datasetUpload: (formData) => req('/dataset', { method: 'POST', body: formData }),
    deleteBatch: (name) => req('/batches/' + encodeURIComponent(name), { method: 'DELETE' }),
    predict:    (payload) => req('/predict', { method: 'POST', body: payload }),
    task:       (id) => req('/task/' + encodeURIComponent(id)),
    train:      (payload) => req('/train', { method: 'POST', body: payload }),
    trainStatus:(id) => req('/train/' + encodeURIComponent(id)),
    trainHistory: () => req('/training-history'),
    exportUrl:  (id) => base + '/export/' + encodeURIComponent(id),
    errorLogs:  (limit) => req('/logs/errors' + (limit ? '?limit=' + limit : '')),
    clearErrors: () => req('/logs/errors', { method: 'DELETE' }),
  };
})();

/* ---- State ---- */
const state = {
  models: [], selectedModel: null, weights: [], selectedWeight: null,
  batches: [], selectedBatch: null, results: null, online: false,
  datasetFiles: {}, trainingTaskId: null, trainingPollTimer: null,
  trainedHistory: [], advParams: {},
  infModels: [], infSelectedModel: null, infWeights: [], infSelectedWeight: null,
  infBatchName: null, infResults: null,
};

/* ---- DOM helpers ---- */
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
const el = (tag, cls, html) => { const e = document.createElement(tag); if(cls) e.className = cls; if(html!=null) e.innerHTML = html; return e; };

/* ---- Card hover tilt ---- */
function makeTilt(wrapper) {
  const card = wrapper.querySelector('.t-tilt-card');
  if (!card) return;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  const MAX = 10;
  function reset() { wrapper.classList.remove('is-hover'); card.classList.remove('is-tilting'); card.style.setProperty('--tilt-rx','0deg'); card.style.setProperty('--tilt-ry','0deg'); }
  function track(e) {
    if(reduce.matches)return;
    const r=wrapper.getBoundingClientRect();
    const px=Math.min(1,Math.max(0,(e.clientX-r.left)/r.width));
    const py=Math.min(1,Math.max(0,(e.clientY-r.top)/r.height));
    wrapper.classList.add('is-hover'); card.classList.add('is-tilting');
    card.style.setProperty('--tilt-ry',((px-0.5)*MAX).toFixed(2)+'deg');
    card.style.setProperty('--tilt-rx',((0.5-py)*MAX).toFixed(2)+'deg');
    card.style.setProperty('--tilt-gx',(px*100).toFixed(1)+'%');
    card.style.setProperty('--tilt-gy',(py*100).toFixed(1)+'%');
  }
  wrapper.addEventListener('pointermove',track); wrapper.addEventListener('pointerup',reset);
  wrapper.addEventListener('pointercancel',reset);
  wrapper.addEventListener('pointerleave',(e)=>{if(e.pointerType==='mouse')reset();});
  wrapper.addEventListener('pointerdown',(e)=>{if(e.pointerType!=='mouse'){try{wrapper.setPointerCapture(e.pointerId)}catch(_){}}});
}

/* ---- Toast ---- */
function toast(msg, type = 'info') {
  const t = el('div','toast '+type);
  const icon = type==='success'?'✓':type==='error'?'✕':'ℹ';
  const color = type==='success'?'normal-dark':type==='error'?'severe':'accent-dark';
  t.innerHTML=`<span style="font-weight:700;color:var(--${color})">${icon}</span><span>${msg}</span>`;
  $('#toastContainer').appendChild(t);
  setTimeout(()=>{t.style.opacity='0';t.style.transform='translateX(40px)';t.style.transition='all 300ms';setTimeout(()=>t.remove(),300);},3500);
}

/* ---- API status ---- */
async function checkApiStatus() {
  const badge=$('#apiStatus'), text=$('#apiStatusText');
  try {
    const data=await API.health(); state.online=true;
    badge.classList.add('online'); badge.classList.remove('offline');
    text.textContent='API 在线 · v'+(data.version||'2'); return true;
  } catch(e) {
    state.online=false; badge.classList.add('offline'); badge.classList.remove('online');
    text.textContent='API 离线'; return false;
  }
}

/* ---- Models ---- */
async function loadModels() {
  try {
    const data=await API.models(); state.models=data.models||[];
    $('#statModels').textContent=state.models.length;
    $('#modelHint').textContent=state.models.length+' 个可用'; renderModels();
  } catch(e){$('#modelHint').textContent='加载失败';toast('模型列表加载失败：'+e.message,'error');}
}
function renderModels() {
  const grid=$('#modelGrid'); grid.innerHTML='';
  state.models.forEach(m=>{
    const wrap=el('div','t-tilt');
    const card=el('div','model-card t-tilt-card'+(state.selectedModel===m.id?' active':''));
    const dn=m.name||m.id;
    card.innerHTML=`<div class="mc-icon">${dn.slice(0,2).toUpperCase()}</div><div class="mc-body"><div class="mc-name">${dn}</div><div class="mc-desc">${m.description||m.architecture||''}</div></div><div class="mc-check"></div><div class="t-tilt-glare"></div>`;
    card.addEventListener('click',()=>selectModel(m.id));
    wrap.appendChild(card); grid.appendChild(wrap); makeTilt(wrap);
  });
}
async function selectModel(modelId) {
  if(state.selectedModel===modelId){state.selectedModel=null;state.selectedWeight=null;renderModels();await loadWeights(null);checkReady();return;}
  state.selectedModel=modelId;state.selectedWeight=null;renderModels();await loadWeights(modelId);checkReady();
}

/* ---- Weights ---- */
async function loadWeights(modelId) {
  if(!modelId){state.weights=[];state.selectedWeight=null;$('#weightHint').textContent='请先选择模型';$('#weightList').innerHTML='<div class="weight-empty">请先选择模型</div>';renderWeights();checkReady();return;}
  $('#weightHint').textContent='加载中…';$('#weightList').innerHTML='<div class="weight-empty">加载中…</div>';
  try {
    const data=await API.weights(modelId); state.weights=data.models||[];
    $('#weightHint').textContent=state.weights.length+' 个权重'; renderWeights();
    if(state.weights.length>0&&!state.selectedWeight) selectWeight(state.weights[0].id);
  } catch(e){$('#weightHint').textContent='加载失败';$('#weightList').innerHTML='<div class="weight-empty">权重加载失败</div>';toast('权重列表加载失败：'+e.message,'error');}
}
function renderWeights() {
  const list=$('#weightList'); list.innerHTML='';
  if(state.weights.length===0){list.innerHTML='<div class="weight-empty">该模型暂无可用权重</div>';return;}
  state.weights.forEach(w=>{
    const item=el('div','weight-item'+(state.selectedWeight===w.id?' active':'')+(w.trained?' trained':''));
    const size=w.size_mb?w.size_mb.toFixed(1)+' MB':'';
    const badge=w.trained?'<span class="wi-badge">训练</span>':'';
    item.innerHTML=`<div class="wi-radio"></div><span class="wi-name">${w.name}</span>${badge}<span class="wi-meta">${size}</span>`;
    item.addEventListener('click',()=>selectWeight(w.id)); list.appendChild(item);
  });
}
function selectWeight(weightId) {
  if(state.selectedWeight===weightId){state.selectedWeight=null;renderWeights();checkReady();return;}
  state.selectedWeight=weightId;renderWeights();checkReady();
}
function checkReady(){}

/* ---- Dataset Upload ---- */
function setupDatasetUpload() {
  const zones=[{zoneId:'zoneDatasetImages',inputId:'inputDatasetImages',key:'images_zip'},
               {zoneId:'zoneDatasetAnno',inputId:'inputDatasetAnno',key:'annotation_json'},
               {zoneId:'zoneDatasetMasks',inputId:'inputDatasetMasks',key:'masks_zip'}];
  state.datasetFiles={};
  zones.forEach(({zoneId,inputId,key})=>{
    const zone=$('#'+zoneId), input=$('#'+inputId);
    zone.addEventListener('click',()=>input.click());
    input.addEventListener('change',()=>{
      if(input.files.length){state.datasetFiles[key]=input.files[0];zone.classList.add('has-file');
        var n=input.files[0].name;zone.querySelector('.uz-sub').textContent=n.length>28?n.slice(0,25)+'…':n;}
      input.value='';$('#uploadDatasetBtn').disabled=!state.datasetFiles['images_zip'];
    });
    ['dragenter','dragover'].forEach(ev=>zone.addEventListener(ev,e=>e.preventDefault()));
    ['dragleave','drop'].forEach(ev=>zone.addEventListener(ev,e=>e.preventDefault()));
  });
  $('#uploadDatasetBtn').addEventListener('click',handleDatasetUpload);
}
async function handleDatasetUpload() {
  const z=state.datasetFiles['images_zip'];if(!z){toast('请选择图片压缩包','error');return;}
  const fd=new FormData();fd.append('images_zip',z);
  if(state.datasetFiles['annotation_json'])fd.append('annotation_json',state.datasetFiles['annotation_json']);
  if(state.datasetFiles['masks_zip'])fd.append('masks_zip',state.datasetFiles['masks_zip']);
  $('#uploadDatasetBtn').disabled=true;$('#uploadDatasetBtn').textContent='上传中…';
  try {
    const result=await API.datasetUpload(fd);
    const info={batch_id:result.batch_id||'batch_'+Date.now().toString(36),
      uploaded_at:result.uploaded_at||new Date().toISOString(),
      images_file:result.images_file||{name:z.name,size_kb:Math.round(z.size/1024)},
      annotation_file:result.annotation_file,masks_file:result.masks_file||null};
    state.batches.unshift(info);state.selectedBatch=info.batch_id;
    toast('数据集上传成功！批次: '+state.selectedBatch,'success');
    state.datasetFiles={};
    document.querySelectorAll('.upload-zone.has-file').forEach(zp=>{
      zp.classList.remove('has-file');
      var k=zp.id==='zoneDatasetImages'?'images_zip':zp.id==='zoneDatasetAnno'?'annotation_json':'masks_zip';
      var sp=zp.querySelector('.uz-sub');
      var texts={images_zip:'上传正常样本图片压缩包<span class="pill">必选 · ZIP</span>',
                  annotation_json:'上传标注 JSON（可选）<span class="pill" style="background:rgba(139,92,246,0.15);color:#7c3aed;">可选 · JSON</span>',
                  masks_zip:'上传掩码图压缩包（可选）<span class="pill" style="background:rgba(16,185,129,0.15);color:#059669;">可选 · ZIP</span>'};
      if(sp)sp.innerHTML=texts[k]||'';
    });
    renderDatasetList();await refreshBatches();checkReady();updateTrainSummary();updateStats();
  } catch(e){toast('上传失败：'+e.message,'error');}
  finally{$('#uploadDatasetBtn').disabled=false;$('#uploadDatasetBtn').textContent='上传数据集';}
}
async function refreshBatches() {
  try {
    var sel=document.getElementById('infBatchSelect');if(!sel)return;
    sel.innerHTML='<option value="">— 选择已有批次 —</option>';
    state.batches.forEach(b=>{var o=document.createElement('option');o.value=b.batch_id;o.textContent=b.batch_id;sel.appendChild(o);});
  } catch(e){}
}

/* ---- Dataset List ---- */
function renderDatasetList() {
  const list=$('#datasetList');if(!list)return;
  if(state.batches.length===0){list.innerHTML='<div class="gallery-empty">尚未上传数据集</div>';return;}
  list.innerHTML='';
  state.batches.forEach(b=>{
    const disabled=b.can_train===false;
    const card=el('div','dataset-card'+(b.batch_id===state.selectedBatch?' active-batch':'')+(disabled?' disabled':''));
    var time=b.uploaded_at?new Date(b.uploaded_at).toLocaleString('zh-CN'):'';
    var filesHtml='';
    var addFile=(icon,name,sz,cls)=>{
      var svg=icon==='zip'?'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>';
      var szText=sz?((sz/1024)>1?(sz/1024).toFixed(1)+' MB':sz+' KB'):'';
      filesHtml+='<div class="dc-file"><div class="dc-fi '+cls+'">'+svg+'</div><span class="dc-fn">'+(name||'')+'</span><span class="dc-fm">'+szText+'</span></div>';
    };
    if(b.images_file)addFile('zip',b.images_file.name,b.images_file.size_kb,'zip');
    if(b.annotation_file)addFile('json',b.annotation_file.name,b.annotation_file.size_kb,'json');
    if(b.masks_file)addFile('zip',b.masks_file.name,b.masks_file.size_kb,'mask');
    card.innerHTML='<div class="dc-header"><span class="dc-batch">'+b.batch_id+'</span><span class="dc-time">'+time+'</span><button class="dc-del" title="删除批次"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button></div><div class="dc-files">'+filesHtml+'</div>'+(disabled?'<div class="dc-warn">⛔ 缺少标注文件，不可用作训练</div>':'');
    card.querySelector('.dc-header').addEventListener('click',(e)=>{
      if(e.target.closest('.dc-del')||disabled)return;
      if(state.selectedBatch===b.batch_id){state.selectedBatch=null;card.classList.remove('active-batch');checkReady();updateTrainSummary();updateStats();toast('已取消选择','info');return;}
      state.selectedBatch=b.batch_id;
      document.querySelectorAll('.dataset-card').forEach(c=>c.classList.remove('active-batch'));
      card.classList.add('active-batch');checkReady();updateTrainSummary();updateStats();
      toast('已选择批次: '+b.batch_id,'info');
    });
    card.querySelector('.dc-del').addEventListener('click',(e)=>{e.stopPropagation();deleteBatch(b.batch_id);});
    if(b.batch_id===state.selectedBatch)card.classList.add('active-batch');
    list.appendChild(card);
  });
}
async function updateStats() {
  $('#statNormal').textContent=state.batches.length;
  $('#statDefect').textContent=state.batches.length>0?state.batches.length:0;
}
async function deleteBatch(batchId) {
  var prev=[...state.batches];state.batches=state.batches.filter(b=>b.batch_id!==batchId);
  if(state.selectedBatch===batchId)state.selectedBatch=state.batches.length>0?state.batches[0].batch_id:null;
  renderDatasetList();updateStats();updateTrainSummary();checkReady();refreshBatches();
  try{await API.deleteBatch(batchId);toast('已删除批次','info');}
  catch(e){state.batches=prev;state.selectedBatch=state.batches.length>0?state.batches[0].batch_id:null;renderDatasetList();updateStats();updateTrainSummary();checkReady();refreshBatches();toast('删除失败：'+e.message,'error');}
}

/* ---- Submit task via SSE ---- */
async function submitTask(batchName, weight) {
  var taskId;
  try {
    var res = await fetch('/api/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ batch_name: batchName, weight: weight })
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    var data = await res.json();
    var taskData = data.data || {};
    if (data.status !== 'ok' || !taskData.task_id) throw new Error(taskData.error || data.error || '提交任务失败：未知状态');
    taskId = taskData.task_id;
  } catch (err) { toast('提交任务失败: ' + err.message, 'error'); throw err; }

  return new Promise(function (resolve, reject) {
    var es = new EventSource('/api/task-stream/' + encodeURIComponent(taskId));
    es.onmessage = function (event) {
      try { var result = JSON.parse(event.data); if (result.status === 'completed') { es.close(); resolve(result); } else if (result.status === 'failed' || result.status === 'error') { es.close(); reject(new Error(result.error || result.message || '未知错误')); } } catch (e) {}
    };
    es.onerror = function () { if (es.readyState === EventSource.CLOSED) { es.close(); reject(new Error('SSE 连接断开')); } };
  });
}

/* ---- Predict (workspace) ---- */
async function runPredict() {
  if (!state.selectedModel || !state.selectedWeight) { toast('请先选择模型和权重', 'error'); return; }
  if (!state.selectedBatch) { toast('请先上传数据集并选择批次', 'error'); return; }
  var overlay = $('#scanOverlay');
  var modelName = (state.models.find(function(m){return m.id===state.selectedModel;})||{}).name || state.selectedModel;
  var weightName = (state.weights.find(function(w){return w.id===state.selectedWeight;})||{}).name || state.selectedWeight;
  $('#scanLabel').textContent = '正在执行缺陷检测…';
  $('#scanSub').textContent = modelName + ' · ' + weightName + ' · 批次: ' + state.selectedBatch;
  overlay.classList.add('show');
  try {
    var sseResult = await submitTask(state.selectedBatch, state.selectedWeight);
    var t = await API.task(sseResult.task_id); state.results = t.results || [];
    overlay.classList.remove('show');
    if (state.results.length) { var nd = state.results.filter(function (r) { return r.verdict === 'defect'; }).length; toast('检测完成，共 ' + state.results.length + ' 项结果（缺陷 ' + nd + ' 张）', 'success'); }
    else { toast('检测完成，未发现缺陷', 'info'); }
    renderDatasetList(); updateStats();
  } catch (e) { overlay.classList.remove('show'); toast('检测失败：' + e.message, 'error'); }
}
function renderResults() {
  if(!state.results||state.results.length===0) return;
  var nd=state.results.filter(r=>r.verdict==='defect').length,nn=state.results.length-nd;
  var c=state.results.filter(r=>r.expected_verdict===r.verdict).length;
  var acc=state.results.length>0?(c/state.results.length*100).toFixed(1):'—';
  toast('检测结果: 共 '+state.results.length+' 张 · 缺陷 '+nd+' 张 · 准确率 '+acc+'%','info');
}
function exportResults(){
  if(!state.results||state.results.length===0){toast('没有可导出的结果','error');return;}
  var rpt={exported_at:new Date().toISOString(),model:state.selectedModel,weight:state.selectedWeight,batch:state.selectedBatch,summary:{total:state.results.length,defect_count:state.results.filter(r=>r.verdict==='defect').length,normal_count:state.results.filter(r=>r.verdict==='normal').length,accuracy:state.results.length>0?state.results.filter(r=>r.expected_verdict===r.verdict).length/state.results.length:0},results:state.results};
  var blob=new Blob([JSON.stringify(rpt,null,2)],{type:'application/json'});var url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='detect_results_'+state.selectedBatch+'.json';document.body.appendChild(a);a.click();document.body.removeChild(a);URL.revokeObjectURL(url);toast('结果已导出','success');
}

/* ============================================================
   Training & Export
   ============================================================ */
const TRAIN_PARAMS = [
  { name:'yolo_epochs',type:'int',def:50,group:'yolo',help:'YOLO 训练轮数',min:1,max:1000 },
  { name:'imgsz',type:'int',def:640,group:'yolo',help:'输入图像尺寸（建议 32 的倍数）',min:32,max:2048 },
  { name:'yolo_batch_size',type:'int',def:16,group:'yolo',help:'YOLO 批大小',min:1,max:512 },
  { name:'workers',type:'int',def:4,group:'yolo',help:'数据加载线程数',min:0,max:32 },
  { name:'patience',type:'int',def:10,group:'yolo',help:'早停耐心值（0=禁用早停）',min:0,max:500 },
  { name:'freeze',type:'int',def:20,group:'yolo',help:'冻结主干前 N 层（0=全量微调）',min:0,max:100 },
  { name:'yolo_lr',type:'float',def:0.001,group:'yolo',help:'YOLO 初始学习率',min:0.00001,max:1.0 },
  { name:'lrf',type:'float',def:0.1,group:'yolo',help:'最终学习率因子',min:0.001,max:1.0 },
  { name:'cos_lr',type:'bool',def:true,group:'yolo',help:'使用 cosine 学习率衰减' },
  { name:'full_train',type:'flag',def:false,group:'yolo',help:'全量训练模式' },
  { name:'sam2_epochs',type:'int',def:8,group:'sam2',help:'SAM2 训练轮数',min:1,max:1000 },
  { name:'sam2_batch_size',type:'int',def:8,group:'sam2',help:'SAM2 批大小',min:1,max:512 },
  { name:'lora_rank',type:'int',def:16,group:'sam2',help:'LoRA rank',min:1,max:256 },
  { name:'use_dora',type:'bool',def:true,group:'sam2',help:'是否使用 DoRA' },
  { name:'sam2_lr',type:'float',def:0.0002,group:'sam2',help:'SAM2 学习率',min:0.00001,max:1.0 },
  { name:'weight_decay',type:'float',def:0.01,group:'sam2',help:'权重衰减',min:0.0,max:1.0 },
];
const _TRAIN_DEFAULTS=Object.fromEntries(TRAIN_PARAMS.map(p=>[p.name,p.def]));
function _advFieldHtml(p){
  const id='adv_'+p.name;const val=state.advParams[p.name]!==undefined?state.advParams[p.name]:p.def;
  if(p.type==='bool'||p.type==='flag'){return `<div class="adv-field${p.auto?' full':''}"><label class="chk"><input type="checkbox" id="${id}" ${val?'checked':''}> ${p.name}${p.auto?'（自动）':''}</label><span class="help">${p.help}</span></div>`;}
  var rangeAttr='';if(p.min!=null)rangeAttr+=` min="${p.min}"`;if(p.max!=null)rangeAttr+=` max="${p.max}"`;
  return `<div class="adv-field${p.auto?' full':''}" data-param="${p.name}"><label>${p.name}<span class="dv">默认 ${p.def}${p.min!=null||p.max!=null?' · 范围 '+_rangeStr(p):''}</span></label><input type="${p.type==='int'||p.type==='float'?'number':'text'}" id="${id}" ${p.type==='int'?'step="1"':''}${p.type==='float'?'step="any"':''}${rangeAttr} value="${val}" oninput="_validateAdvField(TRAIN_PARAMS.find(p=>p.name==='${p.name}'))"><span class="help">${p.help}</span><span class="adv-err"></span></div>`;
}
function _rangeStr(p){var s=[];if(p.min!=null)s.push(p.min);s.push('~');if(p.max!=null)s.push(p.max);return s.join('');}
function _validateAdvField(p){
  var node=document.getElementById('adv_'+p.name);if(!node)return true;
  var val=node.value.trim();if(val===''){_setFieldError(p.name,'');return true;}
  var num=p.type==='int'?parseInt(val,10):parseFloat(val);
  if(isNaN(num)){_setFieldError(p.name,'请输入有效数字');return false;}
  if(p.min!=null&&num<p.min){_setFieldError(p.name,'最小值 '+p.min+'，当前值 '+num);return false;}
  if(p.max!=null&&num>p.max){_setFieldError(p.name,'最大值 '+p.max+'，当前值 '+num);return false;}
  _setFieldError(p.name,'');return true;
}
function _setFieldError(name,msg){
  var field=document.querySelector(`.adv-field[data-param="${name}"]`);if(!field)return;
  var err=field.querySelector('.adv-err');if(err)err.textContent=msg;
  field.classList.toggle('has-error',!!msg);
}
function populateAdvFields(){const groups={yolo:$('#advFieldsYolo'),sam2:$('#advFieldsSam2')};for(const k in groups)groups[k].innerHTML='';TRAIN_PARAMS.forEach(p=>{const host=groups[p.group];if(host)host.insertAdjacentHTML('beforeend',_advFieldHtml(p));});}
function collectAdvParams(){const out={},errs=[];TRAIN_PARAMS.forEach(p=>{const id='adv_'+p.name,node=document.getElementById(id);if(!node)return;let v;if(p.type==='bool'||p.type==='flag')v=node.checked;else if(p.type==='int'){if(!_validateAdvField(p))errs.push(p.name);v=node.value===''?p.def:parseInt(node.value,10);}else if(p.type==='float'){if(!_validateAdvField(p))errs.push(p.name);v=node.value===''?p.def:parseFloat(node.value);}else v=node.value;if(p.min==null&&p.max==null);else if(errs.includes(p.name))return;if(p.auto){if(node.value!=='')out[p.name]=v;}else if(String(v)!==String(p.def))out[p.name]=v;});return errs.length?{errors:errs}:out;}
function _validateAllFields(){var ok=true;TRAIN_PARAMS.forEach(p=>{if(p.type==='bool'||p.type==='flag')return;if(!_validateAdvField(p))ok=false;});return ok;}
let advCloseTimer=null;
function openAdvModal(){populateAdvFields();const m=$('#advModal');if(advCloseTimer){clearTimeout(advCloseTimer);advCloseTimer=null;}m.style.display='flex';const modal=m.querySelector('.t-modal');modal.classList.remove('is-closing');requestAnimationFrame(()=>modal.classList.add('is-open'));}
function closeAdvModal(){const m=$('#advModal'),modal=m.querySelector('.t-modal'),closeMs=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--modal-close-dur'))||150;modal.classList.remove('is-open');modal.classList.add('is-closing');advCloseTimer=setTimeout(()=>{modal.classList.remove('is-closing');m.style.display='none';advCloseTimer=null;},closeMs);}
function updateTrainSummary(){
  var cur=state.batches.find(b=>b.batch_id===state.selectedBatch);
  var imgCount=cur&&cur.images_file?cur.images_file.image_count:'—';var maskCount=cur&&cur.masks_file?cur.masks_file.mask_count:'—';var hasAnno=cur&&cur.annotation_file?'有':'无';
  $('#tdsNormal').textContent='图片: '+imgCount+' 张';$('#tdsDefect').textContent='标注: '+hasAnno;$('#tdsTotal').textContent=state.selectedBatch?'批次: '+state.selectedBatch:'—';$('#tdsEstimate').textContent=cur&&cur.masks_file?'含Mask: '+maskCount+' 张':'—';
  $('#trainBtn').disabled=!state.selectedBatch||!state.online||!!state.trainingTaskId;
  $('#advHint').textContent=Object.keys(state.advParams).length>0?'已自定义 '+Object.keys(state.advParams).length+' 项参数':'默认参数 · 点击可修改';
}
function setupTrainingControls(){$('#advOptionsBtn').addEventListener('click',openAdvModal);$('#advClose').addEventListener('click',closeAdvModal);$('#advModal').addEventListener('click',(e)=>{if(e.target===$('#advModal'))closeAdvModal();});$('#advReset').addEventListener('click',()=>{state.advParams={};populateAdvFields();});$('#advConfirm').addEventListener('click',function(){var result=collectAdvParams();if(result.errors){toast('参数校验失败：'+result.errors.join(', '),'error');return;}state.advParams=result;closeAdvModal();updateTrainSummary();});$('#trainBtn').addEventListener('click',startTraining);}
async function startTraining(){
  if(!state.selectedBatch){toast('请先上传数据集并选择批次','error');return;}
  $('#trainBtn').disabled=true;$('#trainProgress').classList.add('show');$('#tpTotalEpoch').textContent=state.advParams.yolo_epochs||_TRAIN_DEFAULTS.yolo_epochs;$('#tpEpoch').textContent='0';$('#tpPct').textContent='0%';$('#tpFill').style.width='0%';$('#tpStage').textContent='准备中';
  try{const d=await API.train({params:state.advParams,batch_name:state.selectedBatch});if(!d||!d.task_id)throw new Error((d&&d.error)||'训练启动失败，未获取到任务ID');state.trainingTaskId=d.task_id;toast('训练已启动'+(d.estimated_seconds?', 预计 '+d.estimated_seconds+'s':''),'info');pollTraining(d.task_id);}
  catch(e){toast('训练启动失败：'+e.message,'error');$('#trainProgress').classList.remove('show');$('#trainBtn').disabled=false;}
}
async function pollTraining(taskId){
  if(state.trainingPollTimer)clearInterval(state.trainingPollTimer);
  state.trainingPollTimer=setInterval(async()=>{
    try{const resp=await API.trainStatus(taskId);const t=resp.data||resp;const pct=Math.round((t.progress||0)*100);$('#tpEpoch').textContent=t.current_epoch||0;$('#tpStage').textContent=t.stage||(t.status==='training'?'训练中':t.status);$('#tpPct').textContent=pct+'%';$('#tpFill').style.width=pct+'%';
      if(t.status==='error'){clearInterval(state.trainingPollTimer);state.trainingPollTimer=null;state.trainingTaskId=null;$('#trainBtn').disabled=false;toast('训练失败：'+(t.error||'未知错误'),'error');return;}
      if(t.status==='done'){clearInterval(state.trainingPollTimer);state.trainingPollTimer=null;state.trainingTaskId=null;$('#trainBtn').disabled=false;const acc=(t.final_accuracy*100).toFixed(1);toast(`训练完成！准确率 ${acc}%`,'success');if(state.selectedModel)await loadWeights(state.selectedModel);await loadTrainingHistory();await loadStats();updateTrainSummary();}
    }catch(e){clearInterval(state.trainingPollTimer);state.trainingPollTimer=null;state.trainingTaskId=null;$('#trainBtn').disabled=false;toast('训练状态查询失败：'+e.message,'error');}
  },800);
}
async function loadTrainingHistory(){try{const data=await API.trainHistory();state.trainedHistory=data.tasks||[];renderTrainedList();$('#statTrained').textContent=state.trainedHistory.filter(t=>t.status==='done').length;}catch(e){}}
function renderTrainedList(){
  const container=$('#trainedItems'),empty=$('#trainedEmpty');container.innerHTML='';
  const done=state.trainedHistory.filter(t=>t.status==='done');if(done.length===0){empty.style.display='block';return;}empty.style.display='none';
  done.forEach(t=>{const modelObj=state.models.find(m=>m.id===t.model),modelName=modelObj?modelObj.name:t.model;const item=el('div','trained-item');item.innerHTML=`<div class="ti-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg></div><div class="ti-info"><div class="ti-name">${modelName} · 训练权重</div><div class="ti-meta">${t.weight_id||''}</div></div><div class="ti-actions"><button class="btn btn-ghost btn-sm" data-action="use" data-model="${t.model}" data-weight="${t.weight_id}">在线使用</button><a class="btn btn-ghost btn-sm" href="${API.exportUrl(t.id)}" download>导出模型</a></div>`;item.querySelector('[data-action="use"]').addEventListener('click',()=>useTrainedModel(t.model,t.weight_id));container.appendChild(item);});
}
async function useTrainedModel(modelId,weightId){
  if(state.selectedModel!==modelId){
    await selectModel(modelId);
  }
  state.selectedWeight=weightId;
  renderWeights();
  checkReady();
  toast('已切换至训练模型，可直接执行检测','success');
  requestAnimationFrame(()=>{$('#workspace').scrollIntoView({behavior:'smooth',block:'start'});});
}

/* ============================================================
   Inference page (screen 3)
   ============================================================ */
async function loadInfModels(){try{const data=await API.models();state.infModels=data.models||[];renderInfModels();}catch(e){toast('模型列表加载失败','error');}}
function renderInfModels(){
  const grid=$('#infModelGrid');grid.innerHTML='';
  state.infModels.forEach(m=>{const wrap=el('div','t-tilt'),card=el('div','model-card t-tilt-card'+(state.infSelectedModel===m.id?' active':''));const dn=m.name||m.id;card.innerHTML=`<div class="mc-icon">${dn.slice(0,2).toUpperCase()}</div><div class="mc-body"><div class="mc-name">${dn}</div><div class="mc-desc">${m.description||''}</div></div><div class="mc-check"></div><div class="t-tilt-glare"></div>`;card.addEventListener('click',()=>selectInfModel(m.id));wrap.appendChild(card);grid.appendChild(wrap);makeTilt(wrap);});
}
async function selectInfModel(modelId){if(state.infSelectedModel===modelId){state.infSelectedModel=null;state.infSelectedWeight=null;renderInfModels();await loadInfWeights(null);infCheckReady();return;}state.infSelectedModel=modelId;state.infSelectedWeight=null;renderInfModels();await loadInfWeights(modelId);infCheckReady();}
async function loadInfWeights(modelId){
  if(!modelId){state.infWeights=[];state.infSelectedWeight=null;$('#infWeightHint').textContent='请先选择模型';$('#infWeightList').innerHTML='<div class="weight-empty">请先选择模型</div>';infCheckReady();return;}
  $('#infWeightHint').textContent='加载中…';
  try{const data=await API.weights(modelId);state.infWeights=data.models||[];renderInfWeights();if(state.infWeights.length>0&&!state.infSelectedWeight)selectInfWeight(state.infWeights[0].id);}catch(e){toast('权重加载失败','error');}
}
function renderInfWeights(){const list=$('#infWeightList');list.innerHTML='';if(state.infWeights.length===0){list.innerHTML='<div class="weight-empty">暂无可用权重</div>';return;}state.infWeights.forEach(w=>{const item=el('div','weight-item'+(state.infSelectedWeight===w.id?' active':''));item.innerHTML=`<div class="wi-radio"></div><span class="wi-name">${w.name}</span><span class="wi-meta">${w.size_mb||''} MB</span>`;item.addEventListener('click',()=>selectInfWeight(w.id));list.appendChild(item);});}
function selectInfWeight(wid){if(state.infSelectedWeight===wid){state.infSelectedWeight=null;renderInfWeights();infCheckReady();return;}state.infSelectedWeight=wid;renderInfWeights();infCheckReady();}
function infCheckReady(){$('#infPredictBtn').disabled=!(state.infSelectedModel&&state.infSelectedWeight&&state.infBatchName&&state.online);var siBtn=$('#singleImagePredictBtn');if(siBtn)siBtn.disabled=!(state.singleImageFile&&state.infSelectedModel&&state.infSelectedWeight&&state.online);}
function setupInfBatch(){
  var sel=$('#infBatchSelect');
  sel.addEventListener('change',()=>{
    state.infBatchName=sel.value||null;
    infCheckReady();
  });
}
async function runInfPredict(){
  if(!state.infSelectedModel||!state.infSelectedWeight){toast('请先选择模型和权重','error');return;}
  if(!state.infBatchName){toast('请选择或输入数据批次','error');return;}
  var overlay=$('#scanOverlay');
  var infModelName=(state.infModels.find(function(m){return m.id===state.infSelectedModel;})||{}).name||state.infSelectedModel;
  var infWeightName=(state.infWeights.find(function(w){return w.id===state.infSelectedWeight;})||{}).name||state.infSelectedWeight;
  $('#scanLabel').textContent='正在执行缺陷检测…';
  $('#scanSub').textContent=infModelName+' · '+infWeightName+' · 批次: '+state.infBatchName;
  overlay.classList.add('show');
  try{var sseResult=await submitTask(state.infBatchName,state.infSelectedWeight);var t=await API.task(sseResult.task_id);state.infResults=t.results||[];overlay.classList.remove('show');renderInfResults();toast('检测完成，共 '+(state.infResults?state.infResults.length:0)+' 项结果','success');}catch(e){overlay.classList.remove('show');toast('检测失败: '+e.message,'error');}
}
function renderInfResults(){
  var tb=$('#infResultsToolbar'),empty=$('#infResultsEmpty'),list=$('#infResultsList');list.innerHTML='';
  if(!state.infResults||state.infResults.length===0){if(tb)tb.style.display='none';if(empty)empty.style.display='';return;}if(tb)tb.style.display='flex';if(empty)empty.style.display='none';
  var nd=state.infResults.filter(r=>r.verdict==='defect').length,nn=state.infResults.length-nd;
  var s=$('#infRtSummary');if(s)s.innerHTML='<span>共 <strong>'+state.infResults.length+'</strong> 张 · 缺陷 <strong style="color:var(--defect-dark)">'+nd+'</strong> 张 · 正常 <strong style="color:var(--normal-dark)">'+nn+'</strong> 张</span>';
  var eb=$('#infExportResultsBtn');if(eb)eb.onclick=()=>{var rpt={exported_at:new Date().toISOString(),model:state.infSelectedModel,weight:state.infSelectedWeight,batch:state.infBatchName,summary:{total:state.infResults.length,defect_count:nd,normal_count:nn},results:state.infResults};var blob=new Blob([JSON.stringify(rpt,null,2)],{type:'application/json'});var url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='detect_results_'+state.infBatchName+'.json';document.body.appendChild(a);a.click();document.body.removeChild(a);URL.revokeObjectURL(url);toast('结果已导出','success');};
  state.infResults.forEach(r=>{var row=el('div','result-row'),v=r.verdict||'normal',conf=r.confidence||0,sc=v==='critical'?'crit':v==='defect'?'warn':'ok';var vTag=v==='defect'?(r.severity==='critical'?'严重缺陷':'缺陷'):'正常',cp=(conf*100).toFixed(1);row.innerHTML='<div class="result-thumb">'+(r.image_name?`<div class="thumb-name">${r.image_name.slice(0,2)}</div>`:'')+'</div><div class="result-info"><div class="ri-name">'+(r.image_name||'')+(r.rag_similar?`<span class="rag-badge" title="ChromaDB 中检索到 ${r.rag_similar.length} 条相似历史记录">RAG ${r.rag_similar.length}</span>`:'')+'</div><div class="ri-detail">'+(r.defect_type?'类型: '+r.defect_type+' · ':'')+'置信度 '+cp+'%</div></div><div class="result-verdict"><div class="conf-bar"><div class="fill '+sc+'" style="width:'+cp+'%"></div></div><span class="verdict-tag '+sc+'">'+vTag+'</span></div>';list.appendChild(row);});
}

/* ---- Single image recognition ---- */
function setupInfSingleImage(){
  var zone=$('#zoneSingleImage'),input=$('#inputSingleImage'),btn=$('#singleImagePredictBtn'),sub=$('#singleImageSub'),resultDiv=$('#singleImageResult'),preview=$('#singleImagePreview'),verdict=$('#singleImageVerdict'),detail=$('#singleImageDetail');
  state.singleImageFile=null;
  zone.addEventListener('click',function(){input.click();});
  input.addEventListener('change',function(){
    if(input.files.length){state.singleImageFile=input.files[0];zone.classList.add('has-file');var name=state.singleImageFile.name;sub.textContent=name.length>28?name.slice(0,25)+'…':name;var reader=new FileReader();reader.onload=function(e){preview.src=e.target.result;};reader.readAsDataURL(state.singleImageFile);resultDiv.style.display='none';}
    else{state.singleImageFile=null;zone.classList.remove('has-file');sub.textContent='点击选择单张图片';}
    input.value='';infCheckReady();
  });
  btn.addEventListener('click',async function(){
    if(!state.singleImageFile){toast('请先选择图片','error');return;}
    if(!state.infSelectedModel||!state.infSelectedWeight){toast('请先选择模型和权重','error');return;}
    btn.disabled=true;btn.textContent='上传识别中…';
    try{
      var zip=new JSZip();zip.file(state.singleImageFile.name,state.singleImageFile);var zipBlob=await zip.generateAsync({type:'blob'});var zipFile=new File([zipBlob],'single_image.zip',{type:'application/zip'});
      var fd=new FormData();fd.append('images_zip',zipFile);var uploadResult=await API.datasetUpload(fd);var batchId=uploadResult.batch_id||'batch_'+Date.now().toString(36);
      var overlay=$('#scanOverlay');
      var siModelName=(state.infModels.find(function(m){return m.id===state.infSelectedModel;})||{}).name||state.infSelectedModel;
      var siWeightName=(state.infWeights.find(function(w){return w.id===state.infSelectedWeight;})||{}).name||state.infSelectedWeight;
      $('#scanLabel').textContent='正在识别图片…';
      $('#scanSub').textContent=siModelName+' · '+siWeightName+' · '+state.singleImageFile.name;
      overlay.classList.add('show');
      try{var sseResult=await submitTask(batchId,state.infSelectedWeight);var t=await API.task(sseResult.task_id);var results=t.results||[];overlay.classList.remove('show');
        if(results.length>0){var r=results[0],v=r.verdict||'normal',conf=r.confidence||0,cp=(conf*100).toFixed(1),vCls=v==='critical'?'crit':v==='defect'?'warn':'ok',vTxt=v==='defect'?(r.severity==='critical'?'严重缺陷':'缺陷'):'正常';verdict.textContent='判读结果: '+vTxt;verdict.className='single-img-verdict '+vCls;detail.textContent='置信度 '+cp+'%'+(r.defect_type?' · 类型: '+r.defect_type:'');resultDiv.style.display='flex';toast('识别完成: '+vTxt+' (置信度 '+cp+'%)',v==='defect'||v==='critical'?'info':'success');}
        else toast('识别完成，未获取到结果','info');
      }catch(e){overlay.classList.remove('show');toast('识别失败: '+e.message,'error');}
    }catch(e){toast('上传图片失败: '+e.message,'error');}
    finally{btn.disabled=false;btn.textContent='执行单张识别';}
  });
}

/* ---- Stats from API ---- */
async function loadStats(){try{const data=await API.stats();if(data.trained_weights!=null)$('#statTrained').textContent=data.trained_weights;}catch(e){}}

/* ---- Error log viewer ---- */
async function loadErrors(){try{var data=await API.errorLogs(50);var errors=data.errors||[];var el=$('#errIndicator');if(errors.length>0){el.style.display='flex';$('#errCount').textContent=errors.length>99?'99+':errors.length;}else el.style.display='none';}catch(e){}}
function renderErrorModal(){API.errorLogs(50).then(function(data){var errors=data.errors||[];var body=$('#errModalBody');$('#errModalTotal').textContent='共 '+data.total+' 条';if(errors.length===0){body.innerHTML='<div style="padding:40px;text-align:center;color:var(--text-3);">暂无错误记录</div>';return;}var html='<table class="err-table"><thead><tr><th>时间</th><th>类型</th><th>错误信息</th><th>端点</th><th>Traceback</th></tr></thead><tbody>';errors.forEach(function(e){var ts=e.timestamp?new Date(e.timestamp).toLocaleString('zh-CN'):'—';var tb=e.traceback&&e.traceback.length>0?e.traceback.slice(-2).join('\n'):'';html+='<tr><td class="err-ts">'+ts+'</td><td class="err-type">'+(e.error_type||'—')+'</td><td class="err-msg" title="'+(e.error_message||'').replace(/"/g,'&quot;')+'">'+(e.error_message||'—')+'</td><td class="err-ts">'+(e.method||'')+' '+(e.endpoint||'—')+'</td><td class="err-tb" title="'+tb.replace(/"/g,'&quot;')+'">'+(tb?tb.replace(/\n/g,' › '):'—')+'</td></tr>';});html+='</tbody></table>';body.innerHTML=html;}).catch(function(){$('#errModalBody').innerHTML='<div style="padding:40px;text-align:center;color:var(--text-3);">加载失败</div>';});}
function setupErrorModal(){$('#errIndicator').addEventListener('click',function(){openErrModal();});$('#errClose').addEventListener('click',closeErrModal);$('#errModal').addEventListener('click',function(e){if(e.target===$('#errModal'))closeErrModal();});$('#errClearBtn').addEventListener('click',function(){API.clearErrors().then(function(){renderErrorModal();loadErrors();toast('错误日志已清空','success');}).catch(function(){toast('清空失败','error');});});}
function openErrModal(){var m=$('#errModal');m.style.display='flex';var modal=m.querySelector('.t-modal');modal.classList.remove('is-closing');requestAnimationFrame(function(){modal.classList.add('is-open');});renderErrorModal();}
function closeErrModal(){var m=$('#errModal'),modal=m.querySelector('.t-modal'),closeMs=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--modal-close-dur'))||150;modal.classList.remove('is-open');modal.classList.add('is-closing');setTimeout(function(){modal.classList.remove('is-closing');m.style.display='none';},closeMs);}

/* ---- Scroll reveal ---- */
function setupReveal(){const items=document.querySelectorAll('.reveal');if(!('IntersectionObserver' in window)){items.forEach(i=>i.classList.add('in'));return;}const io=new IntersectionObserver((entries)=>{entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});},{threshold:0.12});items.forEach(i=>io.observe(i));}

/* ---- Multi-screen scroll jumps ---- */
function setupMultiScreenScroll(){
  const hero=document.getElementById('heroLanding'),ws=document.getElementById('workspace'),inf=document.getElementById('heroInference'),upCue=document.getElementById('scrollUp'),upCueInf=document.getElementById('scrollUpInf');
  if(!hero||!ws||!inf)return;
  const ANCHORS=[hero,ws,inf];
  const anchorTops=()=>ANCHORS.map((elm,i)=>{const top=Math.round(elm.getBoundingClientRect().top+window.scrollY);return i===0?0:top;});
  const currentIndex=()=>{const sy=window.scrollY,tops=anchorTops();let idx=0,best=Infinity;tops.forEach((y,i)=>{const d=Math.abs(sy-y);if(d<best){best=d;idx=i;}});return idx;};
  let jumpLock=false;
  const jumpTo=(i)=>{jumpLock=true;window.scrollTo({top:anchorTops()[i],behavior:'smooth'});setTimeout(()=>{jumpLock=false;},700);};
  const _screenIO=new IntersectionObserver((entries)=>{entries.forEach((en)=>{if(en.isIntersecting&&en.intersectionRatio>=0.55){const t=en.target;t.classList.add('is-entering');requestAnimationFrame(()=>requestAnimationFrame(()=>t.classList.remove('is-entering')));}});},{threshold:[0,0.55,1]});
  ANCHORS.forEach((a)=>_screenIO.observe(a));
  const inInnerScroll=(e)=>{let node=e.target;while(node&&node!==document.body){const oy=getComputedStyle(node).overflowY;if((oy==='auto'||oy==='scroll')&&node.scrollHeight>node.clientHeight+1){if(e.deltaY>0&&node.scrollTop+node.clientHeight<node.scrollHeight-1)return true;if(e.deltaY<0&&node.scrollTop>1)return true;}node=node.parentElement;}return false;};
  window.addEventListener('wheel',(e)=>{if(jumpLock){e.preventDefault();return;}if(inInnerScroll(e))return;const idx=currentIndex();if(e.deltaY>0&&idx<ANCHORS.length-1){e.preventDefault();jumpTo(idx+1);return;}if(e.deltaY<0&&idx>0){e.preventDefault();jumpTo(idx-1);return;}},{passive:false});
  window.addEventListener('keydown',(e)=>{const tag=(document.activeElement&&document.activeElement.tagName)||'';if(tag==='INPUT'||tag==='TEXTAREA'||tag==='SELECT')return;const idx=currentIndex();if((e.key==='ArrowDown'||e.key==='PageDown'||e.key===' ')&&idx<ANCHORS.length-1){e.preventDefault();jumpTo(idx+1);}else if((e.key==='ArrowUp'||e.key==='PageUp')&&idx>0){e.preventDefault();jumpTo(idx-1);}});
  if(upCue)upCue.addEventListener('click',(e)=>{e.preventDefault();window.scrollTo({top:0,behavior:'smooth'});});
  if(upCueInf)upCueInf.addEventListener('click',(e)=>{e.preventDefault();jumpTo(1);});
  function onScroll(){const scrolled=window.scrollY>2;document.body.classList.toggle('scrolled',scrolled);if(upCue)upCue.classList.toggle('show',scrolled);if(upCueInf)upCueInf.classList.toggle('show',currentIndex()===2);}
  window.addEventListener('scroll',onScroll,{passive:true});onScroll();
}

/* ---- Typewriter title ---- */
function startTypewriter(){
  const target=$('#typewriterText');if(!target)return;
  const text='视觉缺陷检测 训练与推理平台';const hlStart=7;let i=0;
  function type(){
    if(i<text.length){const ch=text.charAt(i);if(i<hlStart){target.textContent+=ch;}else{if(i===hlStart){const hl=document.createElement('span');hl.className='hl';hl.textContent=ch;target.appendChild(hl);}else{const hl=target.querySelector('.hl');if(hl)hl.textContent+=ch;}}i++;setTimeout(type,80+Math.random()*60);}
    else{const meta=document.querySelector('.hero-meta');if(meta)meta.classList.add('reveal');}
  }
  setTimeout(type,500);
}

/* ---- Init ---- */
async function init() {
  setupDatasetUpload();setupTrainingControls();setupReveal();setupMultiScreenScroll();setupErrorModal();setupInfBatch();setupInfSingleImage();
  $('#infPredictBtn').addEventListener('click',runInfPredict);
  setTimeout(startTypewriter,4300);
  const online=await checkApiStatus();
  if(online){await Promise.all([loadModels(),loadTrainingHistory(),loadStats(),loadInfModels(),refreshDatasets()]);loadErrors();}
  else{toast('API 后端未连接，请启动后端服务','error');$('#modelHint').textContent='离线';}
  checkReady();infCheckReady();updateTrainSummary();
  setInterval(checkApiStatus,30000);setInterval(loadErrors,45000);
  setupClickBlur();
}

/* ---- Click blur ---- */
function setupClickBlur(){
  const bg=document.getElementById('bgCanvas');if(!bg)return;let timer=null;
  document.addEventListener('click',(e)=>{
    const tag=e.target.tagName;
    if(tag==='BODY'||tag==='HTML'||tag==='DIV'&&!e.target.closest('.panel, button, .model-card, .weight-item, .upload-zone, .dataset-card, .field, .scroll-cue, .github-link'))return;
    if(timer)clearTimeout(timer);bg.classList.remove('click-blur-return');bg.classList.add('click-blur');
    timer=setTimeout(()=>{bg.classList.remove('click-blur');bg.classList.add('click-blur-return');setTimeout(()=>{bg.classList.remove('click-blur-return');},550);},600);
  });
}

/* ---- Refresh datasets from API ---- */
async function refreshDatasets() {
  try {
    const data = await API.datasets();
    const items = (data.dataset || []).map(d => ({
      batch_id: d.id, uploaded_at: null, can_train: !!d.can_train,
      images_file: d.size_kb != null ? { name: 'images.zip', size_kb: d.size_kb, image_count: d.image_count || 0 } : null,
      annotation_file: d.has_annotation ? { name: 'annotations.json', size_kb: 0 } : null,
      masks_file: d.masks_info || null,
    }));
    state.batches = items;
    renderDatasetList(); updateStats(); updateTrainSummary(); checkReady(); refreshBatches();
  } catch(e) { /* silent */ }
}

document.addEventListener('DOMContentLoaded', init);