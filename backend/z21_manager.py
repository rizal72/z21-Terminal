"""
Z21Manager - Wrapper per la libreria z21.py con gestione stato consist
"""
import sys
from pathlib import Path

# Add scripts directory to path per importare z21.py
scripts_dir = Path(__file__).parent.parent / 'scripts'
sys.path.insert(0, str(scripts_dir))

from z21 import Z21


class Z21Manager:
    """
    Manager per gestire connessioni Z21 e stato consist
    """

    def __init__(self, z21_ip='192.168.1.111', verbose=False):
        """
        Inizializza Z21Manager

        Args:
            z21_ip (str): Indirizzo IP della Z21
            verbose (bool): Modalità verbose per debug
        """
        self.z21_ip = z21_ip
        self.verbose = verbose
        self.z21 = None
        self.consist_state = {}  # {address: {'speed': 0, 'direction': 'forward', 'power': True, 'functions': {}}}

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
            data (dict): Dati consist (lead, rear, functions, etc.)
        """
        self.consist_state[address] = {
            'address': address,
            'lead': data.get('lead'),
            'rear': data.get('rear'),
            'lead_name': data.get('lead_name'),
            'rear_name': data.get('rear_name'),
            'speed': 0,
            'direction': 'forward',
            'power': True,
            'functions': {}  # {0: False, 1: False, ...}
        }

        # Initialize function states
        for fn in data.get('functions', []):
            self.consist_state[address]['functions'][fn['number']] = False

        # Sync initial state from Z21 (read current function states from lead loco)
        if self.z21:
            lead_addr = data.get('lead')
            if lead_addr:
                try:
                    loco_info = self.z21.get_loco_info(lead_addr)
                    if loco_info and 'functions' in loco_info:
                        # Update function states from actual locomotive
                        for fn_num, fn_state in loco_info['functions'].items():
                            if fn_num in self.consist_state[address]['functions']:
                                self.consist_state[address]['functions'][fn_num] = fn_state
                        print(f"  ✓ Synced functions for consist {address} from lead loco {lead_addr}")
                except Exception as e:
                    print(f"  ⚠️  Could not sync functions for consist {address}: {e}")

    def get_consist_state(self, address):
        """Get current state of a consist"""
        return self.consist_state.get(address, {})

    def get_all_consists_state(self):
        """Get state of all consists"""
        return self.consist_state

    def set_speed(self, address, speed, forward=True):
        """
        Imposta velocità locomotiva/consist

        Args:
            address (int): DCC address
            speed (int): Velocità 0-126
            forward (bool): True per avanti, False per indietro
        """
        if not self.z21:
            return False

        try:
            self.z21.set_loco_speed(address, speed, forward)

            # Update state
            if address in self.consist_state:
                self.consist_state[address]['speed'] = speed
                self.consist_state[address]['direction'] = 'forward' if forward else 'reverse'

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
            # If this is a consist, get the lead and rear locomotive addresses
            # Functions must be sent to individual locos, not the consist address
            target_addresses = []

            if address in self.consist_state and 'lead' in self.consist_state[address]:
                lead_addr = self.consist_state[address]['lead']
                rear_addr = self.consist_state[address]['rear']

                # F0 (lights) goes to both lead and rear
                if function_number == 0:
                    target_addresses = [lead_addr, rear_addr]
                    print(f"   → Consist {address}: F0 to lead ({lead_addr}) and rear ({rear_addr})")
                else:
                    # Other functions only to lead (sound decoder)
                    target_addresses = [lead_addr]
                    print(f"   → Consist {address}: F{function_number} to lead ({lead_addr})")
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
                    print(f"   ✗ Error for address {target_addr}: {e}")
                    success = False

            # Update state in consist
            if address in self.consist_state:
                self.consist_state[address]['functions'][function_number] = state

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

            # Update state - reset all speeds to 0
            for address in self.consist_state:
                self.consist_state[address]['speed'] = 0

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


if __name__ == '__main__':
    # Test
    manager = Z21Manager(verbose=True)

    if manager.connect():
        print("Connected to Z21!")

        # Initialize test consist
        manager.initialize_consist(10, {
            'lead': 1,
            'rear': 5,
            'lead_name': 'Gr.675 017',
            'rear_name': 'D645 014',
            'functions': [
                {'number': 0, 'label': 'Light', 'lockable': True},
                {'number': 1, 'label': 'Sound', 'lockable': True}
            ]
        })

        print(f"Consist state: {manager.get_consist_state(10)}")

        manager.disconnect()
    else:
        print("Failed to connect to Z21")
