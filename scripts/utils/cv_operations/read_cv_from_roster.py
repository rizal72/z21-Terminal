#!/usr/bin/env python3
"""
Legge le CV delle locomotive dal roster JMRI (file XML).

Uso:
    python read_cv_from_roster.py           # Lista tutte le locomotive
    python read_cv_from_roster.py 1        # Mostra CV della loco address 1
    python read_cv_from_roster.py 1 5      # Confronta loco 1 e 5
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, List


# Percorso roster JMRI
ROSTER_PATH = Path.home() / "Library/Preferences/JMRI/La_mia_Ferrovia_in_JMRI.jmri/roster"


class Locomotive:
    """Rappresenta una locomotiva con le sue CV."""

    def __init__(self, xml_file: Path):
        self.file = xml_file
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Leggi attributi base
        loco = root.find('locomotive')
        self.name = loco.get('id', 'Unknown')
        self.address = loco.get('dccAddress', '0')
        self.mfg = loco.get('mfg', '')
        self.model = loco.get('model', '')

        # Leggi decoder
        decoder = loco.find('decoder')
        self.decoder_model = decoder.get('model', 'Unknown') if decoder is not None else 'Unknown'
        self.decoder_family = decoder.get('family', '') if decoder is not None else ''

        # Leggi CV speed
        self.cv = self._read_cv(root)

    def _read_cv(self, root) -> Dict[int, int]:
        """Legge TUTTI i CV dal file XML."""
        cv = {}

        # Cerca tutti i tag CVvalue nel formato: <CVvalue name="2" value="2" />
        for cv_elem in root.findall('.//CVvalue'):
            cv_name = cv_elem.get('name', '')
            cv_value = cv_elem.get('value', '')

            if cv_name and cv_value:
                try:
                    cv[int(cv_name)] = int(cv_value)
                except ValueError:
                    pass  # Ignora CV con valori non numerici

        return cv

    def __str__(self) -> str:
        """Rappresentazione testuale."""
        # Mostra CV principali (speed control)
        cv2 = self.cv.get(2, '?')   # Vstart
        cv6 = self.cv.get(6, '?')   # Vmid
        cv5 = self.cv.get(5, '?')   # Vhigh

        result = f"{self.name} (addr {self.address})\n" \
                 f"  {self.mfg} {self.model}\n" \
                 f"  Decoder: {self.decoder_model}\n" \
                 f"  Speed CV: Vstart(2)={cv2}, Vmid(6)={cv6}, Vhigh(5)={cv5}\n"

        # Mostra tutti i CV configurati
        if self.cv:
            result += f"  Totale CV configurati: {len(self.cv)}\n"
            result += "  CV: "
            # Mostra CV in ordine, max 10 per riga
            cv_list = sorted(self.cv.items())
            for i, (cv_num, cv_val) in enumerate(cv_list):
                if i > 0 and i % 10 == 0:
                    result += "\n      "
                result += f"CV{cv_num}={cv_val} "
            result = result.rstrip()  # Remove trailing space

        return result


def load_all_locomotives() -> Dict[str, Locomotive]:
    """Carica tutte le locomotive dal roster."""
    locos = {}

    if not ROSTER_PATH.exists():
        print(f"[ERROR] Roster path non trovato: {ROSTER_PATH}")
        return locos

    for xml_file in ROSTER_PATH.glob("*.xml"):
        # Skip backup files and macOS metadata files
        if xml_file.name.endswith('.bak') or xml_file.name.startswith('._'):
            continue

        try:
            loco = Locomotive(xml_file)
            locos[loco.address] = loco
        except Exception as e:
            print(f"[ERROR] Errore leggendo {xml_file.name}: {e}")

    return locos


def compare_locomotives(loco1: Locomotive, loco2: Locomotive):
    """Confronta due locomotive e mostra i rapporti."""
    print(f"\n{'='*60}")
    print(f"CONFRONTO SINCRONIZZAZIONE")
    print(f"{'='*60}\n")

    print(f"Locomotiva 1: {loco1.name} (address {loco1.address})")
    print(f"  CV: {loco1.cv.get(2, '?')}/{loco1.cv.get(6, '?')}/{loco1.cv.get(5, '?')} (Vstart/Vmid/Vhigh)\n")

    print(f"Locomotiva 2: {loco2.name} (address {loco2.address})")
    print(f"  CV: {loco2.cv.get(2, '?')}/{loco2.cv.get(6, '?')}/{loco2.cv.get(5, '?')} (Vstart/Vmid/Vhigh)\n")

    # Calcola rapporti (CV2=Vstart, CV6=Vmid, CV5=Vhigh)
    if all(k in loco1.cv and k in loco2.cv for k in [2, 6, 5]):
        ratio_start = loco1.cv[2] / loco2.cv[2] if loco2.cv[2] != 0 else 0
        ratio_mid = loco1.cv[6] / loco2.cv[6] if loco2.cv[6] != 0 else 0
        ratio_high = loco1.cv[5] / loco2.cv[5] if loco2.cv[5] != 0 else 0

        print(f"Rapporti (Loco1/Loco2):")
        print(f"  Vstart (CV2): {ratio_start:.3f}")
        print(f"  Vmid (CV6):   {ratio_mid:.3f}")
        print(f"  Vhigh (CV5):  {ratio_high:.3f}")
    else:
        print("⚠️  CV speed incomplete, impossibile calcolare rapporti")


def main():
    """Funzione principale."""
    locos = load_all_locomotives()

    if not locos:
        print("❌ Nessuna locomotiva trovata nel roster")
        return

    # Se non ci sono argomenti, lista tutte le locomotive
    if len(sys.argv) == 1:
        print(f"\n{'='*60}")
        print(f"ROSTER LOCOMOTIVE ({len(locos)} trovate)")
        print(f"{'='*60}\n")

        for addr in sorted(locos.keys(), key=int):
            print(locos[addr])
            print()

        print("\nUso: python read_cv_from_roster.py <address> [<address2>]")
        print("     python read_cv_from_roster.py 1 5    # Confronta loco 1 e 5")
        return

    # Mostra dettagli locomotiva singola
    if len(sys.argv) == 2:
        addr = sys.argv[1]
        if addr in locos:
            print(f"\n{locos[addr]}\n")
        else:
            print(f"❌ Locomotiva con address {addr} non trovata")
            print(f"   Address disponibili: {', '.join(sorted(locos.keys(), key=int))}")
        return

    # Confronta due locomotive
    if len(sys.argv) == 3:
        addr1, addr2 = sys.argv[1], sys.argv[2]

        if addr1 not in locos:
            print(f"❌ Locomotiva con address {addr1} non trovata")
            return

        if addr2 not in locos:
            print(f"❌ Locomotiva con address {addr2} non trovata")
            return

        compare_locomotives(locos[addr1], locos[addr2])
        return


if __name__ == '__main__':
    main()
