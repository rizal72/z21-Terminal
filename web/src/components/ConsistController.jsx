import { useState, useEffect } from 'react';

export default function ConsistController({
  item,
  selection,
  rosterOptions,
  trackPower,
  controllerNumber,
  onSelectionChange,
  onSpeedChange,
  onDirectionChange,
  onFunctionToggle
}) {
  const [speed, setSpeed] = useState(0);
  const [direction, setDirection] = useState('forward');
  const [functions, setFunctions] = useState({});
  const [speedFlash, setSpeedFlash] = useState(false);

  // Check if speed/direction should be disabled (locomotive in consist)
  const isLocoInConsist = selection.type === 'locomotive' && item?.in_consist;

  // Initialize functions from item data
  useEffect(() => {
    if (item?.functions && Array.isArray(item.functions)) {
      const initialFunctions = {};
      item.functions.forEach(fn => {
        if (fn && typeof fn.number !== 'undefined') {
          // Use state from item if available, otherwise default to false
          initialFunctions[fn.number] = item.functionStates?.[fn.number] || false;
        }
      });
      setFunctions(initialFunctions);
    }
  }, [item, item?.functionStates]);

  const handleSpeedChange = (e) => {
    if (isLocoInConsist) return; // Disabled for locos in consist

    const newSpeed = parseInt(e.target.value);
    setSpeed(newSpeed);
    if (onSpeedChange) {
      onSpeedChange(selection.address, newSpeed, direction === 'forward');
    }
  };

  // Set speed by percentage (0-100) with visual feedback
  const setSpeedPercent = (percent) => {
    if (!trackPower || isLocoInConsist) return; // Disabled for locos in consist

    const newSpeed = Math.round((percent / 100) * 126);
    setSpeed(newSpeed);

    // Visual feedback flash
    setSpeedFlash(true);
    setTimeout(() => setSpeedFlash(false), 300);

    if (onSpeedChange) {
      onSpeedChange(selection.address, newSpeed, direction === 'forward');
    }
  };

  // Keyboard shortcuts for speed control
  // No modifier: controls both controllers
  // Shift: controls only controller 1 (left)
  // Ctrl: controls only controller 2 (right)
  useEffect(() => {
    const handleKeyPress = (e) => {
      // Only handle if no input/select is focused
      if (document.activeElement.tagName === 'INPUT' ||
          document.activeElement.tagName === 'TEXTAREA' ||
          document.activeElement.tagName === 'SELECT') {
        return;
      }

      // Determine if this controller should respond
      const noModifiers = !e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey;
      const shiftOnly = e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey;
      const ctrlOnly = e.ctrlKey && !e.shiftKey && !e.metaKey && !e.altKey;

      const shouldRespond =
        noModifiers ||  // No modifiers: both controllers respond
        (shiftOnly && controllerNumber === 1) ||  // Shift: only controller 1 (left)
        (ctrlOnly && controllerNumber === 2);     // Ctrl: only controller 2 (right)

      if (!shouldRespond) {
        return;
      }

      // Backslash = 0%
      if (e.key === '\\' || e.key === '|') {  // | is Shift+\
        e.preventDefault();
        setSpeedPercent(0);
      }
      // 1-9 = 10-90%
      else if (e.key >= '1' && e.key <= '9') {
        e.preventDefault();
        const percent = parseInt(e.key) * 10;
        setSpeedPercent(percent);
      }
      // 0 = 100%
      else if (e.key === '0') {
        e.preventDefault();
        setSpeedPercent(100);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [trackPower, isLocoInConsist, selection?.address, direction, onSpeedChange, controllerNumber]);

  const toggleDirection = () => {
    if (isLocoInConsist) return; // Disabled for locos in consist

    const newDirection = direction === 'forward' ? 'reverse' : 'forward';
    setDirection(newDirection);
    if (onDirectionChange) {
      onDirectionChange(selection.address, newDirection);
    }
  };

  const toggleFunction = (funcNumber, isLockable) => {
    const newState = !functions[funcNumber];
    console.log(`Toggle F${funcNumber}: ${newState} (lockable: ${isLockable})`);

    setFunctions(prev => ({
      ...prev,
      [funcNumber]: newState
    }));

    if (onFunctionToggle) {
      console.log(`Calling onFunctionToggle for address ${selection.address}, F${funcNumber} = ${newState}`);
      onFunctionToggle(selection.address, funcNumber, newState);
    } else {
      console.warn('onFunctionToggle not defined');
    }

    // Auto-release for momentary functions
    if (!isLockable && newState) {
      setTimeout(() => {
        setFunctions(prev => ({
          ...prev,
          [funcNumber]: false
        }));
        if (onFunctionToggle) {
          onFunctionToggle(selection.address, funcNumber, false);
        }
      }, 800);
    }
  };

  // Reset speed when power is cut
  useEffect(() => {
    if (!trackPower) {
      setSpeed(0);
    }
  }, [trackPower]);

  const speedPercent = Math.round((speed / 126) * 100);

  if (!item) {
    return (
      <div className="control-panel grain-overlay">
        <div className="text-center text-track-steel py-12">
          <div className="text-4xl mb-4">⚙️</div>
          <div className="font-mono">No item selected</div>
        </div>
      </div>
    );
  }

  // Build display name
  const displayName = selection.type === 'consist'
    ? `${item.lead} + ${item.rear}`
    : item.name;

  const trackLabel = item.trackName || `${selection.type === 'consist' ? 'Consist' : 'Loco'} ${selection.address}`;

  return (
    <div className="control-panel grain-overlay relative z-10">
      {/* Header with selection dropdown */}
      <div className="mb-6 pb-4 border-b border-control-grey">
        <div className="mb-3">
          <label className="text-xs font-mono text-track-steel uppercase tracking-wider mb-2 block">
            Select {controllerNumber === 1 ? 'Left' : 'Right'} Controller
          </label>
          <select
            value={`${selection.type}-${selection.address}`}
            onChange={(e) => {
              const [type, address] = e.target.value.split('-');
              onSelectionChange({ type, address: parseInt(address) });
            }}
            className="w-full bg-control-dark border border-control-grey rounded px-3 py-2 text-white font-mono text-sm focus:border-signal-amber focus:outline-none"
          >
            {rosterOptions.map((option) => (
              <option key={`${option.type}-${option.address}`} value={`${option.type}-${option.address}`}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <h2 className="text-2xl font-display font-bold text-signal-amber mb-2">
          {trackLabel}
        </h2>
        <div className="font-mono text-sm text-track-steel">
          <div>{displayName}</div>
        </div>

        {/* Warning for loco in consist */}
        {isLocoInConsist && (
          <div className="mt-3 p-2 bg-signal-amber/20 border border-signal-amber/50 rounded text-xs">
            <span className="text-signal-amber font-mono">⚠️ This locomotive is in consist {item.in_consist}. Speed/Direction disabled - Functions only.</span>
          </div>
        )}
      </div>

      {/* Track visualization */}
      <div className="mb-8">
        <div className="relative">
          <div className="track-line"></div>
          <div
            className="absolute top-1/2 -translate-y-1/2 w-6 h-6 bg-signal-amber rounded-full shadow-lg transition-all duration-300"
            style={{
              left: `${speedPercent}%`,
              boxShadow: speed > 0 ? '0 0 20px rgba(255, 149, 0, 0.8)' : 'none'
            }}
          >
            <div className="absolute inset-0 flex items-center justify-center text-xs">
              🚂
            </div>
          </div>
        </div>
        <div className="flex justify-between mt-2 text-xs font-mono text-track-steel">
          <span>0%</span>
          <span className="text-signal-amber font-bold">{speedPercent}%</span>
          <span>100%</span>
        </div>
      </div>

      {/* Speed control */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <label className="text-sm font-display font-semibold text-white/80 uppercase tracking-wider">
            Throttle
          </label>
          <div className="flex items-center gap-4">
            <span className={`font-mono text-3xl font-bold text-signal-amber tabular-nums transition-all duration-300 ${
              speedFlash ? 'scale-110 drop-shadow-[0_0_15px_rgba(255,149,0,0.9)]' : ''
            }`}>
              {speed}
              <span className="text-lg text-track-steel ml-1">/ 126</span>
            </span>
          </div>
        </div>
        <input
          type="range"
          min="0"
          max="126"
          value={speed}
          onChange={handleSpeedChange}
          disabled={!trackPower || isLocoInConsist}
          className="w-full touch-none"
        />

        {/* Speed tick marks (0%, 10%, 20%, ..., 100%) */}
        <div className="relative mt-4 px-1">
          <div className="flex justify-between items-center">
            {[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100].map((percent) => (
              <button
                key={percent}
                onClick={() => setSpeedPercent(percent)}
                disabled={!trackPower || isLocoInConsist}
                className="group flex flex-col items-center gap-1 touch-manipulation disabled:opacity-30 disabled:cursor-not-allowed"
                title={isLocoInConsist ? 'Disabled (loco in consist)' : `Set speed to ${percent}%`}
              >
                <div className={`w-2 h-2 rounded-full transition-all duration-200 ${
                  Math.abs(speedPercent - percent) < 3
                    ? 'bg-signal-amber scale-150 shadow-[0_0_8px_rgba(255,149,0,0.8)]'
                    : 'bg-control-grey group-hover:bg-track-steel group-hover:scale-125'
                }`}></div>
                <span className="text-xs font-mono text-track-steel group-hover:text-white transition-colors">
                  {percent}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Keyboard shortcuts hint */}
        <div className="mt-3 text-xs font-mono text-track-steel text-center opacity-60">
          {isLocoInConsist ? (
            <span className="text-signal-amber">Speed control disabled (loco in consist)</span>
          ) : controllerNumber === 1 ? (
            <>\ = Both • Shift+\ = This only • 1-9 = 10-90% • 0 = 100%</>
          ) : (
            <>\ = Both • Ctrl+\ = This only • 1-9 = 10-90% • 0 = 100%</>
          )}
        </div>
      </div>

      {/* Direction control */}
      <div className="mb-8">
        <button
          onClick={toggleDirection}
          disabled={!trackPower || isLocoInConsist}
          className="control-panel w-full py-4 px-6 flex items-center justify-center gap-3 hover:border-signal-amber transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
          title={isLocoInConsist ? 'Disabled (loco in consist)' : 'Toggle direction'}
        >
          <span className="text-2xl">
            {direction === 'forward' ? '▶️' : '◀️'}
          </span>
          <span className="font-display font-semibold uppercase text-sm">
            {direction}
          </span>
        </button>
      </div>

      {/* Functions grid */}
      {Array.isArray(item.functions) && item.functions.length > 0 ? (
        <div>
          <h3 className="text-sm font-display font-semibold text-white/80 uppercase tracking-wider mb-4">
            Functions ({item.functions.length} available)
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {item.functions.map((fn) => {
              if (!fn || typeof fn.number === 'undefined') {
                console.warn('Invalid function:', fn);
                return null;
              }

              return (
                <button
                  key={fn.number}
                  onClick={() => toggleFunction(fn.number, fn.lockable !== false)}
                  disabled={!trackPower}
                  className={`function-btn ${
                    functions[fn.number]
                      ? 'active'
                      : (fn.lockable !== false)
                        ? 'inactive'
                        : 'momentary'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <div className="flex flex-col items-start gap-1">
                    <span className="text-xs opacity-60">F{fn.number}</span>
                    <span className="text-sm font-medium leading-tight">
                      {fn.label || `Function ${fn.number}`}
                    </span>
                  </div>
                  <div className={`absolute top-2 right-2 status-indicator ${
                    functions[fn.number] ? 'on' : 'off'
                  }`}></div>
                </button>
              );
            })}
          </div>
          <div className="mt-4 text-xs text-track-steel font-mono flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-signal-green rounded-full"></div>
              <span>Toggle</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-signal-amber/50 rounded-full"></div>
              <span>Momentary</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center text-track-steel py-4">
          <div className="text-sm font-mono">No functions available for this {selection.type === 'consist' ? 'consist' : 'locomotive'}</div>
        </div>
      )}
    </div>
  );
}
