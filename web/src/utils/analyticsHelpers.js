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
  CONSIST_BG_CLASSES,
  SPEED_STATUS_COLORS
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

/**
 * Generate speed tuning chart reference lines from config thresholds
 * @param {Object} thresholds - Delta-t thresholds from config (synced_threshold, warning_threshold, critical_threshold)
 * @returns {Array} Reference line objects for Recharts
 */
export const getSpeedTuningReferenceLines = (thresholds) => {
  if (!thresholds) return [];

  const { synced_threshold, warning_threshold, critical_threshold } = thresholds;

  return [
    { y: 0, label: 'Perfect Sync', stroke: '#6b7280', strokeDasharray: '5 5' },
    { y: synced_threshold, label: 'SYNCED', stroke: SPEED_STATUS_COLORS.SYNCED, strokeDasharray: '3 3' },
    { y: -synced_threshold, label: '', stroke: SPEED_STATUS_COLORS.SYNCED, strokeDasharray: '3 3' },
    { y: warning_threshold, label: 'WARNING', stroke: SPEED_STATUS_COLORS.WARNING, strokeDasharray: '3 3' },
    { y: -warning_threshold, label: '', stroke: SPEED_STATUS_COLORS.WARNING, strokeDasharray: '3 3' },
    { y: critical_threshold, label: 'ACTION', stroke: SPEED_STATUS_COLORS.CRITICAL, strokeDasharray: '3 3' },
    { y: -critical_threshold, label: '', stroke: SPEED_STATUS_COLORS.CRITICAL, strokeDasharray: '3 3' }
  ];
};

/**
 * Get dominant status color for speed bucket (based on status distribution)
 * @param {Object} statusDistribution - Status counts (SYNCED, WARNING, CRITICAL)
 * @returns {string} Hex color for dominant status
 */
export const getSpeedBucketColor = (statusDistribution) => {
  if (!statusDistribution) return SPEED_STATUS_COLORS.SYNCED;

  const total = Object.values(statusDistribution).reduce((sum, count) => sum + count, 0);
  if (total === 0) return SPEED_STATUS_COLORS.SYNCED;

  // Dominant status = highest percentage
  const percentages = {
    SYNCED: (statusDistribution.SYNCED || 0) / total,
    WARNING: (statusDistribution.WARNING || 0) / total,
    CRITICAL: (statusDistribution.CRITICAL || 0) / total
  };

  const dominant = Object.entries(percentages).reduce((a, b) => a[1] > b[1] ? a : b)[0];
  return SPEED_STATUS_COLORS[dominant];
};

/**
 * Get CV tuning recommendation text for speed bucket
 * @param {number} meanDeltaT - Mean delta-t for speed bucket
 * @param {Object} thresholds - Delta-t thresholds from config
 * @returns {string} Recommendation text or null if no action needed
 */
export const getSpeedTuningRecommendation = (meanDeltaT, thresholds) => {
  if (!thresholds) return null;

  const absValue = Math.abs(meanDeltaT);

  // No action needed if within action threshold
  if (absValue < thresholds.critical_threshold) {
    return null;
  }

  // Determine which loco is faster
  if (meanDeltaT > 0) {
    return `Rear loco faster (+${meanDeltaT.toFixed(2)}s). Consider decreasing CV speed table for rear loco at this speed.`;
  } else {
    return `Lead loco faster (${meanDeltaT.toFixed(2)}s). Consider increasing CV speed table for rear loco at this speed.`;
  }
};
