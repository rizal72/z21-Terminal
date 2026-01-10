import { useState, useEffect, useRef } from 'react';
import GateEditor from './GateEditor';

export default function VideoFeedPanel({ apiUrl, editMode, onEditModeChange, debugMode, onDebugModeChange }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [videoDimensions, setVideoDimensions] = useState({ width: 0, height: 0 });
  const containerRef = useRef(null);
  const imgRef = useRef(null);

  // Detect mobile on mount and resize
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Update video dimensions when image loads or resizes
  const updateVideoDimensions = () => {
    if (imgRef.current) {
      // Native video aspect ratio (1280x720 = 16:9)
      const nativeRatio = 1280 / 720;

      // Container dimensions
      const containerWidth = imgRef.current.offsetWidth;
      const containerHeight = imgRef.current.offsetHeight;
      const containerRatio = containerWidth / containerHeight;

      // Calculate actual rendered video dimensions (objectFit: contain logic)
      let videoWidth, videoHeight;
      if (containerRatio > nativeRatio) {
        // Container is wider - video is constrained by height
        videoHeight = containerHeight;
        videoWidth = videoHeight * nativeRatio;
      } else {
        // Container is taller - video is constrained by width
        videoWidth = containerWidth;
        videoHeight = videoWidth / nativeRatio;
      }

      console.log(`📐 Container: ${containerWidth}x${containerHeight} (ratio ${containerRatio.toFixed(2)})`);
      console.log(`📐 Video rendered: ${videoWidth}x${videoHeight} (ratio ${nativeRatio.toFixed(2)})`);

      setVideoDimensions({
        width: Math.round(videoWidth),
        height: Math.round(videoHeight)
      });
    }
  };

  useEffect(() => {
    updateVideoDimensions();
    window.addEventListener('resize', updateVideoDimensions);
    return () => window.removeEventListener('resize', updateVideoDimensions);
  }, [isExpanded]);

  // Sync debug mode with backend when panel is expanded (after reload)
  useEffect(() => {
    if (isExpanded) {
      console.log('[VideoFeedPanel] Panel expanded, fetching debug status...');
      fetch(`${apiUrl}/api/debug-status`)
        .then(res => res.json())
        .then(data => {
          console.log('[VideoFeedPanel] Debug status received:', data.debug_visible);
          if (data.debug_visible !== undefined) {
            console.log('[VideoFeedPanel] Setting debugMode to:', data.debug_visible);
            onDebugModeChange(data.debug_visible);
          }
        })
        .catch(err => console.error('[VideoFeedPanel] Failed to fetch debug status:', err));
    }
  }, [isExpanded, apiUrl, onDebugModeChange]);

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
        <div className="mt-3 rounded-lg overflow-hidden bg-control-black border-2 border-control-grey">
          {/* Toolbar */}
          <div className="flex items-center justify-between p-2 bg-control-dark border-b border-control-grey">
            <div className="flex gap-2">
              <button
                onClick={() => {
                  fetch(`${apiUrl}/api/toggle-panel`, { method: 'POST' })
                    .then(res => res.json())
                    .then(data => console.log(`🎛️  Panel toggled: ${data.panel_visible ? 'visible' : 'hidden'}`))
                    .catch(err => console.error('Failed to toggle panel:', err));
                }}
                className="px-3 py-1 bg-control-grey hover:bg-control-black text-track-steel text-sm rounded transition-colors"
                title="Toggle Δt Panel (P)"
              >
                Δt Panel
              </button>
              <button
                onClick={() => {
                  // Sync with backend and use backend state as source of truth
                  fetch(`${apiUrl}/api/toggle-debug`, { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                      const newMode = data.debug_visible;
                      onDebugModeChange(newMode);
                      console.log(`🔍 Debug mode toggled: ${newMode ? 'enabled' : 'disabled'}`);
                    })
                    .catch(err => console.error('Failed to toggle debug:', err));
                }}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  debugMode
                    ? 'bg-signal-amber text-control-black font-semibold'
                    : 'bg-control-grey hover:bg-control-black text-track-steel'
                }`}
                title="Toggle Debug Overlay (D)"
              >
                Debug
              </button>
              {!isMobile && (
                <button
                  onClick={() => onEditModeChange(!editMode)}
                  className={`px-3 py-1 text-sm rounded transition-colors ${
                    editMode
                      ? 'bg-signal-amber text-control-black font-semibold'
                      : 'bg-control-grey hover:bg-control-black text-track-steel'
                  }`}
                  title="Edit Gates (E)"
                >
                  Edit
                </button>
              )}
            </div>
          </div>

          {/* Video Container (relative for GateEditor overlay) */}
          <div ref={containerRef} className="relative">
            <img
              ref={imgRef}
              src={`${apiUrl}/api/video_feed`}
              alt="Live YOLO tracking feed"
              className="w-full h-auto"
              style={{ maxHeight: '70vh', objectFit: 'contain' }}
              onLoad={updateVideoDimensions}
            />

            {/* Gate Editor Overlay */}
            {editMode && videoDimensions.width > 0 && videoDimensions.height > 0 && (
              <GateEditor
                apiUrl={apiUrl}
                videoWidth={videoDimensions.width}
                videoHeight={videoDimensions.height}
                onClose={() => onEditModeChange(false)}
              />
            )}
          </div>

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
