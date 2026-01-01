import { useState } from 'react';

export default function VideoFeedPanel({ apiUrl, consists }) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Get Δt data for Consist 11 (priority) or Consist 10
  const getDeltaTData = () => {
    // Prioritize Consist 11, fallback to 10
    const consist = consists[11] || consists[10];
    if (!consist) return null;

    const deltaT = consist.delta_t;
    const timestamp = consist.delta_t_timestamp;
    const thresholds = consist.timing_thresholds || { normal: 1.0, warning: 2.0 };
    const consistAddress = consist.address || (consists[11] ? 11 : 10);

    return { deltaT, timestamp, thresholds, consistAddress };
  };

  // Calculate status and color based on thresholds
  const getStatusInfo = (deltaT, thresholds) => {
    if (deltaT === null || deltaT === undefined) {
      return { status: 'Waiting...', color: 'text-track-steel' };
    }

    const absDeltaT = Math.abs(deltaT);
    if (absDeltaT < thresholds.normal) {
      return { status: 'SYNCED', color: 'text-signal-green' };
    } else if (absDeltaT < thresholds.warning) {
      return { status: 'WARNING', color: 'text-yellow-400' };
    } else {
      return { status: 'CRITICAL', color: 'text-signal-red' };
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '--:--:--';
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const deltaTData = getDeltaTData();
  const statusInfo = deltaTData ? getStatusInfo(deltaTData.deltaT, deltaTData.thresholds) : { status: 'No data', color: 'text-track-steel' };

  return (
    <div className="w-full mb-6">
      {/* Collapsible Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 bg-control-dark rounded-lg hover:bg-control-grey transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">{isExpanded ? '▼' : '▶'}</span>
          <span className="text-lg font-display font-semibold text-signal-amber">
            🎥 Video Feed
          </span>
        </div>
        <span className="text-sm text-track-steel font-sans">
          YOLO Tracking<span className="hidden md:inline"> + Gate Timing</span>
        </span>
      </button>

      {/* Video Content (only rendered when expanded) */}
      {isExpanded && (
        <div className="mt-3 rounded-lg overflow-hidden bg-control-black border-2 border-control-grey relative">
          <img
            src={`${apiUrl}/api/video_feed`}
            alt="Live YOLO tracking feed"
            className="w-full h-auto"
            style={{ maxHeight: '70vh', objectFit: 'contain' }}
          />

          {/* HTML Overlay Panel - Bottom Left (replaces OpenCV panel) */}
          {deltaTData && (
            <div
              className="absolute bottom-3 left-3 p-3 rounded"
              style={{
                backgroundColor: 'rgba(0, 0, 0, 0.6)',
                minWidth: '250px'
              }}
            >
              {/* Consist Address */}
              <div className="text-white font-sans font-semibold mb-2">
                Consist {deltaTData.consistAddress}
              </div>

              {/* Delta t */}
              <div className="text-white font-sans text-sm mb-1">
                Delta t: {deltaTData.deltaT !== null && deltaTData.deltaT !== undefined
                  ? `${deltaTData.deltaT >= 0 ? '+' : ''}${deltaTData.deltaT.toFixed(3)}s`
                  : 'Waiting...'
                }
              </div>

              {/* Status (color-coded) */}
              <div className={`font-sans text-sm mb-2 ${statusInfo.color} font-semibold`}>
                Status: {statusInfo.status}
              </div>

              {/* Timestamp */}
              <div className="text-gray-400 font-sans text-xs">
                Updated: {formatTimestamp(deltaTData.timestamp)}
              </div>
            </div>
          )}

          <div className="p-3 bg-control-dark text-center">
            <p className="text-xs text-track-steel font-sans">
              Live stream from Tapo camera • Gate markers + Locomotive positions + Δt stats
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
