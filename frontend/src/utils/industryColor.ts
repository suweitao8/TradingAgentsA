/**
 * 行业分组着色工具
 *
 * 用确定性哈希把行业名映射到 12 个颜色组，保证同行业永远同色。
 * 用于 el-table 的 :row-class-name，配合 index.scss 的 .industry-group-N 色板。
 */

const NUM_GROUPS = 12

/**
 * 字符串确定性哈希 → 组号（0 ~ NUM_GROUPS-1）
 * 同一个行业名永远返回同一个组号
 */
function hashToGroup(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (hash * 31 + str.charCodeAt(i)) >>> 0 // 无符号右移保证非负
  }
  return hash % NUM_GROUPS
}

/**
 * 获取股票行业对应的 CSS class（用于 :row-class-name）
 * @param industry 行业名（如"半导体设备"、"银行"）
 * @returns class 名如 "industry-group-3"，空行业返回空字符串
 */
export function getIndustryClass(industry: string | undefined | null): string {
  if (!industry || industry.trim() === '' || industry === '-') {
    return ''
  }
  return `industry-group-${hashToGroup(industry.trim())}`
}

/**
 * 获取 ETF 类型对应的 CSS class
 * fund_type 只有 5 种固定值，直接映射到不同色组
 */
const ETF_TYPE_MAP: Record<string, number> = {
  '宽基': 0,
  '行业': 5,
  '主题': 2,
  '跨境': 7,
  '策略': 4,
}

export function getEtfTypeClass(fundType: string | undefined | null): string {
  if (!fundType) return ''
  const group = ETF_TYPE_MAP[fundType.trim()]
  if (group === undefined) return ''
  return `industry-group-${group}`
}
