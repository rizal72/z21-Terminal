import { useState, useEffect, useRef, useCallback } from 'react';
import ConsistController from './components/ConsistController';
import VideoFeedPanel from './components/VideoFeedPanel';
import MobileMenu from './components/MobileMenu';
import ConsistManagerModal from './components/ConsistManagerModal';
import TrackTelemetryPopover from './components/TrackTelemetryPopover';
import Z21HealthPopover from './components/Z21HealthPopover';
import WebSocketStatsPopover from './components/WebSocketStatsPopover';
import AnalyticsPanel from './components/AnalyticsPanel';
import Notification from './components/Notification';
import { useWebSocket } from './hooks/useWebSocket';
import { useNotification } from './hooks/useNotification.jsx';

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
  const [wakeLockActive, setWakeLockActive] = useState(false); // Wake Lock status
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false); // Mobile hamburger menu
  const [consistManagerOpen, setConsistManagerOpen] = useState(false); // Consist Manager modal (Phase 6B)
  const [analyticsOpen, setAnalyticsOpen] = useState(false); // Analytics dashboard (desktop-only)
  const [editMode, setEditMode] = useState(false); // Gate editor mode
  const [debugMode, setDebugMode] = useState(false); // Debug overlay mode
  const [cvProfileMode, setCvProfileMode] = useState('normal'); // CV Profile mode: 'normal' or 'testing'
  const [trackTelemetryOpen, setTrackTelemetryOpen] = useState(false); // Track telemetry popover
  const [z21HealthOpen, setZ21HealthOpen] = useState(false); // Z21 health popover
  const [wsStatsOpen, setWsStatsOpen] = useState(false); // WebSocket stats popover
  const [telemetryWarnings, setTelemetryWarnings] = useState({ track: false, z21: false }); // Warning indicators

  // Dynamic controllers array (scalable UI with focus management)
  const [controllers, setControllers] = useState([
    { id: 1, type: 'consist', address: 10 },
    { id: 2, type: 'consist', address: 11 },
  ]);
  const [activeControllerId, setActiveControllerId] = useState(1); // Focus-based control
  const lastControllerRef = useRef(null); // Ref for auto-scroll to new controller

  // Notification system
  const { notifications, showNotification } = useNotification();

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
    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
    return `${protocol}//${hostname}:8000`;
  };

  const WS_URL = getWebSocketUrl();
  const API_URL = getApiUrl();
  const { isConnected, lastMessage, sendMessage, stats: wsStats } = useWebSocket(WS_URL);

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
        const backendControllers = lastMessage.controllers;
        console.log('Initial state received:', { consists: backendConsists, locomotives: backendLocomotives, controllers: backendControllers });

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

        // Load controllers configuration from backend
        if (backendControllers) {
          console.log('Loading controllers from backend:', backendControllers);
          setControllers(backendControllers);
          // Set active controller to first one if any
          if (backendControllers.length > 0) {
            setActiveControllerId(backendControllers[0].id);
          }
        }
      } else if (lastMessage.type === 'controllers_update') {
        // Sync controllers from another device
        console.log('Controllers update received:', lastMessage.controllers);
        setControllers(lastMessage.controllers);
      } else if (lastMessage.type === 'z21_status') {
        // Z21 connection status update
        setZ21Online(lastMessage.online);

        // If Z21 goes offline, immediately set track power to OFF
        // (backend will also send consist_update, but this provides immediate feedback)
        if (!lastMessage.online && trackPower) {
          console.log('[Z21] Offline detected - forcing track power OFF');
          setTrackPower(false);
          playPowerSound(false);
        }
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

        // Try to update consists first
        setConsists(prev => {
          const currentConsist = prev[lastMessage.address];
          if (!currentConsist) {
            // Not a consist, will try locomotives next
            return prev;
          }

          return {
            ...prev,
            [lastMessage.address]: {
              ...currentConsist,
              speed: lastMessage.data.speed ?? currentConsist.speed,
              direction: lastMessage.data.direction ?? currentConsist.direction,
              power: lastMessage.data.power ?? currentConsist.power,
              // Update function definitions if provided (for new panel selections)
              functions: lastMessage.data.functions || currentConsist.functions,
              // Update function states from backend (correct key!)
              functionStates: lastMessage.data.functionStates || currentConsist.functionStates || {}
            }
          };
        });

        // Also try to update locomotives (if address is a locomotive)
        setLocomotives(prev => {
          const currentLoco = prev[lastMessage.address];
          if (!currentLoco) {
            // Not a locomotive either (it was a consist handled above)
            return prev;
          }

          return {
            ...prev,
            [lastMessage.address]: {
              ...currentLoco,
              speed: lastMessage.data.speed ?? currentLoco.speed,
              direction: lastMessage.data.direction ?? currentLoco.direction,
              power: lastMessage.data.power ?? currentLoco.power,
              // Update function definitions if provided (for new panel selections)
              functions: lastMessage.data.functions || currentLoco.functions,
              // Update function states from backend (correct key!)
              functionStates: lastMessage.data.functionStates || currentLoco.functionStates || {}
            }
          };
        });
      } else if (lastMessage.type === 'delta_t_update') {
        // Delta T update from tracking daemon
        const consistAddress = lastMessage.consist_address;
        const deltaT = lastMessage.delta_t;
        const timestamp = lastMessage.timestamp;
        const timeStr = lastMessage.time_str; // Pre-calculated elapsed time
        const thresholds = lastMessage.thresholds; // NEW: dynamic thresholds from config
        const adjustLocoAddress = lastMessage.adjust_loco_address; // Which loco is being adjusted
        const adjustSpeed = lastMessage.adjust_speed; // Actual speed sent to adjust loco
        const adjustCorrection = lastMessage.adjust_correction; // Difference from target

        // Update consist with delta_t data (only if changed)
        setConsists(prev => {
          const currentConsist = prev[consistAddress];
          if (!currentConsist) {
            return prev; // Consist not found
          }

          // Check if delta_t actually changed (prevent unnecessary re-renders)
          if (currentConsist.delta_t === deltaT) {
            return prev; // Same value, don't update
          }

          // Detect correction state
          const wasCorrection = currentConsist.adjust_correction && currentConsist.adjust_correction !== 0;
          const nowCorrecting = adjustCorrection && adjustCorrection !== 0;
          const justFinishedCorrecting = wasCorrection && adjustCorrection === 0;
          const correctionChanged = currentConsist.adjust_correction !== adjustCorrection;

          // Show notifications
          if (nowCorrecting) {
            // Auto-compensation active: distinguish between new correction and maintained correction
            const sign = adjustCorrection > 0 ? '+' : '';
            const message = correctionChanged
              ? `Loco ${adjustLocoAddress}: Speed ${sign}${adjustCorrection}%`  // New or changed correction
              : `Loco ${adjustLocoAddress}: still at ${sign}${adjustCorrection}%`;  // Same correction maintained
            showNotification({
              message: message,
              type: 'error',
              duration: 5000
            });
          } else if (justFinishedCorrecting) {
            // SYNCED: Backend reset speeds to equal (adjust_correction: 0 after corrections)
            showNotification({
              message: `Consist ${consistAddress}: SYNCED`,
              type: 'success',
              duration: 5000
            });
          }

          return {
            ...prev,
            [consistAddress]: {
              ...currentConsist,
              delta_t: deltaT,
              delta_t_timestamp: timestamp,
              delta_t_time_str: timeStr, // Pre-calculated elapsed time string
              timing_thresholds: thresholds, // Store thresholds for DeltaTStatsPanel
              adjust_loco_address: adjustLocoAddress, // Compensation info
              adjust_speed: adjustSpeed,
              adjust_correction: adjustCorrection
            }
          };
        });
      }
    }
  }, [lastMessage]);

  const handleSpeedChange = useCallback((address, speed, forward) => {
    sendMessage({
      type: 'set_speed',
      address,
      speed,
      forward
    });
  }, [sendMessage]);

  const handleDirectionChange = useCallback((address, direction) => {
    sendMessage({
      type: 'set_direction',
      address,
      direction
    });
  }, [sendMessage]);

  const handleFunctionToggle = useCallback((address, funcNumber, state) => {
    const message = {
      type: 'set_function',
      address,
      function: funcNumber,
      state
    };
    sendMessage(message);
  }, [sendMessage]);

  const handleEmergencyStop = () => {
    const newPowerState = !trackPower;

    // Update local state immediately for responsive UI
    setTrackPower(newPowerState);

    // Play sound feedback
    playPowerSound(newPowerState);

    // Show notification
    showNotification({
      message: `Track power: ${newPowerState ? 'ON' : 'OFF'}`,
      type: newPowerState ? 'success' : 'warning',
      duration: 2000
    });

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

  // Force repaint when page becomes visible (macOS full screen app switching)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        // Page just became visible (e.g., switching back from another full screen app)
        // Force a full repaint to prevent lazy rendering glitches
        requestAnimationFrame(() => {
          document.body.offsetHeight; // Force reflow
          // Double RAF for Chrome to ensure GPU layers are reconstructed
          requestAnimationFrame(() => {
            document.body.offsetHeight;
          });
        });
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  // Sync debug mode with backend on mount (page reload)
  useEffect(() => {
    fetch(`${API_URL}/api/debug-status`)
      .then(res => res.json())
      .then(data => {
        if (data.debug_visible !== undefined) {
          setDebugMode(data.debug_visible);
        }
      })
      .catch(err => console.error('Failed to fetch debug status:', err));
  }, []);

  // Wake Lock API - Keep screen awake while using the app (iOS/Android)
  const wakeLockRef = useRef(null);

  const requestWakeLock = async () => {
    try {
      if ('wakeLock' in navigator) {
        wakeLockRef.current = await navigator.wakeLock.request('screen');
        setWakeLockActive(true);
        console.log('✅ Wake Lock acquired - screen will stay awake');

        // Re-acquire wake lock if it's released (e.g., when returning to tab)
        wakeLockRef.current.addEventListener('release', () => {
          console.log('⚠️ Wake Lock released');
          setWakeLockActive(false);
        });
      } else {
        console.log('⚠️ Wake Lock API not supported on this browser');
      }
    } catch (err) {
      console.log('❌ Wake Lock request failed:', err.name, err.message);
      setWakeLockActive(false);
    }
  };

  const releaseWakeLock = async () => {
    if (wakeLockRef.current !== null) {
      await wakeLockRef.current.release();
      wakeLockRef.current = null;
      setWakeLockActive(false);
      console.log('Wake Lock released manually');
    }
  };

  useEffect(() => {
    // Try to request wake lock on mount (works on desktop/Android Chrome)
    // Will fail on iOS Safari (requires user interaction) - handled by button
    requestWakeLock();

    // Re-acquire wake lock when page becomes visible again
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && wakeLockRef.current === null && wakeLockActive) {
        requestWakeLock();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Release wake lock on unmount
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      releaseWakeLock();
    };
  }, []);

  // Load CV profile mode on mount
  useEffect(() => {
    fetch(`${API_URL}/api/cv-profile-mode`)
      .then(res => res.json())
      .then(data => {
        setCvProfileMode(data.mode);
        console.log(`🎚️  CV Profile mode loaded: ${data.mode}`);
      })
      .catch(err => console.error('Failed to load CV profile mode:', err));
  }, []);

  // Fetch telemetry periodically to check for warnings
  useEffect(() => {
    const fetchTelemetryWarnings = async () => {
      try {
        const response = await fetch(`${API_URL}/api/z21/telemetry`);
        const data = await response.json();

        if (data.status === 'success') {
          const hasTrackWarnings = data.warnings && data.warnings.length > 0;
          const hasZ21Warnings = data.quality_checks &&
            (data.quality_checks.temperature_high || data.quality_checks.temperature_elevated);

          setTelemetryWarnings({
            track: hasTrackWarnings,
            z21: hasZ21Warnings
          });
        }
      } catch (error) {
        // Silently fail if telemetry unavailable
        console.log('Telemetry fetch failed:', error);
      }
    };

    // Fetch immediately on mount
    fetchTelemetryWarnings();

    // Fetch every 5 seconds
    const interval = setInterval(fetchTelemetryWarnings, 5000);

    return () => clearInterval(interval);
  }, [API_URL]);

  // Global keyboard shortcuts (ESC for emergency stop, TAB to cycle controllers)
  useEffect(() => {
    const handleGlobalKeyPress = (e) => {
      // TAB: cycle through controllers (allow even when dropdown focused)
      if (e.key === 'Tab') {
        e.preventDefault();
        const currentIndex = controllers.findIndex(c => c.id === activeControllerId);
        const nextIndex = (currentIndex + 1) % controllers.length;
        const newController = controllers[nextIndex];
        setActiveControllerId(newController.id);

        // Show notification overlay with selected consist/loco info
        const { type, address } = newController;
        let message = '';

        if (type === 'consist') {
          const consist = consists[address];
          if (consist) {
            // Use short form: "Consist 10" or "Consist 11"
            message = `Consist ${address} selected`;
          }
        } else if (type === 'locomotive') {
          const loco = locomotives[address];
          if (loco) {
            // Use loco name: "Gr.675 017 selected"
            message = `${loco.name} selected`;
          } else {
            message = `Loco ${address} selected`;
          }
        }

        // Trigger notification
        if (message) {
          showNotification({ message, type: 'info', duration: 2000 });
        }

        return;
      }

      // P key to toggle Δt panel in video feed (allow even when dropdown focused)
      if (e.key === 'p' || e.key === 'P') {
        e.preventDefault();
        fetch(`${API_URL}/api/toggle-panel`, { method: 'POST' })
          .then(res => res.json())
          .then(data => {
            const status = data.panel_visible ? 'visible' : 'hidden';
            console.log(`🎛️  Δt panel toggled: ${status}`);
            // Show notification
            showNotification({
              message: `Δt panel: ${data.panel_visible ? 'visible' : 'hidden'}`,
              type: 'info',
              duration: 2000
            });
          })
          .catch(err => console.error('Failed to toggle panel:', err));
        return;
      }

      // D key to toggle debug overlay in video feed (allow even when dropdown focused)
      if (e.key === 'd' || e.key === 'D') {
        e.preventDefault();

        // Sync with backend and use backend state as source of truth
        fetch(`${API_URL}/api/toggle-debug`, { method: 'POST' })
          .then(res => res.json())
          .then(data => {
            const newMode = data.debug_visible;
            setDebugMode(newMode);
            console.log(`🔍 Debug mode toggled: ${newMode ? 'enabled' : 'disabled'}`);
            // Show notification
            showNotification({
              message: `Debug mode: ${newMode ? 'enabled' : 'disabled'}`,
              type: 'info',
              duration: 2000
            });
          })
          .catch(err => console.error('Failed to toggle debug:', err));
        return;
      }

      // T key to toggle CV profile mode (Test ↔ Normal) for ALL locomotives
      if (e.key === 't' || e.key === 'T') {
        e.preventDefault();

        // Save old mode for rollback
        const oldMode = cvProfileMode;
        const newMode = oldMode === 'normal' ? 'testing' : 'normal';

        // Optimistic update (badge changes immediately)
        setCvProfileMode(newMode);

        // Sync with backend (async, notification only on completion)
        fetch(`${API_URL}/api/toggle-cv-profile-mode`, { method: 'POST' })
          .then(res => res.json())
          .then(data => {
            if (data.status === 'success') {
              console.log(`🎚️  CV Profile mode toggled: ${data.mode}`);
              // Sync with backend response (in case it differs from optimistic update)
              setCvProfileMode(data.mode);
              // Show success notification
              showNotification({
                message: data.message,
                type: data.mode === 'testing' ? 'warning' : 'success',
                duration: 3000
              });
            } else {
              console.error('Failed to toggle CV profile mode:', data.message);
              // Rollback on error
              setCvProfileMode(oldMode);
              showNotification({
                message: `Error: ${data.message}`,
                type: 'error',
                duration: 3000
              });
            }
          })
          .catch(err => {
            console.error('Failed to toggle CV profile mode:', err);
            // Rollback on error
            setCvProfileMode(oldMode);
            showNotification({
              message: 'Failed to toggle CV profile mode',
              type: 'error',
              duration: 3000
            });
          });
        return;
      }

      // E key to toggle edit mode in video feed (allow even when dropdown focused, desktop/tablet only)
      if (e.key === 'e' || e.key === 'E') {
        e.preventDefault();
        const isMobile = window.innerWidth < 768;
        if (!isMobile) {
          setEditMode(prev => {
            const newMode = !prev;
            console.log(`🔧 Edit mode toggled: ${newMode ? 'enabled' : 'disabled'}`);
            // Show notification
            showNotification({
              message: `Edit mode: ${newMode ? 'enabled' : 'disabled'}`,
              type: 'info',
              duration: 2000
            });
            return newMode;
          });
        }
        return;
      }

      // For other keys, don't handle if input/select/textarea is focused
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
  }, [trackPower, z21Online, consists, locomotives, controllers, activeControllerId]); // Dependencies

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
        // Build consist label: use names if available, fallback to "lead only" if no rear
        const consistLabel = consist.rear_name
          ? `Consist ${consist.address}: ${consist.lead_name} + ${consist.rear_name}`
          : `Consist ${consist.address}: ${consist.lead_name}`;

        options.push({
          type: 'consist',
          address: consist.address,
          label: consistLabel,
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

  // Controller management functions
  const addController = () => {
    const newId = Math.max(...controllers.map(c => c.id)) + 1;
    const newController = {
      id: newId,
      type: null,  // No selection initially
      address: null
    };

    // Update local state immediately (optimistic update)
    setControllers([...controllers, newController]);
    setActiveControllerId(newId); // Focus on new controller

    // Broadcast to other devices via WebSocket
    sendMessage({
      type: 'add_controller',
      controller: newController
    });

    // Force repaint to cleanup GPU layers (prevents accumulation)
    requestAnimationFrame(() => {
      document.body.offsetHeight; // Force reflow
    });

    // Auto-scroll to new controller after DOM update
    setTimeout(() => {
      if (lastControllerRef.current) {
        lastControllerRef.current.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest'
        });
      }
    }, 100);
  };

  const removeController = (id) => {
    if (controllers.length === 1) {
      // Don't allow removing the last controller
      return;
    }

    // Update local state immediately (optimistic update)
    setControllers(controllers.filter(c => c.id !== id));

    // If removing active controller, switch focus to first remaining
    if (activeControllerId === id) {
      const remaining = controllers.filter(c => c.id !== id);
      if (remaining.length > 0) {
        setActiveControllerId(remaining[0].id);
      }
    }

    // Broadcast to other devices via WebSocket
    sendMessage({
      type: 'remove_controller',
      id
    });

    // Force repaint to cleanup GPU layers and prevent hover lag accumulation
    // This prevents the browser from keeping "ghost" layers from removed panels
    requestAnimationFrame(() => {
      document.body.offsetHeight; // Force reflow
    });
  };

  const updateControllerSelection = (id, type, address) => {
    console.log('updateControllerSelection called:', { id, type, address });

    // Update local state immediately (optimistic update)
    setControllers(controllers.map(c =>
      c.id === id ? { ...c, type, address } : c
    ));

    // Broadcast to other devices via WebSocket
    console.log('Sending update_controller_selection message:', { id, selection: { type, address } });
    sendMessage({
      type: 'update_controller_selection',
      id,
      selection: { type, address }
    });
  };

  const getControllerSelection = (id) => {
    const controller = controllers.find(c => c.id === id);
    return controller ? { type: controller.type, address: controller.address } : null;
  };

  // Virtual Mode toggle handler
  const handleToggleVirtualMode = useCallback((consistAddress, enable) => {
    console.log('toggleVirtualMode:', { consistAddress, enable });

    // Send to backend
    sendMessage({
      type: 'toggle_virtual_mode',
      address: consistAddress,
      enable
    });

    // Optimistic update - backend will broadcast confirmation
    setConsists(prev => {
      const currentConsist = prev[consistAddress];
      if (!currentConsist) return prev;

      return {
        ...prev,
        [consistAddress]: {
          ...currentConsist,
          virtual_mode: enable
        }
      };
    });
  }, [sendMessage]);

  const handleToggleAutoCompensation = useCallback((consistAddress, enable) => {
    console.log('toggleAutoCompensation:', { consistAddress, enable });

    // Send to backend
    sendMessage({
      type: 'toggle_auto_compensation',
      address: consistAddress,
      enable
    });

    // Optimistic update - backend will broadcast confirmation
    setConsists(prev => {
      const currentConsist = prev[consistAddress];
      if (!currentConsist) return prev;

      return {
        ...prev,
        [consistAddress]: {
          ...currentConsist,
          auto_compensation_enabled: enable
        }
      };
    });
  }, [sendMessage]);

  return (
    <div className="min-h-screen bg-control-black grain-overlay">
      {/* Header */}
      <header className="border-b border-control-grey bg-control-dark/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="w-full lg:container lg:mx-auto px-2 sm:px-4 py-2 lg:py-4">
          <div className="flex items-center gap-4">
            {/* Left: Logo + Hamburger (mobile) or Full Title (desktop) */}
            <div className="flex-shrink-0 flex items-center gap-2 md:gap-3">
              {/* Train icon logo - always visible */}
              <i className="fa-solid fa-train text-signal-amber text-2xl md:text-3xl lg:text-4xl" style={{ filter: 'drop-shadow(0 0 8px rgba(255, 149, 0, 0.6))' }}></i>

              {/* Mobile: Hamburger */}
              <button
                onClick={() => setMobileMenuOpen(true)}
                className="md:hidden px-2 py-2 text-track-steel hover:text-signal-amber transition-colors"
                title="Open menu"
              >
                <i className="fa-solid fa-bars text-xl"></i>
              </button>

              {/* Desktop/Tablet: Full title */}
              <div className="hidden md:block">
                <h1 className="text-2xl lg:text-3xl font-display font-bold text-signal-amber text-shadow-glow">
                  z21 Terminal
                </h1>
                <p className="text-xs lg:text-sm font-mono text-track-steel mt-1">
                  DCC Locomotive Controller
                </p>
              </div>
            </div>

            {/* Desktop only: Inline actions */}
            <div className="hidden md:flex items-center gap-3">
              {/* Reload Roster Button */}
              <button
              onClick={handleReloadRoster}
              disabled={reloadingRoster || !isConnected}
              className={`px-2 py-2 md:px-3 bg-control-dark border rounded transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed ${
                reloadSuccess
                  ? 'border-signal-green text-signal-green'
                  : 'border-control-grey text-track-steel hover:border-signal-amber hover:text-signal-amber'
              }`}
              title="Reload roster from JMRI XML files"
            >
              <i className={`fa-solid ${
                reloadingRoster ? 'fa-spinner fa-spin' :
                reloadSuccess ? 'fa-check' :
                'fa-rotate-right'
              } text-base md:text-lg`}></i>
            </button>

              {/* Add Controller Button - desktop only */}
              <button
                onClick={addController}
                disabled={!isConnected}
                className="px-2 py-2 md:px-3 bg-control-dark border border-control-grey rounded hover:border-signal-amber hover:text-signal-amber transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Add controller panel"
              >
                <i className="fa-solid fa-plus text-base md:text-lg"></i>
              </button>

              {/* Consist Manager Button - desktop only (Phase 6B) */}
              <button
                onClick={() => setConsistManagerOpen(true)}
                disabled={!isConnected}
                className="px-2 py-2 md:px-3 bg-control-dark border border-control-grey rounded hover:border-signal-amber hover:text-signal-amber transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Manage consists"
              >
                <i className="fa-solid fa-gears text-base md:text-lg"></i>
              </button>
            </div>

            {/* Spacer */}
            <div className="flex-grow"></div>

            {/* Right: Emergency + Status Icons */}
            <div className="flex items-center gap-2 md:gap-2 lg:gap-3">
              {/* Global Emergency Stop */}
              <button
                onClick={handleEmergencyStop}
                disabled={!z21Online}
                className={`emergency-stop ${!trackPower ? 'active' : ''} disabled:opacity-50 disabled:cursor-not-allowed aspect-square md:aspect-auto md:w-[140px]`}
                title={
                  !z21Online
                    ? 'Z21 offline - Cannot control power'
                    : trackPower
                      ? 'Cut track power (Emergency Stop) - Press ESC'
                      : 'Restore track power - Press ESC'
                }
              >
                <div className="flex items-center justify-center px-2 py-2 md:px-6 md:py-3">
                  {/* Contenuto raggruppato: icona + testo come blocco unico */}
                  <div className="flex items-center gap-2">
                    {trackPower ? (
                      <i className="fa-solid fa-triangle-exclamation text-2xl md:text-3xl"></i>
                    ) : (
                      <i className="fa-solid fa-power-off text-2xl md:text-3xl"></i>
                    )}
                    {/* Testo su tablet/desktop */}
                    <div className="hidden md:flex flex-col items-start text-left h-[44px] justify-center">
                      <span className="uppercase tracking-wider text-sm font-bold w-full text-left leading-tight">
                        {trackPower ? 'Stop All' : 'Restart'}
                      </span>
                      <span className="text-[10px] md:text-xs opacity-70 w-full text-left leading-tight">{trackPower ? <kbd className="pl-0 pr-1 bg-white/10 rounded text-[10px]">ESC</kbd> : <>Power On <kbd className="pl-0 pr-1 bg-white/10 rounded text-[10px]">ESC</kbd></>}</span>
                    </div>
                  </div>
                </div>
              </button>

              {/* Track Telemetry Badge (⚡) - Hover on desktop, click on mobile */}
              <div
                className={`flex items-center gap-2 px-2 py-2 bg-control-dark rounded border transition-all duration-200 ${
                  telemetryWarnings.track
                    ? 'border-amber-500 ring-2 ring-amber-500/50'
                    : 'border-control-grey'
                } ${
                  z21Online ? 'md:hover:border-signal-amber cursor-pointer' : 'opacity-50 cursor-not-allowed'
                }`}
                title={`Track Telemetry${telemetryWarnings.track ? ' - Warning!' : ''}`}
                onMouseEnter={() => {
                  if (z21Online && window.innerWidth >= 768) {
                    setTrackTelemetryOpen(true);
                  }
                }}
                onMouseLeave={() => {
                  if (window.innerWidth >= 768) {
                    setTrackTelemetryOpen(false);
                  }
                }}
                onClick={() => {
                  if (z21Online && window.innerWidth < 768) {
                    setTrackTelemetryOpen(!trackTelemetryOpen);
                  }
                }}
              >
                <i className={`fa-solid fa-bolt text-lg md:text-xl ${trackPower ? 'text-signal-green' : 'text-signal-red'}`}></i>
                <div className="hidden md:block text-xs font-mono w-4">
                  <div className={trackPower ? 'text-signal-green' : 'text-signal-red'}>
                    {trackPower ? 'ON' : 'OFF'}
                  </div>
                </div>
              </div>

              {/* WebSocket Status - Hover on desktop, click on mobile */}
              <div
                className={`flex items-center gap-2 px-2 py-2 bg-control-dark rounded border border-control-grey transition-all duration-200 md:hover:border-signal-amber cursor-pointer`}
                title="WebSocket Connection Statistics"
                onMouseEnter={() => {
                  if (window.innerWidth >= 768) {
                    setWsStatsOpen(true);
                  }
                }}
                onMouseLeave={() => {
                  if (window.innerWidth >= 768) {
                    setWsStatsOpen(false);
                  }
                }}
                onClick={() => {
                  if (window.innerWidth < 768) {
                    setWsStatsOpen(!wsStatsOpen);
                  }
                }}
              >
                <i className={`fa-solid fa-wifi text-lg md:text-xl ${isConnected ? 'text-signal-green' : 'text-signal-red'}`}></i>
                <div className="hidden md:block text-xs font-mono">
                  <div className={isConnected ? 'text-signal-green' : 'text-signal-red'}>
                    WS
                  </div>
                </div>
              </div>

              {/* Z21 Health Badge (🖥️) - Hover on desktop, click on mobile */}
              <div
                className={`flex items-center gap-2 px-2 py-2 bg-control-dark rounded border transition-all duration-200 ${
                  telemetryWarnings.z21
                    ? 'border-amber-500 ring-2 ring-amber-500/50'
                    : 'border-control-grey'
                } ${
                  z21Online ? 'md:hover:border-signal-amber cursor-pointer' : 'opacity-50 cursor-not-allowed'
                }`}
                title={`Z21 System Health${telemetryWarnings.z21 ? ' - Warning!' : ''}`}
                onMouseEnter={() => {
                  if (z21Online && window.innerWidth >= 768) {
                    setZ21HealthOpen(true);
                  }
                }}
                onMouseLeave={() => {
                  if (window.innerWidth >= 768) {
                    setZ21HealthOpen(false);
                  }
                }}
                onClick={() => {
                  if (z21Online && window.innerWidth < 768) {
                    setZ21HealthOpen(!z21HealthOpen);
                  }
                }}
              >
                <i className={`fa-solid fa-server text-lg md:text-xl ${z21Online ? 'text-signal-green' : 'text-signal-red'}`}></i>
                <div className="hidden md:block text-xs font-mono">
                  <div className={z21Online ? 'text-signal-green' : 'text-signal-red'}>
                    z21
                  </div>
                </div>
              </div>

              {/* CV Profile Mode Badge (🎚️) - Click to toggle Test/Normal */}
              <button
                className={`flex items-center gap-2 px-2 py-2 bg-control-dark rounded border transition-all duration-200 ${
                  cvProfileMode === 'testing'
                    ? 'border-amber-500 ring-2 ring-amber-500/50'
                    : 'border-control-grey'
                } ${
                  z21Online ? 'md:hover:border-signal-amber cursor-pointer' : 'opacity-50 cursor-not-allowed'
                }`}
                title={`Test Mode: ${cvProfileMode === 'testing' ? 'ACTIVE (zero momentum) - Press T' : 'OFF (normal) - Press T'}`}
                onClick={() => {
                  if (z21Online) {
                    const event = new KeyboardEvent('keydown', { key: 'T', bubbles: true });
                    window.dispatchEvent(event);
                  }
                }}
                disabled={!z21Online}
              >
                <i className={`fa-solid ${cvProfileMode === 'testing' ? 'fa-flask-vial' : 'fa-check-circle'} text-lg md:text-xl ${cvProfileMode === 'testing' ? 'text-amber-500' : 'text-signal-green'}`}></i>
                <div className="hidden md:block text-xs font-mono">
                  <div className={cvProfileMode === 'testing' ? 'text-amber-500' : 'text-signal-green'}>
                    Test
                  </div>
                </div>
              </button>

              {/* Analytics Dashboard (📊) - Desktop-only (1024px+) */}
              <button
                className="hidden lg:flex items-center gap-2 px-2 py-2 bg-control-dark rounded border border-control-grey transition-all duration-200 md:hover:border-signal-amber cursor-pointer"
                title="Analytics Dashboard (Desktop)"
                onClick={() => setAnalyticsOpen(true)}
              >
                <i className="fa-solid fa-chart-line text-lg md:text-xl text-blue-500"></i>
                <div className="hidden md:block text-xs font-mono">
                  <div className="text-blue-400">
                    Analytics
                  </div>
                </div>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <MobileMenu
          onClose={() => setMobileMenuOpen(false)}
          onConsistManager={() => {
            setMobileMenuOpen(false);
            setConsistManagerOpen(true);
          }}
          onAddController={() => {
            setMobileMenuOpen(false);
            addController();
          }}
          onReloadRoster={() => {
            setMobileMenuOpen(false);
            handleReloadRoster();
          }}
          onWakeLock={() => {
            setMobileMenuOpen(false);
            if (wakeLockActive) {
              releaseWakeLock();
            } else {
              requestWakeLock();
            }
          }}
          onAnalytics={() => {
            setMobileMenuOpen(false);
            setAnalyticsOpen(true);
          }}
          wakeLockActive={wakeLockActive}
          reloadingRoster={reloadingRoster}
        />
      )}

      {/* Consist Manager Modal (Phase 6B) */}
      {consistManagerOpen && (
        <ConsistManagerModal
          onClose={() => setConsistManagerOpen(false)}
        />
      )}

      {/* Main content */}
      <main className="w-full lg:container lg:mx-auto px-2 sm:px-4 py-8">
        {/* Connection warning */}
        {!isConnected && (
          <div className="mb-6 p-4 bg-signal-red/20 border border-signal-red/50 rounded-lg overflow-hidden">
            <div className="flex items-center gap-3">
              <i className="fa-solid fa-wifi text-2xl text-signal-red flex-shrink-0" style={{ transform: 'scaleX(-1)' }}></i>
              <div className="min-w-0 flex-1">
                <div className="font-display font-semibold text-signal-red">
                  Backend Disconnected
                </div>
                <div className="hidden md:block text-sm text-white/70 mt-1 break-all">
                  Attempting to reconnect to WebSocket server at {WS_URL}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Video Feed Panel - Collapsible */}
        <VideoFeedPanel
          apiUrl={API_URL}
          editMode={editMode}
          onEditModeChange={setEditMode}
          debugMode={debugMode}
          onDebugModeChange={setDebugMode}
        />

        {/* Analytics Dashboard (desktop-only) */}
        <AnalyticsPanel
          isOpen={analyticsOpen}
          onClose={() => setAnalyticsOpen(false)}
        />

        {/* Controllers grid - Dynamic and scalable */}
        <div className="controllers-grid grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6 mb-8">
          {controllers.map((controller, index) => {
            const selection = getControllerSelection(controller.id);
            const isActive = activeControllerId === controller.id;
            const isLast = index === controllers.length - 1;

            return (
              <div
                key={controller.id}
                ref={isLast ? lastControllerRef : null}
                className="animate-fade-in"
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <ConsistController
                  item={selection ? getSelectedItem(selection) : null}
                  selection={selection || { type: null, address: null }}
                  rosterOptions={getRosterOptions()}
                  trackPower={trackPower}
                  controllerNumber={index + 1}
                  isActive={isActive}
                  canRemove={controllers.length > 1}
                  onSelectionChange={(newSelection) => updateControllerSelection(controller.id, newSelection.type, newSelection.address)}
                  onRemove={() => removeController(controller.id)}
                  onFocus={() => setActiveControllerId(controller.id)}
                  onSpeedChange={handleSpeedChange}
                  onDirectionChange={handleDirectionChange}
                  onFunctionToggle={handleFunctionToggle}
                  onToggleVirtualMode={handleToggleVirtualMode}
                  onToggleAutoCompensation={handleToggleAutoCompensation}
                  showNotification={showNotification}
                />
              </div>
            );
          })}
        </div>

        {/* Info footer - shows active controllers */}
        <div className="text-center text-track-steel text-sm font-mono">
          <div className="flex items-center justify-center gap-8 flex-wrap">
            {controllers.map((controller, index) => {
              const { type, address } = controller;
              const items = [];

              // Add separator
              if (index > 0) {
                items.push(
                  <div key={`sep-${controller.id}`} className="w-px h-4 bg-control-grey"></div>
                );
              }

              // Build display text
              let displayText = '';

              if (!type || !address) {
                displayText = `Controller ${controller.id}: Empty`;
              } else if (type === 'consist') {
                const consist = consists[address];
                if (consist && consist.locomotives && consist.locomotives.length >= 2) {
                  const names = consist.locomotives.map(l => l.name).join(' + ');
                  displayText = `Consist ${address}: ${names}`;
                } else {
                  displayText = `Consist ${address}`;
                }
              } else if (type === 'locomotive') {
                const loco = locomotives[address];
                displayText = loco ? `Loco ${address}: ${loco.name}` : `Loco ${address}`;
              }

              items.push(
                <div key={controller.id}>{displayText}</div>
              );

              return items;
            })}
          </div>
          <div className="mt-2 text-xs text-white/30">
            BiancAlice Railway Layout • Z21 White Edition
          </div>
        </div>
      </main>

      {/* Telemetry Popovers (Phase 9) */}
      <TrackTelemetryPopover
        isOpen={trackTelemetryOpen}
        onClose={() => setTrackTelemetryOpen(false)}
        apiUrl={API_URL}
        isHover={window.innerWidth >= 768}
      />
      <Z21HealthPopover
        isOpen={z21HealthOpen}
        onClose={() => setZ21HealthOpen(false)}
        apiUrl={API_URL}
        isHover={window.innerWidth >= 768}
      />
      <WebSocketStatsPopover
        isOpen={wsStatsOpen}
        onClose={() => setWsStatsOpen(false)}
        stats={wsStats}
        isConnected={isConnected}
        isHover={window.innerWidth >= 768}
      />

      {/* Notification overlay (generic system) */}
      <Notification notifications={notifications} />
    </div>
  );
}

export default App;
