import { useState, useEffect } from 'react';

/**
 * Settings Modal Component (Phase 3)
 *
 * Modal with 7 tabs for editing config.json:
 * - System (debug mode)
 * - Z21 Network (IP, port, test connection)
 * - Camera (IP, port, stream, resolution, credentials, test stream)
 * - Video Feed (FPS - hot reload)
 * - YOLO Model (confidence, IoU, OBB, preset load buttons)
 * - Tracking (FPS active/idle, idle timeout, timing thresholds)
 * - Locomotives (function labels inline edit)
 */
export default function SettingsModal({ isOpen, onClose, apiUrl }) {
  const [activeTab, setActiveTab] = useState('system');
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Tab definitions (order: System first, then by logical grouping)
  const tabs = [
    { id: 'system', label: 'System', icon: 'fa-sliders' },
    { id: 'z21', label: 'Z21 Network', icon: 'fa-network-wired' },
    { id: 'camera', label: 'Camera', icon: 'fa-camera' },
    { id: 'video', label: 'Video Feed', icon: 'fa-video' },
    { id: 'yolo', label: 'YOLO Model', icon: 'fa-brain' },
    { id: 'tracking', label: 'Tracking', icon: 'fa-crosshairs' },
    { id: 'analytics', label: 'Analytics', icon: 'fa-chart-line' },
    { id: 'locomotives', label: 'Locomotives', icon: 'fa-train' }
  ];

  // Load settings from backend on mount
  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'auto';
    }

    // Cleanup on unmount
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [isOpen]);

  const loadSettings = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/api/config`);
      if (!response.ok) {
        throw new Error('Failed to load settings');
      }

      const data = await response.json();
      setSettings(data);
    } catch (err) {
      console.error('Settings load error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/api/settings/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });

      if (!response.ok) {
        throw new Error('Failed to save settings');
      }

      const result = await response.json();

      // Show success message
      alert(`Settings saved successfully!\n\nRestart required for: ${result.restart_needed.join(', ')}`);

      onClose();
    } catch (err) {
      console.error('Settings save error:', err);
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Slider thumb size override */}
      <style>{`
        input[type="range"]::-webkit-slider-thumb {
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: currentColor;
          cursor: pointer;
          -webkit-appearance: none;
          appearance: none;
        }
        input[type="range"]::-moz-range-thumb {
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: currentColor;
          cursor: pointer;
          border: none;
        }
      `}</style>

      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-6xl max-h-[90vh] bg-slate-800 border border-slate-700 rounded-lg shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <i className="fa-solid fa-gears text-2xl text-signal-amber"></i>
            <h2 className="text-2xl font-display font-bold text-white">Settings</h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <i className="fa-solid fa-times text-2xl"></i>
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-700 bg-slate-900/50 overflow-x-auto">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-6 py-4 text-sm font-medium transition-all duration-200 whitespace-nowrap ${
                activeTab === tab.id
                  ? 'text-signal-amber border-b-2 border-signal-amber bg-slate-800/50'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/30'
              }`}
            >
              <i className={`fa-solid ${tab.icon}`}></i>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-slate-400">
                <i className="fa-solid fa-spinner fa-spin text-4xl mb-4"></i>
                <p>Loading settings...</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-red-400 text-center">
                <i className="fa-solid fa-exclamation-triangle text-4xl mb-4"></i>
                <p className="text-lg font-semibold mb-2">Error loading settings</p>
                <p className="text-sm">{error}</p>
                <button
                  onClick={loadSettings}
                  className="mt-4 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded transition-colors"
                >
                  Retry
                </button>
              </div>
            </div>
          ) : (
            <>
              {activeTab === 'system' && <SystemTab settings={settings} setSettings={setSettings} />}
              {activeTab === 'z21' && <Z21NetworkTab settings={settings} setSettings={setSettings} apiUrl={apiUrl} />}
              {activeTab === 'camera' && <CameraTab settings={settings} setSettings={setSettings} apiUrl={apiUrl} />}
              {activeTab === 'video' && <VideoFeedTab settings={settings} setSettings={setSettings} />}
              {activeTab === 'yolo' && <YoloModelTab settings={settings} setSettings={setSettings} apiUrl={apiUrl} />}
              {activeTab === 'tracking' && <TrackingTab settings={settings} setSettings={setSettings} />}
              {activeTab === 'analytics' && <AnalyticsTab settings={settings} setSettings={setSettings} />}
              {activeTab === 'locomotives' && <LocomotivesTab settings={settings} setSettings={setSettings} />}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-slate-700 bg-slate-900/50">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || loading}
            className="px-6 py-2 bg-signal-amber hover:bg-amber-500 text-black font-semibold rounded transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {saving ? (
              <>
                <i className="fa-solid fa-spinner fa-spin"></i>
                Saving...
              </>
            ) : (
              <>
                <i className="fa-solid fa-save"></i>
                Save Changes
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// Tab Components (placeholders - will implement content next)

function Z21NetworkTab({ settings, setSettings, apiUrl }) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  if (!settings?.z21) return null;

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);

    try {
      const response = await fetch(`${apiUrl}/api/settings/z21/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: settings.z21.host,
          port: settings.z21.port
        })
      });

      const result = await response.json();
      setTestResult(result);
    } catch (error) {
      setTestResult({ status: 'error', message: error.message });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white mb-4">Z21 Network Configuration</h3>

      {/* Host IP */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Host IP Address
        </label>
        <input
          type="text"
          value={settings.z21.host || ''}
          onChange={(e) => setSettings({ ...settings, z21: { ...settings.z21, host: e.target.value } })}
          className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded text-white focus:border-signal-amber focus:ring-1 focus:ring-signal-amber outline-none"
          placeholder="192.168.1.111"
        />
        <p className="mt-1 text-xs text-slate-400">
          IP address of your Z21 command station
        </p>
      </div>

      {/* UDP Port */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          UDP Port
        </label>
        <input
          type="number"
          value={settings.z21.port || 21105}
          onChange={(e) => setSettings({ ...settings, z21: { ...settings.z21, port: parseInt(e.target.value) } })}
          className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded text-white focus:border-signal-amber focus:ring-1 focus:ring-signal-amber outline-none"
          placeholder="21105"
          min="1"
          max="65535"
        />
        <p className="mt-1 text-xs text-slate-400">
          UDP port for Z21 LAN protocol (default: 21105)
        </p>
      </div>

      {/* Test Connection Button */}
      <div>
        <button
          onClick={handleTestConnection}
          disabled={testing}
          className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors disabled:opacity-50 flex items-center gap-2"
        >
          {testing ? (
            <>
              <i className="fa-solid fa-spinner fa-spin"></i>
              Testing...
            </>
          ) : (
            <>
              <i className="fa-solid fa-plug"></i>
              Test Connection
            </>
          )}
        </button>

        {/* Test Result */}
        {testResult && (
          <div className={`mt-3 p-3 rounded border ${
            testResult.status === 'success'
              ? 'bg-green-500/10 border-green-500/30 text-green-200'
              : 'bg-red-500/10 border-red-500/30 text-red-200'
          }`}>
            <p className="text-sm flex items-start gap-2">
              <i className={`fa-solid ${testResult.status === 'success' ? 'fa-check-circle' : 'fa-times-circle'} mt-0.5`}></i>
              <span>{testResult.message}</span>
            </p>
            {testResult.details && (
              <div className="mt-2 text-xs opacity-80">
                Track Power: {testResult.details.track_power ? 'ON' : 'OFF'} |
                Emergency Stop: {testResult.details.emergency_stop ? 'ACTIVE' : 'INACTIVE'}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded">
        <p className="text-sm text-amber-200 flex items-start gap-2">
          <i className="fa-solid fa-exclamation-triangle mt-0.5"></i>
          <span>Changing Z21 network settings requires backend restart</span>
        </p>
      </div>
    </div>
  );
}

function CameraTab({ settings, setSettings, apiUrl }) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  if (!settings?.camera) return null;

  const handleTestStream = async () => {
    setTesting(true);
    setTestResult(null);

    try {
      const response = await fetch(`${apiUrl}/api/settings/camera/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings.camera)
      });

      const result = await response.json();
      setTestResult(result);
    } catch (error) {
      setTestResult({ status: 'error', message: error.message });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white mb-4">Camera Configuration</h3>

      {/* Camera IP */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Camera IP Address
        </label>
        <input
          type="text"
          value={settings.camera.ip || ''}
          onChange={(e) => setSettings({ ...settings, camera: { ...settings.camera, ip: e.target.value } })}
          className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded text-white focus:border-signal-amber focus:ring-1 focus:ring-signal-amber outline-none"
          placeholder="192.168.1.4"
        />
      </div>

      {/* Camera Port */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          RTSP Port
        </label>
        <input
          type="number"
          value={settings.camera.port || 554}
          onChange={(e) => setSettings({ ...settings, camera: { ...settings.camera, port: parseInt(e.target.value) } })}
          className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded text-white focus:border-signal-amber focus:ring-1 focus:ring-signal-amber outline-none"
          placeholder="554"
          min="1"
          max="65535"
        />
      </div>

      {/* Stream Name */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Stream Name
        </label>
        <input
          type="text"
          value={settings.camera.stream || ''}
          onChange={(e) => setSettings({ ...settings, camera: { ...settings.camera, stream: e.target.value } })}
          className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded text-white focus:border-signal-amber focus:ring-1 focus:ring-signal-amber outline-none"
          placeholder="stream2"
        />
        <p className="mt-1 text-xs text-slate-400">
          RTSP stream path (e.g., stream1 for 1080p, stream2 for 720p)
        </p>
      </div>

      {/* Credentials */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Username
          </label>
          <input
            type="text"
            value={settings.camera.username || ''}
            onChange={(e) => setSettings({ ...settings, camera: { ...settings.camera, username: e.target.value } })}
            className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded text-white focus:border-signal-amber focus:ring-1 focus:ring-signal-amber outline-none"
            autoComplete="off"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Password
          </label>
          <input
            type="password"
            value={settings.camera.password || ''}
            onChange={(e) => setSettings({ ...settings, camera: { ...settings.camera, password: e.target.value } })}
            className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded text-white focus:border-signal-amber focus:ring-1 focus:ring-signal-amber outline-none"
            autoComplete="off"
          />
        </div>
      </div>

      {/* Test Stream Button */}
      <div>
        <button
          onClick={handleTestStream}
          disabled={testing}
          className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors disabled:opacity-50 flex items-center gap-2"
        >
          {testing ? (
            <>
              <i className="fa-solid fa-spinner fa-spin"></i>
              Testing...
            </>
          ) : (
            <>
              <i className="fa-solid fa-video"></i>
              Test Stream
            </>
          )}
        </button>

        {/* Test Result */}
        {testResult && (
          <div className={`mt-3 p-3 rounded border ${
            testResult.status === 'success'
              ? 'bg-green-500/10 border-green-500/30 text-green-200'
              : 'bg-red-500/10 border-red-500/30 text-red-200'
          }`}>
            <p className="text-sm flex items-start gap-2">
              <i className={`fa-solid ${testResult.status === 'success' ? 'fa-check-circle' : 'fa-times-circle'} mt-0.5`}></i>
              <span>{testResult.message}</span>
            </p>
          </div>
        )}
      </div>

      <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded">
        <p className="text-sm text-blue-200 flex items-start gap-2">
          <i className="fa-solid fa-info-circle mt-0.5"></i>
          <span>Credentials saved to config.local.json (gitignored). Camera settings require video_feed + tracker restart.</span>
        </p>
      </div>
    </div>
  );
}

function VideoFeedTab({ settings, setSettings }) {
  if (!settings?.video) return null;

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white mb-4">Video Feed Configuration</h3>

      {/* FPS Slider */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Video Feed FPS: {settings.video.fps || 30}
        </label>
        <input
          type="range"
          min="1"
          max="60"
          value={settings.video.fps || 30}
          onChange={(e) => setSettings({ ...settings, video: { ...settings.video, fps: parseInt(e.target.value) } })}
          className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-signal-amber"
        />
        <div className="flex justify-between text-xs text-slate-400 mt-1">
          <span>1 FPS</span>
          <span>30 FPS</span>
          <span>60 FPS</span>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          MJPEG video stream frame rate for web browser
        </p>
      </div>

      <div className="p-4 bg-green-500/10 border border-green-500/30 rounded">
        <p className="text-sm text-green-200 flex items-start gap-2">
          <i className="fa-solid fa-check-circle mt-0.5"></i>
          <span>Video FPS is hot reload - no restart required</span>
        </p>
      </div>
    </div>
  );
}

function YoloModelTab({ settings, setSettings, apiUrl }) {
  const [loadingPreset, setLoadingPreset] = useState(false);

  if (!settings?.tracking) return null;

  const handleLoadPreset = async (presetName) => {
    setLoadingPreset(true);

    try {
      const response = await fetch(`${apiUrl}/api/settings/yolo-preset/load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset: presetName })
      });

      const result = await response.json();

      if (result.status === 'success') {
        // Update tracking settings with preset values
        setSettings({
          ...settings,
          tracking: {
            ...settings.tracking,
            yolo_confidence: result.preset.yolo_confidence,
            yolo_iou: result.preset.yolo_iou,
            yolo_obb: result.preset.yolo_obb
          }
        });
      } else {
        alert(`Failed to load preset: ${result.message}`);
      }
    } catch (error) {
      alert(`Error loading preset: ${error.message}`);
    } finally {
      setLoadingPreset(false);
    }
  };

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white mb-4">YOLO Model Configuration</h3>

      {/* Preset Load Buttons */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Quick Load Presets
        </label>
        <div className="flex gap-2">
          <button
            onClick={() => handleLoadPreset('tracking_OBB')}
            disabled={loadingPreset}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            <i className="fa-solid fa-bolt"></i>
            Load OBB Profile
          </button>
          <button
            onClick={() => handleLoadPreset('tracking_standard')}
            disabled={loadingPreset}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            <i className="fa-solid fa-square"></i>
            Load Standard Profile
          </button>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          Load optimized settings for OBB or Standard YOLO models
        </p>
      </div>

      {/* Confidence Threshold */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Confidence Threshold: {settings.tracking.yolo_confidence || 0.3}
        </label>
        <input
          type="range"
          min="0.1"
          max="0.9"
          step="0.05"
          value={settings.tracking.yolo_confidence || 0.3}
          onChange={(e) => setSettings({
            ...settings,
            tracking: { ...settings.tracking, yolo_confidence: parseFloat(e.target.value) }
          })}
          className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-signal-amber"
        />
        <div className="flex justify-between text-xs text-slate-400 mt-1">
          <span>0.1 (Low)</span>
          <span>0.5 (Medium)</span>
          <span>0.9 (High)</span>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          Minimum confidence score for detection (higher = fewer false positives)
        </p>
      </div>

      {/* IoU Threshold */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          IoU Threshold: {settings.tracking.yolo_iou || 0.6}
        </label>
        <input
          type="range"
          min="0.3"
          max="0.95"
          step="0.05"
          value={settings.tracking.yolo_iou || 0.6}
          onChange={(e) => setSettings({
            ...settings,
            tracking: { ...settings.tracking, yolo_iou: parseFloat(e.target.value) }
          })}
          className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-signal-amber"
        />
        <div className="flex justify-between text-xs text-slate-400 mt-1">
          <span>0.3 (Low)</span>
          <span>0.6 (Medium)</span>
          <span>0.95 (High)</span>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          Non-Maximum Suppression threshold (higher = less bbox merging)
        </p>
      </div>

      {/* OBB Model Toggle */}
      <div>
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.tracking.yolo_obb || false}
            onChange={(e) => setSettings({
              ...settings,
              tracking: { ...settings.tracking, yolo_obb: e.target.checked }
            })}
            className="w-5 h-5 rounded border-slate-700 bg-slate-900 text-signal-amber focus:ring-signal-amber focus:ring-offset-slate-800"
          />
          <div>
            <div className="text-sm font-medium text-white">Use OBB Model (Rotated Bounding Boxes)</div>
            <div className="text-xs text-slate-400">
              Enable oriented bounding boxes for better overlap handling
            </div>
          </div>
        </label>
      </div>

      <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded">
        <p className="text-sm text-amber-200 flex items-start gap-2">
          <i className="fa-solid fa-exclamation-triangle mt-0.5"></i>
          <span>Changing YOLO model settings requires tracker restart</span>
        </p>
      </div>
    </div>
  );
}

function TrackingTab({ settings, setSettings }) {
  if (!settings?.tracking) return null;

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white mb-4">Tracking Configuration</h3>

      {/* FPS Settings */}
      <div className="space-y-4">
        <h4 className="text-md font-medium text-white">Frame Rate Settings</h4>

        {/* Active FPS */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Active FPS: {settings.tracking.fps?.active || 30}
          </label>
          <input
            type="range"
            min="10"
            max="60"
            value={settings.tracking.fps?.active || 30}
            onChange={(e) => setSettings({
              ...settings,
              tracking: {
                ...settings.tracking,
                fps: { ...settings.tracking.fps, active: parseInt(e.target.value) }
              }
            })}
            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-signal-amber"
          />
          <p className="mt-1 text-xs text-slate-400">
            YOLO processing FPS when locomotive detected
          </p>
        </div>

        {/* Idle FPS */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Idle FPS: {settings.tracking.fps?.idle || 1}
          </label>
          <input
            type="range"
            min="1"
            max="10"
            value={settings.tracking.fps?.idle || 1}
            onChange={(e) => setSettings({
              ...settings,
              tracking: {
                ...settings.tracking,
                fps: { ...settings.tracking.fps, idle: parseInt(e.target.value) }
              }
            })}
            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-signal-amber"
          />
          <p className="mt-1 text-xs text-slate-400">
            YOLO processing FPS when no locomotives detected
          </p>
        </div>

        {/* Idle Timeout */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Idle Timeout: {settings.tracking.idle_timeout_seconds || 10}s
          </label>
          <input
            type="number"
            value={settings.tracking.idle_timeout_seconds || 10}
            onChange={(e) => setSettings({
              ...settings,
              tracking: { ...settings.tracking, idle_timeout_seconds: parseInt(e.target.value) }
            })}
            className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded text-white focus:border-signal-amber focus:ring-1 focus:ring-signal-amber outline-none"
            min="1"
            max="60"
          />
          <p className="mt-1 text-xs text-slate-400">
            Seconds of no detection before switching to idle FPS
          </p>
        </div>
      </div>

      {/* Timing Thresholds */}
      <div className="space-y-4">
        <h4 className="text-md font-medium text-white">Timing Thresholds</h4>

        {/* Normal Threshold */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Warning Threshold: {settings.tracking.timing_thresholds?.warning || 1.0}s
          </label>
          <input
            type="number"
            step="0.1"
            value={settings.tracking.timing_thresholds?.warning || 1.0}
            onChange={(e) => setSettings({
              ...settings,
              tracking: {
                ...settings.tracking,
                timing_thresholds: { ...settings.tracking.timing_thresholds, warning: parseFloat(e.target.value) }
              }
            })}
            className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded text-white focus:border-signal-amber focus:ring-1 focus:ring-signal-amber outline-none"
            min="0.1"
            max="5.0"
          />
          <p className="mt-1 text-xs text-slate-400">
            Threshold for <span className="text-amber-400 font-semibold">WARNING</span> status (|Δt| &gt;= this value triggers <span className="text-amber-400 font-semibold">WARNING</span>)
          </p>
        </div>

        {/* Critical Threshold */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Critical Threshold: {settings.tracking.timing_thresholds?.critical || 1.5}s
          </label>
          <input
            type="number"
            step="0.1"
            value={settings.tracking.timing_thresholds?.critical || 1.5}
            onChange={(e) => setSettings({
              ...settings,
              tracking: {
                ...settings.tracking,
                timing_thresholds: { ...settings.tracking.timing_thresholds, critical: parseFloat(e.target.value) }
              }
            })}
            className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded text-white focus:border-signal-amber focus:ring-1 focus:ring-signal-amber outline-none"
            min="0.1"
            max="5.0"
          />
          <p className="mt-1 text-xs text-slate-400">
            Threshold for <span className="text-red-400 font-semibold">CRITICAL</span> status (|Δt| &gt;= this value triggers <span className="text-red-400 font-semibold">CRITICAL</span>)
          </p>
        </div>

        {/* Max Delta T */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Max Delta T: {settings.tracking.timing_thresholds?.max_delta_t || 10.0}s
          </label>
          <input
            type="number"
            step="0.5"
            value={settings.tracking.timing_thresholds?.max_delta_t || 10.0}
            onChange={(e) => setSettings({
              ...settings,
              tracking: {
                ...settings.tracking,
                timing_thresholds: { ...settings.tracking.timing_thresholds, max_delta_t: parseFloat(e.target.value) }
              }
            })}
            className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded text-white focus:border-signal-amber focus:ring-1 focus:ring-signal-amber outline-none"
            min="1.0"
            max="30.0"
          />
          <p className="mt-1 text-xs text-slate-400">
            Maximum |Δt| threshold for filtering outliers
          </p>
        </div>
      </div>

      <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded">
        <p className="text-sm text-amber-200 flex items-start gap-2">
          <i className="fa-solid fa-exclamation-triangle mt-0.5"></i>
          <span>Changing tracking settings requires tracker restart</span>
        </p>
      </div>
    </div>
  );
}

function LocomotivesTab({ settings, setSettings }) {
  if (!settings?.locomotives) return null;

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white mb-4">Locomotives Configuration</h3>

      <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded">
        <p className="text-sm text-blue-200 flex items-start gap-2">
          <i className="fa-solid fa-info-circle mt-0.5"></i>
          <span>Function label editing coming soon. For now, edit locomotive details (name, decoder, color, functions) directly in config.json.</span>
        </p>
      </div>

      {/* Show locomotive list read-only */}
      <div className="space-y-2">
        {Object.entries(settings.locomotives).map(([address, loco]) => (
          <div key={address} className="p-3 bg-slate-900 border border-slate-700 rounded">
            <div className="flex items-center gap-3">
              <div
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: loco.color || '#808080' }}
              ></div>
              <div className="flex-1">
                <div className="text-sm font-medium text-white">
                  Address {address}: {loco.name}
                </div>
                <div className="text-xs text-slate-400">
                  {loco.decoder || 'Unknown decoder'} • {loco.functions?.length || 0} functions
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SystemTab({ settings, setSettings }) {
  if (!settings?.debug) return null;

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white mb-4">System Configuration</h3>

      {/* Debug Mode Toggle */}
      <div>
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.debug.enabled || false}
            onChange={(e) => setSettings({
              ...settings,
              debug: { ...settings.debug, enabled: e.target.checked }
            })}
            className="w-5 h-5 rounded border-slate-700 bg-slate-900 text-signal-amber focus:ring-signal-amber focus:ring-offset-slate-800"
          />
          <div>
            <div className="text-sm font-medium text-white">Debug Mode</div>
            <div className="text-xs text-slate-400">
              Enable verbose logging (frame processing, YOLO detection details)
            </div>
          </div>
        </label>
      </div>

      <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded">
        <p className="text-sm text-amber-200 flex items-start gap-2">
          <i className="fa-solid fa-exclamation-triangle mt-0.5"></i>
          <span>Changing debug mode requires backend restart</span>
        </p>
      </div>
    </div>
  );
}

function AnalyticsTab({ settings, setSettings }) {
  if (!settings?.analytics) return null;

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white mb-4">Analytics Configuration</h3>

      {/* Max Chart Events */}
      <div>
        <label className="block">
          <span className="text-sm font-medium text-white">Max Chart Events</span>
          <div className="text-xs text-slate-400 mb-2">
            Chart optimization threshold: Current shows last N events, Overview downsamples if &gt; N total events
          </div>
          <input
            type="number"
            min="100"
            max="2000"
            step="50"
            value={settings.analytics.max_chart_events || 500}
            onChange={(e) => setSettings({
              ...settings,
              analytics: { ...settings.analytics, max_chart_events: parseInt(e.target.value) || 500 }
            })}
            className="w-32 px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
          <span className="ml-2 text-sm text-slate-400">events</span>
        </label>
      </div>

      <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded">
        <p className="text-sm text-blue-200 flex items-start gap-2">
          <i className="fa-solid fa-info-circle mt-0.5"></i>
          <span>Lower values = better performance but less visible history. Higher values = more data but slower rendering. Recommended: 300-1000.</span>
        </p>
      </div>
    </div>
  );
}
