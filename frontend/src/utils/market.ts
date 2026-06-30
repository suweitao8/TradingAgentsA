// 市场参数规范化（本项目仅支持A股）
export const normalizeMarketForAnalysis = (_market: any): string => {
  return 'A股'
}

/**
 * 将交易所代码转换为市场类型（本项目仅支持A股）
 */
export const exchangeCodeToMarket = (_exchangeCode: string): string => {
  return 'A股'
}

/**
 * 根据股票代码判断市场类型（本项目仅支持A股）
 */
export const getMarketByStockCode = (_stockCode: string): string => {
  return 'A股'
}

export default {
  normalizeMarketForAnalysis,
  exchangeCodeToMarket,
  getMarketByStockCode
}
