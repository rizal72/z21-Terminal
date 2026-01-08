#!/usr/bin/env python3
"""
Test connessione diretta alla Roco Z21 via protocollo Z21 LAN (UDP).

Protocollo Z21 LAN:
- UDP porta 21105
- Formato pacchetto: [DataLen (2 bytes LE)] [Header (2 bytes LE)] [Data]
- Documentazione: https://www.z21.eu/media/Kwc_Basic_DownloadTag_Component/47-2811-3715-customerdata-z21-lan-protokoll-en.pdf
"""

import socket
import struct
import time
from typing import Tuple, Optional


# Configurazione Z21
Z21_IP = "192.168.1.111"
Z21_PORT = 21105
TIMEOUT = 2.0


class Z21:
    """Client per protocollo Z21 LAN."""

    # Header comandi principali
    LAN_GET_SERIAL_NUMBER = 0x10
    LAN_GET_HWINFO = 0x1A
    LAN_LOGOFF = 0x30
    LAN_X_SET_STOP = 0x0080  # Emergency stop (X-Bus)
    LAN_X_SET_TRACK_POWER_OFF = 0x0080  # Power off
    LAN_X_SET_TRACK_POWER_ON = 0x0081  # Power on
    LAN_GET_STATUS = 0x85
    LAN_SET_BROADCASTFLAGS = 0x50
    LAN_GET_BROADCASTFLAGS = 0x51
    LAN_GET_LOCOMODE = 0x60
    LAN_SET_LOCOMODE = 0x61
    LAN_GET_TURNOUTMODE = 0x70
    LAN_SET_TURNOUTMODE = 0x71
    LAN_GET_LOCO_INFO = 0xE3
    LAN_SET_LOCO_DRIVE = 0xE4
    LAN_SET_LOCO_FUNCTION = 0xE5

    def __init__(self, ip: str = Z21_IP, port: int = Z21_PORT, verbose: bool = True):
        self.ip = ip
        self.port = port
        self.verbose = verbose
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(TIMEOUT)
        if self.verbose:
            print(f"📡 Z21 Client inizializzato per {ip}:{port}")

    def _send_packet(self, header: int, data: bytes = b'') -> None:
        """Invia un pacchetto alla Z21."""
        data_len = 4 + len(data)  # header (2) + length (2) + data
        packet = struct.pack('<HH', data_len, header) + data
        self.sock.sendto(packet, (self.ip, self.port))

    def _receive_packet(self, timeout: float = TIMEOUT) -> Optional[Tuple[int, bytes]]:
        """Riceve un pacchetto dalla Z21."""
        self.sock.settimeout(timeout)
        try:
            data, addr = self.sock.recvfrom(1024)
            if len(data) < 4:
                return None

            data_len, header = struct.unpack('<HH', data[:4])
            payload = data[4:data_len]
            return header, payload
        except socket.timeout:
            return None

    def get_serial_number(self) -> Optional[int]:
        """Legge il numero seriale della Z21."""
        if self.verbose:
            print("\n🔍 Richiesta numero seriale Z21...")
        self._send_packet(self.LAN_GET_SERIAL_NUMBER)

        response = self._receive_packet()
        if response:
            header, data = response
            if header == self.LAN_GET_SERIAL_NUMBER and len(data) >= 4:
                serial = struct.unpack('<I', data[:4])[0]
                if self.verbose:
                    print(f"✅ Serial Number: {serial}")
                return serial
        if self.verbose:
            print("❌ Nessuna risposta")
        return None

    def get_hw_info(self) -> Optional[dict]:
        """Legge info hardware della Z21."""
        print("\n🔍 Richiesta info hardware Z21...")
        self._send_packet(self.LAN_GET_HWINFO)

        response = self._receive_packet()
        if response:
            header, data = response
            if header == self.LAN_GET_HWINFO and len(data) >= 8:
                hw_type, fw_version = struct.unpack('<II', data[:8])
                info = {
                    'hw_type': hw_type,
                    'fw_version': f"{(fw_version >> 8) & 0xFF}.{fw_version & 0xFF}"
                }
                print(f"✅ Hardware Type: 0x{hw_type:04X}")
                print(f"✅ Firmware Version: {info['fw_version']}")
                return info
        print("❌ Nessuna risposta")
        return None

    def get_status(self) -> Optional[dict]:
        """
        Legge lo stato del sistema Z21 + telemetria track-level.

        Returns:
            dict con:
            - track_power_on, emergency_stop, programming_mode, short_circuit
            - telemetry: {
                'main_current_ma': int,          # Track current (mA)
                'prog_current_ma': int,           # Programming track current (mA)
                'filtered_current_ma': int,       # Filtered track current (mA)
                'temperature_c': float,           # Z21 internal temp (°C)
                'supply_voltage_v': float,        # Input voltage (V)
                'vcc_voltage_v': float            # Logic voltage (V)
              }
            None se errore
        """
        if self.verbose:
            print("\n🔍 Richiesta stato sistema Z21...")

        self._send_packet(self.LAN_GET_STATUS)

        response = self._receive_packet(timeout=1.0)
        if response:
            header, data = response
            # LAN_STATUS_CHANGED è 0x84
            if header == 0x84 and len(data) >= 13:
                # Format: MainCurrent(2) ProgCurrent(2) FilteredMainCurrent(2)
                #         Temperature(2) SupplyVoltage(2) VCCVoltage(2) CentralState(1) CentralStateEx(1)

                # Parse telemetry data (bytes 0-11, little-endian uint16)
                main_current = struct.unpack('<H', data[0:2])[0]
                prog_current = struct.unpack('<H', data[2:4])[0]
                filtered_current = struct.unpack('<H', data[4:6])[0]
                temperature = struct.unpack('<H', data[6:8])[0]
                supply_voltage = struct.unpack('<H', data[8:10])[0]
                vcc_voltage = struct.unpack('<H', data[10:12])[0]

                # Parse CentralState (byte 12)
                central_state = data[12]

                # Parse CentralState bits
                # Bit 0: emergency stop active
                # Bit 1: track voltage off
                # Bit 2: short circuit
                # Bit 3: programming mode active
                emergency_stop = bool(central_state & 0x01)
                track_power_off = bool(central_state & 0x02)
                short_circuit = bool(central_state & 0x04)
                programming_mode = bool(central_state & 0x08)

                result = {
                    'track_power_on': not track_power_off,
                    'emergency_stop': emergency_stop,
                    'programming_mode': programming_mode,
                    'short_circuit': short_circuit,
                    'telemetry': {
                        'main_current_ma': main_current,
                        'prog_current_ma': prog_current,
                        'filtered_current_ma': filtered_current,
                        'temperature_c': float(temperature),  # Stored as °C (integer)
                        'supply_voltage_v': supply_voltage / 1000.0,  # Stored as mV
                        'vcc_voltage_v': vcc_voltage / 1000.0
                    }
                }

                if self.verbose:
                    print(f"✅ Status: Power={'ON' if result['track_power_on'] else 'OFF'}, "
                          f"Emergency={'YES' if emergency_stop else 'NO'}")
                    print(f"📊 Telemetry: Current={main_current}mA, "
                          f"Voltage={supply_voltage/1000.0:.1f}V, "
                          f"Temp={float(temperature):.1f}°C")

                return result

            if self.verbose:
                print(f"⚠️  Risposta inattesa (header: 0x{header:04X}, data: {data.hex()})")

        if self.verbose:
            print("❌ Nessuna risposta")
        return None

    def get_loco_info(self, address: int) -> Optional[dict]:
        """
        Legge info complete su una locomotiva (velocità, direzione, funzioni).

        Returns:
            dict con 'speed', 'forward', 'functions' (dict F0-F28)
            None se errore
        """
        if self.verbose:
            print(f"\n🚂 Richiesta info locomotiva address {address}...")

        # Prepara richiesta XpressNet: 0xE3 0xF0 [MSB addr] [LSB addr] [XOR]
        msb = (address >> 8) & 0x3F
        lsb = address & 0xFF

        xpressnet_data = bytes([0xE3, 0xF0, msb, lsb])
        xor = 0
        for b in xpressnet_data:
            xor ^= b

        data = xpressnet_data + bytes([xor])
        self._send_packet(0x0040, data)  # X-Bus tunnel

        response = self._receive_packet(timeout=1.0)
        if not response:
            if self.verbose:
                print("❌ Nessuna risposta")
            return None

        header, resp_data = response

        # Risposta: header 0x0040, data: [0xEF] [subheader] [addr MSB] [addr LSB] [speed/dir] [F0-F4] [F5-F12] [F13-F20] [F21-F28] [XOR]
        if len(resp_data) < 8 or resp_data[0] != 0xEF:
            if self.verbose:
                print(f"❌ Risposta non valida: {resp_data.hex()}")
            return None

        # Parse risposta
        speed_dir_byte = resp_data[4]
        direction = bool(speed_dir_byte & 0x80)
        speed = speed_dir_byte & 0x7F

        # Parse funzioni
        functions = {}

        # F0-F4 (byte 5)
        if len(resp_data) > 5:
            f0_f4_byte = resp_data[5]
            functions[0] = bool(f0_f4_byte & 0x10)  # F0 è bit 4
            for i in range(1, 5):
                functions[i] = bool(f0_f4_byte & (1 << (i - 1)))

        # F5-F12 (byte 6)
        if len(resp_data) > 6:
            f5_f12_byte = resp_data[6]
            for i in range(5, 13):
                functions[i] = bool(f5_f12_byte & (1 << (i - 5)))

        # F13-F20 (byte 7)
        if len(resp_data) > 7:
            f13_f20_byte = resp_data[7]
            for i in range(13, 21):
                functions[i] = bool(f13_f20_byte & (1 << (i - 13)))

        # F21-F28 (byte 8)
        if len(resp_data) > 8:
            f21_f28_byte = resp_data[8]
            for i in range(21, 29):
                functions[i] = bool(f21_f28_byte & (1 << (i - 21)))

        result = {
            'speed': speed,
            'forward': direction,
            'functions': functions
        }

        if self.verbose:
            print(f"✅ Loco {address}: speed={speed}, dir={'FWD' if direction else 'REV'}")
            active_funcs = [f"F{k}" for k, v in functions.items() if v]
            if active_funcs:
                print(f"   Funzioni attive: {', '.join(active_funcs)}")
            else:
                print(f"   Nessuna funzione attiva")

        return result

    def set_loco_speed(self, address: int, speed: int, forward: bool = True) -> bool:
        """
        Imposta velocità locomotiva.

        Args:
            address: Indirizzo DCC locomotiva
            speed: Velocità 0-126 (0=stop, 1=emergency stop, 2-127=speed)
            forward: True=avanti, False=indietro
        """
        if self.verbose:
            print(f"\n🚂 Comando locomotiva address {address}: speed={speed}, forward={forward}")

        # XpressNet LAN_X_SET_LOCO_DRIVE format
        msb = (address >> 8) & 0x3F
        lsb = address & 0xFF

        # Speed/direction byte: bit 7=direction, bits 0-6=speed
        direction_bit = 0x80 if forward else 0x00
        speed_byte = direction_bit | (speed & 0x7F)

        # XpressNet command wrapped in Z21 LAN packet
        # Header 0x0040 = X-Bus tunnel
        xpressnet_data = bytes([0xE4, 0x13, msb, lsb, speed_byte])
        xor = 0
        for b in xpressnet_data:
            xor ^= b

        data = xpressnet_data + bytes([xor])

        if self.verbose:
            print(f"   Address: {address} (MSB={msb:02X}, LSB={lsb:02X})")
            print(f"   Speed byte: 0x{speed_byte:02X}")
            print(f"   Packet: {data.hex()}")

        self._send_packet(0x0040, data)  # Usa header X-Bus tunnel

        # Aspetta eventuali risposte (errori)
        if self.verbose:
            print("   Attendo risposta Z21...")
        response = self._receive_packet(timeout=0.5)
        if self.verbose:
            if response:
                header, resp_data = response
                print(f"   Risposta: header=0x{header:04X}, data={resp_data.hex()}")
            else:
                print("   Nessuna risposta (normale)")
            print("✅ Comando inviato")
        return True

    def emergency_stop_all(self) -> bool:
        """
        STOP DI EMERGENZA - ferma tutte le locomotive immediatamente.
        Equivalente al pulsante STOP della Z21.
        """
        if self.verbose:
            print(f"\n🚨 EMERGENCY STOP - Fermo tutte le locomotive!")

        # XpressNet command: STOP (0x80 0x80)
        xpressnet_data = bytes([0x80, 0x80])
        xor = 0x80 ^ 0x80

        data = xpressnet_data + bytes([xor])
        self._send_packet(0x0040, data)  # X-Bus tunnel

        if self.verbose:
            print("✅ Comando STOP inviato")
        return True

    def track_power_off(self) -> bool:
        """
        Spegne la corrente sui binari.
        """
        if self.verbose:
            print(f"\n⚡ POWER OFF - Spengo corrente binari")

        # XpressNet command: Track power off (0x21 0x80)
        xpressnet_data = bytes([0x21, 0x80])
        xor = 0x21 ^ 0x80

        data = xpressnet_data + bytes([xor])
        self._send_packet(0x0040, data)  # X-Bus tunnel

        if self.verbose:
            print("✅ Comando POWER OFF inviato")
        return True

    def track_power_on(self) -> bool:
        """
        Accende la corrente sui binari.
        """
        if self.verbose:
            print(f"\n⚡ POWER ON - Accendo corrente binari")

        # XpressNet command: Track power on (0x21 0x81)
        xpressnet_data = bytes([0x21, 0x81])
        xor = 0x21 ^ 0x81

        data = xpressnet_data + bytes([xor])
        self._send_packet(0x0040, data)  # X-Bus tunnel

        if self.verbose:
            print("✅ Comando POWER ON inviato")
        return True

    def set_loco_function(self, address: int, function_num: int, state: bool,
                          function_states: dict = None) -> bool:
        """
        Imposta stato di una funzione (F0-F28).

        Args:
            address: Indirizzo DCC locomotiva
            function_num: Numero funzione 0-28
            state: True=ON, False=OFF
            function_states: Dict con stato corrente di tutte le funzioni (opzionale)

        Returns:
            True se comando inviato con successo
        """
        if self.verbose:
            print(f"\n🔧 Funzione F{function_num} → {'ON' if state else 'OFF'} (loco {address})")

        msb = (address >> 8) & 0x3F
        lsb = address & 0xFF

        # Se non abbiamo lo stato completo, usiamo solo la funzione richiesta
        if function_states is None:
            function_states = {function_num: state}

        # Determina gruppo funzione e costruisci comando con stato completo del gruppo
        # Protocollo XpressNet wrappato in Z21 LAN (header 0x0040)
        if function_num <= 4:
            # Gruppo 1: F0-F4 → subheader 0x20
            # Byte: [F0:bit4 | F4:bit3 | F3:bit2 | F2:bit1 | F1:bit0]
            subheader = 0x20
            func_byte = 0
            if function_states.get(0, False):
                func_byte |= 0x10
            for i in range(1, 5):
                if function_states.get(i, False):
                    func_byte |= (1 << (i - 1))
        elif function_num <= 8:
            # Gruppo 2: F5-F8 → subheader 0x21
            # Byte: [F8:bit3 | F7:bit2 | F6:bit1 | F5:bit0]
            subheader = 0x21
            func_byte = 0
            for i in range(5, 9):
                if function_states.get(i, False):
                    func_byte |= (1 << (i - 5))
        elif function_num <= 12:
            # Gruppo 3: F9-F12 → subheader 0x22
            # Byte: [F12:bit3 | F11:bit2 | F10:bit1 | F9:bit0]
            subheader = 0x22
            func_byte = 0
            for i in range(9, 13):
                if function_states.get(i, False):
                    func_byte |= (1 << (i - 9))
        elif function_num <= 20:
            # Gruppo 4: F13-F20 → subheader 0x23
            # Byte: F13-F20 in 8 bit
            subheader = 0x23
            func_byte = 0
            for i in range(13, 21):
                if function_states.get(i, False):
                    func_byte |= (1 << (i - 13))
        elif function_num <= 28:
            # Gruppo 5: F21-F28 → subheader 0x28 (NOTA: 0x28 NON 0x24!)
            # Byte: F21-F28 in 8 bit
            subheader = 0x28
            func_byte = 0
            for i in range(21, 29):
                if function_states.get(i, False):
                    func_byte |= (1 << (i - 21))
        else:
            if self.verbose:
                print(f"❌ Funzione F{function_num} non valida (0-28)")
            return False

        xpressnet_data = bytes([0xE4, subheader, msb, lsb, func_byte])
        xor = 0
        for b in xpressnet_data:
            xor ^= b

        data = xpressnet_data + bytes([xor])

        if self.verbose:
            print(f"   Packet: {data.hex()}")

        self._send_packet(0x0040, data)  # X-Bus tunnel

        if self.verbose:
            print("✅ Comando funzione inviato")
        return True

    def read_cv_on_main(self, address: int, cv_number: int, timeout: float = 2.0, retries: int = 3) -> Optional[int]:
        """
        Legge un CV in POM (Program On Main / operations mode) usando Ops Byte Verify.

        ⚠️  NOTA: Successo ~50% su decoder ESU (instabile)
        Consigliato: retry multipli (default 3)

        NOTA decoder:
        - ❌ Hornby TXS (loco 7): Non supporta POM Read
        - ⚠️  ESU LokPilot/LokSound: Supportano ma instabile (~50% successo)
        - ✅ Comando XpressNet: E6 30 [addr] [E4] [cv_lsb] [xor]

        Args:
            address: DCC address della locomotiva
            cv_number: Numero CV da leggere (1-1024)
            timeout: Timeout in secondi per attesa risposta (default 2s)
            retries: Numero di tentativi con pausa 2s tra ognuno (default 3)

        Returns:
            Valore CV (0-255) o None se errore/timeout
        """
        if self.verbose:
            print(f"\n📖 Lettura CV{cv_number} da address {address} (POM - Ops Byte Read)...")

        # Prima "sveglia" la locomotiva con una query
        if self.verbose:
            print("   Sveglia locomotiva...")
        self.get_loco_info(address)
        time.sleep(0.3)

        # CV number nel protocollo parte da 0 (CV1 = 0)
        cv_address = cv_number - 1

        # Prepara comando XpressNet POM Verify: 0xE6 0x30 [MSB addr] [LSB addr] [CV_MSB] [CV_LSB] [value] [XOR]
        # 0xE6 = POM operations
        # 0x30 = Ops Byte Verify (con valore "guess" - JMRI usa 0x00)
        msb = (address >> 8) & 0x3F
        lsb = address & 0xFF
        # CV_MSB formato XpressNet POM Verify: 0xE4 | bit[9:8] del CV
        # 0xE4 = 1110 0100 = [1110:prefix] [01:byte verify mode] [00:CV bit 9-8]
        cv_msb = 0xE4 | ((cv_address >> 8) & 0x03)  # E4 per CV<256, E5 per CV<512, etc.
        cv_lsb = cv_address & 0xFF
        value_guess = 0x00  # Valore "guess" (JMRI usa 0, risposta contiene valore reale)

        xpressnet_data = bytes([0xE6, 0x30, msb, lsb, cv_msb, cv_lsb, value_guess])
        xor = 0
        for b in xpressnet_data:
            xor ^= b

        data = xpressnet_data + bytes([xor])

        # Riprova fino a N volte
        for attempt in range(retries):
            if attempt > 0:
                if self.verbose:
                    print(f"   Retry {attempt}/{retries-1}...")
                time.sleep(2.0)  # Pausa 2s tra i tentativi (decoder ESU instabile)

            if self.verbose:
                print(f"   Packet: {data.hex()}")

            # Invia comando
            self._send_packet(0x0040, data)  # X-Bus tunnel

            # Attendi risposta: 0x64 0x14 [addr_msb] [addr_lsb] [value] [XOR]
            # oppure: 0x61 per errori
            start_time = time.time()
            got_error = False

            while time.time() - start_time < timeout:
                response = self._receive_packet(timeout=0.5)
                if response:
                    header, payload = response

                    # Risposta è X-Bus tunnel (0x0040)
                    if header == 0x0040 and len(payload) >= 2:
                        # Controllo errori XpressNet (0x61)
                        if payload[0] == 0x61:
                            if self.verbose:
                                print(f"   ⚠️  Error 0x{payload[1]:02x}")
                            got_error = True
                            break  # Esci dal while, riprova nel for

                        # Risposta ACK verify: 0x64 0x14 [addr_msb] [addr_lsb] [value] [xor]
                        if len(payload) >= 6 and payload[0] == 0x64 and payload[1] == 0x14:
                            # Il valore è nel byte 5 (indice 4)
                            value = payload[4]

                            if self.verbose:
                                print(f"✅ CV{cv_number} = {value}")
                            return value

            # Se abbiamo ricevuto errore, riprova
            if got_error:
                continue

        if self.verbose:
            print(f"❌ Nessuna risposta dopo {retries} tentativi")
            print("   Possibili cause:")
            print("   - Decoder non supporta CV read in operations mode (POM)")
            print("   - Locomotiva non sul binario o spenta")
            print("   - Binari senza corrente (power off)")
        return None

    def write_cv_ops_mode(self, address: int, cv_number: int, value: int, timeout: float = 3.0) -> bool:
        """
        Scrive un CV in operations mode (POM - Program On Main).
        La locomotiva può essere sul binario principale, anche in movimento.

        Comando XpressNet: E6 30 [addr_msb] [addr_lsb] [cv_msb] [cv_lsb] [value] [xor]

        Args:
            address: DCC address della locomotiva
            cv_number: Numero CV da scrivere (1-1024)
            value: Valore da scrivere (0-255)
            timeout: Timeout in secondi (default 3s)

        Returns:
            True se scrittura confermata, False se errore/timeout
        """
        if not (0 <= value <= 255):
            if self.verbose:
                print(f"❌ Valore CV fuori range: {value} (deve essere 0-255)")
            return False

        if self.verbose:
            print(f"\n✍️  Scrittura CV{cv_number} = {value} su address {address} (POM - Ops Mode Write)...")

        # Prima "sveglia" la locomotiva
        if self.verbose:
            print("   Sveglia locomotiva...")
        self.get_loco_info(address)
        time.sleep(0.3)

        # CV number nel protocollo parte da 0 (CV1 = 0)
        cv_address = cv_number - 1

        # Prepara comando XpressNet POM Write: 0xE6 0x30 [MSB addr] [LSB addr] [CV_MSB] [CV_LSB] [value] [XOR]
        # 0xE6 = POM (Program On Main) operations
        # 0x30 = Ops Byte Write
        msb = (address >> 8) & 0x3F
        lsb = address & 0xFF
        # CV_MSB formato XpressNet POM: 0xEC | bit[9:8] del CV
        # 0xEC = 1110 1100 = [1110:prefix] [11:byte write mode] [00:CV bit 9-8]
        cv_msb = 0xEC | ((cv_address >> 8) & 0x03)  # EC per CV<256, ED per CV<512, etc.
        cv_lsb = cv_address & 0xFF

        xpressnet_data = bytes([0xE6, 0x30, msb, lsb, cv_msb, cv_lsb, value])
        xor = 0
        for b in xpressnet_data:
            xor ^= b

        data = xpressnet_data + bytes([xor])

        if self.verbose:
            print(f"   Packet: {data.hex()}")

        # Invia comando
        self._send_packet(0x0040, data)  # X-Bus tunnel

        # WRITE (E6 30): Z21 NON invia ACK, solo errori!
        # Aspetta solo eventuali errori per 500ms
        start_time = time.time()
        error_timeout = 0.5

        while time.time() - start_time < error_timeout:
            response = self._receive_packet(timeout=0.2)
            if response:
                header, payload = response

                # Risposta è X-Bus tunnel (0x0040)
                if header == 0x0040 and len(payload) >= 2:
                    if self.verbose:
                        print(f"   Risposta: {payload.hex()}")

                    # Controllo errori XpressNet (0x61)
                    if payload[0] == 0x61:
                        error_code = payload[1]
                        error_msgs = {
                            0x01: "Command rejected (busy)",
                            0x02: "Instruction not supported",
                            0x82: "No loco on track"
                        }
                        error_msg = error_msgs.get(error_code, f"Unknown error 0x{error_code:02x}")
                        if self.verbose:
                            print(f"❌ Error: {error_msg}")
                        return False

        # Nessun errore = successo!
        if self.verbose:
            print(f"✅ CV{cv_number} scritto = {value}")
            print("   (Z21 non invia ACK per write, solo errori)")
        return True

    def close(self):
        """Chiude la connessione."""
        self._send_packet(self.LAN_LOGOFF)
        self.sock.close()
        if self.verbose:
            print("\n👋 Connessione Z21 chiusa")


def main():
    """Test connessione Z21."""
    print("=" * 60)
    print("TEST PROTOCOLLO Z21 LAN")
    print("=" * 60)

    z21 = Z21()

    try:
        # Test 1: Serial Number
        serial = z21.get_serial_number()

        # Test 2: Hardware Info
        hw_info = z21.get_hw_info()

        # Test 3: Status
        status = z21.get_status()

        # Test 4: Info locomotiva address 1
        loco_info = z21.get_loco_info(1)

        print("\n" + "=" * 60)
        print("TEST COMPLETATO")
        print("=" * 60)

        if serial or hw_info:
            print("✅ Connessione Z21 funzionante!")
            print("\n⚠️  Per controllare le locomotive usa:")
            print("   z21.set_loco_speed(address=1, speed=20, forward=True)")
        else:
            print("❌ Impossibile comunicare con Z21")
            print("   Verifica:")
            print("   - Z21 accesa e connessa alla rete")
            print("   - IP corretto: 192.168.1.111")
            print("   - Firewall/router non blocca UDP porta 21105")

    finally:
        z21.close()


if __name__ == '__main__':
    main()
