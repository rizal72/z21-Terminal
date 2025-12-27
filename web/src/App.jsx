import { useState, useEffect } from 'react';
import ConsistController from './components/ConsistController';
import { useWebSocket } from './hooks/useWebSocket';

// Mock data for development - will be replaced with real data from backend
const MOCK_CONSISTS = {
  10: {
    address: 10,
    trackName: 'INTERNAL TRACK',
    lead: 'Gr.675 017',
    rear: 'D645 014',
    speed: 0,
    direction: 'forward',
    functions: [
      { number: 0, label: 'Light', lockable: true },
      { number: 1, label: 'Sound', lockable: true },
      { number: 2, label: 'Whistle L', lockable: false },
      { number: 3, label: 'Whistle S', lockable: false },
      { number: 5, label: 'Air Pump', lockable: true },
      { number: 6, label: 'Brake', lockable: false },
      { number: 7, label: 'Horn', lockable: false },
      { number: 8, label: 'Bell', lockable: true },
    ]
  },
  11: {
    address: 11,
    trackName: 'EXTERNAL TRACK',
    lead: 'E656 239',
    rear: 'D445 1140',
    speed: 0,
    direction: 'forward',
    functions: [
      { number: 0, label: 'Light', lockable: true },
      { number: 1, label: 'Sound', lockable: true },
      { number: 2, label: 'Whistle', lockable: false },
      { number: 3, label: 'Horn', lockable: false },
      { number: 4, label: 'Compressor', lockable: true },
      { number: 5, label: 'Brake', lockable: false },
    ]
  }
};

function App() {
  const [consists, setConsists] = useState(MOCK_CONSISTS);
  const [locomotives, setLocomotives] = useState({});
  const [trackPower, setTrackPower] = useState(true);
  const [z21Online, setZ21Online] = useState(false); // Z21 connection status
  const [reloadingRoster, setReloadingRoster] = useState(false);
  const [reloadSuccess, setReloadSuccess] = useState(false);

  // Selected items for each controller (left and right)
  const [selectedLeft, setSelectedLeft] = useState({ type: 'consist', address: 10 });
  const [selectedRight, setSelectedRight] = useState({ type: 'consist', address: 11 });

  // Auto-detect WebSocket URL based on current hostname
  const getWebSocketUrl = () => {
    if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
    const hostname = window.location.hostname;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${hostname}:8000/ws`;
  };

  const getApiUrl = () => {
    if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
    const hostname = window.location.hostname;
    return `http://${hostname}:8000`;
  };

  const WS_URL = getWebSocketUrl();
  const API_URL = getApiUrl();
  const { isConnected, lastMessage, sendMessage } = useWebSocket(WS_URL);

  // Audio feedback for power changes using Web Audio API
  const playPowerSound = (powerOn) => {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      if (powerOn) {
        // Power ON: ascending tone (happy sound)
        oscillator.frequency.setValueAtTime(400, audioContext.currentTime);
        oscillator.frequency.exponentialRampToValueAtTime(800, audioContext.currentTime + 0.1);
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.15);
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.15);
      } else {
        // Power OFF: descending tone (warning sound)
        oscillator.frequency.setValueAtTime(600, audioContext.currentTime);
        oscillator.frequency.exponentialRampToValueAtTime(200, audioContext.currentTime + 0.2);
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.25);
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.25);
      }

      // Cleanup
      setTimeout(() => {
        audioContext.close();
      }, 500);
    } catch (err) {
      console.log('Audio not available:', err);
    }
  };

  // Handle incoming WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      // Update consist state based on message type
      if (lastMessage.type === 'initial_state') {
        // Load initial state from backend
        const backendConsists = lastMessage.consists;
        const backendLocomotives = lastMessage.locomotives;
        console.log('Initial state received:', { consists: backendConsists, locomotives: backendLocomotives });

        if (backendConsists) {
          // Initialize functionStates from backend (uses actual Z21 state)
          const consistsWithStates = {};
          let initialPower = true; // Default

          Object.keys(backendConsists).forEach(key => {
            const consist = backendConsists[key];

            // Get track power from first consist (global state)
            if (typeof consist.power !== 'undefined') {
              initialPower = consist.power;
            }

            const functionStates = {};
            if (Array.isArray(consist.functions)) {
              consist.functions.forEach(fn => {
                // Use actual state from backend, or default to false
                functionStates[fn.number] = consist.functionStates?.[fn.number] || false;
              });
            }
            consistsWithStates[key] = {
              ...consist,
              functionStates
            };
          });

          // Set global track power from backend
          setTrackPower(initialPower);
          setConsists(consistsWithStates);
        }

        if (backendLocomotives) {
          setLocomotives(backendLocomotives);
        }

        // Set Z21 connection status from backend
        if (typeof lastMessage.z21Online !== 'undefined') {
          setZ21Online(lastMessage.z21Online);
        }

        // Track power can also be in top-level initial_state
        if (typeof lastMessage.trackPower !== 'undefined') {
          setTrackPower(lastMessage.trackPower);
        }
      } else if (lastMessage.type === 'z21_status') {
        // Z21 connection status update
        setZ21Online(lastMessage.online);
      } else if (lastMessage.type === 'consist_update') {
        // Update global track power state if changed
        if (typeof lastMessage.data.power !== 'undefined') {
          setTrackPower(prev => {
            const newPower = lastMessage.data.power;
            // Play sound only if power state changed
            if (prev !== newPower) {
              playPowerSound(newPower);
            }
            return newPower;
          });
        }

        setConsists(prev => {
          const currentConsist = prev[lastMessage.address];
          if (!currentConsist) {
            console.warn('Consist not found:', lastMessage.address);
            return prev;
          }

          return {
            ...prev,
            [lastMessage.address]: {
              ...currentConsist,
              speed: lastMessage.data.speed ?? currentConsist.speed,
              direction: lastMessage.data.direction ?? currentConsist.direction,
              power: lastMessage.data.power ?? currentConsist.power,
              // Update function states from backend
              functionStates: lastMessage.data.functions || currentConsist.functionStates || {}
            }
          };
        });
      }
    }
  }, [lastMessage]);

  const handleSpeedChange = (address, speed, forward) => {
    sendMessage({
      type: 'set_speed',
      address,
      speed,
      forward
    });
  };

  const handleDirectionChange = (address, direction) => {
    sendMessage({
      type: 'set_direction',
      address,
      direction
    });
  };

  const handleFunctionToggle = (address, funcNumber, state) => {
    const message = {
      type: 'set_function',
      address,
      function: funcNumber,
      state
    };
    sendMessage(message);
  };

  const handleEmergencyStop = () => {
    const newPowerState = !trackPower;

    // Update local state immediately for responsive UI
    setTrackPower(newPowerState);

    // Play sound feedback
    playPowerSound(newPowerState);

    // Send to backend
    sendMessage({
      type: 'emergency_stop',
      powerOn: newPowerState
    });

    // If turning power ON, send speed=0 to all consists/locomotives
    // to prevent them from restarting at previous speed
    if (newPowerState) {
      // Wait a bit for track power to stabilize, then reset speeds
      setTimeout(() => {
        // Reset all consists to speed 0
        Object.keys(consists).forEach(address => {
          sendMessage({
            type: 'set_speed',
            address: parseInt(address),
            speed: 0,
            forward: true
          });
        });

        // Reset all standalone locomotives to speed 0
        Object.values(locomotives).forEach(loco => {
          if (!loco.in_consist) {
            sendMessage({
              type: 'set_speed',
              address: loco.address,
              speed: 0,
              forward: true
            });
          }
        });
      }, 100); // 100ms delay for Z21 to power up
    }
  };

  // Global keyboard shortcut for Emergency Stop (ESC key)
  useEffect(() => {
    const handleGlobalKeyPress = (e) => {
      // Only handle if no input/select/textarea is focused
      if (document.activeElement.tagName === 'INPUT' ||
          document.activeElement.tagName === 'TEXTAREA' ||
          document.activeElement.tagName === 'SELECT') {
        return;
      }

      // ESC key for emergency stop toggle
      if (e.key === 'Escape') {
        e.preventDefault();
        // Only allow emergency stop if Z21 is online
        if (z21Online) {
          handleEmergencyStop();
        } else {
          console.log('ESC blocked: Z21 is offline');
        }
      }
    };

    window.addEventListener('keydown', handleGlobalKeyPress);
    return () => window.removeEventListener('keydown', handleGlobalKeyPress);
  }, [trackPower, z21Online, consists, locomotives]); // Dependencies for handleEmergencyStop

  // Reload roster from JMRI without restarting backend
  const handleReloadRoster = async () => {
    if (reloadingRoster) return; // Prevent double-click

    setReloadingRoster(true);
    setReloadSuccess(false);

    try {
      const response = await fetch(`${API_URL}/api/reload-roster`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.status === 'success') {
        console.log('✅ Roster reloaded:', data);
        setReloadSuccess(true);

        // Hide success indicator after 3 seconds
        setTimeout(() => {
          setReloadSuccess(false);
        }, 3000);
      } else {
        console.error('❌ Roster reload failed:', data.message);
        alert(`Failed to reload roster: ${data.message}`);
      }
    } catch (error) {
      console.error('❌ Error reloading roster:', error);
      alert(`Error reloading roster: ${error.message}`);
    } finally {
      setReloadingRoster(false);
    }
  };

  // Get selected item (consist or locomotive) for a controller
  const getSelectedItem = (selection) => {
    if (selection.type === 'consist') {
      return consists[selection.address];
    } else {
      return locomotives[selection.address];
    }
  };

  // Build options list for dropdown
  const getRosterOptions = () => {
    const options = [];

    // Add consists
    Object.values(consists).forEach(consist => {
      if (consist) {
        options.push({
          type: 'consist',
          address: consist.address,
          label: `Consist ${consist.address}: ${consist.lead} + ${consist.rear}`,
          trackName: consist.trackName
        });
      }
    });

    // Add locomotives
    Object.values(locomotives).forEach(loco => {
      if (loco) {
        const inConsistWarning = loco.in_consist ? ` (in consist ${loco.in_consist} - functions only)` : '';
        options.push({
          type: 'locomotive',
          address: loco.address,
          label: `Loco ${loco.address}: ${loco.name}${inConsistWarning}`,
          inConsist: loco.in_consist
        });
      }
    });

    return options;
  };

  return (
    <div className="min-h-screen bg-control-black grain-overlay">
      {/* Header */}
      <header className="border-b border-control-grey bg-control-dark/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="w-full lg:container lg:mx-auto px-3 py-2 md:px-4 lg:py-4">
          <div className="flex items-center gap-2 md:gap-4">
            {/* Left: Title */}
            <div className="flex-shrink-0">
              {/* Mobile: solo "z21" */}
              <h1 className="text-lg md:text-2xl lg:text-3xl font-display font-bold text-signal-amber text-shadow-glow md:hidden">
                z21
              </h1>
              {/* Tablet/Desktop: titolo completo */}
              <div className="hidden md:block">
                <h1 className="text-2xl lg:text-3xl font-display font-bold text-signal-amber text-shadow-glow">
                  z21 Terminal
                </h1>
                <p className="text-xs lg:text-sm font-mono text-track-steel mt-1">
                  DCC Locomotive Controller
                </p>
              </div>
            </div>

            {/* Reload Roster Button */}
            <button
              onClick={handleReloadRoster}
              disabled={reloadingRoster || !isConnected}
              className={`px-2 md:px-4 py-2 bg-control-dark border rounded transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed ${
                reloadSuccess
                  ? 'border-signal-green text-signal-green'
                  : 'border-control-grey text-track-steel hover:border-signal-amber hover:text-signal-amber'
              }`}
              title="Reload roster from JMRI XML files"
            >
              <div className="flex items-center gap-2">
                <i className={`fa-solid ${
                  reloadingRoster ? 'fa-spinner fa-spin' :
                  reloadSuccess ? 'fa-check' :
                  'fa-rotate-right'
                } text-base md:text-lg`}></i>
                <span className="hidden lg:inline text-xs font-mono uppercase tracking-wider">
                  {reloadingRoster ? 'Reloading...' : reloadSuccess ? 'Reloaded!' : 'Reload'}
                </span>
              </div>
            </button>

            {/* Spacer */}
            <div className="flex-grow"></div>

            {/* Right: Emergency + Status Icons */}
            <div className="flex items-center gap-2 md:gap-3">
              {/* Global Emergency Stop */}
              <button
                onClick={handleEmergencyStop}
                disabled={!z21Online}
                className={`emergency-stop ${!trackPower ? 'active' : ''} disabled:opacity-50 disabled:cursor-not-allowed`}
                title={
                  !z21Online
                    ? 'Z21 offline - Cannot control power'
                    : trackPower
                      ? 'Cut track power (Emergency Stop) - Press ESC'
                      : 'Restore track power - Press ESC'
                }
              >
                <div className="flex items-center gap-1.5 md:gap-3 px-4 md:px-6 py-2 md:py-3">
                  {trackPower ? (
                    <i className="fa-solid fa-triangle-exclamation text-lg md:text-2xl"></i>
                  ) : (
                    <i className="fa-solid fa-power-off text-lg md:text-2xl"></i>
                  )}
                  <div className="flex flex-col items-start">
                    <span className="uppercase tracking-wider text-xs md:text-sm font-bold">
                      {trackPower ? 'Emergency' : 'Restart'}
                    </span>
                    <span className="text-[10px] md:text-xs opacity-70 hidden md:block">
                      {trackPower ? 'Stop All' : 'Power On'} <kbd className="ml-1 px-1 bg-white/10 rounded text-[10px]">ESC</kbd>
                    </span>
                  </div>
                </div>
              </button>

              {/* Track Power Status */}
              <div className="flex items-center gap-2 px-2 md:px-3 py-2 bg-control-dark border border-control-grey rounded">
                <i className={`fa-solid fa-bolt text-lg md:text-xl ${trackPower ? 'text-signal-green' : 'text-signal-red'}`}></i>
                <div className="hidden md:block text-xs font-mono">
                  <div className={trackPower ? 'text-signal-green' : 'text-signal-red'}>
                    {trackPower ? 'ON' : 'OFF'}
                  </div>
                </div>
              </div>

              {/* WebSocket Status */}
              <div className="flex items-center gap-2 px-2 md:px-3 py-2 bg-control-dark border border-control-grey rounded">
                <i className={`fa-solid fa-wifi text-lg md:text-xl ${isConnected ? 'text-signal-green' : 'text-signal-red'}`}></i>
                <div className="hidden md:block text-xs font-mono">
                  <div className={isConnected ? 'text-signal-green' : 'text-signal-red'}>
                    WS
                  </div>
                </div>
              </div>

              {/* Z21 Status */}
              <div className="flex items-center gap-2 px-2 md:px-3 py-2 bg-control-dark border border-control-grey rounded">
                <i className={`fa-solid fa-server text-lg md:text-xl ${z21Online ? 'text-signal-green' : 'text-signal-red'}`}></i>
                <div className="hidden md:block text-xs font-mono">
                  <div className={z21Online ? 'text-signal-green' : 'text-signal-red'}>
                    z21
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="w-full lg:container lg:mx-auto px-0 sm:px-4 py-8">
        {/* Connection warning */}
        {!isConnected && (
          <div className="mb-6 p-4 bg-signal-red/20 border border-signal-red/50 rounded-lg">
            <div className="flex items-center gap-3">
              <i className="fa-solid fa-wifi text-2xl text-signal-red" style={{ transform: 'scaleX(-1)' }}></i>
              <div>
                <div className="font-display font-semibold text-signal-red">
                  Backend Disconnected
                </div>
                <div className="text-sm text-white/70 mt-1">
                  Attempting to reconnect to WebSocket server at {WS_URL}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Controllers grid */}
        <div className="controllers-grid grid lg:grid-cols-2 gap-0 lg:gap-6 mb-8">
          <div className="animate-fade-in" style={{ animationDelay: '0.1s' }}>
            <ConsistController
              item={getSelectedItem(selectedLeft)}
              selection={selectedLeft}
              rosterOptions={getRosterOptions()}
              trackPower={trackPower}
              controllerNumber={1}
              onSelectionChange={setSelectedLeft}
              onSpeedChange={handleSpeedChange}
              onDirectionChange={handleDirectionChange}
              onFunctionToggle={handleFunctionToggle}
            />
          </div>

          <div className="animate-fade-in" style={{ animationDelay: '0.2s' }}>
            <ConsistController
              item={getSelectedItem(selectedRight)}
              selection={selectedRight}
              rosterOptions={getRosterOptions()}
              trackPower={trackPower}
              controllerNumber={2}
              onSelectionChange={setSelectedRight}
              onSpeedChange={handleSpeedChange}
              onDirectionChange={handleDirectionChange}
              onFunctionToggle={handleFunctionToggle}
            />
          </div>
        </div>

        {/* Info footer */}
        <div className="text-center text-track-steel text-sm font-mono">
          <div className="flex items-center justify-center gap-8">
            <div>Consist 10: Gr.675 017 + D645 014</div>
            <div className="w-px h-4 bg-control-grey"></div>
            <div>Consist 11: E656 239 + D445 1140</div>
          </div>
          <div className="mt-2 text-xs text-white/30">
            BiancAlice Railway Layout • Z21 White Edition
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
