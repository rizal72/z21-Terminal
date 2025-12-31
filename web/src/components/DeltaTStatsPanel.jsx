export default function DeltaTStatsPanel({ consistAddress, deltaT, deltaTTimestamp, timingThresholds }) {
  // Use dynamic thresholds from backend (or fallback to defaults)
  const thresholdNormal = timingThresholds?.normal || 1.0;
  const thresholdWarning = timingThresholds?.warning || 2.0;

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

    if (absDeltaT < thresholdNormal) {
      return {
        status: 'SYNCED',
        color: 'text-signal-green',
        bgColor: 'bg-signal-green/10',
        message: 'Locomotives synchronized'
      };
    } else if (absDeltaT < thresholdWarning) {
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

  // Format timestamp
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div className={`p-4 rounded-lg ${statusInfo.bgColor} border border-control-grey`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-display font-semibold text-white">
          ⏱️ Gate Timing
        </h3>
        {deltaTTimestamp && (
          <span className="text-xs text-track-steel font-mono">
            {formatTimestamp(deltaTTimestamp)}
          </span>
        )}
      </div>

      {/* Delta T Value */}
      {deltaT !== null && deltaT !== undefined ? (
        <>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-3xl font-mono font-bold text-white">
              Δt = {deltaT >= 0 ? '+' : ''}{deltaT.toFixed(3)}s
            </span>
            <span className={`text-sm font-semibold ${statusInfo.color}`}>
              {statusInfo.status}
            </span>
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
