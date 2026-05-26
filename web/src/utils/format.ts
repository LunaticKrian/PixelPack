export function formatCurrency(amount: number, currency = 'CNY'): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(amount)
}

export function formatDate(date: string): string {
  return new Date(date).toLocaleDateString('zh-CN')
}

export function formatDays(days: number): string {
  if (days < 30) return `${days}天`
  if (days < 365) {
    const months = Math.floor(days / 30)
    const remainDays = days % 30
    return `${months}个月${remainDays ? ` ${remainDays}天` : ''}`
  }
  const years = Math.floor(days / 365)
  const remainDays = days % 365
  return `${years}年${remainDays ? ` ${Math.floor(remainDays / 30)}个月` : ''}`
}
