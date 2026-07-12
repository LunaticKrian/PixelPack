/* =====================================================================
   PixelPack · 每日任务系统 V1.0 设计稿 · 交互演示
   - 委托交付印章切换 + 浮动经验
   - 新增委托（弹层用 prompt 演示）
   - 军师连线打字机 + 发送回声
   实际实现：tasks.html 走 REST，chat.html 走 SSE (fetch+ReadableStream)
   ===================================================================== */

/* ── 委托大厅：交付 / 撤销 ── */
function toggleQuest(el) {
  const q = el.closest('.quest');
  const done = q.classList.toggle('quest--done');
  el.textContent = done ? '✓' : '○';

  if (done) {
    // 浮动 +EXP
    const exp = q.querySelector('.quest__exp')?.textContent || '+10';
    const f = document.createElement('div');
    f.className = 'float-exp';
    f.textContent = exp;
    q.appendChild(f);
    setTimeout(() => f.remove(), 1100);
  }
  syncToday();
}

/* 重算今日进度条 + 计数 */
function syncToday() {
  const quests = document.querySelectorAll('.quest');
  const done = document.querySelectorAll('.quest--done').length;
  const total = quests.length;
  const head = document.querySelector('.today-stat b');
  if (head) head.textContent = done;
  const bar = document.querySelector('.today-bar__fill');
  if (bar) bar.style.width = (total ? (done / total * 100) : 0) + '%';
}

/* ── 新增委托（演示）── */
function openAdd() {
  const title = window.prompt('新增委托 · 标题');
  if (!title) return;
  const cat = window.prompt('分类 (study / work / life / health / other)', 'work') || 'work';
  addQuestDOM({ title, cat, exp: 20 });
}
function addQuestDOM({ title, cat, exp }) {
  const list = document.querySelector('.quests');
  if (!list) return;
  const gem = { study: '✎', work: '▦', life: '⌂', health: '✚', other: '◆' }[cat] || '◆';
  const node = document.createElement('article');
  node.className = 'quest';
  node.setAttribute('data-cat', cat);
  node.innerHTML = `
    <div class="quest__gem">${gem}</div>
    <div class="quest__main">
      <div class="quest__title">${escapeHTML(title)}</div>
      <div class="quest__meta">
        <span class="quest__diff">★☆☆</span>
        <span class="tag tag--manual">手动</span>
        <span>待执行</span>
      </div>
    </div>
    <div class="quest__exp">+${exp}</div>
    <div class="quest__check" onclick="toggleQuest(this)">○</div>`;
  list.appendChild(node);
  syncToday();
}

/* ── 军师连线：发送回声 + 打字机 ── */
function sendDemo() {
  const box = document.getElementById('composer');
  const thread = document.getElementById('thread');
  if (!box || !thread) return;
  const text = box.value.trim();
  if (!text) return;

  // 1. 我的消息
  appendMsg('me', '你', text);
  box.value = '';

  // 2. 内核状态行
  const tool = document.createElement('div');
  tool.className = 'tool-line';
  tool.innerHTML = '<span class="tool-line__dot"></span> 内核运行中 · 生成任务 …';
  thread.appendChild(tool);

  // 3. 模拟一段打字机回复
  setTimeout(() => {
    tool.remove();
    const reply = '收到。已将你的计划解析为任务节点写入今日清单。建议优先处理高难度项，趁当前算力充沛。';
    typeWriter('ai', 'NEXA', reply);
  }, 700);
}

function appendMsg(who, name, html) {
  const thread = document.getElementById('thread');
  if (!thread) return;
  const av = who === 'me' ? '◈' : '';   // AI 头像留空，由 .sci CSS 绘制内核
  const node = document.createElement('div');
  node.className = 'msg msg--' + who;
  node.innerHTML = `
    <div class="msg__avatar">${av}</div>
    <div class="msg__col">
      <div class="msg__name">${name}</div>
      <div class="msg__bubble">${escapeHTML(html)}</div>
    </div>`;
  thread.appendChild(node);
  thread.scrollTop = thread.scrollHeight;
}

function typeWriter(who, name, full) {
  const thread = document.getElementById('thread');
  if (!thread) return;
  const av = who === 'me' ? '◈' : '';   // AI 头像留空，由 .sci CSS 绘制内核
  const node = document.createElement('div');
  node.className = 'msg msg--' + who;
  node.innerHTML = `
    <div class="msg__avatar">${av}</div>
    <div class="msg__col">
      <div class="msg__name">${name}</div>
      <div class="msg__bubble"><span class="tw"></span><span class="cursor"></span></div>
    </div>`;
  thread.appendChild(node);
  const span = node.querySelector('.tw');
  let i = 0;
  const tick = setInterval(() => {
    span.textContent = full.slice(0, ++i);
    thread.scrollTop = thread.scrollHeight;
    if (i >= full.length) {
      clearInterval(tick);
      node.querySelector('.cursor')?.remove();
    }
  }, 45);
}

function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

document.addEventListener('DOMContentLoaded', syncToday);
