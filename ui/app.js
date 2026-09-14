document.addEventListener('DOMContentLoaded', () => {
  const statusBadge = document.getElementById('status-badge');
  const autoList = document.getElementById('automation-list');
  const autoId = document.getElementById('auto-id');
  const autoName = document.getElementById('auto-name');
  const autoDesc = document.getElementById('auto-desc');
  const autoSteps = document.getElementById('auto-steps');
  const btnNew = document.getElementById('btn-new');
  const btnSave = document.getElementById('btn-save');
  const btnRun = document.getElementById('btn-run');
  const btnDelete = document.getElementById('btn-delete');
  const logsContainer = document.getElementById('logs-container');
  const btnRefreshLogs = document.getElementById('btn-refresh-logs');

  const defaultTemplate = [
    { "action": "navigate", "url": "https://example.com", "wait": 2 },
    { "action": "click", "selector": "#login-button", "wait": 1 },
    { "action": "type", "selector": "#username", "text": "my_user" },
    { "action": "type", "selector": "#password", "text": "my_pass" },
    { "action": "wait", "seconds": 1 }
  ];

  async function checkBrowserStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      if (data.browser_active) {
        statusBadge.textContent = 'مرورگر اشکال‌زدایی فعال است (پورت 9222)';
        statusBadge.className = 'badge badge-active';
      } else {
        statusBadge.textContent = 'مرورگر آماده نیست (start-browser.cmd را اجرا کنید)';
        statusBadge.className = 'badge badge-inactive';
      }
    } catch {
      statusBadge.textContent = 'ارتباط با سرور قطع است';
      statusBadge.className = 'badge badge-inactive';
    }
  }

  async function loadAutomations() {
    try {
      const res = await fetch('/api/automations');
      const automations = await res.json();
      autoList.innerHTML = '';
      automations.forEach(item => {
        const li = document.createElement('li');
        li.textContent = item.name;
        li.onclick = () => selectAutomation(item);
        autoList.appendChild(li);
      });
    } catch (e) {
      console.error('Error loading automations', e);
    }
  }

  function selectAutomation(item) {
    autoId.value = item.id;
    autoName.value = item.name;
    autoDesc.value = item.description || '';
    try {
      const parsed = JSON.parse(item.steps_json);
      autoSteps.value = JSON.stringify(parsed, null, 2);
    } catch {
      autoSteps.value = item.steps_json;
    }
    btnDelete.style.display = 'inline-block';
  }

  btnNew.onclick = () => {
    autoId.value = '';
    autoName.value = 'اتوماسیون جدید';
    autoDesc.value = '';
    autoSteps.value = JSON.stringify(defaultTemplate, null, 2);
    btnDelete.style.display = 'none';
  };

  btnSave.onclick = async () => {
    let steps;
    try {
      steps = JSON.parse(autoSteps.value);
    } catch {
      alert('ساختار JSON گام‌ها معتبر نیست!');
      return;
    }

    const payload = {
      id: autoId.value ? parseInt(autoId.value) : null,
      name: autoName.value,
      description: autoDesc.value,
      steps: steps
    };

    const res = await fetch('/api/automations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    if (result.success) {
      alert('اتوماسیون با موفقیت ذخیره شد.');
      loadAutomations();
    }
  };

  btnRun.onclick = async () => {
    let steps;
    try {
      steps = JSON.parse(autoSteps.value);
    } catch {
      alert('ساختار JSON گام‌ها معتبر نیست!');
      return;
    }

    btnRun.disabled = true;
    btnRun.textContent = 'در حال اجرا...';

    try {
      const res = await fetch('/api/automations/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps: steps, id: autoId.value ? parseInt(autoId.value) : null })
      });
      const data = await res.json();
      if (data.success) {
        alert('اتوماسیون با موفقیت اجرا شد.');
      } else {
        alert('خطا در اجرا: ' + data.error);
      }
    } catch (e) {
      alert('خطای ارتباط با سرور.');
    } finally {
      btnRun.disabled = false;
      btnRun.textContent = '▶ اجرای اتوماسیون';
      loadLogs();
    }
  };

  btnDelete.onclick = async () => {
    if (!autoId.value || !confirm('آیا از حذف این اتوماسیون اطمینان دارید؟')) return;
    await fetch(`/api/automations?id=${autoId.value}`, { method: 'DELETE' });
    btnNew.click();
    loadAutomations();
  };

  async function loadLogs() {
    try {
      const res = await fetch('/api/logs');
      const logs = await res.json();
      logsContainer.innerHTML = '';
      logs.forEach(log => {
        const div = document.createElement('div');
        div.className = `log-item ${log.status === 'موفق' ? 'success' : 'error'}`;
        div.innerHTML = `<strong>[${log.executed_at}] [${log.status}]</strong> ${log.message}`;
        logsContainer.appendChild(div);
      });
    } catch (e) {
      console.error('Error loading logs', e);
    }
  }

  btnRefreshLogs.onclick = loadLogs;

  checkBrowserStatus();
  loadAutomations();
  loadLogs();
  setInterval(checkBrowserStatus, 5000);
});
