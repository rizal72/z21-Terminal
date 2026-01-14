import { useEffect, useState } from 'react';

export default function Z21HealthPopover({ isOpen, onClose, apiUrl, isHover = false }) {
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
      <div className={`fixed top-16 right-12 w-80 bg-control-dark border-2 border-control-grey rounded-lg shadow-2xl z-[100] ${
        isHover ? '' : 'animate-slide-in'
      }`}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-control-grey">
          <div className="flex items-center gap-2">
            <i className="fa-solid fa-server text-signal-green text-xl"></i>
            <h3 className="font-display font-semibold text-signal-amber">Z21 System Health</h3>
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
              {/* Temperature Warnings */}
              {telemetry.quality_checks && (
                <>
                  {telemetry.quality_checks.temperature_high && (
                    <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded">
                      <div className="flex items-start gap-2 text-sm">
                        <i className="fa-solid fa-fire text-red-500 mt-0.5"></i>
                        <span className="text-red-100">Z21 temperature critical - Check ventilation!</span>
                      </div>
                    </div>
                  )}
                  {telemetry.quality_checks.temperature_elevated && !telemetry.quality_checks.temperature_high && (
                    <div className="mb-4 p-3 bg-amber-500/20 border border-amber-500/50 rounded">
                      <div className="flex items-start gap-2 text-sm">
                        <i className="fa-solid fa-temperature-high text-amber-500 mt-0.5"></i>
                        <span className="text-amber-100">Z21 temperature elevated - Monitor closely</span>
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Telemetry Data */}
              <div className="space-y-3">
                {/* Temperature */}
                <div className="flex items-center justify-between">
                  <span className="text-sm text-track-steel">Temperature:</span>
                  <span className={`font-mono text-sm font-semibold ${
                    telemetry.quality_checks?.temperature_high ? 'text-signal-red' :
                    telemetry.quality_checks?.temperature_elevated ? 'text-amber-500' :
                    'text-signal-green'
                  }`}>
                    {telemetry.telemetry.temperature_c.toFixed(1)} °C
                  </span>
                </div>

                {/* VCC Voltage */}
                <div className="flex items-center justify-between">
                  <span className="text-sm text-track-steel">Logic Voltage (VCC):</span>
                  <span className="font-mono text-sm font-semibold text-signal-green">
                    {telemetry.telemetry.vcc_voltage_v.toFixed(2)} V
                  </span>
                </div>

                {/* Programming Track Current (if available) */}
                {telemetry.telemetry.prog_current_ma > 0 && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-track-steel">Prog Track Current:</span>
                    <span className="font-mono text-sm font-semibold text-track-steel">
                      {telemetry.telemetry.prog_current_ma} mA
                    </span>
                  </div>
                )}
              </div>

              {/* System Info (static, fetched once) */}
              <div className="mt-4 pt-3 border-t border-control-grey space-y-2">
                <div className="text-xs text-track-steel">
                  <div className="flex justify-between">
                    <span>Model:</span>
                    <span className="font-mono text-white">Z21 White</span>
                  </div>
                  <div className="flex justify-between mt-1">
                    <span>Hardware:</span>
                    <span className="font-mono text-white">0x0203</span>
                  </div>
                  <div className="flex justify-between mt-1">
                    <span>Firmware:</span>
                    <span className="font-mono text-white">1.67</span>
                  </div>
                  <div className="flex justify-between mt-1">
                    <span>Serial:</span>
                    <span className="font-mono text-white">111466</span>
                  </div>
                </div>
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
