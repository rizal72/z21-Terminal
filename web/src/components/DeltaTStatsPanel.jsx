export default function DeltaTStatsPanel({ consistAddress, deltaT, deltaTTimestamp, deltaTTimeStr, timingThresholds, virtualMode, adjustLocoAddress, adjustSpeed, adjustCorrection, referenceLocoAddress, referenceSpeed, referenceCorrection }) {
  // Use dynamic thresholds from backend (or fallback to defaults)
  const thresholdWarning = timingThresholds?.warning || 1.0;
  const thresholdCritical = timingThresholds?.critical || 1.5;

  // Calculate status based on |Δt| thresholds
  const getStatusInfo = () => {
    if (deltaT === null || deltaT === undefined) {
      return {
        status: 'WAITING',
        color: 'text-track-steel',
        bgColor: 'bg-control-grey',
        message: 'Waiting for gate crossing data...'
      };
    }

    const absDeltaT = Math.abs(deltaT);

    if (absDeltaT < thresholdWarning) {
      return {
        status: 'SYNCED',
        color: 'text-signal-green',
        bgColor: 'bg-signal-green/10',
        message: 'Locomotives synchronized'
      };
    } else if (absDeltaT < thresholdCritical) {
      return {
        status: 'WARNING',
        color: 'text-signal-amber',
        bgColor: 'bg-signal-amber/10',
        message: 'Slight desynchronization detected'
      };
    } else {
      return {
        status: 'CRITICAL',
        color: 'text-signal-red',
        bgColor: 'bg-signal-red/10',
        message: 'Critical desynchronization!'
      };
    }
  };

  const statusInfo = getStatusInfo();

  // Format elapsed time between THIS Δt and PREVIOUS Δt (not "now - timestamp"!)
  // NOTE: This should be pre-calculated by backend when Δt updates, not here
  // For now, just display the timestamp as-is (backend should send 'time_str')
  const formatElapsedTime = (timestamp) => {
    // This function is DEPRECATED - backend should send pre-calculated 'time_str'
    // Kept for backwards compatibility only
    return '';  // Return empty, backend provides time_str
  };

  return (
    <div className={`p-4 rounded-lg ${statusInfo.bgColor} border border-control-grey`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-display font-semibold text-white">
          ⏱️ Gate Timing
        </h3>
        {deltaTTimeStr && (
          <span className="text-xs text-track-steel font-mono">
            {deltaTTimeStr}
          </span>
        )}
      </div>

      {/* Delta T Value */}
      {deltaT !== null && deltaT !== undefined ? (
        <>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-2">
            <div className="flex items-center gap-3">
              <span className="text-3xl font-mono font-bold text-white">
                Δt = {deltaT >= 0 ? '+' : ''}{deltaT.toFixed(3)}s
              </span>
              <span className={`text-sm font-semibold ${statusInfo.color}`}>
                {statusInfo.status}
              </span>
            </div>

            {/* Compensation info (only if adjust data available) */}
            {adjustLocoAddress !== null && adjustLocoAddress !== undefined && adjustSpeed !== null && adjustSpeed !== undefined && (
              <div className="flex items-center gap-2 text-sm font-mono">
                <span className="text-track-steel">Loco {adjustLocoAddress}:</span>
                <span className="text-white font-semibold">{adjustSpeed}</span>
                {adjustCorrection !== 0 && (
                  <span className={adjustCorrection > 0 ? 'text-signal-green' : 'text-signal-red'}>
                    ({adjustCorrection > 0 ? '+' : ''}{adjustCorrection})
                  </span>
                )}
              </div>
            )}

            {/* Reference compensation info (only when reference is compensated on overflow) */}
            {referenceLocoAddress !== null && referenceLocoAddress !== undefined && referenceSpeed !== null && referenceSpeed !== undefined && referenceCorrection !== 0 && (
              <div className="flex items-center gap-2 text-sm font-mono">
                <span className="text-track-steel">Loco {referenceLocoAddress} (ref):</span>
                <span className="text-white font-semibold">{referenceSpeed}</span>
                <span className={referenceCorrection > 0 ? 'text-signal-green' : 'text-signal-red'}>
                  ({referenceCorrection > 0 ? '+' : ''}{referenceCorrection})
                </span>
              </div>
            )}
          </div>

          {/* Interpretation */}
          <p className="text-xs text-track-steel font-sans mb-2">
            {deltaT > 0 ? (
              <>Lead loco passing first (running faster)</>
            ) : deltaT < 0 ? (
              <>Rear loco passing first (lead too slow)</>
            ) : (
              <>Perfect synchronization</>
            )}
          </p>

          {/* Status Message */}
          <p className={`text-xs font-sans ${statusInfo.color}`}>
            {statusInfo.message}
          </p>
        </>
      ) : (
        <div className="text-center py-3">
          <p className="text-sm text-track-steel font-sans">
            {statusInfo.message}
          </p>
          <p className="text-xs text-track-steel/60 font-sans mt-1">
            Start moving consist {consistAddress} to begin tracking
          </p>
        </div>
      )}
    </div>
  );
}
