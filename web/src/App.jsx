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

  // Selected items for each controller (left and right)
  const [selectedLeft, setSelectedLeft] = useState({ type: 'consist', address: 10 });
  const [selectedRight, setSelectedRight] = useState({ type: 'consist', address: 11 });

  const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
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
      console.log('Received message:', lastMessage);

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
      } else if (lastMessage.type === 'consist_update') {
        console.log('Consist update:', lastMessage.address, lastMessage.data);

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
    console.log(`Speed change: consist ${address}, speed ${speed}, forward ${forward}`);
    sendMessage({
      type: 'set_speed',
      address,
      speed,
      forward
    });
  };

  const handleDirectionChange = (address, direction) => {
    console.log(`Direction change: consist ${address}, direction ${direction}`);
    sendMessage({
      type: 'set_direction',
      address,
      direction
    });
  };

  const handleFunctionToggle = (address, funcNumber, state) => {
    console.log(`Function toggle: consist ${address}, F${funcNumber} = ${state}`);
    const message = {
      type: 'set_function',
      address,
      function: funcNumber,
      state
    };
    console.log('Sending WebSocket message:', message);
    const sent = sendMessage(message);
    console.log('Message sent:', sent);
  };

  const handleEmergencyStop = () => {
    const newPowerState = !trackPower;
    console.log(`Emergency stop: power ${newPowerState ? 'ON' : 'OFF'}`);

    // Update local state immediately for responsive UI
    setTrackPower(newPowerState);

    // Play sound feedback
    playPowerSound(newPowerState);

    // Send to backend
    sendMessage({
      type: 'emergency_stop',
      powerOn: newPowerState
    });
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
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-display font-bold text-signal-amber text-shadow-glow">
                z21-Terminal
              </h1>
              <p className="text-sm text-track-steel font-mono mt-1">
                DCC Locomotive Control Dashboard
              </p>
            </div>
            <div className="flex items-center gap-4">
              {/* Track Power Status */}
              <div className="flex items-center gap-2 px-4 py-2 bg-control-dark border border-control-grey rounded">
                <div className={`status-indicator ${trackPower ? 'on' : 'off'}`}></div>
                <div className="text-xs font-mono">
                  <div className={trackPower ? 'text-signal-green' : 'text-signal-red'}>
                    TRACK POWER {trackPower ? 'ON' : 'OFF'}
                  </div>
                </div>
              </div>

              {/* Global Emergency Stop */}
              <button
                onClick={handleEmergencyStop}
                className={`emergency-stop ${!trackPower ? 'active' : ''}`}
                title={trackPower ? 'Cut track power (Emergency Stop)' : 'Restore track power'}
              >
                <div className="flex items-center gap-3 px-6 py-3">
                  {trackPower ? (
                    <i className="fa-solid fa-triangle-exclamation text-2xl"></i>
                  ) : (
                    <i className="fa-solid fa-power-off text-2xl"></i>
                  )}
                  <div className="flex flex-col items-start">
                    <span className="uppercase tracking-wider text-sm font-bold">
                      {trackPower ? 'Emergency' : 'Restart'}
                    </span>
                    <span className="text-xs opacity-70">
                      {trackPower ? 'Stop All' : 'Power On'}
                    </span>
                  </div>
                </div>
              </button>

              {/* Connection Status */}
              <div className="flex items-center gap-3">
                <div className={`status-indicator ${isConnected ? 'on' : 'off'}`}></div>
                <div className="text-right">
                  <div className="text-xs font-mono text-track-steel">
                    {isConnected ? 'Connected' : 'Disconnected'}
                  </div>
                  <div className="text-xs font-mono text-white/50">
                    Z21: 192.168.1.111
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="container mx-auto px-4 py-8">
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
        <div className="grid lg:grid-cols-2 gap-6 mb-8">
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
