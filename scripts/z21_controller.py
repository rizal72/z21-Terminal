#!/usr/bin/env python3
"""
z21-Terminal - Controller interattivo da terminale per locomotive via Z21.

Nota: Può coesistere con JMRI. In caso di problemi, riavviare Z21 o JMRI.

Comandi tastiera:
    w       - Aumenta velocità (+5)
    s       - Diminuisci velocità (-5)
    \       - Velocità 0 (stop immediato)
    1-9     - Velocità 10%-90%
    0       - Velocità 100% (massima)
    SPACE   - STOP graduale (solo questa loco)
    TAB     - 🚨 EMERGENCY STOP toggle (on: toglie corrente / off: riaccende)
    d       - Cambia direzione (avanti/indietro)
    l       - Lista locomotive/consist disponibili
    c       - Cambia locomotiva
    f       - Menu funzioni (F0-F28)
    h       - Help comandi
    q       - Quit

Uso:
    python z21_controller.py [address]

    Se non specifichi address, ti chiederà quale locomotiva controllare.
"""

import sys
import time
import threading
import select
import tty
import termios
import subprocess
import xml.etree.ElementTree as ET
from typing import Optional, Dict
from pathlib import Path

sys.path.insert(0, '/Users/riccardosallusti/Documents/_PROGETTI/z21-Terminal/scripts')
from z21 import Z21


# Percorsi JMRI
ROSTER_PATH = Path.home() / "Library/Preferences/JMRI/La_mia_Ferrovia_in_JMRI.jmri/roster"
CONSIST_FILE = ROSTER_PATH / "consist" / "consist.xml"


def load_locomotives_from_roster() -> Dict[int, dict]:
    """Carica locomotive dal roster JMRI con funzioni."""
    locomotives = {}

    if not ROSTER_PATH.exists():
        print(f"⚠️  Warning: Roster path non trovato: {ROSTER_PATH}")
        return locomotives

    for xml_file in ROSTER_PATH.glob("*.xml"):
        if xml_file.name.endswith('.bak'):
            continue

        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            loco = root.find('locomotive')

            name = loco.get('id', 'Unknown')
            address = int(loco.get('dccAddress', '0'))
            mfg = loco.get('mfg', '')
            model = loco.get('model', '')

            # Leggi functionlabels
            functions = {}
            functionlabels = loco.find('functionlabels')
            if functionlabels is not None:
                for func in functionlabels.findall('functionlabel'):
                    num = int(func.get('num', '0'))
                    label = func.text or f"F{num}"
                    lockable = func.get('lockable', 'false') == 'true'
                    functions[num] = {'label': label, 'lockable': lockable}

            locomotives[address] = {
                'name': f"{name} ({mfg} {model})",
                'functions': functions
            }
        except Exception as e:
            continue

    return locomotives


def load_consists() -> Dict[int, Dict]:
    """Carica consist configurati."""
    consists = {}

    if not CONSIST_FILE.exists():
        print(f"⚠️  Warning: Consist file non trovato: {CONSIST_FILE}")
        return consists

    try:
        tree = ET.parse(CONSIST_FILE)
        root = tree.getroot()

        for consist_elem in root.findall('.//consist'):
            consist_num = int(consist_elem.get('consistNumber', '0'))

            # Leggi locomotive nel consist
            locos = []
            for loco_elem in consist_elem.findall('loco'):
                addr = int(loco_elem.get('dccLocoAddress', '0'))
                role = loco_elem.get('locoName', '')
                roster_id = loco_elem.get('locoRosterId', '')
                locos.append({'address': addr, 'role': role, 'name': roster_id})

            consists[consist_num] = locos

    except Exception as e:
        print(f"⚠️  Warning: Errore leggendo consist: {e}")

    return consists


class LocoController:
    """Controller interattivo per locomotive."""

    def __init__(self, address: Optional[int] = None):
        self.z21 = Z21(verbose=False)  # Disabilita messaggi debug Z21
        self.address = address
        self.speed = 0
        self.forward = True
        self.running = True
        self.max_speed = 126
        self.track_power_on = True  # Stato corrente binari

        # Polling configuration
        self.last_poll = time.time()
        self.poll_interval = 0.5  # Sincronizza ogni 500ms
        self.sync_movement = False  # Disabilita sync velocità/direzione (conflitto con JMRI throttle)
        self.last_command_time = 0  # Timestamp ultimo comando inviato
        self.command_cooldown = 2.0  # Cooldown 2 secondi dopo comando prima di sincronizzare

        # Verify Z21 connection
        print("\n" + "="*60)
        print("z21-Terminal - INTERACTIVE CONTROLLER")
        print("="*60)

        serial = self.z21.get_serial_number()
        if not serial:
            print("\n❌ ERROR: Z21 not reachable!")
            print("   Check:")
            print("   - Z21 powered on and connected")
            print("   - Correct IP (192.168.1.111)")
            print("   - Network working")
            sys.exit(1)

        # Load locomotives and consists from JMRI roster
        print("\n📂 Loading JMRI roster...")
        self.locomotives = load_locomotives_from_roster()
        self.consists = load_consists()

        # Create complete address list with consists
        self.all_addresses = {}
        for addr, loco_data in self.locomotives.items():
            self.all_addresses[addr] = loco_data['name']

        for consist_num, locos in self.consists.items():
            if locos:
                loco_names = " + ".join([l['name'].split()[0] for l in locos[:2]])
                self.all_addresses[consist_num] = f"CONSIST {consist_num} ({loco_names}) 🚂🚂"

        # Mark locomotives in consists
        for consist_num, locos in self.consists.items():
            for loco in locos:
                addr = loco['address']
                if addr in self.all_addresses:
                    self.all_addresses[addr] += f" [IN CONSIST {consist_num}]"

        # Function states (local tracking)
        self.function_states = {i: False for i in range(29)}  # F0-F28

        print(f"✅ Loaded {len(self.locomotives)} locomotives and {len(self.consists)} consists")

        if not self.all_addresses:
            print("\n❌ ERROR: No locomotives found in roster!")
            print("   Check that JMRI has configured locomotives.")
            sys.exit(1)

        if not address:
            self.select_locomotive()
        else:
            # Validate address provided as parameter
            if address not in self.all_addresses:
                print(f"\n❌ ERROR: Address {address} not found in roster!")
                print("\n📋 Available locomotives and consists:")

                # Show complete list
                consists = {a: n for a, n in self.all_addresses.items() if "CONSIST" in n and "🚂🚂" in n}
                in_consist = {a: n for a, n in self.all_addresses.items() if "[IN CONSIST" in n}
                singles = {a: n for a, n in self.all_addresses.items() if a not in consists and a not in in_consist}

                if singles:
                    print("\n🚂 Single locomotives:")
                    for addr, name in sorted(singles.items()):
                        print(f"  {addr} - {name}")

                if consists:
                    print("\n🚂🚂 Consists:")
                    for addr, name in sorted(consists.items()):
                        print(f"  {addr} - {name}")

                if in_consist:
                    print("\n⚠️  Locomotives in consists (not individually controllable):")
                    for addr, name in sorted(in_consist.items()):
                        print(f"  {addr} - {name}")

                print(f"\n💡 Usage: python3 z21_controller.py [address]")
                print(f"   Example: python3 z21_controller.py 1")
                sys.exit(1)

            self.address = address
            # Read actual state from locomotive
            self._sync_function_states()
            print(f"\n✅ Selected: {self.all_addresses[address]}")

    def select_locomotive(self):
        """Interactive locomotive selection."""
        print("\n" + "-"*60)
        print("AVAILABLE LOCOMOTIVES AND CONSISTS:")
        print("-"*60)

        # Separate single locos, in-consist, and consists
        singles = {}
        in_consist = {}
        consists = {}

        for addr, name in sorted(self.all_addresses.items()):
            if "CONSIST" in name and "🚂🚂" in name:
                consists[addr] = name
            elif "[IN CONSIST" in name:
                in_consist[addr] = name
            else:
                singles[addr] = name

        if singles:
            print("\n🚂 Single locomotives (not in consist):")
            for addr, name in singles.items():
                print(f"  {addr} - {name}")

        if in_consist:
            print("\n⚠️  Locomotives in consist (don't respond individually):")
            for addr, name in in_consist.items():
                print(f"  {addr} - {name}")

        if consists:
            print("\n🚂🚂 Consists (control both locos together):")
            for addr, name in consists.items():
                print(f"  {addr} - {name}")

        while True:
            try:
                choice = input("\nSelect locomotive/consist address: ").strip()
                addr = int(choice)
                if addr in self.all_addresses:
                    self.address = addr
                    # Reset local function state
                    self.function_states = {i: False for i in range(29)}

                    # Read actual state from locomotive
                    self._sync_function_states()

                    print(f"\n✅ Selected: {self.all_addresses[addr]}")
                    return
                else:
                    print(f"❌ Invalid address {addr}")
            except (ValueError, KeyboardInterrupt):
                print("\n❌ Invalid input")

    def show_help(self):
        """Show available commands."""
        print("\n" + "="*60)
        print("AVAILABLE COMMANDS")
        print("="*60)
        print("""
SPEED CONTROL:
  w          Increase speed (+5)
  s          Decrease speed (-5)
  \\          Speed 0 (immediate stop)
  1-9        Speed 10%-90%
  0          Speed 100% (maximum)
  SPACE      Gradual STOP (this loco only, with braking)

EMERGENCY:
  TAB        🚨 EMERGENCY STOP toggle
             - Power ON  → STOP all + power off
             - Power OFF → Power on

DIRECTION:
  d          Change direction (forward ⇄ reverse)

FUNCTIONS (always visible below slider):
  Shift+A    Toggle F0 (first function)
  Shift+B    Toggle F1
  Shift+C    Toggle F2
  ...        ...
  Shift+Z    Toggle F25
  ,          Toggle F26
  .          Toggle F27
  -          Toggle F28
  f          Sync function states (re-read from loco)

OTHER:
  l          List available locomotives
  c          Change locomotive
  h          Show this help
  q          Quit (exit controller)
""")
        input("Press ENTER to continue...")

    def show_status(self):
        """Show current status with slider and functions always visible."""
        direction = "FORWARD ⟶" if self.forward else "REVERSE ⟵"
        speed_pct = round((self.speed / self.max_speed) * 100)

        # Barra velocità
        bar_length = 30
        filled = int((self.speed / self.max_speed) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)

        # Tronca nome se troppo lungo
        loco_name = self.all_addresses[self.address]
        if len(loco_name) > 40:
            loco_name = loco_name[:37] + "..."

        # Indicatore stato corrente
        power_indicator = "⚡ \033[92mPOWER\033[0m" if self.track_power_on else "\033[91m⚡ OFF\033[0m  "

        # Indicatore loco in consist (movimento non controllabile)
        consist_warning = ""
        if "[IN CONSIST" in self.all_addresses.get(self.address, ""):
            consist_warning = " \033[93m⚠️ FUNCTIONS ONLY\033[0m"

        # Status line
        status_line = (f"🚂 {loco_name:40s} | "
                      f"{direction:15s} | "
                      f"[{bar}] {speed_pct:3d}% ({self.speed:3d}/126) | {power_indicator}{consist_warning}")

        # Pulisci schermo e ridisegna tutto
        output = "\033[2J\033[H"  # Clear screen e vai a (1,1)
        output += status_line + "\n"
        output += "━" * 120 + "\n"

        # Funzioni
        output += self._render_functions_display()

        output += "━" * 120 + "\n"
        output += "Commands: w/s=±speed  \\=0%  1-9=10-90%  0=100%  d=dir  SPACE=stop  TAB=emergency  Shift+A-Z,.-=funcs  h=help  q=quit\n"

        print(output, end="", flush=True)

    def _render_functions_display(self) -> str:
        """Renderizza display funzioni."""
        # Determina quali funzioni mostrare
        if "[IN CONSIST" in self.all_addresses.get(self.address, ""):
            function_address = self.address
            loco_data = self.locomotives.get(self.address, {})
            functions = loco_data.get('functions', {})
        elif "CONSIST" in self.all_addresses.get(self.address, ""):
            # Consist: mostra funzioni lead
            consist_locos = self.consists.get(self.address, [])
            lead_address = None
            for loco in consist_locos:
                if loco['role'].lower() == 'lead':
                    lead_address = loco['address']
                    break
            if lead_address:
                loco_data = self.locomotives.get(lead_address, {})
                functions = loco_data.get('functions', {})
            else:
                functions = {}
        else:
            loco_data = self.locomotives.get(self.address, {})
            functions = loco_data.get('functions', {})

        if not functions:
            return "FUNCTIONS: No functions defined for this locomotive\n"

        # Mappa funzioni -> tasti (Shift+A-Z = F0-F25, ,.-=- = F26-F28)
        def get_key_for_func(num):
            if num <= 25:
                return chr(ord('A') + num)  # A-Z
            elif num == 26:
                return ','
            elif num == 27:
                return '.'
            elif num == 28:
                return '-'
            else:
                return f"F{num}"  # F29+ se mai servisse

        output = "FUNCTIONS:\n"

        # Mostra funzioni in 2 colonne, ordine verticale (alto->basso poi prossima colonna)
        sorted_funcs = sorted(functions.items())
        total = len(sorted_funcs)

        # Calcola righe necessarie (arrotonda per eccesso)
        rows = (total + 1) // 2

        for row in range(rows):
            # Prima colonna (indice: row)
            if row < total:
                func1_num, func1_data = sorted_funcs[row]
                func1_state = self.function_states.get(func1_num, False)
                func1_indicator = "🟢" if func1_state else "🔴"
                func1_key = get_key_for_func(func1_num)
                func1_label = func1_data['label']
                line = f"[{func1_key:2s}] {func1_indicator} F{func1_num:2d}: {func1_label:20s}"
            else:
                line = " " * 35  # Spazio vuoto se non c'è funzione

            # Seconda colonna (indice: row + rows)
            second_idx = row + rows
            if second_idx < total:
                func2_num, func2_data = sorted_funcs[second_idx]
                func2_state = self.function_states.get(func2_num, False)
                func2_indicator = "🟢" if func2_state else "🔴"
                func2_key = get_key_for_func(func2_num)
                func2_label = func2_data['label']
                line += f"    [{func2_key:2s}] {func2_indicator} F{func2_num:2d}: {func2_label:20s}"

            output += line + "\n"

        return output

    def _sync_function_states(self):
        """Sincronizza stato funzioni dal decoder locomotive (o lead se consist)."""
        # Determina quale address interrogare
        if "CONSIST" in self.all_addresses.get(self.address, ""):
            # Per consist, leggi dalla loco lead
            consist_locos = self.consists.get(self.address, [])
            query_address = None
            for loco in consist_locos:
                if loco['role'].lower() == 'lead':
                    query_address = loco['address']
                    break
            if not query_address:
                print("⚠️  Loco lead non trovata, stato funzioni non sincronizzato")
                return
        else:
            # Per loco singola, leggi direttamente
            query_address = self.address

        # Interroga locomotiva
        print(f"🔄 Reading function states from address {query_address}...", end="", flush=True)
        loco_info = self.z21.get_loco_info(query_address)

        if loco_info and 'functions' in loco_info:
            # Aggiorna stato locale
            self.function_states = loco_info['functions']
            active_funcs = [f"F{k}" for k, v in self.function_states.items() if v]
            if active_funcs:
                print(f" ✅ Active: {', '.join(active_funcs)}")
            else:
                print(f" ✅ No functions active")
        else:
            print(" ⚠️  Cannot read state (using default: all OFF)")

    def _sync_state(self) -> bool:
        """
        Sincronizza stato da Z21 (polling periodico).
        Legge: velocità, direzione, funzioni, track power.

        Returns:
            True se qualcosa è cambiato (serve ridisegnare UI)
        """
        changed = False

        # 1. Sincronizza track power status
        status = self.z21.get_status()
        if status:
            old_power = self.track_power_on
            self.track_power_on = status['track_power_on']
            if old_power != self.track_power_on:
                changed = True
                # Suono feedback per cambi power da esterno (Z21 fisico o JMRI)
                if not self.track_power_on:
                    # Power OFF
                    subprocess.Popen(['afplay', '/System/Library/Sounds/Frog.aiff'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    # Power ON
                    subprocess.Popen(['afplay', '/System/Library/Sounds/Funk.aiff'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 2. Sincronizza stato locomotiva (solo se power on e dopo cooldown)
        # Aspetta command_cooldown secondi dopo l'ultimo comando per evitare conflitti con JMRI
        time_since_command = time.time() - self.last_command_time

        if self.track_power_on and time_since_command >= self.command_cooldown:
            # Determina quale address interrogare (come in _sync_function_states)
            if "CONSIST" in self.all_addresses.get(self.address, ""):
                consist_locos = self.consists.get(self.address, [])
                query_address = None
                for loco in consist_locos:
                    if loco['role'].lower() == 'lead':
                        query_address = loco['address']
                        break
                if not query_address:
                    return changed
            else:
                query_address = self.address

            loco_info = self.z21.get_loco_info(query_address)
            if loco_info:
                # Controlla cambiamenti velocità/direzione (solo se abilitato)
                if self.sync_movement:
                    if loco_info['speed'] != self.speed or loco_info['forward'] != self.forward:
                        self.speed = loco_info['speed']
                        self.forward = loco_info['forward']
                        changed = True

                # Controlla cambiamenti funzioni (sempre sincronizzato)
                if 'functions' in loco_info:
                    if loco_info['functions'] != self.function_states:
                        self.function_states = loco_info['functions']
                        changed = True

        return changed

    def increase_speed(self, amount: int = 5):
        """Aumenta velocità."""
        self.speed = min(self.speed + amount, self.max_speed)
        self.send_speed()

    def decrease_speed(self, amount: int = 5):
        """Diminuisci velocità."""
        self.speed = max(self.speed - amount, 0)
        self.send_speed()

    def set_speed_percent(self, percent: int):
        """Imposta velocità percentuale (0-100)."""
        self.speed = round((percent / 100) * self.max_speed)
        self.send_speed()

    def emergency_stop(self):
        """Stop immediato."""
        self.speed = 0
        self.send_speed()

    def toggle_direction(self):
        """Cambia direzione."""
        self.forward = not self.forward
        self.send_speed()

    def send_speed(self):
        """Invia comando velocità alla Z21."""
        self.z21.set_loco_speed(self.address, self.speed, self.forward)
        # Marca timestamp comando per evitare sync immediato (da tempo a JMRI di stabilizzarsi)
        self.last_command_time = time.time()
        self.show_status()

    def toggle_function(self, func_num: int):
        """Toggle una funzione ON/OFF."""
        # Determina address corretto
        if "[IN CONSIST" in self.all_addresses.get(self.address, ""):
            function_address = self.address
            loco_data = self.locomotives.get(self.address, {})
        elif "CONSIST" in self.all_addresses.get(self.address, ""):
            # Consist: usa lead address per funzioni normali
            consist_locos = self.consists.get(self.address, [])
            lead_address = None
            for loco in consist_locos:
                if loco['role'].lower() == 'lead':
                    lead_address = loco['address']
                    break
            if not lead_address:
                return  # Errore silenzioso
            function_address = lead_address
            loco_data = self.locomotives.get(lead_address, {})
        else:
            function_address = self.address
            loco_data = self.locomotives.get(self.address, {})

        functions = loco_data.get('functions', {})
        if func_num not in functions:
            return  # Funzione non definita

        func_data = functions[func_num]
        is_lockable = func_data.get('lockable', True)

        # F0 (luci) è speciale: se siamo in un consist, sincronizza su TUTTE le loco
        if func_num == 0 and "CONSIST" in self.all_addresses.get(self.address, ""):
            # Toggle stato
            current_state = self.function_states.get(func_num, False)
            new_state = not current_state
            self.function_states[func_num] = new_state

            consist_locos = self.consists.get(self.address, [])
            for loco in consist_locos:
                loco_addr = loco['address']
                # Leggi stato funzioni corrente della loco
                loco_func_states = {i: False for i in range(29)}
                loco_info = self.z21.get_loco_info(loco_addr)
                if loco_info and 'functions' in loco_info:
                    loco_func_states = loco_info['functions']

                # Aggiorna F0
                loco_func_states[0] = new_state

                # Invia comando a questa loco
                self.z21.set_loco_function(loco_addr, 0, new_state, loco_func_states)
        elif not is_lockable:
            # Funzione momentanea: ON per breve periodo poi OFF automatico
            self.function_states[func_num] = True
            self.z21.set_loco_function(function_address, func_num, True, self.function_states)
            self.show_status()  # Mostra verde
            time.sleep(0.8)  # Mantieni ON per 800ms
            self.function_states[func_num] = False
            self.z21.set_loco_function(function_address, func_num, False, self.function_states)
        else:
            # Funzione normale toggle (lockable): ON/OFF permanente
            current_state = self.function_states.get(func_num, False)
            new_state = not current_state
            self.function_states[func_num] = new_state
            self.z21.set_loco_function(function_address, func_num, new_state, self.function_states)

        # Marca timestamp comando per evitare sync immediato
        self.last_command_time = time.time()

        # Aggiorna display
        self.show_status()

    def function_menu(self):
        """Menu funzioni locomotive - interattivo."""
        # IMPORTANTE: Controllare prima "[IN CONSIST" (specifico) poi "CONSIST" (generico)
        # altrimenti "[IN CONSIST 10]" matcha il primo if!

        if "[IN CONSIST" in self.all_addresses.get(self.address, ""):
            # Locomotiva singola IN consist - può controllare le sue funzioni
            function_address = self.address
            loco_data = self.locomotives.get(self.address, {})
            functions = loco_data.get('functions', {})
            display_name = f"{self.all_addresses[self.address]} (solo funzioni)"
        elif "CONSIST" in self.all_addresses.get(self.address, ""):
            # Consist virtuale - usa la loco lead per le funzioni
            consist_locos = self.consists.get(self.address, [])
            lead_address = None
            lead_name = None

            for loco in consist_locos:
                if loco['role'].lower() == 'lead':
                    lead_address = loco['address']
                    lead_name = loco['name']
                    break

            if not lead_address:
                print("\n\n" + "="*60)
                print("⚠️  LOCO LEAD NON TROVATA NEL CONSIST")
                print("="*60)
                print("\nImpossibile controllare funzioni per questo consist.")
                input("\nPremi INVIO per continuare...")
                return

            # Usa l'address della loco lead per le funzioni
            function_address = lead_address
            loco_data = self.locomotives.get(lead_address, {})
            functions = loco_data.get('functions', {})
            display_name = f"{self.all_addresses[self.address]} → Lead: {lead_name}"
        else:
            # Locomotiva singola
            function_address = self.address
            loco_data = self.locomotives.get(self.address, {})
            functions = loco_data.get('functions', {})
            display_name = self.all_addresses[self.address]

        if not functions:
            print("\n\n" + "="*60)
            print("⚠️  NESSUNA FUNZIONE DEFINITA")
            print("="*60)
            print(f"\nLocomotiva non ha funzioni nel roster.")
            input("\nPremi INVIO per continuare...")
            return

        # Sincronizza stato reale funzioni dalla locomotiva
        print("\n🔄 Lettura stato funzioni dalla locomotiva...", end="", flush=True)
        loco_info = self.z21.get_loco_info(function_address)
        if loco_info and 'functions' in loco_info:
            self.function_states = loco_info['functions']
            active_funcs = [f"F{k}" for k, v in self.function_states.items() if v]
            if active_funcs:
                print(f" ✅ Sincronizzato! Attive: {', '.join(active_funcs[:5])}")
            else:
                print(f" ✅ Sincronizzato! Nessuna funzione attiva")
        else:
            print(" ⚠️  Impossibile leggere stato (uso default: tutte OFF)")
        time.sleep(1)

        # Mappa funzioni -> tasti
        def get_key_for_func(num):
            if num <= 9:
                return str(num)
            else:
                return chr(ord('a') + (num - 10))

        # Funzione per disegnare menu
        def draw_menu():
            # Indicatore stato corrente
            if self.track_power_on:
                power_status = "⚡ \033[92mPOWER ON\033[0m"
            else:
                power_status = "⚡ \033[91mPOWER OFF\033[0m - Premi TAB per riaccendere"

            print("\033[2J\033[H", end="", flush=True)
            print("="*60)
            print(f"FUNZIONI: {display_name}")
            print(f"Stato: {power_status}")
            print("="*60)
            print("\n" + "-"*60)
            for num in sorted(functions.keys()):
                label = functions[num]['label']
                key = get_key_for_func(num)
                # Emoji + colore per rendere più visibile
                if self.function_states[num]:
                    state_display = "🟢 \033[92mON \033[0m"
                else:
                    state_display = "🔴 \033[91mOFF\033[0m"
                print(f"  [{key}] F{num:2d} {label:25s} {state_display}")
            print("-"*60)
            print("\nPremi tasto per toggle | TAB = Emergency Stop | q = Esci")

        # Disegna menu iniziale
        draw_menu()

        # Loop input carattere singolo
        running = True
        while running:
            if select.select([sys.stdin], [], [], 0.1)[0]:
                cmd = sys.stdin.read(1).lower()

                if cmd == 'q':
                    running = False
                elif cmd == '\t':
                    # Emergency stop (TAB) - sempre attivo anche nel menu funzioni
                    if self.track_power_on:
                        # Suono emergency stop (interruttore che scatta)
                        subprocess.Popen(['afplay', '/System/Library/Sounds/Frog.aiff'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        # Toglie corrente (emergenza immediata)
                        self.z21.track_power_off()
                        time.sleep(0.3)
                        # Ferma tutto
                        self.z21.emergency_stop_all()
                        time.sleep(0.1)
                        # Resetta velocità questa loco
                        self.speed = 0
                        self.z21.set_loco_speed(self.address, 0, self.forward)
                        self.track_power_on = False
                    else:
                        # Suono power on
                        subprocess.Popen(['afplay', '/System/Library/Sounds/Funk.aiff'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        # Riaccende corrente
                        self.z21.track_power_on()
                        self.track_power_on = True
                    # Ridisegna menu
                    draw_menu()
                elif cmd.isdigit():
                    num = int(cmd)
                    if num in functions:
                        is_lockable = functions[num]['lockable']

                        if is_lockable:
                            # Funzione toggle (lockable)
                            self.function_states[num] = not self.function_states[num]
                            self.z21.set_loco_function(function_address, num,
                                                      self.function_states[num],
                                                      self.function_states)

                            # F0 (luci) su consist: sincronizza su tutte le loco
                            if num == 0 and "CONSIST" in self.all_addresses.get(self.address, ""):
                                consist_locos = self.consists.get(self.address, [])
                                for loco in consist_locos:
                                    if loco['address'] != function_address:
                                        # Invia F0 anche alle altre loco del consist
                                        self.z21.set_loco_function(loco['address'], 0,
                                                                  self.function_states[0],
                                                                  self.function_states)
                                        time.sleep(0.05)

                            draw_menu()
                        else:
                            # Funzione momentanea (non lockable) - ON poi OFF
                            self.function_states[num] = True
                            self.z21.set_loco_function(function_address, num, True,
                                                      self.function_states)
                            draw_menu()
                            time.sleep(0.8)  # Mantieni attivo per 800ms
                            self.function_states[num] = False
                            self.z21.set_loco_function(function_address, num, False,
                                                      self.function_states)
                            draw_menu()

                elif 'a' <= cmd <= 's':
                    # a=F10, b=F11, ..., s=F28
                    num = 10 + (ord(cmd) - ord('a'))
                    if num in functions:
                        is_lockable = functions[num]['lockable']

                        if is_lockable:
                            # Funzione toggle (lockable)
                            self.function_states[num] = not self.function_states[num]
                            self.z21.set_loco_function(function_address, num,
                                                      self.function_states[num],
                                                      self.function_states)
                            draw_menu()
                        else:
                            # Funzione momentanea (non lockable) - ON poi OFF
                            self.function_states[num] = True
                            self.z21.set_loco_function(function_address, num, True,
                                                      self.function_states)
                            draw_menu()
                            time.sleep(0.8)  # Mantieni attivo per 800ms
                            self.function_states[num] = False
                            self.z21.set_loco_function(function_address, num, False,
                                                      self.function_states)
                            draw_menu()

    def list_locomotives(self):
        """List available locomotives."""
        print("\n\n" + "="*60)
        print("AVAILABLE LOCOMOTIVES AND CONSISTS")
        print("="*60)
        for addr, name in sorted(self.all_addresses.items()):
            current = " ← CURRENT" if addr == self.address else ""
            print(f"  {addr:2d} - {name}{current}")
        input("\nPress ENTER to continue...")

    def run(self):
        """Main controller loop."""
        print("\n" + "="*60)
        print(f"CONTROLLING: {self.all_addresses[self.address]}")
        print("="*60)

        # Special warning for loco in consist
        if "[IN CONSIST" in self.all_addresses.get(self.address, ""):
            print("\n⚠️  LOCOMOTIVE IN CONSIST:")
            print("   - MOVEMENT: ❌ Not controllable (use consist)")
            print("   - FUNCTIONS: ✅ Controllable (press 'f')")
            print("   - To control movement, select the consist\n")
        else:
            print("\n⚠️  IMPORTANT:")
            print("   - Locomotive must be on track")
            print("   - \\ = 0% | 1-9 = 10-90% | 0 = 100%")
            print("   - SPACE = gradual stop | TAB = EMERGENCY STOP toggle 🚨")
            print("   - Press 'h' for command help")
            print("   - Can coexist with JMRI (last command has priority)\n")

        input("Press ENTER to start control... ")

        # Sincronizza stato funzioni iniziale
        self._sync_function_states()

        # Pulisci schermo e mostra status completo
        self.show_status()

        # Salva impostazioni terminale
        old_settings = termios.tcgetattr(sys.stdin)

        try:
            # Metti terminale in modalità raw (cattura caratteri singoli)
            tty.setcbreak(sys.stdin.fileno())

            while self.running:
                # Controllo input non bloccante (timeout 0.1s)
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    cmd = sys.stdin.read(1)  # NON lowercase - serve per Shift+lettere

                    # Prima controlla Shift+lettere (A-Z maiuscole)
                    if cmd.isupper() and 'A' <= cmd <= 'Z':
                        # Shift+A-Z = toggle F0-F25
                        func_num = ord(cmd) - ord('A')
                        self.toggle_function(func_num)
                    elif cmd == ',':
                        # , = toggle F26
                        self.toggle_function(26)
                    elif cmd == '.':
                        # . = toggle F27
                        self.toggle_function(27)
                    elif cmd == '-':
                        # - = toggle F28
                        self.toggle_function(28)
                    elif cmd.lower() == 'w':
                        self.increase_speed(5)
                    elif cmd.lower() == 's':
                        self.decrease_speed(5)
                    elif cmd == ' ':
                        self.emergency_stop()
                    elif cmd == '\\':
                        # Velocità 0 (stop immediato)
                        self.set_speed_percent(0)
                    elif cmd == '\t':
                        # Emergency stop toggle (TAB)
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        if self.track_power_on:
                            # Suono emergency stop (interruttore che scatta)
                            subprocess.Popen(['afplay', '/System/Library/Sounds/Frog.aiff'],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            # Toglie corrente (emergenza immediata)
                            self.z21.track_power_off()
                            time.sleep(0.3)
                            # Ferma tutto
                            self.z21.emergency_stop_all()
                            time.sleep(0.1)
                            # Resetta velocità questa loco
                            self.speed = 0
                            self.z21.set_loco_speed(self.address, 0, self.forward)
                            self.track_power_on = False
                        else:
                            # Suono power on
                            subprocess.Popen(['afplay', '/System/Library/Sounds/Funk.aiff'],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            # Riaccende corrente
                            self.z21.track_power_on()
                            self.track_power_on = True
                        tty.setcbreak(sys.stdin.fileno())
                        self.show_status()
                    elif cmd.lower() == 'd':
                        self.toggle_direction()
                    elif cmd == '0':
                        # Velocità 100%
                        self.set_speed_percent(100)
                    elif cmd in '123456789':
                        # Velocità 10-90%
                        percent = int(cmd) * 10
                        self.set_speed_percent(percent)
                    elif cmd.lower() == 'l':
                        # Ripristina terminale per input normale
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        self.list_locomotives()
                        # Rimetti in modalità raw
                        tty.setcbreak(sys.stdin.fileno())
                        # Ridisegna display
                        self.show_status()
                    elif cmd.lower() == 'c':
                        # Ripristina terminale per input normale
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        self.emergency_stop()
                        time.sleep(0.5)
                        self.select_locomotive()
                        self.speed = 0
                        self.forward = True
                        # Sync funzioni nuova loco
                        self._sync_function_states()
                        # Rimetti in modalità raw
                        tty.setcbreak(sys.stdin.fileno())
                        # Ridisegna display
                        self.show_status()
                    elif cmd.lower() == 'f':
                        # Sync funzioni: rilegge stato da locomotiva e aggiorna display
                        self._sync_function_states()
                        self.show_status()
                    elif cmd.lower() == 'h':
                        # Ripristina terminale per input normale
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        self.show_help()
                        # Rimetti in modalità raw
                        tty.setcbreak(sys.stdin.fileno())
                        # Ridisegna display
                        self.show_status()
                    elif cmd.lower() == 'q':
                        print("\n\n👋 Exiting...")
                        self.emergency_stop()
                        time.sleep(0.5)
                        self.running = False

                # Polling periodico: sincronizza stato da Z21
                # (eseguito sempre ad ogni iterazione, non solo quando c'è input)
                now = time.time()
                if now - self.last_poll >= self.poll_interval:
                    if self._sync_state():
                        # Ridisegna UI solo se qualcosa è cambiato
                        self.show_status()
                    self.last_poll = now

        except KeyboardInterrupt:
            print("\n\n🛑 CTRL+C detected - STOP!")
        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            # Make sure to stop loco
            self.emergency_stop()
            time.sleep(0.3)
            self.z21.close()
            print("\n\n✅ Controller closed. Locomotive stopped.\n")


def main():
    """Entry point."""
    address = None
    if len(sys.argv) > 1:
        try:
            address = int(sys.argv[1])
        except ValueError:
            print(f"❌ Address non valido: {sys.argv[1]}")
            sys.exit(1)

    controller = LocoController(address)
    controller.run()


if __name__ == '__main__':
    main()
