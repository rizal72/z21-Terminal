# Z21 LAN Protocol - Technical Details

Dettagli tecnici completi del protocollo Z21 LAN (UDP).

Per info essenziali, vedi main CLAUDE.md file.

---

## Informazioni Connessione

- **IP Z21**: 192.168.1.111
- **Porta**: 21105 (UDP)
- **Protocollo**: Z21 LAN Protocol
- **Documentazione**: https://www.z21.eu (Z21 LAN Protocol PDF)

## Hardware Z21 Rilevato

- **Serial Number**: 111466
- **Hardware Type**: 0x0203 (Z21 White Edition)
- **Firmware Version**: 1.67

## Z21 Hardware Behavior

### Track Power Default on Startup

La Z21 **ripristina sempre track power ON** all'accensione:

```
Scenario: Spegni Z21 (con power ON o OFF, non importa)
→ Riaccendi Z21: track power SEMPRE ON (luce blu)
```

**z21-Terminal Sync**:
- ✅ Backend rileva automaticamente stato da Z21 (~5s health check)
- ✅ Frontend badge/button riflettono stato reale
- ✅ Locomotive non ripartono (speed=0 nel backend state)

**Note**: Comportamento standard Z21 - track power ON è default sicuro perché locomotive hanno comunque speed=0 dopo startup sistema.

## Formato Pacchetti Z21

- **Little Endian** per length e header
- **Header 0x0040** per X-Bus tunnel (comandi XpressNet)
- **XOR checksum** per comandi XpressNet

## Timeout

- Comandi info: risposta immediata
- Comandi movimento: nessuna risposta (fire-and-forget)
- Timeout default: 2 secondi

## Comandi LAN Implementati

### ✅ Comandi Funzionanti

1. **LAN_GET_SERIAL_NUMBER** (0x10) - Lettura serial number
2. **LAN_GET_HWINFO** (0x1A) - Lettura info hardware/firmware
3. **LAN_GET_STATUS** (0x85) - Lettura stato sistema
4. **LAN_X_GET_LOCO_INFO** (0x0040 X-Bus 0xE3 0xF0) - Lettura stato locomotiva completo
5. **LAN_X_SET_LOCO_DRIVE** (0x0040 X-Bus 0xE4 0x13) - Controllo movimento locomotive
6. **LAN_X_SET_LOCO_FUNCTION** (0x0040 X-Bus 0xE4 0x20-0x28) - Controllo funzioni F0-F28
7. **LAN_X_SET_STOP** (0x0040 X-Bus 0x80 0x80) - Emergency stop
8. **LAN_X_SET_TRACK_POWER** (0x0040 X-Bus 0x21 0x80/0x81) - Power ON/OFF

## Comandi XpressNet Implementati

### Lettura informazioni locomotiva (0xE3 0xF0)

**Richiesta**:
```
[0xE3] [0xF0] [MSB addr] [LSB addr] [XOR]
```

**Risposta**:
```
[0xEF] [subheader] [addr] [speed/dir] [F0-F4] [F5-F12] [F13-F20] [F21-F28] [XOR]
```

- Parsing bit per bit di tutte le 29 funzioni (F0-F28)
- Usato per sincronizzazione stato controller

### Controllo movimento (0xE4 0x13)

**Formato**:
```
[0xE4] [0x13] [MSB] [LSB] [speed/dir] [XOR]
```

- **Bit 7** del byte speed = direzione (1=avanti, 0=indietro)
- **Bits 0-6** = velocità (0-126)

### Controllo funzioni (0xE4 0x20-0x28)

**Gruppi funzioni**:
- Gruppo 1 (F0-F4): subheader **0x20**
- Gruppo 2 (F5-F8): subheader **0x21**
- Gruppo 3 (F9-F12): subheader **0x22**
- Gruppo 4 (F13-F20): subheader **0x23**
- Gruppo 5 (F21-F28): subheader **0x28**

⚠️ **NOTA**: Ogni comando invia stato completo del gruppo (non toggle singolo bit)

### Emergency stop (0x80 0x80)

Ferma tutte le locomotive immediatamente.

### Track power (0x21 0x80 / 0x21 0x81)

- **0x80** = power OFF
- **0x81** = power ON

## Test Movimento Locomotive

### ✅ Locomotive singole

- Funzionante (testate: address 3, 4)
- Comando diretto via Z21 muove la locomotiva
- Velocità 0-126 controllabile
- Direzione (avanti/indietro) controllabile

### ❌ Locomotive in consist

- NON rispondono ai comandi individuali
- Comportamento corretto DCC standard
- Address 1, 5, 6, 7 non rispondono quando in consist 10 o 11

### ✅ Consist (address virtuali)

- Funzionante (testati: consist 10, 11)
- Comando a consist 10 muove ENTRAMBE le loco 1 e 5 insieme
- Comando a consist 11 muove ENTRAMBE le loco 7 e 6 insieme
- Sincronizzazione perfetta

## Limitazioni e Note Operative

### Coesistenza JMRI e Z21 Direct

- ✅ JMRI e controllo Z21 diretto possono coesistere senza problemi
- Entrambi i sistemi possono controllare le locomotive contemporaneamente
- Se si verificano interferenze: riavviare Z21 o JMRI risolve il problema
- Nota: in caso di controllo simultaneo della stessa loco, l'ultimo comando ha priorità

### CV Operations Mode (POM)

**CV WRITE** (0xE6 0x30):
```
[0xE6] [0x30] [addr] [EC|cv_msb] [cv_lsb] [value] [xor]
```

- Z21 NON invia ACK per successo, solo errori `0x61`
- Timeout 500ms per rilevare errori, silenzio = successo
- Funziona su decoder ESU + Hornby

**CV READ** (0xE6 0x30 verify trick):
```
[0xE6] [0x30] [addr] [E4|cv_msb] [cv_lsb] [0x00] [xor]
```

- Risposta: `[0x64] [0x14] [addr_msb] [addr_lsb] [VALUE] [xor]`
- ⚠️ Funziona SOLO su decoder ESU, NON su Hornby TXS
- Z21 White NON supporta CV read standard (solo verify trick)

## Implementazione Python

Libreria completa: `scripts/z21.py`

Metodi principali:
- `get_serial_number()`
- `get_status()`
- `get_loco_info(address)`
- `set_loco_speed(address, speed, forward)`
- `set_loco_function(address, func_num, state, function_states)`
- `write_cv_ops_mode(address, cv_number, cv_value)`
- `read_cv_on_main(address, cv_number)`
- `emergency_stop_all()`
- `track_power_on()` / `track_power_off()`
- `close()`
