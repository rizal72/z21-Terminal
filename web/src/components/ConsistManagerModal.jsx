import { useState, useEffect } from 'react';
import ConsistCard from './ConsistCard';
import ConsistForm from './ConsistForm';

export default function ConsistManagerModal({ onClose }) {
  const [consists, setConsists] = useState({});
  const [gates, setGates] = useState([]);
  const [trackingAssignments, setTrackingAssignments] = useState({});
  const [referenceLocos, setReferenceLocos] = useState({});
  const [locomotives, setLocomotives] = useState({});
  const [showForm, setShowForm] = useState(false);
  const [editingConsist, setEditingConsist] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleteConfirm, setDeleteConfirm] = useState(null); // {address, isDccMode}

  // Load consists and locomotives on mount
  useEffect(() => {
    loadData();
  }, []);

  // Block body scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);

      // Load consists, gates, and reference_locos
      const consistsResponse = await fetch('/api/consists');
      if (!consistsResponse.ok) {
        throw new Error(`Failed to load consists: ${consistsResponse.status}`);
      }
      const consistsData = await consistsResponse.json();
      setConsists(consistsData.consists || {});
      setGates(consistsData.gates || []);
      setTrackingAssignments(consistsData.tracking_assignments || {});
      setReferenceLocos(consistsData.reference_locos || {});

      // Load locomotives
      const locomotivesResponse = await fetch('/api/locomotives');
      if (!locomotivesResponse.ok) {
        throw new Error(`Failed to load locomotives: ${locomotivesResponse.status}`);
      }
      const locomotivesData = await locomotivesResponse.json();
      setLocomotives(locomotivesData || {});

      setLoading(false);
    } catch (error) {
      console.error('Failed to load data:', error);
      // Silently continue - data might be partially loaded
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingConsist(null);
    setShowForm(true);
  };

  const handleEdit = (consistAddress) => {
    const assignment = trackingAssignments[consistAddress];
    const refLoco = referenceLocos[consistAddress];
    const consistData = consists[consistAddress];

    if (assignment) {
      // Determine which is reference: "lead" or "rear"
      let referenceLoco = "rear"; // default
      if (refLoco) {
        if (refLoco.reference === assignment.lead_address) {
          referenceLoco = "lead";
        }
      }

      setEditingConsist({
        address: consistAddress,
        lead_address: assignment.lead_address,
        rear_address: assignment.rear_address,
        gate_ids: assignment.gate_ids || [],
        reference_loco: referenceLoco,
        virtual_mode: consistData?.virtual_mode !== undefined ? consistData.virtual_mode : true
      });
      setShowForm(true);
    }
  };

  const handleDelete = (consistAddress) => {
    // Check if consist is in DCC mode (virtual_mode=false)
    const consistData = consists[consistAddress];
    const isDccMode = consistData && !consistData.virtual_mode;

    // Show confirmation modal
    setDeleteConfirm({
      address: consistAddress,
      isDccMode
    });
  };

  const confirmDelete = async () => {
    if (!deleteConfirm) return;

    const consistAddress = deleteConfirm.address;

    try {
      const response = await fetch(`/api/consists/${consistAddress}`, {
        method: 'DELETE'
      });

      const result = await response.json();

      if (result.success) {
        // Restart daemon to reload config
        await fetch('/api/restart-daemon', { method: 'POST' });

        // Reload data
        await loadData();

        // Close confirm modal
        setDeleteConfirm(null);
      } else {
        alert(`Failed to delete consist: ${result.error}`);
        setDeleteConfirm(null);
      }
    } catch (error) {
      console.error('Failed to delete consist:', error);
      alert('Failed to delete consist');
      setDeleteConfirm(null);
    }
  };

  const cancelDelete = () => {
    setDeleteConfirm(null);
  };

  const handleFormSubmit = async (formData) => {
    try {
      const isEdit = !!editingConsist;
      const url = isEdit
        ? `/api/consists/${formData.address}`
        : '/api/consists';

      const method = isEdit ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      const result = await response.json();

      if (result.success) {
        // Restart daemon to reload config
        await fetch('/api/restart-daemon', { method: 'POST' });

        // Close form and reload data
        setShowForm(false);
        setEditingConsist(null);
        await loadData();
      } else {
        alert(`Failed to ${isEdit ? 'update' : 'create'} consist: ${result.error}`);
      }
    } catch (error) {
      console.error('Failed to submit form:', error);
      alert(`Failed to ${editingConsist ? 'update' : 'create'} consist`);
    }
  };

  const handleFormCancel = () => {
    setShowForm(false);
    setEditingConsist(null);
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 z-[80]"
        onClick={onClose}
      />

      {/* Modal Panel */}
      <div className="fixed inset-4 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:w-[90%] md:max-w-4xl md:max-h-[90vh] bg-control-dark border border-control-grey rounded-lg z-[90] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-control-grey">
          <h2 className="text-xl font-display font-semibold text-signal-amber flex items-center gap-2">
            <i className="fa-solid fa-gears"></i>
            Consist Manager
          </h2>
          <button
            onClick={onClose}
            className="text-track-steel hover:text-signal-amber transition-colors"
          >
            <i className="fa-solid fa-times text-xl"></i>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <i className="fa-solid fa-spinner fa-spin text-3xl text-signal-amber"></i>
            </div>
          ) : showForm ? (
            <ConsistForm
              consist={editingConsist}
              locomotives={locomotives}
              gates={gates}
              onSubmit={handleFormSubmit}
              onCancel={handleFormCancel}
            />
          ) : (
            <div className="space-y-4">
              {/* Consist Cards */}
              {Object.keys(trackingAssignments).filter(key => key !== '_comment').length > 0 ? (
                Object.entries(trackingAssignments)
                  .filter(([address]) => address !== '_comment')
                  .map(([address, assignment]) => (
                    <ConsistCard
                      key={address}
                      consistAddress={address}
                      assignment={assignment}
                      consistData={consists[address]}
                      referenceData={referenceLocos[address]}
                      locomotives={locomotives}
                      gates={gates}
                      onEdit={() => handleEdit(address)}
                      onDelete={() => handleDelete(address)}
                    />
                  ))
              ) : (
                <div className="text-center py-12 text-track-steel">
                  <i className="fa-solid fa-train text-4xl mb-4 opacity-50"></i>
                  <p>No consists configured yet.</p>
                  <p className="text-sm mt-2">Click "Create New Consist" to get started.</p>
                </div>
              )}

              {/* Create Button */}
              <button
                onClick={handleCreate}
                className="w-full p-4 bg-control-black border-2 border-dashed border-signal-green/30 rounded-lg hover:border-signal-green hover:bg-control-grey transition-all text-signal-green font-medium"
              >
                <i className="fa-solid fa-plus mr-2"></i>
                Create New Consist
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/80 z-[100]"
            onClick={cancelDelete}
          />

          {/* Confirmation Dialog */}
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90%] max-w-md bg-control-dark border-2 border-signal-red rounded-lg z-[110] p-6">
            <div className="text-center">
              {/* Warning Icon */}
              <i className="fa-solid fa-triangle-exclamation text-5xl text-signal-red mb-4"></i>

              {/* Title */}
              <h3 className="text-xl font-display font-semibold text-white mb-3">
                Delete Consist {deleteConfirm.address}?
              </h3>

              {/* Message */}
              <div className="text-track-steel mb-6 space-y-2">
                {deleteConfirm.isDccMode ? (
                  <>
                    <p className="text-signal-amber font-semibold">
                      ⚠️ This consist is in DCC Mode
                    </p>
                    <p>
                      Deleting will write <span className="text-white font-mono">CV19=0</span> to both locomotives to disable the hardware consist.
                    </p>
                  </>
                ) : (
                  <p>
                    This will permanently remove the consist from your configuration.
                  </p>
                )}
                <p className="text-sm">
                  This action cannot be undone.
                </p>
              </div>

              {/* Buttons */}
              <div className="flex gap-3 justify-center">
                <button
                  onClick={cancelDelete}
                  className="px-6 py-2 bg-control-black border border-control-grey rounded text-track-steel hover:border-signal-amber hover:text-signal-amber transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDelete}
                  className="px-6 py-2 bg-signal-red border border-signal-red rounded text-white hover:bg-signal-red/80 transition-all font-semibold"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
