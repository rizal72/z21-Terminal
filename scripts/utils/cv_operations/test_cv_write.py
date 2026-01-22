#!/usr/bin/env python3
"""
Test CV write in operations mode (POM) via Z21.

Usage:
    python test_cv_write.py <address> <cv_number> <value> [restore_value]

Examples:
    python test_cv_write.py 2 4 20          # Write CV4=20 on loco 2
    python test_cv_write.py 2 4 20 14       # Write CV4=20, then restore to 14
"""

import sys
import os

# Add scripts to path (z21.py is in scripts/)
scripts_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, scripts_path)

from z21 import Z21


def main():
    if len(sys.argv) < 4:
        print("Usage: python test_cv_write.py <address> <cv_number> <value> [restore_value]")
        print()
        print("Examples:")
        print("  python test_cv_write.py 2 4 20          # Write CV4=20 on loco 2")
        print("  python test_cv_write.py 2 4 20 14       # Write CV4=20, then restore to 14")
        return

    address = int(sys.argv[1])
    cv_number = int(sys.argv[2])
    value = int(sys.argv[3])
    restore_value = int(sys.argv[4]) if len(sys.argv) > 4 else None

    print("=" * 60)
    print("TEST CV WRITE IN OPERATIONS MODE")
    print("=" * 60)
    print()
    print(f"Locomotiva: address {address}")
    print(f"CV da scrivere: CV{cv_number} = {value}")
    if restore_value is not None:
        print(f"Valore da ripristinare dopo: {restore_value}")
    print()
    print("⚠️  IMPORTANTE: Locomotiva deve essere sul binario con power ON")
    print()

    # Connetti a Z21
    z21 = Z21(verbose=True)

    try:
        # Verifica connessione
        serial = z21.get_serial_number()
        if not serial:
            print("❌ Impossibile connettersi a Z21")
            return

        # Test scrittura
        print("\n" + "=" * 60)
        print(f"TEST: Scrittura CV{cv_number} = {value}")
        print("=" * 60)

        success = z21.write_cv_ops_mode(
            address=address,
            cv_number=cv_number,
            value=value
        )

        if success:
            print(f"\n✅ Test SUPERATO!")
            print(f"   CV{cv_number} = {value} scritto con successo")

            # Ripristina valore originale se richiesto
            if restore_value is not None:
                input(f"\nPremi INVIO per ripristinare CV{cv_number} = {restore_value}...")

                print("\n" + "=" * 60)
                print(f"RIPRISTINO: CV{cv_number} = {restore_value}")
                print("=" * 60)

                success2 = z21.write_cv_ops_mode(
                    address=address,
                    cv_number=cv_number,
                    value=restore_value
                )

                if success2:
                    print(f"\n✅ CV{cv_number} ripristinato a {restore_value}")
                else:
                    print(f"\n⚠️  Ripristino fallito, ripristinare manualmente CV{cv_number}={restore_value}")
        else:
            print("\n❌ Test FALLITO: CV write non funziona")

    finally:
        z21.close()


if __name__ == '__main__':
    main()
