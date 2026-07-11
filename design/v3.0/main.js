/* ============================================================
   PixelPack v2.0 —— 共享 Shell 注入 + 通用交互
   每个页面 <body data-page="..." data-layout="main|auth">
   MainLayout 页面提供 #hud-top / #hud-bottom 占位，由本文件填充。
   ============================================================ */

// 原型页面清单（开发导航，非产品 UI）
const PAGES = [
  { id: 'index',           href: 'index.html',           label: '角色信息 · Dashboard', gly: '◈' },
  { id: 'world-map',       href: '../world-map/world-map.html', label: '世界地图 · Intel',   gly: '❖' },
  { id: 'items',           href: 'items.html',           label: '背包 · ItemList',      gly: '◆' },
  { id: 'item-detail',     href: 'item-detail.html',     label: '物品详情 · ItemDetail', gly: '▶' },
  { id: 'quests',          href: 'quests.html',          label: '任务系统 · Quests',     gly: '▣' },
  { id: 'stats',           href: 'stats.html',           label: '数据统计 · Stats',      gly: '◢' },
  { id: 'blog',            href: 'blog.html',            label: '旅行日志 · Blog',       gly: '✦' },
  { id: 'categories',      href: 'categories.html',      label: '分类管理 · Categories', gly: '▦' },
  { id: 'settings',        href: 'settings.html',        label: '个人设置 · Settings',   gly: '◈' },
  { id: 'login',           href: 'login.html',           label: '登录 · Login',          gly: '▸' },
  { id: 'register',        href: 'register.html',        label: '注册 · Register',       gly: '✦' },
  { id: 'character-create',href: 'character-create.html',label: '角色创建 · Character',  gly: '☆' },
];

const CRUMB = {
  index: '/', items: '/items', 'item-detail': '/items/1042',
  quests: '/quests', stats: '/stats', blog: '/blog',
  categories: '/categories', settings: '/settings',
  login: '/login', register: '/register', 'character-create': '/character/create',
  'world-map': '/world-map',
};

const PAGE_LABEL = {
  index: '角色信息', items: '背包', 'item-detail': '物品详情',
  quests: '任务系统', stats: '数据统计', blog: '旅行日志',
  categories: '分类管理', settings: '个人设置', 'world-map': '世界地图',
};

const USER = { name: 'Krian', level: 12 };

function el(html) {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

function renderShell() {
  const page = document.body.dataset.page || 'index';
  const $top = document.getElementById('hud-top');
  const $bot = document.getElementById('hud-bottom');
  if (!$top) return; // auth 布局无 HUD

  // —— 顶部 HUD ——
  $top.appendChild(el(`
    <div class="hud-logo">
      <div class="hud-logo__mark">PP</div>
      <span>PixelPack</span>
    </div>
  `));
  const nav = el(`<nav class="hud-nav"></nav>`);
  // 真实 App：顶部导航 —— 角色信息 ｜ 世界地图（位于角色信息右侧）
  nav.appendChild(el(`
    <a class="hud-nav__item ${page === 'index' ? 'is-active' : ''}" href="index.html">◈ 角色信息</a>
  `));
  nav.appendChild(el(`
    <a class="hud-nav__item ${page === 'world-map' ? 'is-active' : ''}" href="../world-map/world-map.html">❖ 世界地图</a>
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
    <a class="hud-user" href="settings.html">☺ ${USER.name}</a>
    <span class="hud-crumb">~${CRUMB[page] || '/'}</span>
    <a class="hud-logout" href="login.html">退出</a>
  `));

  // —— 原型导航 ——
  const proto = el(`
    <div class="proto-nav">
      <button class="proto-nav__btn" id="protoBtn" aria-label="原型页面导航">📋</button>
      <div class="proto-nav__panel" id="protoPanel">
        <div class="proto-nav__title">PROTOTYPE NAV · 原型导航</div>
        <div class="proto-nav__list" id="protoList"></div>
      </div>
    </div>
  `);
  document.body.appendChild(proto);
  const list = proto.querySelector('#protoList');
  PAGES.forEach(p => {
    list.appendChild(el(
      `<a class="proto-nav__link ${p.id === page ? 'is-active' : ''}" href="${p.href}">${p.gly} ${p.label}</a>`
    ));
  });
  const btn = proto.querySelector('#protoBtn');
  const panel = proto.querySelector('#protoPanel');
  btn.addEventListener('click', e => { e.stopPropagation(); panel.classList.toggle('is-open'); });
  document.addEventListener('click', e => {
    if (!proto.contains(e.target)) panel.classList.remove('is-open');
  });
}

/* ---------- 通用交互 ---------- */

// 手风琴
function initAccordion() {
  document.querySelectorAll('.acc__head').forEach(head => {
    head.addEventListener('click', () => head.parentElement.classList.toggle('is-open'));
  });
}

// 标签页：[data-tab-group] 内 .tab 切换 [data-tab-panel]
function initTabs() {
  document.querySelectorAll('[data-tab-group]').forEach(group => {
    const tabs = group.querySelectorAll('.tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const target = tab.dataset.tab;
        tabs.forEach(t => t.classList.toggle('is-active', t === tab));
        group.querySelectorAll('[data-tab-panel]').forEach(p => {
          p.style.display = (p.dataset.tabPanel === target) ? '' : 'none';
        });
      });
    });
  });
}

// 模态：[data-open="id"] 打开；.modal__close / 遮罩 / Esc 关闭
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

// Toast
function notify(msg, type = '') {
  let wrap = document.querySelector('.toast-wrap');
  if (!wrap) { wrap = el('<div class="toast-wrap"></div>'); document.body.appendChild(wrap); }
  const t = el(`<div class="toast toast--${type}">${msg}</div>`);
  wrap.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 200); }, 2200);
}
window.notify = notify;

// 物品网格筛选（items.html 用）：按 data-cat 显示/隐藏
function initSlotFilter() {
  const filterBtns = document.querySelectorAll('[data-filter]');
  if (!filterBtns.length) return;
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.toggle('is-active', b === btn));
      const f = btn.dataset.filter;
      document.querySelectorAll('[data-cat]').forEach(slot => {
        slot.style.display = (f === 'all' || slot.dataset.cat === f) ? '' : 'none';
      });
    });
  });
}

// 简单的打字机效果（Dashboard 问候语）
function initTypewriter() {
  const tw = document.querySelector('[data-typewriter]');
  if (!tw) return;
  const lines = JSON.parse(tw.dataset.typewriter);
  let li = 0, ci = 0, deleting = false;
  function tick() {
    const cur = lines[li];
    if (!deleting) { ci++; tw.textContent = cur.slice(0, ci); if (ci >= cur.length) { deleting = true; return setTimeout(tick, 1600); } }
    else { ci--; tw.textContent = cur.slice(0, ci); if (ci <= 0) { deleting = false; li = (li + 1) % lines.length; } }
    setTimeout(tick, deleting ? 35 : 70);
  }
  tick();
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  renderShell();
  initAccordion();
  initTabs();
  initModals();
  initSlotFilter();
  initTypewriter();
});
