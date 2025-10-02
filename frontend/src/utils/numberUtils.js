// Utility functions for number formatting

/**
 * Formats number according to Indian numbering system (lakhs/crores)
 * @param {number} num - Number to format
 * @param {boolean} includeCurrency - Whether to include ₹ symbol
 * @returns {string} Formatted number string
 */
export const formatIndianNumber = (num, includeCurrency = false) => {
  if (!num || isNaN(num)) return includeCurrency ? '₹0' : '0';
  
  const absNum = Math.abs(num);
  const isNegative = num < 0;
  
  let result = '';
  
  // Handle crores (10,000,000 and above)
  if (absNum >= 10000000) {
    const crores = (absNum / 10000000).toFixed(2);
    result = `${crores} Cr`;
  }
  // Handle lakhs (100,000 to 9,999,999)
  else if (absNum >= 100000) {
    const lakhs = (absNum / 100000).toFixed(2);
    result = `${lakhs} L`;
  }
  // Handle thousands (1,000 to 99,999)
  else if (absNum >= 1000) {
    const numStr = absNum.toString();
    const lastThree = numStr.slice(-3);
    const otherNumbers = numStr.slice(0, -3);
    const formatted = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + lastThree;
    result = formatted;
  }
  // Numbers less than 1000
  else {
    result = absNum.toString();
  }
  
  // Add negative sign if needed
  if (isNegative) result = '-' + result;
  
  // Add currency symbol if requested
  if (includeCurrency) result = '₹' + result;
  
  return result;
};

/**
 * Formats number for display in tables and charts with Indian formatting
 * @param {number} num - Number to format
 * @returns {string} Formatted number string
 */
export const formatTableNumber = (num) => {
  if (!num || isNaN(num)) return '0';
  
  const absNum = Math.abs(num);
  const isNegative = num < 0;
  
  if (absNum >= 1000) {
    const numStr = absNum.toString();
    const lastThree = numStr.slice(-3);
    const otherNumbers = numStr.slice(0, -3);
    const formatted = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + lastThree;
    return isNegative ? '-' + formatted : formatted;
  }
  
  return num.toString();
};

/**
 * Formats percentage with proper decimal places
 * @param {number} num - Percentage number
 * @param {number} decimals - Number of decimal places (default: 1)
 * @returns {string} Formatted percentage string
 */
export const formatPercentage = (num, decimals = 1) => {
  if (!num || isNaN(num)) return '0%';
  return `${num.toFixed(decimals)}%`;
};