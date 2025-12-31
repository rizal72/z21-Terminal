import { useState } from 'react';

export default function VideoFeedPanel({ apiUrl }) {
  const [isExpanded, setIsExpanded] = useState(false);

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
          YOLO Tracking + Gate Timing
        </span>
      </button>

      {/* Video Content (only rendered when expanded) */}
      {isExpanded && (
        <div className="mt-3 rounded-lg overflow-hidden bg-control-black border-2 border-control-grey">
          <img
            src={`${apiUrl}/api/video_feed`}
            alt="Live YOLO tracking feed"
            className="w-full h-auto"
            style={{ maxHeight: '70vh', objectFit: 'contain' }}
          />
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
