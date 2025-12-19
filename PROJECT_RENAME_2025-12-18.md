# Rinomina Progetto → z21-Terminal

## 📦 Modifiche Effettuate

### 1. Cartella Progetto
- **Vecchio nome**: `Plastico-DCC/`
- **Nuovo nome**: `z21-Terminal/`
- **Path**: `~/Documents/_PROGETTI/z21-Terminal/`

### 2. Documentazione
- ✅ README.md: Titolo, struttura progetto, path
- ✅ CLAUDE.md: Titolo, descrizione, refocus note
- ✅ z21_controller.py: Header, banner startup, sys.path

### 3. Aggiornamenti Path
```python
# Prima
sys.path.insert(0, '/Users/riccardosallusti/Documents/_PROGETTI/Plastico-DCC/scripts')

# Dopo
sys.path.insert(0, '/Users/riccardosallusti/Documents/_PROGETTI/z21-Terminal/scripts')
```

```bash
# Prima
cd ~/Documents/_PROGETTI/Plastico-DCC/scripts

# Dopo  
cd ~/Documents/_PROGETTI/z21-Terminal/scripts
```

---

## 🎯 Nome Progetto: z21-Terminal

### Significato
- **z21**: Protocollo Roco Z21 LAN
- **Terminal**: Interfaccia da terminale/CLI
- Chiaro, descrittivo, professionale

### Banner Startup
```
============================================================
z21-Terminal - CONTROLLER INTERATTIVO
============================================================
```

---

## 📁 Struttura Finale

```
z21-Terminal/
├── CLAUDE.md                     # Documentazione dettagliata
├── README.md                     # Quick start
├── PROJECT_RENAME_2025-12-18.md  # Questo file
├── FEATURES_2025-12-18.md        # Features implementate
├── scripts/
│   ├── z21_controller.py         # 🎮 z21-Terminal (main app)
│   ├── z21.py                    # 📚 Libreria Z21 LAN
│   ├── read_cv_from_roster.py    # 🔧 Utility CV
│   └── read_consists.py          # 🔧 Utility consist
├── docs/                         # Documentazione aggiuntiva
└── data/                         # Log, backup, export
```

---

## ✅ Verifica Funzionamento

Test eseguiti:
```bash
cd ~/Documents/_PROGETTI/z21-Terminal/scripts
python3 z21_controller.py  # ✅ OK - Path corretto, import funzionante
```

Tutte le importazioni funzionano correttamente!

---

**Data rinomina**: 2025-12-18
**Progetto**: Plastico DCC - BiancAlice
**Nome applicazione**: z21-Terminal
**Versione**: 2.0
