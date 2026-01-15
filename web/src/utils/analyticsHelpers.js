/**
 * Analytics Helper Functions
 *
 * Pure utility functions for Analytics dashboard:
 * - Session and address filtering
 * - Consist color assignment (stroke, text, background)
 * - Data formatting (delta-t, operating time)
 */

import {
  CONSIST_COLOR_PALETTE,
  CONSIST_COLOR_CLASSES,
  CONSIST_BG_CLASSES
} from '../constants/analyticsConstants';

/**
 * Filter events by session (Current vs Overview mode)
 */
export const filterEventsBySession = (events, viewMode, currentSession) => {
  if (viewMode === 'current' && currentSession && events) {
    return events.filter(e => e.session_id === currentSession.session_id);
  }
  return events || [];
};

/**
 * Get locomotive addresses for consist filter (dynamic from config)
 */
export const getAddressFilter = (consistFilter, consistConfig) => {
  const config = consistConfig || {};
  if (consistFilter === 'all') {
    // All consists: flatten all addresses
    return Object.values(config).flatMap(c => c.addresses);
  }
  return config[consistFilter]?.addresses || [];
};

/**
 * Get consist stroke color (cyclic palette)
 */
export const getConsistStrokeColor = (consistId, consistConfig) => {
  const config = consistConfig || {};
  const consistIds = Object.keys(config).map(Number).sort((a, b) => a - b);
  const index = consistIds.indexOf(consistId);
  return index >= 0 ? CONSIST_COLOR_PALETTE[index % CONSIST_COLOR_PALETTE.length] : '#9CA3AF';
};

/**
 * Get consist text color class (cyclic palette)
 */
export const getConsistColorClass = (consistFilter, consistConfig, defaultColor = 'text-white') => {
  if (consistFilter === 'all') return defaultColor;
  const config = consistConfig || {};
  const consistIds = Object.keys(config).map(Number).sort((a, b) => a - b);
  const index = consistIds.indexOf(consistFilter);
  return index >= 0 ? CONSIST_COLOR_CLASSES[index % CONSIST_COLOR_CLASSES.length] : defaultColor;
};

/**
 * Get consist background color class for buttons (cyclic palette)
 */
export const getConsistBgClass = (consistId, consistConfig) => {
  const config = consistConfig || {};
  const consistIds = Object.keys(config).map(Number).sort((a, b) => a - b);
  const index = consistIds.indexOf(consistId);
  return index >= 0 ? CONSIST_BG_CLASSES[index % CONSIST_BG_CLASSES.length] : 'bg-slate-600';
};

/**
 * Format delta-t with sign (always show + for positive values)
 */
export const formatDeltaT = (value, decimals = 2) => {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}`;
};

/**
 * Format operating time seconds to "Xh Ym" format
 */
export const formatOperatingTime = (seconds) => {
  if (!seconds || seconds === 0) return '0h 0m';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
};
