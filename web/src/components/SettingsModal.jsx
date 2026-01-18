import { useState, useEffect } from 'react';

/**
 * Settings Modal Component (Phase 3)
 *
 * Modal with 5 tabs for editing config.json:
 * - Z21 Network (IP, port)
 * - Video Feed (resolution, fps, RTSP URL)
 * - YOLO Model (confidence, iou, obb, device)
 * - Gates (consist assignment, strategy)
 * - System (debug mode)
 */
export default function SettingsModal({ isOpen, onClose, apiUrl }) {
  const [activeTab, setActiveTab] = useState('z21');
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Tab definitions
  const tabs = [
    { id: 'z21', label: 'Z21 Network', icon: 'fa-network-wired' },
    { id: 'video', label: 'Video Feed', icon: 'fa-video' },
    { id: 'yolo', label: 'YOLO Model', icon: 'fa-brain' },
    { id: 'gates', label: 'Gates', icon: 'fa-diagram-project' },
    { id: 'system', label: 'System', icon: 'fa-sliders' }
  ];

  // Load settings from backend on mount
  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
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
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-slate-800 border border-slate-700 rounded-lg shadow-2xl overflow-hidden flex flex-col">
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
              {activeTab === 'z21' && <Z21NetworkTab settings={settings} setSettings={setSettings} />}
              {activeTab === 'video' && <VideoFeedTab settings={settings} setSettings={setSettings} />}
              {activeTab === 'yolo' && <YoloModelTab settings={settings} setSettings={setSettings} />}
              {activeTab === 'gates' && <GatesTab settings={settings} setSettings={setSettings} />}
              {activeTab === 'system' && <SystemTab settings={settings} setSettings={setSettings} />}
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

function Z21NetworkTab({ settings, setSettings }) {
  if (!settings?.z21) return null;

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white mb-4">Z21 Network Configuration</h3>

      {/* IP Address */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          IP Address
        </label>
        <input
          type="text"
          value={settings.z21.ip}
          onChange={(e) => setSettings({ ...settings, z21: { ...settings.z21, ip: e.target.value } })}
          className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded text-white focus:border-signal-amber focus:ring-1 focus:ring-signal-amber outline-none"
          placeholder="192.168.1.111"
        />
        <p className="mt-1 text-xs text-slate-400">
          IP address of your Z21 command station
        </p>
      </div>

      {/* Port */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          UDP Port
        </label>
        <input
          type="number"
          value={settings.z21.port}
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

      <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded">
        <p className="text-sm text-amber-200 flex items-start gap-2">
          <i className="fa-solid fa-exclamation-triangle mt-0.5"></i>
          <span>Changing Z21 network settings requires backend restart</span>
        </p>
      </div>
    </div>
  );
}

function VideoFeedTab({ settings, setSettings }) {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white mb-4">Video Feed Configuration</h3>
      <p className="text-slate-400">Video feed settings coming soon...</p>
    </div>
  );
}

function YoloModelTab({ settings, setSettings }) {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white mb-4">YOLO Model Configuration</h3>
      <p className="text-slate-400">YOLO model settings coming soon...</p>
    </div>
  );
}

function GatesTab({ settings, setSettings }) {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white mb-4">Gates Configuration</h3>
      <p className="text-slate-400">Gates settings coming soon...</p>
    </div>
  );
}

function SystemTab({ settings, setSettings }) {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white mb-4">System Configuration</h3>
      <p className="text-slate-400">System settings coming soon...</p>
    </div>
  );
}
