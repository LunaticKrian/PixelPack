/* ============================================================
   PixelPack · 世界地图模块 —— 共享 Shell 注入 + 通用交互
   <body data-page="..." data-layout="main"> 提供 #hud-top / #hud-bottom
   顶部导航：◈ 角色信息 ｜ ❖ 世界地图（新增，位于角色信息右侧）
   ============================================================ */

const USER = { name: 'Krian', level: 12 };

function el(html) {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

function renderShell() {
  const page = document.body.dataset.page || 'world-map';
  const $top = document.getElementById('hud-top');
  const $bot = document.getElementById('hud-bottom');
  if (!$top) return;

  // —— 顶部 HUD ——
  $top.appendChild(el(`
    <div class="hud-logo">
      <div class="hud-logo__mark">PP</div>
      <span>PixelPack</span>
    </div>
  `));
  const nav = el(`<nav class="hud-nav"></nav>`);
  nav.appendChild(el(`
    <a class="hud-nav__item ${page === 'index' ? 'is-active' : ''}" href="../v3.0/index.html">◈ 角色信息</a>
  `));
  nav.appendChild(el(`
    <a class="hud-nav__item ${page === '260711-world-map' ? 'is-active' : ''}" href="world-map.html">❖ 世界地图</a>
  `));
  $top.appendChild(nav);

  $top.appendChild(el(`
    <div class="hud-right">
      <span class="hud-coin">投币</span>
      <div class="hud-hp">
        <span class="hud-hp__label">HP</span>
        <div class="minibar"><div class="minibar__fill" style="width:78%"></div></div>
      </div>
    </div>
  `));

  // —— 底部状态栏 ——
  $bot.appendChild(el(`
    <a class="hud-user" href="../v3.0/settings.html">☺ ${USER.name}</a>
    <span class="hud-crumb">~ /world-map</span>
    <a class="hud-logout" href="../v3.0/login.html">退出</a>
  `));
}

/* ---------- 通用交互 ---------- */
function initModals() {
  document.querySelectorAll('[data-open]').forEach(btn => {
    btn.addEventListener('click', () => openModal(btn.dataset.open));
  });
  document.querySelectorAll('.modal').forEach(m => {
    m.querySelector('.modal__overlay')?.addEventListener('click', () => closeModal(m.id));
    m.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click', () => closeModal(m.id)));
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') document.querySelectorAll('.modal.is-open').forEach(m => m.classList.remove('is-open'));
  });
}
function openModal(id) { document.getElementById(id)?.classList.add('is-open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('is-open'); }

function notify(msg, type = '') {
  let wrap = document.querySelector('.toast-wrap');
  if (!wrap) { wrap = el('<div class="toast-wrap"></div>'); document.body.appendChild(wrap); }
  const t = el(`<div class="toast toast--${type}">${msg}</div>`);
  wrap.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 200); }, 2200);
}
window.notify = notify;

// 打字机（信号台 ticker）
function initTypewriter() {
  const tw = document.querySelector('[data-typewriter]');
  if (!tw) return;
  const lines = JSON.parse(tw.dataset.typewriter);
  const target = document.getElementById(tw.dataset.target) || tw;
  let li = 0, ci = 0, deleting = false;
  function tick() {
    const cur = lines[li];
    if (!deleting) {
      ci++; target.textContent = cur.slice(0, ci);
      if (ci >= cur.length) { deleting = true; return setTimeout(tick, 2200); }
    } else {
      ci--; target.textContent = cur.slice(0, ci);
      if (ci <= 0) { deleting = false; li = (li + 1) % lines.length; }
    }
    setTimeout(tick, deleting ? 28 : 55);
  }
  tick();
}

document.addEventListener('DOMContentLoaded', () => {
  renderShell();
  initModals();
  initTypewriter();
});
