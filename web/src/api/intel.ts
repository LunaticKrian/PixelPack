// ── 世界地图模块 · Mock 数据层 ────────────────────────────────────────
// 当前为前端 mock，函数均返回 Promise，便于后续无缝替换为真实 API（ofetch）。
// 日期相对今天生成，保证每次打开都是"新鲜"的每日推送。

import type { Article, IntelStats, RegionSlug } from '../types/intel'

/** 把"今天往前推 n 天"格式化为 YYYY-MM-DD */
function daysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

const today = () => daysAgo(0)

// ── 文章模板（dayOffset 相对今天；今日推送 dayOffset=0） ───────────────
interface ArticleSeed {
  region: RegionSlug
  title: string
  summary: string
  body: string
  source: string
  readTime: string
  url?: string
  dayOffset: number
}

const TODAY_SEEDS: ArticleSeed[] = [
  {
    region: 'llm',
    title: 'Opus 4.8 百万上下文实测：长文档检索的衰减曲线',
    summary: '在海量上下文窗口下重跑针-in-haystack，发现 600K token 后召回率出现明显塌方，附复现脚本。',
    body: '用 128 组 needle-in-haystack 与一组真实长合同 QA 压测了 Opus 4.8 的 1M 窗口。\n\n结论：前 600K token 召回稳定在 98% 以上；越过 600K 后，深度定位类问题的准确率以每 100K 约 6 个百分点的速度下滑。最脆弱的是「跨段聚合」类任务。\n\n建议：把超长文档做语义分块 + 检索增强，而不是整塞进上下文。复现脚本已开源。',
    source: 'Anthropic',
    readTime: '8 min',
    url: 'https://www.anthropic.com',
    dayOffset: 0,
  },
  {
    region: 'agent',
    title: 'Agent 记忆架构演进：从向量检索到结构化状态机',
    summary: '纯 RAG 记忆在多步任务里会丢状态。结构化状态机 + scratchpad 把长程任务完成率拉高了 34%。',
    body: '一个常见的 Agent 失效模式：跑了 20 步之后，它「忘了」第 3 步的约束——因为向量库里语义相近但时序无关的片段把它淹了。\n\n做法是把记忆分两层：\n· 事实层：向量检索，回答「是什么」。\n· 状态层：结构化 scratchpad（当前目标 / 已完成 / 待办 / 约束），每步强制读写。\n\n在 50 步以上的长程任务上，完成率从 51% 提到 85%。代价是每步多一次结构化写入。',
    source: '工程博客',
    readTime: '12 min',
    url: 'https://example.com/agent-memory',
    dayOffset: 0,
  },
  {
    region: 'infra',
    title: '投机解码 × 2-bit 量化：推理成本再降 40%',
    summary: '投机解码的拒绝机制天然消化了低比特量化的精度损失，两者叠加是当前最划算的推理组合。',
    body: '单独上 2-bit 量化，模型质量塌方；单独上投机解码，吞吐翻倍但单 token 成本没变。\n\n组合起来：draft model 用 4-bit，target 用 2-bit，投机解码的「拒绝并重采样」天然修正了 2-bit 的偶发乱码。实测吞吐 ×2.3，单 token 成本再降 40%，质量在 MMLU 上仅掉 1.2 分。生产可用。',
    source: 'Infra Weekly',
    readTime: '6 min',
    dayOffset: 0,
  },
  {
    region: 'research',
    title: 'VLA 模型 2026 综述：通用机器人的现状与瓶颈',
    summary: '从 RT-2 到 π0.5，VLA 在仿真里突飞猛进，但 sim-to-real 的长尾仍是最大瓶颈。',
    body: '视觉-语言-动作（VLA）模型这一年进展很快，但拆开看：\n· 强项：仿真环境内的泛化、语言指令跟随。\n· 弱项：真实世界长尾物体、可形变物体、接触丰富任务（拧螺丝、插拔）。\n\n瓶颈不在模型容量，而在真实交互数据的稀缺。几个团队在用「人类示教 + 仿真扩增」补这块，但 sim-to-real 的 gap 仍没有银弹。',
    source: 'arXiv 速读',
    readTime: '15 min',
    url: 'https://arxiv.org',
    dayOffset: 0,
  },
]

const ARCHIVE_SEEDS: ArticleSeed[] = [
  { region: 'llm', dayOffset: 2, readTime: '5 min', source: 'LongBench', title: 'LongBench-v3 评测解读：21 项长上下文任务的新基线', summary: '', body: '（历史记录正文 · 演示占位）\n\n该功能将在后端接入后提供完整正文阅读。当前原型展示情报卡的样式与交互。' },
  { region: 'agent', dayOffset: 5, readTime: '9 min', source: '工程博客', title: 'MCP 协议实战：把 12 个工具接进同一个 Agent', summary: '', body: '（历史记录正文 · 演示占位）' },
  { region: 'tools', dayOffset: 8, readTime: '4 min', source: 'CLI 周刊', title: '开源 CLI 工具盘点：替代日常重复操作的 7 个选择', summary: '', body: '（历史记录正文 · 演示占位）' },
  { region: 'vision', dayOffset: 13, readTime: '7 min', source: 'CV 简报', title: '扩散模型实时推理：LCM 与一致性蒸馏的横向对比', summary: '', body: '（历史记录正文 · 演示占位）' },
  { region: 'llm', dayOffset: 19, readTime: '11 min', source: 'MoE 专题', title: 'MoE 路由的可解释性：专家到底学会了什么', summary: '', body: '（历史记录正文 · 演示占位）' },
  { region: 'infra', dayOffset: 26, readTime: '6 min', source: 'Infra Weekly', title: 'KV Cache 量化：FP8 在生产环境的落地清单', summary: '', body: '（历史记录正文 · 演示占位）' },
  { region: 'research', dayOffset: 33, readTime: '14 min', source: 'arXiv 速读', title: '世界模型综述：从 Sora 到 Genie 2 的技术脉络', summary: '', body: '（历史记录正文 · 演示占位）' },
  { region: 'agent', dayOffset: 42, readTime: '10 min', source: 'Agent Lab', title: '多 Agent 协作：辩论式架构真的能减少幻觉吗', summary: '', body: '（历史记录正文 · 演示占位）' },
  { region: 'vision', dayOffset: 52, readTime: '6 min', source: 'CV 简报', title: 'OCR 已死？用 VLM 端到端解析复杂版式文档的实测', summary: '', body: '（历史记录正文 · 演示占位）' },
  { region: 'tools', dayOffset: 61, readTime: '8 min', source: '部署实战', title: '本地模型部署：ollama 与 vLLM 的选型决策树', summary: '', body: '（历史记录正文 · 演示占位）' },
]

let _id = 0
function toArticle(seed: ArticleSeed): Article {
  _id += 1
  return {
    id: _id,
    region: seed.region,
    title: seed.title,
    summary: seed.summary,
    body: seed.body,
    source: seed.source,
    readTime: seed.readTime,
    url: seed.url,
    publishedAt: daysAgo(seed.dayOffset),
  }
}

// 预生成全部文章（今日 + 归档）
const ALL_ARTICLES: Article[] = [...TODAY_SEEDS, ...ARCHIVE_SEEDS].map(toArticle)

/** 模拟网络延迟 */
function delay<T>(value: T, ms = 220): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms))
}

/** 今日推送（信号台） */
export function listTodayIntel(): Promise<Article[]> {
  const todayList = ALL_ARTICLES.filter((a) => a.publishedAt === today())
  return delay(todayList)
}

/** 历史归档（航海日志），可选按疆域筛选 */
export function listArchive(region?: RegionSlug | null): Promise<Article[]> {
  const list = ALL_ARTICLES.filter((a) => a.publishedAt !== today())
  const filtered = region ? list.filter((a) => a.region === region) : list
  // 按日期降序
  return delay([...filtered].sort((a, b) => (a.publishedAt < b.publishedAt ? 1 : -1)))
}

/** 顶部统计 */
export function getIntelStats(): Promise<IntelStats> {
  const todayList = ALL_ARTICLES.filter((a) => a.publishedAt === today())
  const archived = ALL_ARTICLES.length - todayList.length
  return delay({
    todayCount: todayList.length,
    weekCount: 18, // mock：本周累计
    archivedCount: 142 + archived, // mock：累计归档基数
    unreadCount: todayList.length, // 视觉效果：今日即未读
  })
}
