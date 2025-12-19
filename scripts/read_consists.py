#!/usr/bin/env python3
"""
Legge e visualizza la configurazione dei consist da JMRI.

Uso:
    python read_consists.py           # Mostra tutti i consist
    python read_consists.py 10        # Mostra dettagli consist 10
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple


# Percorsi JMRI
ROSTER_PATH = Path.home() / "Library/Preferences/JMRI/La_mia_Ferrovia_in_JMRI.jmri/roster"
CONSIST_FILE = ROSTER_PATH / "consist" / "consist.xml"


class ConsistLoco:
    """Rappresenta una locomotiva in un consist."""

    def __init__(self, address: str, long_address: bool, direction: str, role: str, roster_id: str):
        self.address = address
        self.long_address = long_address
        self.direction = direction
        self.role = role
        self.roster_id = roster_id
        self.cv = self._load_cv()

    def _load_cv(self) -> Dict[str, int]:
        """Carica le CV dal roster."""
        cv = {}

        # Cerca il file roster
        for xml_file in ROSTER_PATH.glob("*.xml"):
            if xml_file.name.endswith('.bak'):
                continue

            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                loco = root.find('locomotive')

                if loco.get('dccAddress') == self.address:
                    # Leggi CV
                    values = root.find('.//values/decoderDef')
                    if values is not None:
                        for var in values.findall('varValue'):
                            item = var.get('item', '')
                            value = var.get('value', '')

                            if item == 'Vstart':
                                cv['vstart'] = int(value)
                            elif item == 'Vmid':
                                cv['vmid'] = int(value)
                            elif item == 'Vhigh':
                                cv['vhigh'] = int(value)
                    break
            except:
                continue

        return cv

    def cv_string(self) -> str:
        """Ritorna stringa CV formattata."""
        if not self.cv:
            return "CV: non disponibili"
        return f"CV: {self.cv.get('vstart', '?')}/{self.cv.get('vmid', '?')}/{self.cv.get('vhigh', '?')}"


class Consist:
    """Rappresenta un consist completo."""

    def __init__(self, consist_id: str, number: str, long_address: bool, consist_type: str):
        self.id = consist_id
        self.number = number
        self.long_address = long_address
        self.type = consist_type
        self.locomotives: List[ConsistLoco] = []

    def add_loco(self, loco: ConsistLoco):
        """Aggiunge una locomotiva al consist."""
        self.locomotives.append(loco)

    def get_lead(self) -> ConsistLoco:
        """Ritorna la locomotiva lead."""
        for loco in self.locomotives:
            if loco.role == 'lead':
                return loco
        return self.locomotives[0] if self.locomotives else None

    def get_rear(self) -> ConsistLoco:
        """Ritorna la locomotiva rear."""
        for loco in self.locomotives:
            if loco.role == 'rear':
                return loco
        return None

    def __str__(self) -> str:
        """Rappresentazione testuale."""
        output = []
        output.append(f"\n{'='*60}")
        output.append(f"CONSIST {self.number} ({self.type})")
        output.append(f"{'='*60}\n")

        # Controlla se consist è vuoto
        if not self.locomotives:
            output.append("⚠️  Consist vuoto (nessuna locomotiva)")
            return '\n'.join(output)

        lead = self.get_lead()
        rear = self.get_rear()

        if lead:
            output.append(f"LEAD 🔊: Address {lead.address} - {lead.roster_id}")
            output.append(f"  Direction: {lead.direction}")
            output.append(f"  {lead.cv_string()}\n")
        else:
            output.append("⚠️  Lead non definita\n")

        if rear:
            output.append(f"REAR: Address {rear.address} - {rear.roster_id}")
            output.append(f"  Direction: {rear.direction}")
            output.append(f"  {rear.cv_string()}")
        else:
            if len(self.locomotives) == 1:
                output.append("⚠️  Consist incompleto (solo 1 locomotiva)")

        # Calcola rapporti se possibile
        if lead and rear and lead.cv and rear.cv:
            if all(k in lead.cv and k in rear.cv for k in ['vstart', 'vmid', 'vhigh']):
                output.append("\nRapporti sincronizzazione (Lead/Rear):")

                r_start = lead.cv['vstart'] / rear.cv['vstart'] if rear.cv['vstart'] != 0 else 0
                r_mid = lead.cv['vmid'] / rear.cv['vmid'] if rear.cv['vmid'] != 0 else 0
                r_high = lead.cv['vhigh'] / rear.cv['vhigh'] if rear.cv['vhigh'] != 0 else 0

                output.append(f"  Vstart: {r_start:.3f}")
                output.append(f"  Vmid:   {r_mid:.3f}")
                output.append(f"  Vhigh:  {r_high:.3f}")

        return '\n'.join(output)


def load_consists() -> Dict[str, Consist]:
    """Carica tutti i consist dal file JMRI."""
    consists = {}

    if not CONSIST_FILE.exists():
        print(f"❌ File consist non trovato: {CONSIST_FILE}")
        return consists

    try:
        tree = ET.parse(CONSIST_FILE)
        root = tree.getroot()

        for consist_elem in root.findall('.//consist'):
            consist_id = consist_elem.get('id', '')
            consist_num = consist_elem.get('consistNumber', '')
            long_addr = consist_elem.get('longAddress', 'no') == 'yes'
            consist_type = consist_elem.get('type', 'Unknown')

            consist = Consist(consist_id, consist_num, long_addr, consist_type)

            # Carica locomotive
            for loco_elem in consist_elem.findall('loco'):
                loco = ConsistLoco(
                    address=loco_elem.get('dccLocoAddress', ''),
                    long_address=loco_elem.get('longAddress', 'no') == 'yes',
                    direction=loco_elem.get('locoDir', 'normal'),
                    role=loco_elem.get('locoName', ''),
                    roster_id=loco_elem.get('locoRosterId', '')
                )
                consist.add_loco(loco)

            consists[consist_num] = consist

    except Exception as e:
        print(f"❌ Errore leggendo consist: {e}")

    return consists


def main():
    """Funzione principale."""
    consists = load_consists()

    if not consists:
        print("❌ Nessun consist trovato")
        return

    # Se non ci sono argomenti, lista tutti i consist
    if len(sys.argv) == 1:
        print(f"\n{'='*60}")
        print(f"CONSIST CONFIGURATI ({len(consists)} trovati)")
        print(f"{'='*60}")

        for num in sorted(consists.keys(), key=int):
            print(consists[num])
            print()

        print("\nUso: python read_consists.py <numero_consist>")
        print("     python read_consists.py 10")
        return

    # Mostra dettagli consist specifico
    consist_num = sys.argv[1]

    if consist_num in consists:
        print(consists[consist_num])
        print()
    else:
        print(f"❌ Consist {consist_num} non trovato")
        print(f"   Consist disponibili: {', '.join(sorted(consists.keys(), key=int))}")


if __name__ == '__main__':
    main()
