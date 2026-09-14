document.addEventListener('DOMContentLoaded', () => {
  const $ = s => document.getElementById(s);
  const statusBadge = $('status-badge');
  const autoList = $('automation-list');
  const autoId = $('auto-id');
  const autoName = $('auto-name');
  const autoDesc = $('auto-desc');
  const autoSteps = $('auto-steps');
  const stepsList = $('steps-list');
  const btnNew = $('btn-new');
  const btnSave = $('btn-save');
  const btnRun = $('btn-run');
  const btnDelete = $('btn-delete');
  const logsContainer = $('logs-container');
  const resultsCard = $('results-card');
  const resultsContainer = $('results-container');
  const tabVisual = $('tab-visual');
  const tabJson = $('tab-json');
  const visualMode = $('visual-mode');
  const jsonMode = $('json-mode');
  const helpModal = $('help-modal');

  // ─── Step definitions ───
  const STEP_DEFS = {
    navigate:         { label: '🌐 هدایت به URL',    fields: [{key:'url',label:'آدرس URL',ph:'https://example.com'},{key:'wait',label:'انتظار (ثانیه)',ph:'2',type:'number'}] },
    click:            { label: '👆 کلیک',            fields: [{key:'selector',label:'سلکتور CSS',ph:'#login-btn'},{key:'wait',label:'انتظار (ثانیه)',ph:'0.5',type:'number'}] },
    type:             { label: '⌨️ تایپ متن',        fields: [{key:'selector',label:'سلکتور CSS',ph:'#username'},{key:'text',label:'متن',ph:'admin'}] },
    wait:             { label: '⏱️ انتظار زمانی',    fields: [{key:'seconds',label:'مدت (ثانیه)',ph:'1',type:'number'}] },
    wait_for_element: { label: '🔍 انتظار عنصر',    fields: [{key:'selector',label:'سلکتور CSS',ph:'.dashboard'},{key:'timeout',label:'حداکثر (ثانیه)',ph:'10',type:'number'}] },
    evaluate_js:      { label: '📜 اجرای JS',       fields: [{key:'code',label:'کد JavaScript',ph:'document.title',multiline:true}] },
    bale_export:      { label: '📨 استخراج بله',    fields: [{key:'count',label:'تعداد مخاطب',ph:'10',type:'number'},{key:'timeout',label:'تایم‌اوت (ثانیه)',ph:'20',type:'number'}] },
  };

  let currentSteps = [];
  let isVisual = true;

  // ─── Status ───
  async function checkStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      if (data.browser_active) {
        statusBadge.innerHTML = '<span class="pulse"></span> مرورگر فعال (پورت 9222)';
        statusBadge.className = 'badge badge-active';
      } else {
        statusBadge.innerHTML = '<span class="pulse"></span> مرورگر آماده نیست';
        statusBadge.className = 'badge badge-inactive';
      }
    } catch {
      statusBadge.innerHTML = '<span class="pulse"></span> ارتباط قطع';
      statusBadge.className = 'badge badge-inactive';
    }
  }

  // ─── Load automations list ───
  async function loadAutomations() {
    try {
      const items = await (await fetch('/api/automations')).json();
      autoList.innerHTML = '';
      items.forEach(item => {
        const li = document.createElement('li');
        li.innerHTML = `<span class="dot"></span>${item.name}`;
        li.onclick = () => selectAutomation(item);
        if (autoId.value && parseInt(autoId.value) === item.id) li.classList.add('active');
        autoList.appendChild(li);
      });
    } catch {}
  }

  function selectAutomation(item) {
    autoId.value = item.id;
    autoName.value = item.name;
    autoDesc.value = item.description || '';
    try {
      currentSteps = JSON.parse(item.steps_json);
    } catch {
      currentSteps = [];
    }
    renderVisualSteps();
    syncJsonFromVisual();
    btnDelete.style.display = 'inline-flex';
    $('editor-title').textContent = item.name;
    document.querySelectorAll('.auto-list li').forEach(li => li.classList.remove('active'));
    event.currentTarget.classList.add('active');
  }

  // ─── Visual Step Rendering ───
  function renderVisualSteps() {
    stepsList.innerHTML = '';
    currentSteps.forEach((step, i) => {
      const def = STEP_DEFS[step.action];
      if (!def) return;
      const card = document.createElement('div');
      card.className = 'step-card';
      card.innerHTML = `
        <div class="step-num">${i + 1}</div>
        <div class="step-fields">
          <div class="step-action-label">${def.label}</div>
          ${def.fields.map(f => `
            <div class="step-field">
              <label>${f.label}:</label>
              ${f.multiline
                ? `<textarea data-step="${i}" data-key="${f.key}" placeholder="${f.ph || ''}" rows="2">${step[f.key] || ''}</textarea>`
                : `<input type="${f.type || 'text'}" data-step="${i}" data-key="${f.key}" placeholder="${f.ph || ''}" value="${step[f.key] ?? ''}">`
              }
            </div>
          `).join('')}
        </div>
        <div class="step-actions">
          ${i > 0 ? `<button title="بالا" data-move-up="${i}">⬆️</button>` : ''}
          ${i < currentSteps.length - 1 ? `<button title="پایین" data-move-down="${i}">⬇️</button>` : ''}
          <button title="حذف گام" data-remove="${i}">❌</button>
        </div>
      `;
      stepsList.appendChild(card);
    });

    // Bind field changes
    stepsList.querySelectorAll('input, textarea').forEach(el => {
      el.addEventListener('input', () => {
        const idx = parseInt(el.dataset.step);
        const key = el.dataset.key;
        let val = el.value;
        if (el.type === 'number' && val) val = parseFloat(val);
        currentSteps[idx][key] = val;
        syncJsonFromVisual();
      });
    });

    // Bind actions
    stepsList.querySelectorAll('[data-remove]').forEach(btn => {
      btn.onclick = () => { currentSteps.splice(parseInt(btn.dataset.remove), 1); renderVisualSteps(); syncJsonFromVisual(); };
    });
    stepsList.querySelectorAll('[data-move-up]').forEach(btn => {
      btn.onclick = () => { const i = parseInt(btn.dataset.moveUp); [currentSteps[i-1], currentSteps[i]] = [currentSteps[i], currentSteps[i-1]]; renderVisualSteps(); syncJsonFromVisual(); };
    });
    stepsList.querySelectorAll('[data-move-down]').forEach(btn => {
      btn.onclick = () => { const i = parseInt(btn.dataset.moveDown); [currentSteps[i], currentSteps[i+1]] = [currentSteps[i+1], currentSteps[i]]; renderVisualSteps(); syncJsonFromVisual(); };
    });
  }

  function syncJsonFromVisual() {
    autoSteps.value = JSON.stringify(currentSteps, null, 2);
  }

  function syncVisualFromJson() {
    try {
      currentSteps = JSON.parse(autoSteps.value);
      renderVisualSteps();
    } catch {}
  }

  // ─── Add Step Chips ───
  document.querySelectorAll('.chip[data-action]').forEach(chip => {
    chip.onclick = () => {
      const action = chip.dataset.action;
      const newStep = { action };
      const def = STEP_DEFS[action];
      if (def) def.fields.forEach(f => { if (f.ph) newStep[f.key] = f.type === 'number' ? parseFloat(f.ph) : ''; });
      currentSteps.push(newStep);
      renderVisualSteps();
      syncJsonFromVisual();
      stepsList.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    };
  });

  // ─── Tab Switching ───
  tabVisual.onclick = () => {
    isVisual = true;
    tabVisual.classList.add('active');
    tabJson.classList.remove('active');
    visualMode.style.display = '';
    jsonMode.style.display = 'none';
    syncVisualFromJson();
  };
  tabJson.onclick = () => {
    isVisual = false;
    tabJson.classList.add('active');
    tabVisual.classList.remove('active');
    jsonMode.style.display = '';
    visualMode.style.display = 'none';
    syncJsonFromVisual();
  };

  // ─── New ───
  btnNew.onclick = () => {
    autoId.value = '';
    autoName.value = '';
    autoDesc.value = '';
    currentSteps = [];
    renderVisualSteps();
    syncJsonFromVisual();
    btnDelete.style.display = 'none';
    $('editor-title').textContent = 'اتوماسیون جدید';
    document.querySelectorAll('.auto-list li').forEach(li => li.classList.remove('active'));
  };

  // ─── Save ───
  btnSave.onclick = async () => {
    if (isVisual) syncJsonFromVisual();
    let steps;
    try { steps = JSON.parse(autoSteps.value); }
    catch { alert('ساختار JSON گام‌ها معتبر نیست!'); return; }

    if (!autoName.value.trim()) { alert('عنوان اتوماسیون را وارد کنید.'); return; }

    const payload = {
      id: autoId.value ? parseInt(autoId.value) : null,
      name: autoName.value,
      description: autoDesc.value,
      steps
    };

    const res = await fetch('/api/automations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      autoId.value = result.id;
      loadAutomations();
      showToast('اتوماسیون ذخیره شد.', 'success');
    }
  };

  // ─── Run ───
  btnRun.onclick = async () => {
    if (isVisual) syncJsonFromVisual();
    let steps;
    try { steps = JSON.parse(autoSteps.value); }
    catch { alert('ساختار JSON گام‌ها معتبر نیست!'); return; }

    if (!steps.length) { alert('حداقل یک گام تعریف کنید.'); return; }

    btnRun.disabled = true;
    btnRun.innerHTML = '<span class="icon">⏳</span> در حال اجرا...';

    try {
      const res = await fetch('/api/automations/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps, id: autoId.value ? parseInt(autoId.value) : null })
      });
      const data = await res.json();
      showResults(data);
      if (data.success) showToast('اتوماسیون با موفقیت اجرا شد.', 'success');
      else showToast('خطا: ' + data.error, 'error');
    } catch {
      showToast('خطای ارتباط با سرور.', 'error');
    } finally {
      btnRun.disabled = false;
      btnRun.innerHTML = '<span class="icon">▶</span> اجرا';
      loadLogs();
    }
  };

  function showResults(data) {
    resultsCard.style.display = '';
    resultsContainer.innerHTML = '';
    if (data.results) {
      data.results.forEach(r => {
        const div = document.createElement('div');
        div.className = `result-step ${r.status === 'success' ? 'ok' : 'fail'}`;
        div.innerHTML = `<span class="result-icon">${r.status === 'success' ? '✅' : '❌'}</span>
          <strong>گام ${r.step} (${r.action}):</strong> ${r.message || r.error || ''}`;
        resultsContainer.appendChild(div);
      });
    } else if (data.error) {
      resultsContainer.innerHTML = `<div class="result-step fail"><span class="result-icon">❌</span> ${data.error}</div>`;
    }
  }

  $('btn-close-results').onclick = () => { resultsCard.style.display = 'none'; };

  // ─── Delete ───
  btnDelete.onclick = async () => {
    if (!autoId.value || !confirm('آیا از حذف این اتوماسیون اطمینان دارید؟')) return;
    await fetch(`/api/automations?id=${autoId.value}`, { method: 'DELETE' });
    btnNew.click();
    loadAutomations();
    showToast('اتوماسیون حذف شد.', 'error');
  };

  // ─── Logs ───
  async function loadLogs() {
    try {
      const logs = await (await fetch('/api/logs')).json();
      if (!logs.length) {
        logsContainer.innerHTML = '<p class="empty-state">هنوز اجرایی ثبت نشده است.</p>';
        return;
      }
      logsContainer.innerHTML = '';
      logs.forEach(log => {
        const div = document.createElement('div');
        div.className = `log-item ${log.status === 'موفق' ? 'success' : 'error'}`;
        div.innerHTML = `<span class="log-time">${log.executed_at || ''}</span>
          <strong>${log.automation_name || 'دستی'}:</strong> ${log.message}`;
        logsContainer.appendChild(div);
      });
    } catch {}
  }

  $('btn-refresh-logs').onclick = loadLogs;

  // ─── Help Modal ───
  $('btn-help').onclick = () => { helpModal.style.display = 'flex'; };
  $('btn-close-help').onclick = () => { helpModal.style.display = 'none'; };
  helpModal.querySelector('.modal-backdrop').onclick = () => { helpModal.style.display = 'none'; };

  // ─── Toast ───
  function showToast(msg, type) {
    const toast = document.createElement('div');
    toast.style.cssText = `position:fixed;bottom:20px;left:50%;transform:translateX(-50%);padding:10px 24px;border-radius:8px;font-size:.9rem;font-weight:600;z-index:999;box-shadow:0 4px 12px rgba(0,0,0,.15);transition:opacity .3s;`;
    toast.style.background = type === 'success' ? '#059669' : '#dc2626';
    toast.style.color = '#fff';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 2500);
  }

  // ─── Init ───
  checkStatus();
  loadAutomations();
  loadLogs();
  setInterval(checkStatus, 5000);
});
