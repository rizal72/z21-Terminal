export default function ConsistCard({
  consistAddress,
  assignment,
  consistData,
  referenceData,
  locomotives,
  gates,
  onEdit,
  onDelete
}) {
  // Get locomotive names
  const leadLoco = locomotives[assignment.lead_address];
  const rearLoco = locomotives[assignment.rear_address];

  const leadName = leadLoco?.name || `Loco ${assignment.lead_address}`;
  const rearName = rearLoco?.name || `Loco ${assignment.rear_address}`;

  // Determine which is reference/adjust
  const leadIsReference = referenceData?.reference === assignment.lead_address;
  const rearIsReference = referenceData?.reference === assignment.rear_address;

  // Get gate names
  const gateNames = (assignment.gate_ids || [])
    .map(gateId => {
      const gate = gates.find(g => g.id === gateId);
      return gate ? `Gate ${gate.id}` : `Gate ${gateId}`;
    })
    .join(', ');

  // Determine gate assignment type (symmetric vs asymmetric)
  const isSymmetric = !assignment.gate_assignment || assignment.gate_assignment === null;
  const gateAssignmentLabel = isSymmetric ? 'Symmetric' : 'Asymmetric';
  const gateAssignmentColor = isSymmetric ? 'text-signal-green' : 'text-signal-amber';

  // Track name
  const trackName = consistAddress === '10' ? 'INTERNAL TRACK' : 'EXTERNAL TRACK';

  // Virtual mode status
  const virtualMode = consistData?.virtual_mode || false;
  const autoCompensation = consistData?.auto_compensation_enabled || false;

  return (
    <div className="control-panel p-4">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-lg font-display font-semibold text-signal-amber flex items-center gap-2">
            <i className="fa-solid fa-train"></i>
            Consist {consistAddress}
          </h3>
          <p className="text-xs text-track-steel mt-1">{trackName}</p>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={onEdit}
            className="px-3 py-1.5 bg-control-black border border-signal-amber/50 rounded text-signal-amber hover:bg-signal-amber hover:text-control-black transition-all text-sm"
            title="Edit consist"
          >
            <i className="fa-solid fa-pen"></i>
          </button>
          <button
            onClick={onDelete}
            className="px-3 py-1.5 bg-control-black border border-signal-red/50 rounded text-signal-red hover:bg-signal-red hover:text-white transition-all text-sm"
            title="Delete consist"
          >
            <i className="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>

      {/* Locomotives */}
      <div className="space-y-2 mb-3">
        <div className="flex items-center gap-2 text-sm flex-wrap">
          <i className="fa-solid fa-circle-arrow-right text-signal-green"></i>
          <span className="text-track-steel">Lead:</span>
          <span className="text-white font-mono">
            {leadName} <span className="text-signal-amber">(#{assignment.lead_address})</span>
          </span>
          {leadIsReference && (
            <span className="px-2 py-0.5 bg-signal-green/20 border border-signal-green/50 text-signal-green rounded text-xs">
              Reference
            </span>
          )}
          {!leadIsReference && referenceData && (
            <span className="px-2 py-0.5 bg-signal-amber/20 border border-signal-amber/50 text-signal-amber rounded text-xs">
              Adjust
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-sm flex-wrap">
          <i className="fa-solid fa-circle-arrow-right text-signal-green"></i>
          <span className="text-track-steel">Rear:</span>
          <span className="text-white font-mono">
            {rearName} <span className="text-signal-amber">(#{assignment.rear_address})</span>
          </span>
          {rearIsReference && (
            <span className="px-2 py-0.5 bg-signal-green/20 border border-signal-green/50 text-signal-green rounded text-xs">
              Reference
            </span>
          )}
          {!rearIsReference && referenceData && (
            <span className="px-2 py-0.5 bg-signal-amber/20 border border-signal-amber/50 text-signal-amber rounded text-xs">
              Adjust
            </span>
          )}
        </div>
      </div>

      {/* Gates */}
      {assignment.gate_ids && assignment.gate_ids.length > 0 && (
        <div className="mb-3 text-sm flex items-center gap-2">
          <span className="text-track-steel">Tracking Gates:</span>
          <span className="text-white">{gateNames}</span>
          <span
            className="px-2 py-0.5 bg-control-grey/50 border border-control-grey rounded text-xs flex items-center gap-1.5"
            title={isSymmetric ? 'Both locomotives tracked by all gates' : 'Each locomotive tracked by specific gates'}
          >
            <i className={`fa-solid fa-exchange-alt ${gateAssignmentColor}`}></i>
            <span className="text-track-steel">{gateAssignmentLabel}</span>
          </span>
        </div>
      )}

      {/* Status Badges */}
      <div className="flex flex-wrap gap-2">
        {/* Virtual Mode Badge */}
        <div className={`px-2 py-1 rounded text-xs flex items-center gap-1.5 ${
          virtualMode
            ? 'bg-signal-green/20 border border-signal-green/50 text-signal-green'
            : 'bg-control-grey border border-control-grey text-track-steel'
        }`}>
          <i className={`fa-solid ${virtualMode ? 'fa-gears' : 'fa-link'}`}></i>
          <span>{virtualMode ? 'Virtual Mode' : 'DCC Mode'}</span>
        </div>

        {/* Auto Compensation Badge (only in Virtual Mode) */}
        {virtualMode && (
          <div className={`px-2 py-1 rounded text-xs flex items-center gap-1.5 ${
            autoCompensation
              ? 'bg-signal-amber/20 border border-signal-amber/50 text-signal-amber'
              : 'bg-control-grey border border-control-grey text-track-steel'
          }`}>
            <i className="fa-solid fa-gauge-high"></i>
            <span>Speed Compensation {autoCompensation ? 'ON' : 'OFF'}</span>
          </div>
        )}
      </div>
    </div>
  );
}
