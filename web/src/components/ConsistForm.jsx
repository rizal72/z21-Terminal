import { useState, useEffect } from 'react';

export default function ConsistForm({ consist, locomotives, gates, onSubmit, onCancel }) {
  const isEdit = !!consist;

  const [formData, setFormData] = useState({
    address: consist?.address || '',
    lead_address: consist?.lead_address || '',
    rear_address: consist?.rear_address || '',
    gate_ids: consist?.gate_ids || [],
    reference_loco: consist?.reference_loco || 'rear',  // default: rear is reference
    virtual_mode: consist?.virtual_mode !== undefined ? consist.virtual_mode : true  // default: Virtual Mode
  });

  const [errors, setErrors] = useState({});

  // Get available locomotives (not already lead/rear in other consists)
  const availableLocomotives = Object.entries(locomotives).filter(([address, loco]) => {
    // Include current consist's locomotives when editing
    if (isEdit) {
      return !loco.in_consist ||
             address === String(consist.lead_address) ||
             address === String(consist.rear_address);
    }
    // Only non-consist locomotives when creating
    return !loco.in_consist;
  });

  const handleChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const handleGateToggle = (gateId) => {
    setFormData(prev => {
      const newGateIds = prev.gate_ids.includes(gateId)
        ? prev.gate_ids.filter(id => id !== gateId)
        : [...prev.gate_ids, gateId];
      return { ...prev, gate_ids: newGateIds };
    });
  };

  const validate = () => {
    const newErrors = {};

    if (!formData.address) {
      newErrors.address = 'Consist address is required';
    } else if (!/^\d+$/.test(formData.address)) {
      newErrors.address = 'Address must be a number';
    }

    if (!formData.lead_address) {
      newErrors.lead_address = 'Lead locomotive is required';
    }

    if (!formData.rear_address) {
      newErrors.rear_address = 'Rear locomotive is required';
    }

    if (formData.lead_address === formData.rear_address) {
      newErrors.rear_address = 'Lead and rear must be different locomotives';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    onSubmit({
      address: formData.address,
      lead_address: parseInt(formData.lead_address),
      rear_address: parseInt(formData.rear_address),
      gate_ids: formData.gate_ids,
      reference_loco: formData.reference_loco,
      virtual_mode: formData.virtual_mode
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Title */}
      <div>
        <h3 className="text-lg font-display font-semibold text-signal-amber mb-1">
          {isEdit ? 'Edit Consist' : 'Create New Consist'}
        </h3>
        <p className="text-sm text-track-steel">
          {isEdit
            ? 'Update consist configuration and gate assignments'
            : 'Configure a new consist with lead and rear locomotives'}
        </p>
      </div>

      {/* Consist Address */}
      <div>
        <label className="block text-sm font-medium text-white mb-2">
          Consist Address *
        </label>
        <input
          type="text"
          value={formData.address}
          onChange={(e) => handleChange('address', e.target.value)}
          disabled={isEdit}
          className={`w-full px-3 py-2 bg-control-black border rounded text-white ${
            errors.address ? 'border-signal-red' : 'border-control-grey'
          } ${isEdit ? 'opacity-50 cursor-not-allowed' : 'focus:border-signal-amber focus:outline-none'}`}
          placeholder="e.g., 12"
        />
        {errors.address && (
          <p className="text-signal-red text-xs mt-1">{errors.address}</p>
        )}
        {isEdit && (
          <p className="text-track-steel text-xs mt-1">Address cannot be changed</p>
        )}
      </div>

      {/* Lead Locomotive */}
      <div>
        <label className="block text-sm font-medium text-white mb-2">
          Lead Locomotive *
        </label>
        <select
          value={formData.lead_address}
          onChange={(e) => handleChange('lead_address', e.target.value)}
          className={`w-full px-3 py-2 bg-control-black border rounded text-white ${
            errors.lead_address ? 'border-signal-red' : 'border-control-grey'
          } focus:border-signal-amber focus:outline-none`}
        >
          <option value="">Select lead locomotive...</option>
          {availableLocomotives.map(([address, loco]) => (
            <option key={address} value={address}>
              {loco.name} (#{address})
            </option>
          ))}
        </select>
        {errors.lead_address && (
          <p className="text-signal-red text-xs mt-1">{errors.lead_address}</p>
        )}
      </div>

      {/* Rear Locomotive */}
      <div>
        <label className="block text-sm font-medium text-white mb-2">
          Rear Locomotive *
        </label>
        <select
          value={formData.rear_address}
          onChange={(e) => handleChange('rear_address', e.target.value)}
          className={`w-full px-3 py-2 bg-control-black border rounded text-white ${
            errors.rear_address ? 'border-signal-red' : 'border-control-grey'
          } focus:border-signal-amber focus:outline-none`}
        >
          <option value="">Select rear locomotive...</option>
          {availableLocomotives.map(([address, loco]) => (
            <option key={address} value={address}>
              {loco.name} (#{address})
            </option>
          ))}
        </select>
        {errors.rear_address && (
          <p className="text-signal-red text-xs mt-1">{errors.rear_address}</p>
        )}
      </div>

      {/* Reference Locomotive */}
      <div>
        <label className="block text-sm font-medium text-white mb-2">
          Reference Locomotive (Speed Matching)
        </label>
        <p className="text-xs text-track-steel mb-3">
          The reference loco has stable decoder and is NEVER modified by speed compensation.
          The other loco will be adjusted to match.
        </p>
        <div className="space-y-2">
          <label className="flex items-center gap-3 p-3 bg-control-black rounded hover:bg-control-grey cursor-pointer transition-colors border-2 border-transparent has-[:checked]:border-signal-green">
            <input
              type="radio"
              name="reference_loco"
              value="lead"
              checked={formData.reference_loco === 'lead'}
              onChange={(e) => handleChange('reference_loco', e.target.value)}
            />
            <div>
              <div className="text-white font-medium">Lead is Reference</div>
              <div className="text-track-steel text-xs">Rear will be adjusted</div>
            </div>
          </label>
          <label className="flex items-center gap-3 p-3 bg-control-black rounded hover:bg-control-grey cursor-pointer transition-colors border-2 border-transparent has-[:checked]:border-signal-green">
            <input
              type="radio"
              name="reference_loco"
              value="rear"
              checked={formData.reference_loco === 'rear'}
              onChange={(e) => handleChange('reference_loco', e.target.value)}
            />
            <div>
              <div className="text-white font-medium">Rear is Reference (Default)</div>
              <div className="text-track-steel text-xs">Lead will be adjusted</div>
            </div>
          </label>
        </div>
      </div>

      {/* Consist Mode */}
      <div>
        <label className="block text-sm font-medium text-white mb-2">
          Consist Mode
        </label>
        <p className="text-xs text-track-steel mb-3">
          Choose how the consist will be controlled
        </p>
        <div className="space-y-2">
          <label className="flex items-center gap-3 p-3 bg-control-black rounded hover:bg-control-grey cursor-pointer transition-colors border-2 border-transparent has-[:checked]:border-signal-green">
            <input
              type="radio"
              name="virtual_mode"
              value="true"
              checked={formData.virtual_mode === true}
              onChange={() => handleChange('virtual_mode', true)}
            />
            <div className="flex-1">
              <div className="text-white font-medium flex items-center gap-2">
                <i className="fa-solid fa-gears text-signal-green"></i>
                Virtual Mode (Default)
              </div>
              <div className="text-track-steel text-xs mt-1">
                Software consist control • CV19=0 • Safe default
              </div>
            </div>
          </label>
          <label className="flex items-center gap-3 p-3 bg-control-black rounded hover:bg-control-grey cursor-pointer transition-colors border-2 border-transparent has-[:checked]:border-signal-amber">
            <input
              type="radio"
              name="virtual_mode"
              value="false"
              checked={formData.virtual_mode === false}
              onChange={() => handleChange('virtual_mode', false)}
            />
            <div className="flex-1">
              <div className="text-white font-medium flex items-center gap-2">
                <i className="fa-solid fa-link text-signal-amber"></i>
                DCC Mode
              </div>
              <div className="text-track-steel text-xs mt-1">
                Hardware consist • CV19=consist_address • Writes CV to locomotives
              </div>
            </div>
          </label>
        </div>
        {!formData.virtual_mode && (
          <div className="mt-3 p-3 bg-signal-amber/10 border border-signal-amber/30 rounded">
            <div className="flex items-start gap-2 text-signal-amber text-xs">
              <i className="fa-solid fa-triangle-exclamation mt-0.5"></i>
              <div>
                <span className="font-semibold">Warning:</span> {isEdit ? 'Switching to' : 'Creating in'} DCC Mode will write <span className="font-mono">CV19={formData.address || 'consist_address'}</span> to both locomotives.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Gate Assignments */}
      <div>
        <label className="block text-sm font-medium text-white mb-2">
          Tracking Gates (Optional)
        </label>
        <p className="text-xs text-track-steel mb-3">
          Select gates for position tracking and speed compensation
        </p>
        <div className="space-y-2">
          {gates.length > 0 ? (
            gates.map((gate) => (
              <label
                key={gate.id}
                className="flex items-center gap-3 p-2 bg-control-black rounded hover:bg-control-grey cursor-pointer transition-colors"
              >
                <input
                  type="checkbox"
                  checked={formData.gate_ids.includes(gate.id)}
                  onChange={() => handleGateToggle(gate.id)}
                />
                <div className="flex-1">
                  <div className="text-white text-sm">Gate {gate.id}</div>
                  <div className="text-track-steel text-xs">
                    Center: ({gate.center[0]}, {gate.center[1]}) • Size: {gate.width}x{gate.height}px
                  </div>
                </div>
              </label>
            ))
          ) : (
            <p className="text-track-steel text-sm py-2">No gates configured yet</p>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3 pt-4 border-t border-control-grey">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 px-4 py-2 bg-control-black border border-control-grey rounded text-track-steel hover:text-white hover:border-white transition-all"
        >
          Cancel
        </button>
        <button
          type="submit"
          className="flex-1 px-4 py-2 bg-signal-amber text-control-black rounded hover:bg-signal-amber/90 transition-all font-medium"
        >
          {isEdit ? 'Update Consist' : 'Create Consist'}
        </button>
      </div>
    </form>
  );
}
