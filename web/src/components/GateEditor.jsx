import { useState, useEffect, useRef } from 'react';

export default function GateEditor({ apiUrl, videoWidth, videoHeight, onClose }) {
  const [gates, setGates] = useState([]);
  const [dragging, setDragging] = useState(null); // {gateId, handle: 'move'|'rotate'|'nw'|'ne'|'sw'|'se', initialAngle}
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [saving, setSaving] = useState(false);
  const containerRef = useRef(null);

  // Load gates from API
  useEffect(() => {
    console.log(`🎯 GateEditor mounted - Video dimensions: ${videoWidth}x${videoHeight}`);
    fetch(`${apiUrl}/api/gates`)
      .then(res => res.json())
      .then(data => {
        console.log(`📦 Loaded ${data.length} gates from API`);
        setGates(data);
      })
      .catch(err => console.error('Failed to load gates:', err));
  }, [apiUrl, videoWidth, videoHeight]);

  const handleMouseDown = (e, gateId, handle) => {
    e.preventDefault();

    // For rotation, store initial angle and mouse angle
    let initialAngle = 0;
    let initialMouseAngle = 0;
    if (handle === 'rotate') {
      const gate = gates.find(g => g.id === gateId);
      initialAngle = gate ? gate.angle : 0;

      // Calculate initial mouse angle relative to gate center
      if (gate && containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const scaleScreenX = videoWidth / 1280;
        const scaleScreenY = videoHeight / 720;
        const centerScreenX = gate.center[0] * scaleScreenX;
        const centerScreenY = gate.center[1] * scaleScreenY;

        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        initialMouseAngle = Math.atan2(mouseY - centerScreenY, mouseX - centerScreenX) * 180 / Math.PI;
      }
    }

    setDragging({ gateId, handle, initialAngle, initialMouseAngle });
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e) => {
    if (!dragging || !containerRef.current) return;

    const container = containerRef.current;
    const rect = container.getBoundingClientRect();
    const scaleX = 1280 / videoWidth;  // Camera resolution / displayed width
    const scaleY = 720 / videoHeight;

    setGates(prev => prev.map(gate => {
      if (gate.id !== dragging.gateId) return gate;

      if (dragging.handle === 'rotate') {
        // Rotate gate - calculate delta from initial mouse angle
        const scaleScreenX = videoWidth / 1280;
        const scaleScreenY = videoHeight / 720;
        const centerScreenX = gate.center[0] * scaleScreenX;
        const centerScreenY = gate.center[1] * scaleScreenY;

        // Mouse position relative to container
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        // Calculate current mouse angle
        const currentMouseAngle = Math.atan2(mouseY - centerScreenY, mouseX - centerScreenX) * 180 / Math.PI;

        // Apply delta to initial gate angle
        const angleDelta = currentMouseAngle - dragging.initialMouseAngle;
        const newAngle = dragging.initialAngle + angleDelta;

        return {
          ...gate,
          angle: Math.round(newAngle)
        };
      } else if (dragging.handle === 'move') {
        // Move gate center
        const dx = (e.clientX - dragStart.x) * scaleX;
        const dy = (e.clientY - dragStart.y) * scaleY;

        setDragStart({ x: e.clientX, y: e.clientY });

        return {
          ...gate,
          center: [
            Math.max(0, Math.min(1280, gate.center[0] + dx)),
            Math.max(0, Math.min(720, gate.center[1] + dy))
          ]
        };
      } else {
        // Resize gate (handle: nw, ne, sw, se) - opposite corner stays fixed
        const dx = (e.clientX - dragStart.x) * scaleX;
        const dy = (e.clientY - dragStart.y) * scaleY;

        setDragStart({ x: e.clientX, y: e.clientY });

        // Transform mouse delta from world coordinates to gate local coordinates
        const angleRad = -gate.angle * Math.PI / 180; // Negative for inverse rotation
        const cos = Math.cos(angleRad);
        const sin = Math.sin(angleRad);

        const localDx = dx * cos - dy * sin;
        const localDy = dx * sin + dy * cos;

        // Determine which side we're dragging (in local coordinates)
        const isEast = dragging.handle.includes('e');
        const isWest = dragging.handle.includes('w');
        const isSouth = dragging.handle.includes('s');
        const isNorth = dragging.handle.includes('n');

        // Calculate width/height change in local coordinates
        let widthChange = 0;
        let heightChange = 0;

        if (isEast) widthChange = localDx;
        else if (isWest) widthChange = -localDx;

        if (isSouth) heightChange = localDy;
        else if (isNorth) heightChange = -localDy;

        const newWidth = Math.max(20, gate.width + widthChange);
        const newHeight = Math.max(20, gate.height + heightChange);

        // Calculate center movement in local coordinates
        let localCenterDx = 0;
        let localCenterDy = 0;

        if (isEast) localCenterDx = widthChange / 2;
        else if (isWest) localCenterDx = -widthChange / 2;

        if (isSouth) localCenterDy = heightChange / 2;
        else if (isNorth) localCenterDy = -heightChange / 2;

        // Transform center movement back to world coordinates
        const worldAngleRad = gate.angle * Math.PI / 180;
        const worldCos = Math.cos(worldAngleRad);
        const worldSin = Math.sin(worldAngleRad);

        const worldCenterDx = localCenterDx * worldCos - localCenterDy * worldSin;
        const worldCenterDy = localCenterDx * worldSin + localCenterDy * worldCos;

        return {
          ...gate,
          width: newWidth,
          height: newHeight,
          center: [
            gate.center[0] + worldCenterDx,
            gate.center[1] + worldCenterDy
          ]
        };
      }
    }));
  };

  const handleMouseUp = () => {
    setDragging(null);
  };

  useEffect(() => {
    if (dragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [dragging, dragStart]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${apiUrl}/api/save-gates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(gates)
      });
      const data = await response.json();
      if (data.status === 'success') {
        console.log('✅ Gates saved successfully');

        // Restart tracking daemon to reload new gate configuration
        try {
          await fetch(`${apiUrl}/api/restart-daemon`, { method: 'POST' });
          console.log('✅ Tracking daemon restarted with new gates');
        } catch (err) {
          console.warn('⚠️  Failed to restart tracking daemon:', err);
        }

        onClose();
      } else {
        console.error('Failed to save gates:', data.message);
        alert(`Error: ${data.message}`);
      }
    } catch (err) {
      console.error('Failed to save gates:', err);
      alert('Failed to save gates. Check console for details.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    onClose();
  };

  // Convert gate coordinates (camera space) to screen space
  const gateToScreen = (gate) => {
    const scaleX = videoWidth / 1280;
    const scaleY = videoHeight / 720;

    return {
      left: (gate.center[0] - gate.width / 2) * scaleX,
      top: (gate.center[1] - gate.height / 2) * scaleY,
      width: gate.width * scaleX,
      height: gate.height * scaleY
    };
  };

  return (
    <div
      ref={containerRef}
      className="absolute top-0 left-1/2 bg-black bg-opacity-50 cursor-crosshair"
      style={{
        zIndex: 10,
        width: `${videoWidth}px`,
        height: `${videoHeight}px`,
        transform: 'translateX(-50%)'
      }}
    >
      {/* Toolbar */}
      <div className="absolute top-1/2 left-1/2 flex gap-2 bg-control-dark px-4 py-2 rounded-lg shadow-lg z-20" style={{ transform: 'translate(-50%, -50%)' }}>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-signal-green text-control-black font-semibold rounded hover:bg-green-400 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
        <button
          onClick={handleCancel}
          className="px-4 py-2 bg-signal-red text-control-black font-semibold rounded hover:bg-red-400"
        >
          Cancel
        </button>
      </div>

      {/* Gates overlay */}
      {gates.map(gate => {
        const pos = gateToScreen(gate);
        const color = `rgb(${gate.color.join(',')})`;

        return (
          <div
            key={gate.id}
            className="absolute border-2 cursor-move"
            style={{
              left: pos.left,
              top: pos.top,
              width: pos.width,
              height: pos.height,
              borderColor: color,
              transform: `rotate(${gate.angle}deg)`
            }}
            onMouseDown={(e) => handleMouseDown(e, gate.id, 'move')}
          >
            {/* Gate label */}
            <div
              className="absolute -top-6 left-0 px-2 py-1 text-xs font-semibold rounded"
              style={{ backgroundColor: color, color: '#000' }}
            >
              {gate.name}
            </div>

            {/* Rotate handle */}
            <div
              className="absolute w-4 h-4 bg-white border-2 border-blue-500 rounded-full cursor-grab"
              style={{
                top: -30,
                left: '50%',
                transform: 'translateX(-50%)'
              }}
              onMouseDown={(e) => {
                e.stopPropagation();
                handleMouseDown(e, gate.id, 'rotate');
              }}
            />

            {/* Resize handles */}
            {['nw', 'ne', 'sw', 'se'].map(handle => (
              <div
                key={handle}
                className="absolute w-3 h-3 bg-white border border-gray-700 cursor-nwse-resize"
                style={{
                  [handle.includes('n') ? 'top' : 'bottom']: -6,
                  [handle.includes('w') ? 'left' : 'right']: -6
                }}
                onMouseDown={(e) => {
                  e.stopPropagation();
                  handleMouseDown(e, gate.id, handle);
                }}
              />
            ))}
          </div>
        );
      })}

      {/* Instructions */}
      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-control-dark px-4 py-2 rounded-lg shadow-lg text-sm text-track-steel">
        💡 Drag gates to move • Drag blue circle to rotate • Drag corners to resize • Press E or Cancel to exit
      </div>
    </div>
  );
}
