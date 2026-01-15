/**
 * Analytics Dashboard Constants
 *
 * Centralized constants for Analytics panel charts and UI.
 * Used across multiple chart components for consistent styling.
 */

// Locomotive colors (matches config.json locomotive_colors)
export const LOCO_COLORS = {
  1: '#FFFF00',  // Yellow (Gr675 017)
  5: '#FF8000',  // Orange (D645 014)
  7: '#00FF00',  // Green (E656 239)
  8: '#FF0000',  // Red (E444 056)
};

// Consist colors (dynamic assignment, cyclic if > colors available)
export const CONSIST_COLOR_PALETTE = ['#d946ef', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
export const CONSIST_COLOR_CLASSES = ['text-fuchsia-400', 'text-blue-400', 'text-green-400', 'text-amber-400', 'text-red-400', 'text-purple-400'];
export const CONSIST_BG_CLASSES = ['bg-fuchsia-600', 'bg-blue-600', 'bg-green-600', 'bg-amber-600', 'bg-red-600', 'bg-purple-600'];

// Shared chart styles (dark mode)
export const TOOLTIP_STYLES = {
  contentStyle: { backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' },
  labelStyle: { color: '#e2e8f0' },
  itemStyle: { color: '#e2e8f0' }
};

export const CHART_AXIS_STYLES = {
  grid: { strokeDasharray: '3 3', stroke: '#374151' },
  axis: { stroke: '#9CA3AF' }
};

// Speed Tuning Status Colors (matches delta_t status colors)
export const SPEED_STATUS_COLORS = {
  SYNCED: '#10b981',    // Green
  WARNING: '#f59e0b',   // Amber
  CRITICAL: '#ef4444'   // Red
};
