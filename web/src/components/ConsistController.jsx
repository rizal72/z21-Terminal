import { useState, useEffect, useRef } from 'react';
import DeltaTStatsPanel from './DeltaTStatsPanel';

export default function ConsistController({
  item,
  selection,
  rosterOptions,
  trackPower,
  controllerNumber,
  isActive = false,
  canRemove = false,
  onSelectionChange,
  onRemove,
  onFocus,
  onSpeedChange,
  onDirectionChange,
  onFunctionToggle,
  onToggleVirtualMode
}) {
  const [speed, setSpeed] = useState(0);
  const [direction, setDirection] = useState('forward');
  const [functions, setFunctions] = useState({});
  const [speedFlash, setSpeedFlash] = useState(false);

  // Throttling refs for speed commands (like JMRI throttle)
  const lastSpeedSentTime = useRef(0);
  const speedThrottleTimeout = useRef(null);
  const pendingSpeedValue = useRef(null);

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

  // Sync speed from WebSocket updates (multi-device sync)
  useEffect(() => {
    if (item?.speed !== undefined) {
      setSpeed(item.speed);
    }
  }, [item?.speed]);

  // Sync direction from WebSocket updates (multi-device sync)
  useEffect(() => {
    if (item?.direction !== undefined) {
      setDirection(item.direction);
    }
  }, [item?.direction]);

  const handleSpeedChange = (e) => {
    if (isLocoInConsist) return; // Disabled for locos in consist

    const newSpeed = parseInt(e.target.value);
    setSpeed(newSpeed); // Update UI immediately

    // Throttle Z21 commands to 200ms (like JMRI throttle behavior)
    const now = Date.now();
    const timeSinceLastSend = now - lastSpeedSentTime.current;
    const THROTTLE_MS = 200;

    // Clear any pending timeout
    if (speedThrottleTimeout.current) {
      clearTimeout(speedThrottleTimeout.current);
    }

    // If enough time passed, send immediately
    if (timeSinceLastSend >= THROTTLE_MS) {
      if (onSpeedChange) {
        onSpeedChange(selection.address, newSpeed, direction === 'forward');
        lastSpeedSentTime.current = now;
      }
    } else {
      // Schedule send after remaining time
      pendingSpeedValue.current = newSpeed;
      const remainingTime = THROTTLE_MS - timeSinceLastSend;

      speedThrottleTimeout.current = setTimeout(() => {
        if (onSpeedChange && pendingSpeedValue.current !== null) {
          onSpeedChange(selection.address, pendingSpeedValue.current, direction === 'forward');
          lastSpeedSentTime.current = Date.now();
          pendingSpeedValue.current = null;
        }
      }, remainingTime);
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
  // No modifier: controls only active controller
  // Shift: controls ALL controllers simultaneously
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

      const shouldRespond =
        (noModifiers && isActive) ||  // No modifiers: only active controller responds
        shiftOnly;                     // Shift: ALL controllers respond

      if (!shouldRespond) {
        return;
      }

      // Backslash = 0%
      if (e.key === '\\' || e.key === '|') {  // | is Shift+\
        e.preventDefault();
        setSpeedPercent(0);
      }
      // 1-9 = 10-90% (use e.code to detect physical key, works with Shift/Ctrl)
      else if (e.code >= 'Digit1' && e.code <= 'Digit9') {
        e.preventDefault();
        const digit = parseInt(e.code.slice(-1)); // Extract digit from "Digit1", "Digit2", etc.
        const percent = digit * 10;
        setSpeedPercent(percent);
      }
      // 0 = 100% (use e.code to detect physical key, works with Shift/Ctrl)
      else if (e.code === 'Digit0') {
        e.preventDefault();
        setSpeedPercent(100);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [trackPower, isLocoInConsist, selection?.address, direction, onSpeedChange, isActive]);

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

    setFunctions(prev => ({
      ...prev,
      [funcNumber]: newState
    }));

    if (onFunctionToggle) {
      onFunctionToggle(selection.address, funcNumber, newState);
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

  // Cleanup throttle timeout on unmount
  useEffect(() => {
    return () => {
      if (speedThrottleTimeout.current) {
        clearTimeout(speedThrottleTimeout.current);
      }
    };
  }, []);

  const speedPercent = Math.round((speed / 126) * 100);

  if (!item) {
    return (
      <div
        className={`control-panel grain-overlay relative cursor-pointer ${
          isActive ? 'ring-2 ring-signal-amber' : ''
        }`}
        onClick={onFocus}
      >
        {/* Close button */}
        {canRemove && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            className="absolute top-3 right-3 z-20 w-8 h-8 flex items-center justify-center bg-control-dark border border-control-grey rounded hover:border-signal-red hover:text-signal-red transition-all duration-200"
            title="Remove this controller"
          >
            <i className="fa-solid fa-xmark text-lg"></i>
          </button>
        )}

        {/* Dropdown always visible even without selection */}
        <div className="mt-6 mb-6 pb-4 border-b border-control-grey">
          <div className="mb-3">
            <label className="text-xs font-mono text-track-steel uppercase tracking-wider mb-2 block">
              Controller #{controllerNumber}
            </label>
            <div className="flex items-center gap-2 overflow-hidden">
              <div className="relative flex-1 min-w-0">
                <select
                  value=""
                  onChange={(e) => {
                    if (e.target.value) {
                      const [type, address] = e.target.value.split('-');
                      onSelectionChange({ type, address: parseInt(address) });
                    }
                  }}
                  className="w-full max-w-full bg-control-dark border border-control-grey rounded px-3 py-2 pr-8 text-white font-mono text-sm focus:border-signal-amber focus:outline-none overflow-hidden text-ellipsis appearance-none"
                  style={{
                    width: '100%',
                    WebkitAppearance: 'none',
                    MozAppearance: 'none'
                  }}
                >
                  <option value="">-- Select Locomotive or Consist --</option>
                  {rosterOptions.map((option) => (
                    <option key={`${option.type}-${option.address}`} value={`${option.type}-${option.address}`}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {/* Custom dropdown arrow */}
                <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-track-steel">
                  <i className="fa-solid fa-chevron-down text-xs"></i>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* No selection message */}
        <div className="text-center text-track-steel py-12">
          <i className="fa-solid fa-gear text-5xl mb-4 opacity-50"></i>
          <div className="font-mono">No item selected</div>
          <div className="text-xs mt-2 opacity-60">Use the dropdown above to select a locomotive</div>
        </div>
      </div>
    );
  }

  // Build display name: use names, handle consist with only lead
  const displayName = selection.type === 'consist'
    ? item.rear_name
      ? `${item.lead_name} + ${item.rear_name}`
      : item.lead_name
    : item.name;

  const trackLabel = item.trackName || `${selection.type === 'consist' ? 'Consist' : 'Loco'} ${selection.address}`;

  return (
    <div
      className={`control-panel grain-overlay relative z-10 cursor-pointer ${
        isActive ? 'ring-2 ring-signal-amber' : ''
      }`}
      onClick={onFocus}
    >
      {/* Close button */}
      {canRemove && (
        <button
          onClick={(e) => {
            e.stopPropagation(); // Prevent panel click (focus change)
            onRemove();
          }}
          className="absolute top-3 right-3 z-20 w-8 h-8 flex items-center justify-center bg-control-dark border border-control-grey rounded hover:border-signal-red hover:text-signal-red transition-all duration-200"
          title="Remove this controller"
        >
          <i className="fa-solid fa-xmark text-lg"></i>
        </button>
      )}

      {/* Header with selection dropdown */}
      <div className="mt-6 mb-6 pb-4 border-b border-control-grey">
        <div className="mb-3">
          <label className="text-xs font-mono text-track-steel uppercase tracking-wider mb-2 block">
            Controller #{controllerNumber}
          </label>
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="relative flex-1 min-w-0">
              <select
                value={`${selection.type}-${selection.address}`}
                onChange={(e) => {
                  const [type, address] = e.target.value.split('-');
                  onSelectionChange({ type, address: parseInt(address) });
                }}
                className="w-full max-w-full bg-control-dark border border-control-grey rounded px-3 py-2 pr-8 text-white font-mono text-sm focus:border-signal-amber focus:outline-none overflow-hidden text-ellipsis appearance-none"
                style={{
                  width: '100%',
                  WebkitAppearance: 'none',
                  MozAppearance: 'none'
                }}
              >
                {rosterOptions.map((option) => (
                  <option key={`${option.type}-${option.address}`} value={`${option.type}-${option.address}`}>
                    {option.label}
                  </option>
                ))}
              </select>
              {/* Custom dropdown arrow */}
              <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-track-steel">
                <i className="fa-solid fa-chevron-down text-xs"></i>
              </div>
            </div>
            {/* Train icon indicator */}
            <div className="flex items-center justify-center w-10 h-10 bg-control-dark border border-control-grey rounded flex-shrink-0">
              <div className="relative">
                <div
                  className="absolute inset-0 bg-signal-amber rounded-full opacity-20 blur-md transition-opacity duration-300"
                  style={{
                    opacity: speed > 0 ? 0.3 : 0
                  }}
                ></div>
                <i
                  className="fa-solid fa-train text-signal-amber relative z-10 transition-all duration-300"
                  style={{
                    fontSize: '1.25rem',
                    filter: speed > 0 ? 'drop-shadow(0 0 4px rgba(255, 149, 0, 0.8))' : 'none'
                  }}
                ></i>
              </div>
            </div>
          </div>
        </div>

        <h2 className="text-2xl font-display font-bold text-signal-amber mb-2">
          {trackLabel}
        </h2>
        <div className="font-mono text-sm text-track-steel">
          <div>{displayName}</div>
        </div>

        {/* Warning for loco in consist */}
        {isLocoInConsist && (
          <div className="mt-3 p-2 bg-signal-amber/20 border border-signal-amber/50 rounded">
            <div className="flex items-center gap-2 text-xs">
              <i className="fa-solid fa-triangle-exclamation text-signal-amber"></i>
              <span className="text-signal-amber font-mono">
                This locomotive is in consist {item.in_consist}. Speed/Direction disabled - Functions only.
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Speed control */}
      <div className="mb-4 lg:mb-8">
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
        {/* Slider with progress fill */}
        <div className="relative">
          {/* Progress fill reveals gradient */}
          <div
            className="absolute left-0 top-1/2 -translate-y-1/2 h-3 rounded-full pointer-events-none transition-all duration-200"
            style={{
              width: `${speedPercent}%`,
              zIndex: 0,
              background: 'linear-gradient(to right, #2a2a2a 0%, #ff9500 50%, #e63946 100%)',
              boxShadow: speed > 0 ? '0 0 15px rgba(255, 149, 0, 0.4)' : 'none'
            }}
          >
          </div>
          <input
            type="range"
            min="0"
            max="126"
            value={speed}
            onChange={handleSpeedChange}
            disabled={!trackPower || isLocoInConsist}
            className="w-full touch-none relative z-10"
            style={{ background: 'transparent' }}
          />
        </div>

        {/* Speed tick marks (0%, 10%, 20%, ..., 100%) */}
        <div className="relative mt-8 h-12">
          {[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100].map((percent) => {
            // Calculate offset to align with thumb position
            // Thumb is 48px wide, so at 0% center is at 24px, at 100% center is at calc(100% - 24px)
            const offset = 24 - (percent * 0.48);
            return (
              <button
                key={percent}
                onClick={() => setSpeedPercent(percent)}
                disabled={!trackPower || isLocoInConsist}
                className="group absolute flex flex-col items-center gap-1 touch-manipulation disabled:opacity-30 disabled:cursor-not-allowed -translate-x-1/2"
                style={{ left: `calc(${percent}% + ${offset}px)` }}
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
            );
          })}
        </div>

        {/* Keyboard shortcuts hint - Desktop only (touch devices don't need keyboard hints) */}
        <div className="mt-3 text-xs font-mono text-track-steel text-center opacity-60 overflow-hidden hidden lg:block">
          {isLocoInConsist ? (
            <span className="text-signal-amber">Speed control disabled (loco in consist)</span>
          ) : (
            <div>Speed: \=0% • 1,2,3..0=10-100% → <span className="text-signal-amber">{isActive ? 'This' : '(click to activate)'}</span> | +Shift → <span className="text-signal-amber">All</span></div>
          )}
        </div>
      </div>

      {/* Delta T Stats Panel - Only for consists */}
      {selection.type === 'consist' && item.delta_t !== undefined && (
        <div className="mb-6">
          <DeltaTStatsPanel
            consistAddress={selection.address}
            deltaT={item.delta_t}
            deltaTTimestamp={item.delta_t_timestamp}
          />
        </div>
      )}

      {/* Stop and Direction controls */}
      <div className="mb-8 grid grid-cols-2 gap-2 md:gap-4">
        {/* Stop button */}
        <button
          onClick={() => {
            setSpeed(0);
            if (onSpeedChange) {
              onSpeedChange(selection.address, 0, direction === 'forward');
            }
          }}
          disabled={!trackPower || isLocoInConsist}
          className="control-panel py-3 px-2 md:py-4 md:px-6 flex items-center justify-center gap-2 md:gap-3 hover:border-signal-red transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
          title={isLocoInConsist ? 'Disabled (loco in consist)' : 'Stop (set speed to 0)'}
        >
          <i
            className="fa-solid fa-stop text-xl"
            style={{ color: trackPower && !isLocoInConsist ? '#e63946' : '#64748b' }}
          ></i>
          <span className="font-display font-semibold uppercase text-sm">
            Stop
          </span>
        </button>

        {/* Direction control */}
        <button
          onClick={toggleDirection}
          disabled={!trackPower || isLocoInConsist}
          className="control-panel py-3 px-2 md:py-4 md:px-6 flex items-center justify-center gap-2 md:gap-3 hover:border-signal-amber transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
          title={isLocoInConsist ? 'Disabled (loco in consist)' : 'Toggle direction'}
        >
          <i
            className={`fa-solid fa-arrow-right text-xl transition-transform duration-300 ${direction === 'reverse' ? 'rotate-180' : ''}`}
            style={{ color: trackPower && !isLocoInConsist ? '#ff9500' : '#64748b' }}
          ></i>
          <span className="font-display font-semibold uppercase text-sm">
            {direction}
          </span>
        </button>
      </div>

      {/* Virtual Mode Toggle - Only for consists */}
      {selection.type === 'consist' && (
        <div className="mb-8">
          <button
            onClick={() => {
              if (onToggleVirtualMode) {
                onToggleVirtualMode(selection.address, !item.virtual_mode);
              }
            }}
            disabled={!trackPower}
            className={`w-full control-panel py-4 px-6 flex items-center justify-between hover:border-signal-amber transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation ${
              item.virtual_mode ? 'border-signal-green' : ''
            }`}
            title={item.virtual_mode ? 'Virtual Mode Active - CV19=0' : 'DCC Consist Mode - CV19=consist_address'}
          >
            <div className="flex items-center gap-3">
              <i className={`fa-solid ${item.virtual_mode ? 'fa-gears' : 'fa-link'} text-xl`}
                style={{ color: item.virtual_mode ? '#06d6a0' : '#64748b' }}
              ></i>
              <span className="font-display font-semibold uppercase text-sm">
                {item.virtual_mode ? 'Virtual Consist Mode' : 'DCC Consist Mode'}
              </span>
            </div>
            <div className={`px-3 py-1 rounded-full text-xs font-mono ${
              item.virtual_mode
                ? 'bg-signal-green/20 text-signal-green'
                : 'bg-control-grey text-track-steel'
            }`}>
              {item.virtual_mode ? 'CV19=0' : `CV19=${selection.address}`}
            </div>
          </button>
          <div className="mt-2 text-xs text-track-steel font-sans text-center">
            {item.virtual_mode ? (
              <>
                <span className="text-signal-green">●</span> Locomotives freed from consist • Individual speed control possible
              </>
            ) : (
              <>
                <span className="text-track-steel">●</span> Standard DCC consist • Locomotives synchronized via CV19
              </>
            )}
          </div>
        </div>
      )}

      {/* Functions grid */}
      {Array.isArray(item.functions) && item.functions.length > 0 ? (
        <div>
          <h3 className="text-sm font-display font-semibold text-white/80 uppercase tracking-wider mb-4">
            Functions ({item.functions.length} available)
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 md:gap-3">
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
                  } ${fn.lockable !== false ? 'toggle' : 'temporary'}`}></div>
                </button>
              );
            })}
          </div>
          <div className="mt-4 text-xs text-track-steel font-mono flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-signal-red/30 rounded-full"></div>
              <span>Toggle (stays ON)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-signal-amber/70 rounded-full"></div>
              <span>Temporary (auto-release)</span>
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
