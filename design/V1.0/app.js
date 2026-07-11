/* ============================================================
   PixelPack · 冒险者背包 —— 交互逻辑
   渲染 / 筛选 / 选中 / 键盘导航 / Toast
   ============================================================ */

// 物品数据 —— RPG 风味 + 日均成本（连接真实物品追踪功能）
const RARITY_LABEL = {
  common: '普通 · COMMON',
  rare:   '稀有 · RARE',
  epic:   '史诗 · EPIC',
  legend: '传说 · LEGEND',
};

const ITEMS = [
  // ── 武器 ──
  { id:'w1', cat:'weapon',     rarity:'rare',   icon:'🗡️', name:'霜咬短剑',   qty:1, equipped:true,
    desc:'寒霜铸成的匕首，刃上常凝白雾。出自北境冰窟的遗物，握柄缠着褪色的旧布。',
    stats:[ {l:'攻击 ATK', v:'+9'}, {l:'暴击', v:'+4%'}, {l:'冰属性', v:'+2'} ],
    daily:'1.8 💰/日' },
  { id:'w2', cat:'weapon',     rarity:'epic',   icon:'🏹', name:'破晓长弓',   qty:1,
    desc:'以晨光木与月银弦制成。据说破晓时分拉弓，箭矢会泛起淡金色的光。',
    stats:[ {l:'攻击 ATK', v:'+12'}, {l:'射程', v:'+1'}, {l:'敏捷', v:'+3'} ],
    daily:'3.4 💰/日' },
  { id:'w3', cat:'weapon',     rarity:'common', icon:'🔨', name:'生锈铁锤',   qty:1,
    desc:'一把再普通不过的铁锤，锈迹斑斑。修理防具时倒还趁手。',
    stats:[ {l:'攻击 ATK', v:'+3'}, {l:'修理', v:'+10%'} ],
    daily:'0.2 💰/日' },
  { id:'w4', cat:'weapon',     rarity:'legend', icon:'🪄', name:'龙息权杖',   qty:1,
    desc:'顶端封印着一缕古龙之焰。挥动时空气灼热扭曲，低语着被遗忘的真名。',
    stats:[ {l:'攻击 ATK', v:'+18'}, {l:'火焰', v:'+6'}, {l:'法力', v:'+25'} ],
    daily:'12.0 💰/日' },

  // ── 防具 ──
  { id:'a1', cat:'armor',      rarity:'common', icon:'🧥', name:'旅人斗篷',   qty:1, equipped:true,
    desc:'粗糙的羊毛斗篷，挡风遮雨足矣。领口绣着一个看不清的家族徽记。',
    stats:[ {l:'防御 DEF', v:'+2'}, {l:'抗寒', v:'+1'} ],
    daily:'0.4 💰/日' },
  { id:'a2', cat:'armor',      rarity:'rare',   icon:'🛡️', name:'秘银护腕',   qty:1,
    desc:'秘银薄片叠成的护腕，轻得不可思议，却坚硬如磐石。',
    stats:[ {l:'防御 DEF', v:'+5'}, {l:'魔抗', v:'+2'} ],
    daily:'2.1 💰/日' },
  { id:'a3', cat:'armor',      rarity:'epic',   icon:'🧣', name:'寒霜护甲',   qty:1,
    desc:'冰精灵祝福过的胸甲，表面终年覆着薄霜。攻击者会被寒意反噬。',
    stats:[ {l:'防御 DEF', v:'+9'}, {l:'冰抗', v:'+4'}, {l:'反伤', v:'+5%'} ],
    daily:'4.6 💰/日' },
  { id:'a4', cat:'armor',      rarity:'legend', icon:'👑', name:'王者之冠',   qty:1,
    desc:'失落王朝的加冕之冠。佩戴者周身光环流转，万物似皆俯首。',
    stats:[ {l:'防御 DEF', v:'+6'}, {l:'全属性', v:'+1'}, {l:'威严', v:'MAX'} ],
    daily:'18.5 💰/日' },

  // ── 消耗品 ──
  { id:'c1', cat:'consumable', rarity:'common', icon:'🧪', name:'红药水',     qty:5,
    desc:'涩中带甜的恢复药剂。冒险者的老朋友，没什么是一瓶红药解决不了的。',
    stats:[ {l:'效果', v:'回复 50 HP'} ],
    daily:'0.5 💰/日' },
  { id:'c2', cat:'consumable', rarity:'common', icon:'🍞', name:'勇气面包',   qty:8,
    desc:'酒馆老板娘烤的粗麦面包。饱腹之外，据说还能壮胆。',
    stats:[ {l:'效果', v:'回复 20 HP'}, {l:'勇气', v:'+1'} ],
    daily:'0.1 💰/日' },
  { id:'c3', cat:'consumable', rarity:'common', icon:'📜', name:'回城卷轴',   qty:3,
    desc:'淡蓝墨水绘就的传送卷轴。展开时会在脑海中浮现家乡的轮廓。',
    stats:[ {l:'效果', v:'传送至最近城镇'} ],
    daily:'0.3 💰/日' },
  { id:'c4', cat:'consumable', rarity:'epic',   icon:'🍶', name:'神秘药水',   qty:1,
    desc:'瓶身贴着褪色的警告标签，液体在瓶中缓缓变色。喝下去会发生什么，无人确知。',
    stats:[ {l:'效果', v:'暂时 +10 ATK'}, {l:'持续', v:'60 秒'} ],
    daily:'2.9 💰/日' },
  { id:'c5', cat:'consumable', rarity:'legend', icon:'🪶', name:'凤凰之羽',   qty:1,
    desc:'传说中凤凰褪下的尾羽，触手温热。持有者濒死之时，它会自行燃烧重生。',
    stats:[ {l:'效果', v:'一次性复活'} ],
    daily:'25.0 💰/日' },

  // ── 材料 ──
  { id:'m1', cat:'material',   rarity:'rare',   icon:'💎', name:'月光矿',     qty:6,
    desc:'只在满月夜显露于矿脉深处的蓝色矿石。打磨后会泛起幽幽冷光。',
    stats:[ {l:'用途', v:'锻造 / 附魔'} ],
    daily:'1.2 💰/日' },
  { id:'m2', cat:'material',   rarity:'epic',   icon:'🐲', name:'龙鳞片',     qty:2,
    desc:'坚硬且折射虹光的鳞片，从一头古龙的旧伤处剥落。刀剑难伤其分毫。',
    stats:[ {l:'用途', v:'顶级护甲素材'} ],
    daily:'5.5 💰/日' },
  { id:'m3', cat:'material',   rarity:'common', icon:'✨', name:'萤石粉末',   qty:14,
    desc:'研磨萤石得到的发光粉末，常用于炼金与照明。廉价而实用。',
    stats:[ {l:'用途', v:'炼金 / 照明'} ],
    daily:'0.05 💰/日' },
  { id:'m4', cat:'material',   rarity:'epic',   icon:'🪨', name:'古老符文',   qty:1,
    desc:'刻满失落文字的石板残片。凑近耳畔，依稀能听见远古的低吟。',
    stats:[ {l:'用途', v:'解谜 / 任务'} ],
    daily:'4.0 💰/日' },
  { id:'m5', cat:'material',   rarity:'legend', icon:'⭐', name:'星辰碎片',   qty:1,
    desc:'坠落于山顶的陨星残骸，至今仍微微发烫。其中蕴含的力量深不可测。',
    stats:[ {l:'用途', v:'传说级锻造'} ],
    daily:'30.0 💰/日' },
];

// ── 状态 ──
let currentFilter = 'all';
let selectedId = null;

const $grid   = document.getElementById('grid');
const $detail = document.getElementById('detail');
const $tabs   = document.getElementById('tabs');
const $toast  = document.getElementById('toast');
const $capNum = document.getElementById('capNum');
const $capFill= document.getElementById('capFill');

const CAP_MAX = 30;

// ── 工具 ──
const filteredItems = () =>
  ITEMS.filter(i => currentFilter === 'all' || i.cat === currentFilter);

function showToast(msg, gold = false) {
  $toast.textContent = msg;
  $toast.classList.toggle('toast--gold', gold);
  $toast.classList.add('is-show');
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => $toast.classList.remove('is-show'), 1600);
}

// ── 渲染：网格 ──
function renderGrid() {
  $grid.innerHTML = '';
  filteredItems().forEach((item, idx) => {
    const btn = document.createElement('button');
    btn.className = `item r-${item.rarity}`;
    btn.dataset.id = item.id;
    btn.style.animationDelay = `${Math.min(idx * 22, 360)}ms`;
    btn.setAttribute('aria-label', `${item.name} · ${RARITY_LABEL[item.rarity]}`);
    if (item.id === selectedId) btn.classList.add('is-selected');

    btn.innerHTML = `
      <div class="item__slot">${item.icon}</div>
      <div class="item__name">${item.name}</div>
      ${item.qty > 1 ? `<span class="item__qty">×${item.qty}</span>` : ''}
      ${item.equipped ? `<span class="item__eq">装</span>` : ''}
      <span class="item__gem"></span>
    `;
    btn.addEventListener('click', () => selectItem(item.id));
    $grid.appendChild(btn);
  });
  updateCapacity();
}

// ── 渲染：详情 ──
function renderDetail() {
  const item = ITEMS.find(i => i.id === selectedId);
  if (!item) {
    $detail.className = 'detail detail--empty';
    $detail.innerHTML = `
      <div class="detail__empty-icon">📦</div>
      <div class="detail__empty-text">选择一件物品查看详情</div>
      <div class="detail__empty-hint">CLICK OR USE ARROW KEYS</div>
    `;
    return;
  }
  $detail.className = 'detail';
  $detail.style.setProperty('--r', `var(--r-${item.rarity})`);

  const statsHtml = item.stats.map(s => `
    <li class="stat"><span class="stat__l">${s.l}</span><span class="stat__v">${s.v}</span></li>
  `).join('');

  const primaryLabel = item.equipped ? '卸下' : (item.cat === 'consumable' || item.cat === 'material' ? '使用' : '装备');

  $detail.innerHTML = `
    <div class="detail__inner">
      <div class="detail__head">
        <div class="detail__icon">${item.icon}</div>
        <div>
          <div class="detail__name">${item.name}${item.qty > 1 ? ` <span style="color:var(--text-dim);font-size:14px;">×${item.qty}</span>` : ''}</div>
          <span class="detail__rarity">${RARITY_LABEL[item.rarity]}</span>
        </div>
      </div>
      <p class="detail__desc">${item.desc}</p>
      <ul class="stats">${statsHtml}
        <li class="stat stat--gold"><span class="stat__l">日均成本</span><span class="stat__v">${item.daily}</span></li>
      </ul>
      <div class="actions">
        <button class="btn btn--primary" data-act="primary">${primaryLabel}</button>
        <button class="btn btn--danger" data-act="discard">丢弃</button>
      </div>
    </div>
  `;

  $detail.querySelector('[data-act="primary"]').addEventListener('click', () => onPrimary(item));
  $detail.querySelector('[data-act="discard"]').addEventListener('click', () => onDiscard(item));
}

// ── 选中 ──
function selectItem(id) {
  selectedId = id;
  document.querySelectorAll('.item').forEach(el => {
    el.classList.toggle('is-selected', el.dataset.id === id);
  });
  renderDetail();
}

// ── 动作 ──
function onPrimary(item) {
  if (item.cat === 'consumable' || item.cat === 'material') {
    if (item.qty > 1) { item.qty -= 1; showToast(`使用了 ${item.name}　剩余 ×${item.qty}`); }
    else { showToast(`使用了 ${item.name}`); }
  } else {
    // 装备 / 卸下（同类型唯一）
    ITEMS.filter(i => i.cat === item.cat && i.id !== item.id).forEach(i => i.equipped = false);
    item.equipped = !item.equipped;
    showToast(item.equipped ? `已装备　${item.name}` : `已卸下　${item.name}`, !item.equipped ? false : item.rarity === 'legend');
  }
  renderGrid();
  renderDetail();
}

function onDiscard(item) {
  const idx = ITEMS.findIndex(i => i.id === item.id);
  if (idx === -1) return;
  ITEMS.splice(idx, 1);
  selectedId = null;
  showToast(`丢弃了 ${item.name}`, true);
  renderGrid();
  renderDetail();
}

// ── 背包容量 ──
function updateCapacity() {
  const used = filteredItems().reduce((n, i) => n + i.qty, 0);
  $capNum.textContent = `${used} / ${CAP_MAX}`;
  $capFill.style.width = `${Math.min(100, (used / CAP_MAX) * 100)}%`;
}

// ── 筛选标签 ──
$tabs.addEventListener('click', e => {
  const tab = e.target.closest('.tab');
  if (!tab) return;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('is-active'));
  tab.classList.add('is-active');
  currentFilter = tab.dataset.filter;
  // 切换后若选中项被过滤掉，则清空选中
  if (selectedId && !filteredItems().some(i => i.id === selectedId)) selectedId = null;
  renderGrid();
  renderDetail();
});

// ── 键盘导航：方向键 / Enter / X ──
document.addEventListener('keydown', e => {
  const list = filteredItems();
  if (!list.length) return;
  let idx = list.findIndex(i => i.id === selectedId);

  if (e.key === 'ArrowRight' || e.key === 'ArrowLeft' || e.key === 'ArrowUp' || e.key === 'ArrowDown') {
    e.preventDefault();
    if (idx === -1) { selectItem(list[0].id); return; }
    const cols = getCols();
    let next = idx;
    if (e.key === 'ArrowRight') next = Math.min(list.length - 1, idx + 1);
    if (e.key === 'ArrowLeft')  next = Math.max(0, idx - 1);
    if (e.key === 'ArrowDown')  next = Math.min(list.length - 1, idx + cols);
    if (e.key === 'ArrowUp')    next = Math.max(0, idx - cols);
    selectItem(list[next].id);
    scrollSelectedIntoView();
  } else if (e.key === 'Enter') {
    e.preventDefault();
    const item = idx !== -1 ? list[idx] : list[0];
    if (item) { selectItem(item.id); onPrimary(item); }
  } else if (e.key === 'x' || e.key === 'X') {
    const item = idx !== -1 ? list[idx] : null;
    if (item) { selectItem(item.id); onDiscard(item); }
  }
});

function getCols() {
  const w = window.innerWidth;
  if (w <= 860) return 5;
  return 8;
}
function scrollSelectedIntoView() {
  const el = $grid.querySelector('.item.is-selected');
  if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

// ── 初始化 ──
renderGrid();
selectItem('w1');   // 默认选中已装备武器，首屏即展示详情 + 选中呼吸光
