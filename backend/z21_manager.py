"""
Z21Manager - Wrapper per la libreria z21.py con gestione stato consist

REFACTOR HISTORY:
- 2025-01-03: config.json structure refactored (see docs/CONFIG_REFACTOR.md)
  - Hierarchical structure: debug → consists → gates → tracking
  - Consolidated reference_locos inside each consist
  - Grouped settings: tracking.fps, tracking.timing_thresholds

FUTURE CONSIDERATION (see docs/CONFIG_REFACTOR.md):
Potential split into config.json (static) + state.json (runtime).
Currently consolidated for simplicity. Revisit if state management becomes complex.
"""
import sys
import json
from pathlib import Path

# Add scripts directory to path per importare z21.py
scripts_dir = Path(__file__).parent.parent / 'scripts'
sys.path.insert(0, str(scripts_dir))

from z21 import Z21
from config_loader import load_config, save_config
from log_colors import log, colorize_status


class Z21Manager:
    """
    Manager per gestire connessioni Z21 e stato consist
    """

    def __init__(self, z21_ip='192.168.1.111', verbose=False, reference_locos=None, timing_thresholds=None, debug_enabled=False, config_path=None):
        """
        Inizializza Z21Manager

        Args:
            z21_ip (str): Indirizzo IP della Z21
            verbose (bool): Modalità verbose per debug
            reference_locos (dict): Reference loco strategy config from config.json
            timing_thresholds (dict): Timing thresholds config {'normal': 1.0, 'warning': 1.5}
            debug_enabled (bool): Debug mode for verbose logging
            config_path (Path): Path to config.json for persisting virtual_mode state
        """
        self.z21_ip = z21_ip
        self.verbose = verbose
        self.debug_enabled = debug_enabled
        self.z21 = None
        self.config_path = config_path or (Path(__file__).parent.parent / 'config.json')
        self.consist_state = {}  # {address: {'speed': 0, 'direction': 'forward', 'power': True, 'functions': {}}}
        self.persisted_state = self._load_persisted_state()  # Load virtual_mode from file
        self.reference_locos = reference_locos or {}  # Reference loco strategy from config
        self.timing_thresholds = timing_thresholds or {'normal': 1.0, 'warning': 1.5}  # Timing thresholds from config
        self.overflow_warnings = {}  # Track overflow occurrences for CV adjustment warnings {address: count}

    def connect(self):
        """Connetti alla Z21"""
        try:
            self.z21 = Z21(ip=self.z21_ip, verbose=self.verbose)
            if self.verbose:
                print(f"Connected to Z21 at {self.z21_ip}")
            return True
        except Exception as e:
            print(f"Error connecting to Z21: {e}")
            return False

    def disconnect(self):
        """Disconnetti dalla Z21"""
        if self.z21:
            self.z21.close()
            self.z21 = None

    def initialize_consist(self, address, data):
        """
        Inizializza stato consist

        Args:
            address (int): DCC address del consist
            data (dict): Dati consist con array locomotives
        """
        # Load virtual_mode and auto_compensation_enabled from persisted state if available
        persisted = self.persisted_state.get(str(address), {})
        virtual_mode = persisted.get('virtual_mode', False)
        auto_compensation_enabled = persisted.get('auto_compensation_enabled', virtual_mode)  # Default to virtual_mode if not saved

        self.consist_state[address] = {
            'address': address,
            'locomotives': data.get('locomotives', []),  # Array: [lead, rear1, rear2, ...]
            'speed': 0,
            'direction': 'forward',
            'power': True,
            'functions': {},  # {0: False, 1: False, ...}
            'virtual_mode': virtual_mode,  # Load from persisted state
            'auto_compensation_enabled': auto_compensation_enabled,  # Load from persisted state (or default to virtual_mode)
            'delta_t': None,  # NEW: Latest dT from tracking daemon (for display only)
            'delta_t_timestamp': None,  # NEW: When dT was last updated
            'speed_actual_adjust': 0,  # NEW: Incremental compensated speed for adjust loco
            'compensation_accumulated': 0,  # NEW: Tracks total compensation applied (signed integer)
            'decay_applied': False  # NEW: One-shot decay flag (reset on new CRITICAL compensation)
        }

        if virtual_mode:
            if self.debug_enabled:
                log('[INIT]', f"Consist {address}: Restored Virtual Mode from saved state")

        # Initialize function states
        for fn in data.get('functions', []):
            self.consist_state[address]['functions'][fn['number']] = False

        # Sync initial state from Z21 (read current function states from lead loco)
        if self.z21:
            locomotives = data.get('locomotives', [])
            if locomotives:
                lead_addr = locomotives[0]['address']  # First in array = lead
                try:
                    loco_info = self.z21.get_loco_info(lead_addr)
                    if loco_info and 'functions' in loco_info:
                        # Update function states from actual locomotive
                        for fn_num, fn_state in loco_info['functions'].items():
                            if fn_num in self.consist_state[address]['functions']:
                                self.consist_state[address]['functions'][fn_num] = fn_state
                        if self.debug_enabled:
                            log('[SYNC]', f"Synced functions for consist {address} from lead loco {lead_addr}")
                except Exception as e:
                    if self.debug_enabled:
                        log('[WARN]', f"Could not sync functions for consist {address}: {e}")

    def get_consist_state(self, address):
        """Get current state of a consist"""
        return self.consist_state.get(address, {})

    def get_all_consists_state(self):
        """Get state of all consists"""
        return self.consist_state

    def set_speed(self, address, speed, forward=True, is_auto_compensation=False):
        """
        Imposta velocità locomotiva/consist

        Args:
            address (int): DCC address
            speed (int): Velocità 0-126
            forward (bool): True per avanti, False per indietro
            is_auto_compensation (bool): True se chiamato da auto-compensation (incremental), False se chiamato da user (reset)
        """
        if not self.z21:
            return False

        try:
            # Check if this is a consist in Virtual Mode
            if address in self.consist_state:
                consist = self.consist_state[address]
                is_virtual = consist.get('virtual_mode', False)
                locomotives = consist.get('locomotives', [])

                if is_virtual and len(locomotives) >= 2:
                    # Virtual Mode: control locomotives separately with dT compensation
                    loco_lead_addr = locomotives[0]['address']
                    loco_rear_addr = locomotives[1]['address']
                    delta_t = consist.get('delta_t', 0)

                    # Get reference loco config for this consist
                    consist_config = self.reference_locos.get(str(address), {})

                    if consist_config:
                        adjust_addr = consist_config.get('adjust')
                        reference_addr = consist_config.get('reference')
                    else:
                        # Fallback: default to adjusting lead (rear as reference)
                        adjust_addr = loco_lead_addr
                        reference_addr = loco_rear_addr
                        if self.verbose and self.debug_enabled:
                            log('[WARN]', f"No reference config for consist {address}, using default (adjust lead)")

                    # User command: reset speed_actual_adjust to target
                    if not is_auto_compensation:
                        consist['speed_actual_adjust'] = speed

                    # Calculate compensated speeds
                    # Reference loco always gets target speed (unless overflow)
                    speed_reference = speed
                    # Adjust loco: use incremental speed_actual_adjust for compensation
                    speed_adjust = consist.get('speed_actual_adjust', speed)

                    # CRITICAL: If speed = 0 (STOP), always send 0 to both locos (no compensation)
                    if speed == 0:
                        speed_adjust = 0
                        speed_reference = 0
                        consist['speed_actual_adjust'] = 0  # Reset incremental speed
                        consist['compensation_accumulated'] = 0  # Reset accumulated compensation
                        consist['decay_applied'] = False  # Reset decay flag
                        # Reset delta_t (user may move locos manually while stopped)
                        consist['delta_t'] = None
                        consist['delta_t_timestamp'] = None
                        log('[STOP]', f"STOP: both locos set to 0 (compensation reset)")
                    # No compensation in REVERSE direction (only forward supported)
                    elif not forward:
                        speed_adjust = speed
                        speed_reference = speed
                        consist['speed_actual_adjust'] = speed  # Reset incremental speed
                        consist['compensation_accumulated'] = 0  # Reset accumulated compensation
                        consist['decay_applied'] = False  # Reset decay flag
                        consist['delta_t'] = None  # Reset delta_t (reverse movement invalidates forward timing)
                        consist['delta_t_timestamp'] = None
                        if self.debug_enabled:
                            log('[COMP]', f"REVERSE: no compensation (forward direction only)")
                    # Bang-bang compensation: intervene only if |dT| > warning threshold (CRITICAL)
                    # Dead band < warning avoids oscillations from YOLO detection noise
                    elif is_auto_compensation and delta_t is not None and abs(delta_t) > self.timing_thresholds['warning']:
                        compensation = 2  # Fixed: 2 speed steps per intervention (even number for cleaner decay)

                        if delta_t > 0:
                            # dT > 0: adjust loco passes AFTER (too slow) → SPEED UP
                            # INCREMENTAL: add compensation to current speed_adjust
                            speed_adjust_target = speed_adjust + compensation
                            if speed_adjust_target > 126:
                                # Overflow: adjust at max, shift compensation to reference
                                overflow = speed_adjust_target - 126
                                speed_adjust = 126
                                speed_reference = max(0, speed - overflow)

                                # Track overflow occurrences
                                if address not in self.overflow_warnings:
                                    self.overflow_warnings[address] = 0
                                self.overflow_warnings[address] += 1

                                log('[COMP]', f"Auto-compensation: {colorize_status(f'dT={delta_t:.3f}s (CRITICAL)')}, speed up loco {adjust_addr} by {compensation} steps")
                                log('[OVFL]', f"Overflow: adjust at max (126), reference reduced by {overflow} steps")

                                # Persistent overflow warning every 5 occurrences
                                if self.overflow_warnings[address] % 5 == 0:
                                    log('[WARN]', f"PERSISTENT OVERFLOW ({self.overflow_warnings[address]}x): Consider increasing CV5 (Vmax) for loco {adjust_addr} via JMRI")

                                # Track accumulated compensation
                                consist['compensation_accumulated'] += compensation
                                consist['decay_applied'] = False  # Reset: new compensation allows new decay
                            else:
                                speed_adjust = speed_adjust_target
                                # CRITICAL compensation
                                log('[COMP]', f"Auto-compensation: {colorize_status(f'dT={delta_t:.3f}s (CRITICAL)')}, speed up loco {adjust_addr} by {compensation} steps")
                                # Reset overflow counter (normal compensation, no overflow)
                                if address in self.overflow_warnings:
                                    self.overflow_warnings[address] = 0

                                # Track accumulated compensation
                                consist['compensation_accumulated'] += compensation
                                consist['decay_applied'] = False  # Reset: new compensation allows new decay

                            # Save new incremental speed
                            consist['speed_actual_adjust'] = speed_adjust
                        else:
                            # dT < 0: adjust loco passes BEFORE (too fast) → SLOW DOWN
                            # INCREMENTAL: subtract compensation from current speed_adjust
                            speed_adjust_target = speed_adjust - compensation
                            if speed_adjust_target < 0:
                                # Overflow: adjust at min, shift compensation to reference
                                overflow = abs(speed_adjust_target)
                                speed_adjust = 0
                                speed_reference = min(126, speed + overflow)

                                # Track overflow occurrences
                                if address not in self.overflow_warnings:
                                    self.overflow_warnings[address] = 0
                                self.overflow_warnings[address] += 1

                                log('[COMP]', f"Auto-compensation: {colorize_status(f'dT={delta_t:.3f}s (CRITICAL)')}, slow down loco {adjust_addr} by {compensation} steps")
                                log('[OVFL]', f"Overflow: adjust at min (0), reference increased by {overflow} steps")

                                # Persistent overflow warning every 5 occurrences
                                if self.overflow_warnings[address] % 5 == 0:
                                    log('[WARN]', f"PERSISTENT OVERFLOW ({self.overflow_warnings[address]}x): Consider decreasing CV2 (Vstart) or CV5 (Vmax) for loco {adjust_addr} via JMRI")

                                # Track accumulated compensation
                                consist['compensation_accumulated'] -= compensation
                                consist['decay_applied'] = False  # Reset: new compensation allows new decay

                                # Save new incremental speed
                                consist['speed_actual_adjust'] = speed_adjust
                            else:
                                speed_adjust = speed_adjust_target
                                # CRITICAL compensation
                                log('[COMP]', f"Auto-compensation: {colorize_status(f'dT={delta_t:.3f}s (CRITICAL)')}, slow down loco {adjust_addr} by {compensation} steps")
                                # Reset overflow counter (normal compensation, no overflow)
                                if address in self.overflow_warnings:
                                    self.overflow_warnings[address] = 0

                                # Track accumulated compensation
                                consist['compensation_accumulated'] -= compensation
                                consist['decay_applied'] = False  # Reset: new compensation allows new decay

                                # Save new incremental speed
                                consist['speed_actual_adjust'] = speed_adjust
                    # SYNCED zone reset: immediate snapback to target speed (unified for all track geometries)
                    elif is_auto_compensation and delta_t is not None and abs(delta_t) < self.timing_thresholds['normal']:
                        accumulated = consist.get('compensation_accumulated', 0)

                        if accumulated != 0:  # Reset only if there was previous compensation
                            # Snapback: reset adjust loco to target speed (complete reset, no progressive decay)
                            # This works better for both short-interval (C11) and long-interval (C10) tracks
                            # Avoids oscillations and overshoot from progressive decay with infrequent checks
                            old_speed = speed_adjust
                            speed_adjust = speed  # Reset to target
                            correction = speed_adjust - old_speed

                            # SYNCED reset (returning to target)
                            if correction > 0:
                                log('[SYNC]', f"Reset: {colorize_status('SYNCED')} (dT={delta_t:.3f}s), speed up loco {adjust_addr} by {correction} steps (reset accumulated: {accumulated} → 0)")
                            elif correction < 0:
                                log('[SYNC]', f"Reset: {colorize_status('SYNCED')} (dT={delta_t:.3f}s), slow down loco {adjust_addr} by {abs(correction)} steps (reset accumulated: {accumulated} → 0)")
                            else:
                                log('[SYNC]', f"Reset: {colorize_status('SYNCED')} (dT={delta_t:.3f}s), no change needed (already at target, reset accumulated: {accumulated} → 0)")

                            # Save reset speed
                            consist['speed_actual_adjust'] = speed_adjust

                            # Reset accumulated compensation
                            consist['compensation_accumulated'] = 0
                    else:
                        # WARNING zone (normal < |dT| < warning): No action, reset overflow counter
                        if address in self.overflow_warnings:
                            self.overflow_warnings[address] = 0

                    # Send commands (reference-preferred: adjust compensated first, overflow shifts to reference)
                    if loco_lead_addr == adjust_addr:
                        self.z21.set_loco_speed(loco_lead_addr, speed_adjust, forward)
                        self.z21.set_loco_speed(loco_rear_addr, speed_reference, forward)
                    else:
                        self.z21.set_loco_speed(loco_lead_addr, speed_reference, forward)
                        self.z21.set_loco_speed(loco_rear_addr, speed_adjust, forward)

                    # Save compensation data for UI display
                    consist['adjust_loco_address'] = adjust_addr
                    consist['adjust_speed'] = speed_adjust
                    consist['adjust_correction'] = speed_adjust - speed  # Difference from target

                    # Virtual Mode speed command
                    log('[VIRT]', f"Virtual Mode: L{adjust_addr}={speed_adjust}, L{reference_addr}={speed_reference}")
                else:
                    # Normal DCC consist mode
                    self.z21.set_loco_speed(address, speed, forward)
            else:
                # Single locomotive
                self.z21.set_loco_speed(address, speed, forward)

            # Update state
            if address in self.consist_state:
                consist = self.consist_state[address]
                consist['speed'] = speed
                consist['direction'] = 'forward' if forward else 'reverse'

            return True
        except Exception as e:
            print(f"Error setting speed for address {address}: {e}")
            return False

    def set_function(self, address, function_number, state):
        """
        Imposta funzione F0-F28

        Args:
            address (int): DCC address (consist or locomotive)
            function_number (int): Numero funzione 0-28
            state (bool): True per ON, False per OFF
        """
        if not self.z21:
            return False

        try:
            # If this is a consist, get locomotive addresses from array
            # Functions must be sent to individual locos, not the consist address
            target_addresses = []

            if address in self.consist_state:
                locomotives = self.consist_state[address].get('locomotives', [])

                if locomotives:
                    # F0 (lights) goes to ALL locomotives in consist
                    if function_number == 0:
                        target_addresses = [loco['address'] for loco in locomotives]
                        loco_addrs = ', '.join(map(str, target_addresses))
                        if self.debug_enabled:
                            log('[INIT]', f"Consist {address}: F0 to all locos ({loco_addrs})")
                    else:
                        # Other functions only to lead (sound decoder)
                        target_addresses = [locomotives[0]['address']]
                        if self.debug_enabled:
                            log('[INIT]', f"Consist {address}: F{function_number} to lead ({target_addresses[0]})")
                else:
                    # Fallback: treat as single locomotive
                    target_addresses = [address]
            else:
                # Single locomotive
                target_addresses = [address]

            # Get current function states
            current_functions = {}
            if address in self.consist_state:
                current_functions = self.consist_state[address]['functions'].copy()

            # Update the specific function
            current_functions[function_number] = state

            # Send command to Z21 for each target locomotive
            success = True
            for target_addr in target_addresses:
                try:
                    self.z21.set_loco_function(target_addr, function_number, state, current_functions)
                except Exception as e:
                    log('[FAIL]', f"Error for address {target_addr}: {e}")
                    success = False

            # Update state in consist
            if address in self.consist_state:
                self.consist_state[address]['functions'][function_number] = state

                # Also update individual locomotive states (for single loco panels)
                locomotives = self.consist_state[address].get('locomotives', [])
                for loco in locomotives:
                    loco_addr = loco['address']
                    if loco_addr in self.consist_state:
                        # F0 goes to all locos, other functions only to lead
                        if function_number == 0 or loco_addr == locomotives[0]['address']:
                            self.consist_state[loco_addr]['functions'][function_number] = state

            return success
        except Exception as e:
            print(f"Error setting function F{function_number} for address {address}: {e}")
            return False

    def emergency_stop(self):
        """Emergency stop - ferma tutte le locomotive"""
        if not self.z21:
            return False

        try:
            self.z21.emergency_stop_all()

            # Update state - reset all speeds to 0 and clear delta_t
            for address in self.consist_state:
                self.consist_state[address]['speed'] = 0
                # Reset delta_t (user may move locos manually after emergency stop)
                if 'delta_t' in self.consist_state[address]:
                    self.consist_state[address]['delta_t'] = None
                    self.consist_state[address]['delta_t_timestamp'] = None

            log('[STOP]', f"Emergency stop: all consists stopped (compensation reset)")
            return True
        except Exception as e:
            print(f"Error emergency stop: {e}")
            return False

    def track_power_on(self):
        """Accendi alimentazione binari"""
        if not self.z21:
            return False

        try:
            self.z21.track_power_on()

            # Update state
            for address in self.consist_state:
                self.consist_state[address]['power'] = True

            return True
        except Exception as e:
            print(f"Error track power on: {e}")
            return False

    def track_power_off(self):
        """Spegni alimentazione binari"""
        if not self.z21:
            return False

        try:
            self.z21.track_power_off()

            # Update state
            for address in self.consist_state:
                self.consist_state[address]['power'] = False
                self.consist_state[address]['speed'] = 0

            return True
        except Exception as e:
            print(f"Error track power off: {e}")
            return False

    def sync_consist_state(self, address):
        """
        Sincronizza stato consist dalla Z21

        Args:
            address (int): DCC address del consist

        Returns:
            dict: Stato aggiornato del consist
        """
        if not self.z21:
            return None

        try:
            # Get locomotive info from Z21
            loco_info = self.z21.get_loco_info(address)

            if loco_info and address in self.consist_state:
                # Update local state
                self.consist_state[address]['speed'] = loco_info['speed']
                self.consist_state[address]['direction'] = 'forward' if loco_info['forward'] else 'reverse'

                # Update function states
                for fn_num, fn_state in loco_info['functions'].items():
                    if fn_num in self.consist_state[address]['functions']:
                        self.consist_state[address]['functions'][fn_num] = fn_state

                return self.consist_state[address]

        except Exception as e:
            print(f"Error syncing consist {address}: {e}")

        return None

    def enable_virtual_mode(self, consist_address):
        """
        Enable Virtual Mode: write CV19=0 to both locos (operations mode)

        This frees locomotives from consist, but does NOT auto-compensate speed yet.
        MVP: Only CV19 toggle, speed compensation is Phase 2.

        Args:
            consist_address (int): Consist address

        Returns:
            bool: True if successful
        """
        if consist_address not in self.consist_state:
            log('[WARN]', f"Consist {consist_address} not found")
            return False

        consist = self.consist_state[consist_address]
        locomotives = consist.get('locomotives', [])

        if len(locomotives) < 2:
            log('[WARN]', f"Consist {consist_address} has less than 2 locomotives")
            return False

        lead_addr = locomotives[0]['address']
        rear_addr = locomotives[1]['address']

        # Always log Virtual Mode toggle (critical operation)
        log('[CV]', f"Enabling Virtual Mode for consist {consist_address}...")
        log('[CV]', f"Writing CV19=0 to loco {lead_addr} (lead)")
        log('[CV]', f"Writing CV19=0 to loco {rear_addr} (rear)")

        # Write CV19=0 to free from consist (operations mode)
        success_lead = self.z21.write_cv_ops_mode(lead_addr, 19, 0)
        success_rear = self.z21.write_cv_ops_mode(rear_addr, 19, 0)

        if success_lead and success_rear:
            consist['virtual_mode'] = True
            consist['auto_compensation_enabled'] = True  # Auto-enable compensation with Virtual Mode
            self._save_persisted_state()  # Persist to file
            log('[CV]', f"Virtual Mode enabled for consist {consist_address} (auto-compensation ON)")
            return True
        else:
            error_locos = []
            if not success_lead:
                error_locos.append(f"lead {lead_addr}")
            if not success_rear:
                error_locos.append(f"rear {rear_addr}")
            log('[CV]', f"Failed to enable Virtual Mode: CV write failed for {', '.join(error_locos)}")
            return False

    def disable_virtual_mode(self, consist_address):
        """
        Disable Virtual Mode: restore CV19=consist_address

        This restores normal DCC consist operation.

        Args:
            consist_address (int): Consist address

        Returns:
            bool: True if successful
        """
        if consist_address not in self.consist_state:
            log('[WARN]', f"Consist {consist_address} not found")
            return False

        consist = self.consist_state[consist_address]
        locomotives = consist.get('locomotives', [])

        if len(locomotives) < 2:
            log('[WARN]', f"Consist {consist_address} has less than 2 locomotives")
            return False

        lead_addr = locomotives[0]['address']
        rear_addr = locomotives[1]['address']

        # Always log Virtual Mode toggle (critical operation)
        log('[CV]', f"Disabling Virtual Mode for consist {consist_address}...")
        log('[CV]', f"Writing CV19={consist_address} to loco {lead_addr} (lead)")
        log('[CV]', f"Writing CV19={consist_address} to loco {rear_addr} (rear)")

        # Restore CV19 to consist address (operations mode)
        success_lead = self.z21.write_cv_ops_mode(lead_addr, 19, consist_address)
        success_rear = self.z21.write_cv_ops_mode(rear_addr, 19, consist_address)

        if success_lead and success_rear:
            consist['virtual_mode'] = False
            consist['auto_compensation_enabled'] = False  # Auto-disable compensation with DCC Mode
            self._save_persisted_state()  # Persist to file
            log('[CV]', f"Virtual Mode disabled for consist {consist_address} (auto-compensation OFF)")
            return True
        else:
            error_locos = []
            if not success_lead:
                error_locos.append(f"lead {lead_addr}")
            if not success_rear:
                error_locos.append(f"rear {rear_addr}")
            log('[CV]', f"Failed to disable Virtual Mode: CV write failed for {', '.join(error_locos)}")
            return False

    def _load_persisted_state(self):
        """Load persisted virtual_mode state from config.json consists"""
        try:
            # Try loading from config.json first (new consolidated approach)
            if self.config_path.exists():
                config = load_config()
                consists = config.get('consists', {})

                # Extract virtual_mode and auto_compensation_enabled from each consist
                state = {}
                for consist_id, consist_info in consists.items():
                    virtual_mode = consist_info.get('virtual_mode', False)
                    auto_compensation = consist_info.get('auto_compensation_enabled', virtual_mode)

                    state[consist_id] = {
                        'virtual_mode': virtual_mode,
                        'auto_compensation_enabled': auto_compensation
                    }

                    # Warn if virtual_mode is not configured (locomotives won't respond to speed commands)
                    if not virtual_mode:
                        log('[WARN]', f"WARNING: Consist {consist_id} has virtual_mode=False")
                        log('[WARN]', f"Speed commands will be sent to consist address {consist_id} (DCC mode)")
                        log('[WARN]', f"Locomotives may not respond unless CV19={consist_id} is programmed")
                        log('[WARN]', f"Set 'virtual_mode: true' in config.json consists.{consist_id} for proper operation")

                if self.debug_enabled and state:
                    log('[INIT]', f"Loaded persisted state from config.json: {state}")
                return state

        except Exception as e:
            if self.debug_enabled:
                log('[WARN]', f"Failed to load persisted state: {e}")
        return {}

    def _save_persisted_state(self):
        """Save virtual_mode and auto_compensation_enabled state to config.json consists"""
        try:
            # Load current config.json
            config = load_config()

            consists = config.get('consists', {})

            # Update virtual_mode and auto_compensation_enabled for each consist
            for address, consist in self.consist_state.items():
                if 'locomotives' in consist and len(consist.get('locomotives', [])) >= 2:
                    consist_id = str(address)

                    # Skip if not in consists (shouldn't happen)
                    if consist_id not in consists:
                        continue

                    # Update fields in consists
                    consists[consist_id]['virtual_mode'] = consist.get('virtual_mode', False)
                    consists[consist_id]['auto_compensation_enabled'] = consist.get('auto_compensation_enabled', False)

            # Write back to config.json
            config['consists'] = consists
            save_config(config)

            if self.debug_enabled:
                saved_state = {k: {'virtual_mode': v.get('virtual_mode'), 'auto_compensation_enabled': v.get('auto_compensation_enabled')}
                               for k, v in consists.items()}
                log('[INIT]', f"Saved persisted state to config.json: {saved_state}")

        except Exception as e:
            if self.debug_enabled:
                log('[WARN]', f"Failed to save persisted state: {e}")


    def toggle_cv_profile_mode(self):
        """Toggle CV profile mode between 'normal' and 'testing' for ALL locomotives. Returns (success: bool, new_mode: str, message: str)."""
        try:
            config = load_config()
            current_mode = config.get('cv_profile_mode', 'normal')
            cv_profiles = config.get('cv_profiles', {})
            if not cv_profiles:
                return False, current_mode, "No CV profiles configured in config.json"

            # Check track power before attempting writes
            status = self.z21.get_status()
            if not status:
                return False, current_mode, "Cannot read Z21 status"
            if not status['track_power_on']:
                return False, current_mode, "Track power is OFF - Turn on power before changing CV profiles"
            if status['short_circuit']:
                return False, current_mode, "Short circuit detected - Check track and locomotives"

            new_mode = 'testing' if current_mode == 'normal' else 'normal'
            addresses = [int(addr) for addr in cv_profiles.keys()]
            log('[CV]', f"CV Profile Toggle: {current_mode} → {new_mode} (addresses: {addresses})")
            if new_mode == 'testing':
                import time
                start_time = time.time()
                log('[CV]', f"Writing CV testing values from config.json...")
                success_count = 0
                failed_locos = []
                for addr in addresses:
                    addr_str = str(addr)
                    try:
                        loco_start = time.time()
                        cv3_value = cv_profiles[addr_str]['testing']['cv3']
                        cv4_value = cv_profiles[addr_str]['testing']['cv4']
                        self.z21.write_cv_ops_mode(addr, 3, cv3_value)
                        time.sleep(0.1)  # Delay tra CV write per dare tempo al decoder
                        self.z21.write_cv_ops_mode(addr, 4, cv4_value)
                        time.sleep(0.1)  # Delay prima del prossimo loco
                        elapsed = time.time() - loco_start
                        log('[CV]', f"Loco {addr}: CV3={cv3_value}, CV4={cv4_value} [{elapsed*1000:.0f}ms]")
                        success_count += 1
                    except Exception as e:
                        log('[CV]', f"Loco {addr}: write failed: {e}")
                        failed_locos.append(addr)
                total_elapsed = time.time() - start_time
                log('[CV]', f"Total time: {total_elapsed:.2f}s")
                config['cv_profile_mode'] = 'testing'
                save_config(config)
                if failed_locos:
                    return True, 'testing', f"TEST MODE enabled - {success_count}/{len(addresses)} locomotives updated (failed: {', '.join(map(str, failed_locos))})"
                return True, 'testing', f"TEST MODE enabled - CV testing values for {len(addresses)} locomotives"
            else:
                import time
                start_time = time.time()
                log('[CV]', f"Restoring CV values from config.json normal profiles...")
                success_count = 0
                failed_locos = []
                for addr in addresses:
                    addr_str = str(addr)
                    try:
                        loco_start = time.time()
                        cv3_value = cv_profiles[addr_str]['normal']['cv3']
                        cv4_value = cv_profiles[addr_str]['normal']['cv4']
                        self.z21.write_cv_ops_mode(addr, 3, cv3_value)
                        time.sleep(0.1)  # Delay tra CV write per dare tempo al decoder
                        self.z21.write_cv_ops_mode(addr, 4, cv4_value)
                        time.sleep(0.1)  # Delay prima del prossimo loco
                        elapsed = time.time() - loco_start
                        log('[CV]', f"Loco {addr}: CV3={cv3_value}, CV4={cv4_value} [{elapsed*1000:.0f}ms]")
                        success_count += 1
                    except Exception as e:
                        log('[CV]', f"Loco {addr}: restore failed: {e}")
                        failed_locos.append(addr)
                total_elapsed = time.time() - start_time
                log('[CV]', f"Total time: {total_elapsed:.2f}s")
                config['cv_profile_mode'] = 'normal'
                save_config(config)
                if failed_locos:
                    return True, 'normal', f"NORMAL MODE restored - {success_count}/{len(addresses)} locomotives updated (failed: {', '.join(map(str, failed_locos))})"
                return True, 'normal', f"NORMAL MODE restored - CV3/CV4 restored for {len(addresses)} locomotives"
        except Exception as e:
            return False, current_mode, f"Error toggling CV profile mode: {e}"


if __name__ == '__main__':
    # Test
    manager = Z21Manager(verbose=True)

    if manager.connect():
        print("Connected to Z21!")

        # Initialize test consist
        manager.initialize_consist(10, {
            'locomotives': [
                {'address': 1, 'name': 'Gr.675 017'},  # Lead
                {'address': 5, 'name': 'D645 014'}      # Rear
            ],
            'functions': [
                {'number': 0, 'label': 'Light', 'lockable': True},
                {'number': 1, 'label': 'Sound', 'lockable': True}
            ]
        })

        print(f"Consist state: {manager.get_consist_state(10)}")

        manager.disconnect()
    else:
        print("Failed to connect to Z21")
