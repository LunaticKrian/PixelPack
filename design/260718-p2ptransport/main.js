/* =====================================================================
   设计稿交互：状态切换预览（实现到 Transfer.vue 时整体删除）
   切换 html[data-state]，同步对端状态/频道标签/控制台提示/进度，
   让四种连接状态都能被肉眼审阅。
   ===================================================================== */
(function () {
  const STATES = {
    idle: {
      peerName: '???',
      peerDot: 'dot--off',
      peerText: '待连接',
      channel: 'EMPTY',
      hint: '生成频道码，或输入对方的码建立通道',
      pct: '0%',
      rate: '等待建立连接',
      fill: '0%',
      sendDisabled: true,
    },
    waiting: {
      peerName: '???',
      peerDot: 'dot--wait',
      peerText: '等待对方加入…',
      channel: 'SCANNING',
      hint: '把频道码告诉对方，等待其加入',
      pct: '0%',
      rate: '频道码 AB7K2X · 等待应答',
      fill: '0%',
      sendDisabled: true,
    },
    linked: {
      peerName: 'alice',
      peerDot: 'dot--ok',
      peerText: '已连接',
      channel: 'LINKED',
      hint: '通道就绪，可以投放货物',
      pct: '0%',
      rate: '已建立直连 · 等待选择货物',
      fill: '0%',
      sendDisabled: false,
    },
    transfer: {
      peerName: 'alice',
      peerDot: 'dot--ok',
      peerText: '已连接',
      channel: 'STREAMING',
      hint: '传输中，请保持页面在前台',
      pct: '63%',
      rate: '2.8 MB/s · 1.6 MB / 4.3 MB',
      fill: '63%',
      sendDisabled: true,
    },
  }

  const root = document.documentElement
  const $ = (s) => document.querySelector(s)
  const peerName = $('#peerName')
  const peerState = $('#peerState')
  const channelVal = $('#channelVal')
  const statusHint = $('#statusHint')
  const progPct = $('#progPct')
  const progRate = $('#progRate')
  const progFill = $('#progFill')
  const sendBtn = $('#sendBtn')

  function apply(key) {
    const s = STATES[key]
    root.setAttribute('data-state', key)

    peerName.textContent = s.peerName
    peerState.innerHTML = `<i class="dot ${s.peerDot}"></i> ${s.peerText}`
    channelVal.textContent = s.channel
    statusHint.textContent = s.hint
    progPct.textContent = s.pct
    progRate.textContent = s.rate
    progFill.style.width = s.fill
    sendBtn.disabled = s.sendDisabled

    document.querySelectorAll('.dev-switch button').forEach((b) => {
      b.classList.toggle('is-active', b.dataset.s === key)
    })
  }

  document.querySelectorAll('.dev-switch button').forEach((b) => {
    b.addEventListener('click', () => apply(b.dataset.s))
  })

  // 初始 = linked
  apply('linked')
})()
