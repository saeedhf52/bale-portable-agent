document.addEventListener('DOMContentLoaded', () => {
  const $ = s => document.getElementById(s);
  const statusBadge = $('status-badge');
  const autoList = $('automation-list');
  const templateList = $('template-list');
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

  // ─── Step Definitions ───
  const STEP_DEFS = {
    navigate:         { label:'🌐 هدایت به URL',      fields:[{key:'url',label:'آدرس URL',ph:'https://example.com'},{key:'wait',label:'انتظار (ث)',ph:'2',type:'number'}] },
    click:            { label:'👆 کلیک',              fields:[{key:'selector',label:'سلکتور',ph:'#login-btn'},{key:'wait',label:'انتظار (ث)',ph:'0.5',type:'number'}] },
    type:             { label:'⌨️ تایپ متن',          fields:[{key:'selector',label:'سلکتور',ph:'#username'},{key:'text',label:'متن',ph:'admin'}] },
    type_human:       { label:'🤖 تایپ هوشمند',       fields:[{key:'selector',label:'سلکتور',ph:'#password'},{key:'text',label:'متن',ph:'mypass'},{key:'char_delay',label:'تاخیر (ث)',ph:'0.08',type:'number'}] },
    select_option:    { label:'📋 انتخاب گزینه',      fields:[{key:'selector',label:'سلکتور select',ph:'select#city'},{key:'value',label:'مقدار',ph:'tehran'}] },
    wait:             { label:'⏱️ انتظار زمانی',      fields:[{key:'seconds',label:'مدت (ث)',ph:'1',type:'number'}] },
    wait_for_element: { label:'🔍 انتظار عنصر',       fields:[{key:'selector',label:'سلکتور',ph:'.dashboard'},{key:'timeout',label:'حداکثر (ث)',ph:'10',type:'number'}] },
    wait_element_gone:{ label:'👻 ناپدیدشدن عنصر',    fields:[{key:'selector',label:'سلکتور',ph:'.loading-spinner'},{key:'timeout',label:'حداکثر (ث)',ph:'15',type:'number'}] },
    wait_for_human:   { label:'🧑 دخالت کاربر',       fields:[{key:'prompt',label:'پیام',ph:'کپچا را حل کنید...'},{key:'success_selector',label:'سلکتور موفقیت',ph:'.dashboard'},{key:'timeout',label:'حداکثر (ث)',ph:'120',type:'number'}] },
    extract_text:     { label:'📝 استخراج متن',       fields:[{key:'selector',label:'سلکتور',ph:'h1.title'},{key:'attribute',label:'ویژگی (اختیاری)',ph:''},{key:'store_as',label:'نام متغیر',ph:'title'}] },
    extract_list:     { label:'📃 استخراج لیست',      fields:[{key:'selector',label:'سلکتور',ph:'.item'},{key:'attribute',label:'ویژگی',ph:''},{key:'store_as',label:'نام متغیر',ph:'items'}] },
    crawl_links:      { label:'🔗 جمع‌آوری لینک‌ها',    fields:[{key:'selector',label:'سلکتور',ph:'a[href]'},{key:'store_as',label:'نام متغیر',ph:'links'}] },
    scroll:           { label:'📜 اسکرول',            fields:[{key:'selector',label:'سلکتور (خالی=صفحه)',ph:''},{key:'direction',label:'جهت',ph:'down'},{key:'amount',label:'مقدار (px)',ph:'500',type:'number'}] },
    scroll_to_bottom: { label:'⏬ پیمایش کامل',       fields:[{key:'selector',label:'سلکتور (خالی=صفحه)',ph:''},{key:'max_scrolls',label:'حداکثر دفعات',ph:'20',type:'number'},{key:'wait',label:'وقفه (ث)',ph:'1',type:'number'}] },
    screenshot:       { label:'📸 اسکرین‌شات',        fields:[] },
    set_variable:     { label:'📌 تعریف متغیر',       fields:[{key:'key',label:'نام',ph:'user'},{key:'value',label:'مقدار',ph:'admin'}] },
    evaluate_js:      { label:'📜 اجرای JS',          fields:[{key:'code',label:'کد JavaScript',ph:'document.title',multiline:true},{key:'store_as',label:'ذخیره در متغیر',ph:''}] },
    loop:             { label:'🔁 حلقه تکرار',        fields:[{key:'count',label:'تعداد',ph:'3',type:'number'}] },
    conditional:      { label:'❓ اجرای شرطی',        fields:[{key:'selector',label:'سلکتور شرط',ph:'.error-msg'}] },
    bale_export:      { label:'📨 استخراج بله',       fields:[{key:'count',label:'تعداد مخاطب',ph:'10',type:'number'},{key:'timeout',label:'تایم‌اوت (ث)',ph:'20',type:'number'}] },
  };

  let currentSteps = [];
  let isVisual = true;

  // ─── Status ───
  async function checkStatus() {
    try {
      const data = await (await fetch('/api/status')).json();
      if (data.browser_active) {
        statusBadge.innerHTML = '<span class="pulse"></span> مرورگر فعال';
        statusBadge.className = 'badge badge-active';
      } else {
        statusBadge.innerHTML = '<span class="pulse"></span> مرورگر آماده نیست';
        statusBadge.className = 'badge badge-inactive';
      }
    } catch {
      statusBadge.innerHTML = '<span class="pulse"></span> قطع ارتباط';
      statusBadge.className = 'badge badge-inactive';
    }
  }

  // ─── Automations ───
  async function loadAutomations() {
    try {
      const items = await (await fetch('/api/automations')).json();
      autoList.innerHTML = '';
      items.forEach(item => {
        const li = document.createElement('li');
        li.innerHTML = `<span class="dot"></span>${item.name}`;
        li.onclick = () => { selectAutomation(item); markActive(autoList, li); };
        if (autoId.value && parseInt(autoId.value) === item.id) li.classList.add('active');
        autoList.appendChild(li);
      });
    } catch {}
  }

  function markActive(list, activeLi) {
    list.querySelectorAll('li').forEach(l => l.classList.remove('active'));
    activeLi.classList.add('active');
    // Clear active in the other list
    const other = list === autoList ? templateList : autoList;
    other.querySelectorAll('li').forEach(l => l.classList.remove('active'));
  }

  function selectAutomation(item) {
    autoId.value = item.id || '';
    autoName.value = item.name || '';
    autoDesc.value = item.description || '';
    try { currentSteps = JSON.parse(typeof item.steps_json === 'string' ? item.steps_json : JSON.stringify(item.steps || [])); }
    catch { currentSteps = item.steps || []; }
    renderVisualSteps();
    syncJsonFromVisual();
    btnDelete.style.display = item.id ? 'inline-flex' : 'none';
    $('editor-title').textContent = item.name || 'اتوماسیون جدید';
  }

  // ─── Templates ───
  async function loadTemplates() {
    try {
      const tpls = await (await fetch('/api/templates')).json();
      templateList.innerHTML = '';
      Object.entries(tpls).forEach(([key, tpl]) => {
        const li = document.createElement('li');
        li.innerHTML = `<span class="dot"></span>${tpl.name}`;
        li.title = tpl.description;
        li.onclick = () => {
          autoId.value = '';
          autoName.value = tpl.name;
          autoDesc.value = tpl.description;
          currentSteps = JSON.parse(JSON.stringify(tpl.steps));
          renderVisualSteps();
          syncJsonFromVisual();
          btnDelete.style.display = 'none';
          $('editor-title').textContent = '📦 ' + tpl.name;
          markActive(templateList, li);
        };
        templateList.appendChild(li);
      });
    } catch {}
  }

  // ─── Visual Step Rendering ───
  function renderVisualSteps() {
    stepsList.innerHTML = '';
    if (!currentSteps.length) {
      stepsList.innerHTML = '<p class="empty-state">هنوز گامی تعریف نشده. از چیپ‌های زیر یک گام اضافه کنید.</p>';
      return;
    }
    currentSteps.forEach((step, i) => {
      const def = STEP_DEFS[step.action];
      if (!def) {
        const card = document.createElement('div');
        card.className = 'step-card';
        card.innerHTML = `<div class="step-num">${i+1}</div><div class="step-fields"><div class="step-action-label">⚠️ ${step.action || 'نامشخص'}</div></div>
          <div class="step-actions"><button data-remove="${i}" title="حذف">❌</button></div>`;
        stepsList.appendChild(card);
        return;
      }
      const card = document.createElement('div');
      card.className = 'step-card';
      card.innerHTML = `
        <div class="step-num">${i+1}</div>
        <div class="step-fields">
          <div class="step-action-label">${def.label}</div>
          ${def.fields.map(f => `
            <div class="step-field">
              <label>${f.label}:</label>
              ${f.multiline
                ? `<textarea data-step="${i}" data-key="${f.key}" placeholder="${f.ph||''}" rows="2">${step[f.key]||''}</textarea>`
                : `<input type="${f.type||'text'}" data-step="${i}" data-key="${f.key}" placeholder="${f.ph||''}" value="${step[f.key]??''}">`
              }
            </div>`).join('')}
        </div>
        <div class="step-actions">
          ${i>0?`<button title="بالا" data-move-up="${i}">⬆️</button>`:''}
          ${i<currentSteps.length-1?`<button title="پایین" data-move-down="${i}">⬇️</button>`:''}
          <button title="کپی" data-dup="${i}">📋</button>
          <button title="حذف" data-remove="${i}">❌</button>
        </div>`;
      stepsList.appendChild(card);
    });

    // Bind inputs
    stepsList.querySelectorAll('input, textarea').forEach(el => {
      el.addEventListener('input', () => {
        const idx = parseInt(el.dataset.step);
        let val = el.value;
        if (el.type === 'number' && val) val = parseFloat(val);
        currentSteps[idx][el.dataset.key] = val;
        syncJsonFromVisual();
      });
    });

    // Bind actions
    stepsList.querySelectorAll('[data-remove]').forEach(btn => {
      btn.onclick = () => { currentSteps.splice(parseInt(btn.dataset.remove), 1); renderVisualSteps(); syncJsonFromVisual(); };
    });
    stepsList.querySelectorAll('[data-move-up]').forEach(btn => {
      btn.onclick = () => { const i=parseInt(btn.dataset.moveUp); [currentSteps[i-1],currentSteps[i]]=[currentSteps[i],currentSteps[i-1]]; renderVisualSteps(); syncJsonFromVisual(); };
    });
    stepsList.querySelectorAll('[data-move-down]').forEach(btn => {
      btn.onclick = () => { const i=parseInt(btn.dataset.moveDown); [currentSteps[i],currentSteps[i+1]]=[currentSteps[i+1],currentSteps[i]]; renderVisualSteps(); syncJsonFromVisual(); };
    });
    stepsList.querySelectorAll('[data-dup]').forEach(btn => {
      btn.onclick = () => { const i=parseInt(btn.dataset.dup); currentSteps.splice(i+1,0,JSON.parse(JSON.stringify(currentSteps[i]))); renderVisualSteps(); syncJsonFromVisual(); };
    });
  }

  function syncJsonFromVisual() { autoSteps.value = JSON.stringify(currentSteps, null, 2); }
  function syncVisualFromJson() { try { currentSteps = JSON.parse(autoSteps.value); renderVisualSteps(); } catch {} }

  // ─── Add Step Chips ───
  document.querySelectorAll('.chip[data-action]').forEach(chip => {
    chip.onclick = () => {
      const action = chip.dataset.action;
      const newStep = { action };
      const def = STEP_DEFS[action];
      if (def) def.fields.forEach(f => { newStep[f.key] = ''; });
      currentSteps.push(newStep);
      renderVisualSteps();
      syncJsonFromVisual();
      stepsList.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    };
  });

  // ─── Tabs ───
  tabVisual.onclick = () => { isVisual=true; tabVisual.classList.add('active'); tabJson.classList.remove('active'); visualMode.style.display=''; jsonMode.style.display='none'; syncVisualFromJson(); };
  tabJson.onclick = () => { isVisual=false; tabJson.classList.add('active'); tabVisual.classList.remove('active'); jsonMode.style.display=''; visualMode.style.display='none'; syncJsonFromVisual(); };

  // ─── New ───
  btnNew.onclick = () => {
    autoId.value=''; autoName.value=''; autoDesc.value='';
    currentSteps=[]; renderVisualSteps(); syncJsonFromVisual();
    btnDelete.style.display='none'; $('editor-title').textContent='اتوماسیون جدید';
    autoList.querySelectorAll('li').forEach(l=>l.classList.remove('active'));
    templateList.querySelectorAll('li').forEach(l=>l.classList.remove('active'));
  };

  // ─── Save ───
  btnSave.onclick = async () => {
    if(isVisual) syncJsonFromVisual();
    let steps; try { steps=JSON.parse(autoSteps.value); } catch { toast('ساختار JSON معتبر نیست!','error'); return; }
    if(!autoName.value.trim()) { toast('عنوان را وارد کنید.','error'); return; }
    const res = await fetch('/api/automations', { method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ id:autoId.value?parseInt(autoId.value):null, name:autoName.value, description:autoDesc.value, steps }) });
    const result = await res.json();
    if(result.success) { autoId.value=result.id; btnDelete.style.display='inline-flex'; loadAutomations(); toast('ذخیره شد.','success'); }
  };

  // ─── Run ───
  btnRun.onclick = async () => {
    if(isVisual) syncJsonFromVisual();
    let steps; try { steps=JSON.parse(autoSteps.value); } catch { toast('ساختار JSON معتبر نیست!','error'); return; }
    if(!steps.length) { toast('حداقل یک گام تعریف کنید.','error'); return; }
    btnRun.disabled=true; btnRun.innerHTML='<span class="icon">⏳</span> در حال اجرا...';
    try {
      const res = await fetch('/api/automations/run', { method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ steps, id:autoId.value?parseInt(autoId.value):null }) });
      const data = await res.json();
      showResults(data);
      toast(data.success?'اجرا موفق بود.':'خطا: '+data.error, data.success?'success':'error');
    } catch { toast('خطای ارتباط با سرور.','error'); }
    finally { btnRun.disabled=false; btnRun.innerHTML='<span class="icon">▶</span> اجرا'; loadLogs(); }
  };

  function showResults(data) {
    resultsCard.style.display='';
    resultsContainer.innerHTML='';
    if(data.results) {
      data.results.forEach(r => {
        const div=document.createElement('div');
        div.className=`result-step ${r.status==='success'?'ok':'fail'}`;
        div.innerHTML=`<strong>گام ${r.step} (${r.action}):</strong> ${r.message||r.error||''}`;
        resultsContainer.appendChild(div);
      });
    } else if(data.error) {
      resultsContainer.innerHTML=`<div class="result-step fail">❌ ${data.error}</div>`;
    }
  }
  $('btn-close-results').onclick = () => { resultsCard.style.display='none'; };

  // ─── Delete ───
  btnDelete.onclick = async () => {
    if(!autoId.value || !confirm('آیا از حذف اطمینان دارید؟')) return;
    await fetch(`/api/automations?id=${autoId.value}`, {method:'DELETE'});
    btnNew.click(); loadAutomations(); toast('حذف شد.','error');
  };

  // ─── Logs ───
  async function loadLogs() {
    try {
      const logs = await (await fetch('/api/logs')).json();
      if(!logs.length) { logsContainer.innerHTML='<p class="empty-state">هنوز اجرایی ثبت نشده.</p>'; return; }
      logsContainer.innerHTML='';
      logs.forEach(log => {
        const div=document.createElement('div');
        div.className=`log-item ${log.status==='موفق'?'success':'error'}`;
        div.innerHTML=`<span class="log-time">${log.executed_at||''}</span><strong>${log.automation_name||'دستی'}:</strong> ${log.message}`;
        logsContainer.appendChild(div);
      });
    } catch {}
  }
  $('btn-refresh-logs').onclick = loadLogs;

  // ─── Help ───
  $('btn-help').onclick = () => { helpModal.style.display='flex'; };
  $('btn-close-help').onclick = () => { helpModal.style.display='none'; };
  helpModal.querySelector('.modal-backdrop').onclick = () => { helpModal.style.display='none'; };

  // ─── Toast ───
  function toast(msg, type) {
    const el=document.createElement('div');
    el.className='toast';
    el.style.background = type==='success'?'#059669':'#dc2626';
    el.textContent=msg;
    document.body.appendChild(el);
    setTimeout(()=>{ el.style.opacity='0'; setTimeout(()=>el.remove(),300); },2500);
  }

  // ─── Init ───
  checkStatus(); loadAutomations(); loadTemplates(); loadLogs();
  setInterval(checkStatus, 5000);
});
