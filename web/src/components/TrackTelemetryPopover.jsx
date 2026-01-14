import { useEffect, useState } from 'react';

export default function TrackTelemetryPopover({ isOpen, onClose, apiUrl, isHover = false }) {
  const [telemetry, setTelemetry] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isOpen) return;

    const fetchTelemetry = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/z21/telemetry`);
        const data = await response.json();
        if (data.status === 'success') {
          setTelemetry(data);
        }
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch telemetry:', error);
        setLoading(false);
      }
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 2000); // Update every 2s

    return () => clearInterval(interval);
  }, [isOpen, apiUrl]);

  if (!isOpen) return null;

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
      <div className={`fixed top-20 right-4 md:right-40 w-80 bg-control-dark border-2 border-control-grey rounded-lg shadow-2xl z-[100] ${
        isHover ? '' : 'animate-slide-in'
      }`}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-control-grey">
          <div className="flex items-center gap-2">
            <i className="fa-solid fa-bolt text-signal-green text-xl"></i>
            <h3 className="font-display font-semibold text-signal-amber">Track Telemetry</h3>
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
          {loading ? (
            <div className="text-center py-4 text-track-steel">
              <i className="fa-solid fa-spinner fa-spin mr-2"></i>
              Loading...
            </div>
          ) : telemetry ? (
            <>
              {/* Warnings */}
              {telemetry.warnings && telemetry.warnings.length > 0 && (
                <div className="mb-4 p-3 bg-amber-500/20 border border-amber-500/50 rounded">
                  {telemetry.warnings.map((warning, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      <i className="fa-solid fa-triangle-exclamation text-amber-500 mt-0.5"></i>
                      <span className="text-amber-100">{warning}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Telemetry Data */}
              <div className="space-y-3">
                {/* Main Current */}
                <div className="flex items-center justify-between">
                  <span className="text-sm text-track-steel">Main Current:</span>
                  <span className={`font-mono text-sm font-semibold ${
                    telemetry.telemetry.main_current_ma > 2000 ? 'text-signal-red' :
                    telemetry.telemetry.main_current_ma > 500 ? 'text-signal-green' :
                    'text-track-steel'
                  }`}>
                    {telemetry.telemetry.main_current_ma} mA
                  </span>
                </div>

                {/* Supply Voltage */}
                <div className="flex items-center justify-between">
                  <span className="text-sm text-track-steel">Supply Voltage:</span>
                  <span className={`font-mono text-sm font-semibold ${
                    telemetry.quality_checks.voltage_ok ? 'text-signal-green' : 'text-amber-500'
                  }`}>
                    {telemetry.telemetry.supply_voltage_v.toFixed(2)} V
                  </span>
                </div>

                {/* Filtered Current */}
                <div className="flex items-center justify-between">
                  <span className="text-sm text-track-steel">Filtered Current:</span>
                  <span className="font-mono text-sm font-semibold text-track-steel">
                    {telemetry.telemetry.filtered_current_ma} mA
                  </span>
                </div>

                {/* Track Power State */}
                <div className="flex items-center justify-between pt-2 border-t border-control-grey">
                  <span className="text-sm text-track-steel">Track Power:</span>
                  <span className={`text-sm font-semibold ${
                    telemetry.track_power_on ? 'text-signal-green' : 'text-signal-red'
                  }`}>
                    {telemetry.track_power_on ? 'ON' : 'OFF'}
                  </span>
                </div>

                {/* Emergency Stop */}
                {telemetry.emergency_stop && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-track-steel">Emergency Stop:</span>
                    <span className="text-sm font-semibold text-signal-red">ACTIVE</span>
                  </div>
                )}

                {/* Short Circuit */}
                {telemetry.short_circuit && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-track-steel">Short Circuit:</span>
                    <span className="text-sm font-semibold text-signal-red">DETECTED</span>
                  </div>
                )}
              </div>

              {/* Last Update */}
              <div className="mt-4 pt-3 border-t border-control-grey text-xs text-track-steel text-center">
                Last update: {new Date(telemetry.timestamp * 1000).toLocaleTimeString()}
              </div>
            </>
          ) : (
            <div className="text-center py-4 text-signal-red">
              <i className="fa-solid fa-exclamation-triangle mr-2"></i>
              Failed to load telemetry
            </div>
          )}
        </div>
      </div>
    </>
  );
}
