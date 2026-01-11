import { useEffect, useState } from 'react';

export default function WebSocketStatsPopover({ isOpen, onClose, stats, isConnected, isHover = false }) {
  const [uptime, setUptime] = useState('0s');
  const [lastActivity, setLastActivity] = useState('--');

  // Update uptime and last activity every second
  useEffect(() => {
    if (!isOpen || !stats) return;

    const updateTimes = () => {
      // Calculate uptime
      if (stats.connectedSince) {
        const uptimeMs = Date.now() - stats.connectedSince;
        const hours = Math.floor(uptimeMs / 3600000);
        const minutes = Math.floor((uptimeMs % 3600000) / 60000);
        const seconds = Math.floor((uptimeMs % 60000) / 1000);

        if (hours > 0) {
          setUptime(`${hours}h ${minutes}m`);
        } else if (minutes > 0) {
          setUptime(`${minutes}m ${seconds}s`);
        } else {
          setUptime(`${seconds}s`);
        }
      } else {
        setUptime('--');
      }

      // Calculate last activity
      if (stats.lastMessageTime) {
        const lastActivityMs = Date.now() - stats.lastMessageTime;
        const seconds = Math.floor(lastActivityMs / 1000);

        if (seconds < 60) {
          setLastActivity(`${seconds}s ago`);
        } else {
          const minutes = Math.floor(seconds / 60);
          setLastActivity(`${minutes}m ago`);
        }
      } else {
        setLastActivity('--');
      }
    };

    updateTimes();
    const interval = setInterval(updateTimes, 1000); // Update every second

    return () => clearInterval(interval);
  }, [isOpen, stats]);

  if (!isOpen) return null;

  // Connection quality based on reconnect count
  const getConnectionQuality = () => {
    if (!isConnected) return { label: 'Disconnected', color: 'text-signal-red' };
    if (stats.reconnectCount === 0) return { label: 'Excellent ✓', color: 'text-signal-green' };
    if (stats.reconnectCount < 3) return { label: 'Good', color: 'text-signal-green' };
    if (stats.reconnectCount < 10) return { label: 'Fair', color: 'text-amber-500' };
    return { label: 'Poor', color: 'text-signal-red' };
  };

  const quality = getConnectionQuality();

  return (
    <>
      {/* Backdrop (only on mobile click, not on desktop hover) */}
      {!isHover && (
        <div
          className="fixed inset-0 bg-black/40 z-[90] md:hidden"
          onClick={onClose}
        />
      )}

      {/* Popover */}
      <div className={`fixed top-20 right-4 w-80 bg-control-dark border-2 border-control-grey rounded-lg shadow-2xl z-[100] ${
        isHover ? '' : 'animate-slide-in'
      }`}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-control-grey">
          <div className="flex items-center gap-2">
            <i className={`fa-solid fa-wifi text-xl ${isConnected ? 'text-signal-green' : 'text-signal-red'}`}></i>
            <h3 className="font-display font-semibold text-signal-amber">WebSocket Statistics</h3>
          </div>
          <button
            onClick={onClose}
            className="text-track-steel hover:text-signal-amber transition-colors"
          >
            <i className="fa-solid fa-times text-xl"></i>
          </button>
        </div>

        {/* Content */}
        <div className="p-4">
          <div className="space-y-3">
            {/* Connection Status */}
            <div className="flex items-center justify-between pb-3 border-b border-control-grey">
              <span className="text-sm text-track-steel">Status:</span>
              <span className={`text-sm font-semibold ${isConnected ? 'text-signal-green' : 'text-signal-red'}`}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>

            {/* Uptime */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-track-steel">Connected:</span>
              <span className="font-mono text-sm font-semibold text-track-steel">
                {uptime}
              </span>
            </div>

            {/* Last Activity */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-track-steel">Last msg:</span>
              <span className="font-mono text-sm font-semibold text-track-steel">
                {lastActivity}
              </span>
            </div>

            {/* Messages Sent/Received */}
            <div className="flex items-center justify-between pt-2 border-t border-control-grey">
              <span className="text-sm text-track-steel">Messages:</span>
              <span className="font-mono text-sm font-semibold text-track-steel">
                {stats.messagesReceived.toLocaleString()} ↓ / {stats.messagesSent.toLocaleString()} ↑
              </span>
            </div>

            {/* Reconnect Count */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-track-steel">Reconnects:</span>
              <span className={`font-mono text-sm font-semibold ${
                stats.reconnectCount === 0 ? 'text-signal-green' :
                stats.reconnectCount < 10 ? 'text-amber-500' :
                'text-signal-red'
              }`}>
                {stats.reconnectCount}
              </span>
            </div>

            {/* Connection Quality */}
            <div className="flex items-center justify-between pt-2 border-t border-control-grey">
              <span className="text-sm text-track-steel">Quality:</span>
              <span className={`text-sm font-semibold ${quality.color}`}>
                {quality.label}
              </span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
