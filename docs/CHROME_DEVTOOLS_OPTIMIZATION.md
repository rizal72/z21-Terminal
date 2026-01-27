# Chrome DevTools MCP Guide

**Version**: 2.0.0
**Last Updated**: 2026-01-27
**Author**: Riccardo Sallusti
**Project**: z21-Terminal

**Official Project**: https://github.com/ChromeDevTools/chrome-devtools-mcp

---

## 📋 Overview

**chrome-devtools-mcp** è un progetto **ufficiale Google Chrome** che permette agli AI coding agent (Claude, Cursor, Copilot, etc.) di controllare e ispezionare un browser Chrome in tempo reale tramite il **Model Context Protocol (MCP)**.

### ⚠️ Importante: NO Estensione Necessaria

**NON serve installare un'estensione Chrome**. È un server MCP che comunica con Chrome tramite il **Chrome DevTools Protocol (CDP)** usando Puppeteer sotto il cofano.

### Target Audience
- Developers che vogliono ottimizzare performance frontend/backend
- QA automation per testing E2E
- Sysadmin per monitoraggio produzione

### Prerequisiti
- **Node.js** v20.19+ (LTS)
- **Chrome** current stable o newer
- **npm**
- Backend z21-Terminal avviato (porta 8000)

---

## 🚀 Installazione

### Configurazione Claude Code

Aggiungi al tuo file di configurazione MCP:

```bash
claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest
```

Oppure manualmente in `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"]
    }
  }
}
```

### Profilo Dedicato

Chrome viene avviato con un profilo dedicato per non sporcare il tuo profilo principale:

- **macOS/Linux**: `$HOME/.cache/chrome-devtools-mcp/chrome-profile-stable`
- **Windows**: `%HOMEPATH%\.cache\chrome-devtools-mcp\chrome-profile-stable`

---

## 🔧 Modalità di Connessione

### 1. Default Mode (Avvio Automatico)

Il server MCP avvia automaticamente una nuova istanza di Chrome con profilo dedicato. **Modalità consigliata** per testing isolato.

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"]
    }
  }
}
```

### 2. Auto-Connect Mode (Chrome 144+)

Si collega a un'istanza di Chrome **già in esecuzione**. Ideale per mantenere lo stato tra testing manuale e agent-driven.

**Step 1**: Abilita remote debugging in Chrome
1. Vai a `chrome://inspect/#remote-debugging`
2. Segui la UI per permettere connessioni debugging in arrivo

**Step 2**: Configura il server MCP

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "chrome-devtools-mcp@latest",
        "--autoConnect",
        "--channel=beta"
      ]
    }
  }
}
```

### 3. Manual Connection (Remote Debugging Port)

Si collega a Chrome tramite porta di debugging (es. `9222`). Utile per ambienti sandboxed.

**Step 1**: Avvia Chrome con remote debugging

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-profile-stable

# Linux
/usr/bin/google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-profile-stable

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" \
  --remote-debugging-port=9222 \
  --user-data-dir="%TEMP%\chrome-profile-stable"
```

**Step 2**: Configura il server MCP

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "chrome-devtools-mcp@latest",
        "--browser-url=http://127.0.0.1:9222"
      ]
    }
  }
}
```

### Opzioni Configurazione Avanzate

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "chrome-devtools-mcp@latest",
        "--channel=canary",        // stable|canary|beta|dev
        "--headless=true",         // No UI (max 3840x2160)
        "--isolated=true",         // Cleanup automatico profilo
        "--viewport=1280x720",     // Dimensioni iniziali
        "--accept-insecure-certs"  // Ignora errori SSL (usa cautela!)
      ]
    }
  }
}
```

---

## 🛠️ Tool Disponibili (26 totali)

### Input Automation (8 tools)
| Tool | Descrizione |
|------|-------------|
| `click` | Click su elemento (supporta double-click) |
| `drag` | Drag element onto another |
| `fill` | Type text in input/select |
| `fill_form` | Fill multiple form elements at once |
| `handle_dialog` | Handle browser dialogs (alert, confirm, prompt) |
| `hover` | Hover over element |
| `press_key` | Press key or key combination |
| `upload_file` | Upload file via file input |

### Navigation Automation (6 tools)
| Tool | Descrizione |
|------|-------------|
| `close_page` | Close page by index |
| `list_pages` | Get list of open pages |
| `navigate_page` | Navigate to URL or back/forward/reload |
| `new_page` | Create new page with URL |
| `select_page` | Select page as context for future tools |
| `wait_for` | Wait for text to appear on page |

### Emulation (2 tools)
| Tool | Descrizione |
|------|-------------|
| `emulate` | Emulate device, geolocation, network conditions, CPU throttling |
| `resize_page` | Resize page window to specific dimensions |

### Performance (3 tools)
| Tool | Descrizione |
|------|-------------|
| `performance_analyze_insight` | Analyze performance insights from trace |
| `performance_start_trace` | Start performance trace recording |
| `performance_stop_trace` | Stop performance trace and save to file |

### Network (2 tools)
| Tool | Descrizione |
|------|-------------|
| `get_network_request` | Get details of specific network request |
| `list_network_requests` | List all network requests for current page |

### Debugging (5 tools)
| Tool | Descrizione |
|------|-------------|
| `evaluate_script` | Execute JavaScript in page context |
| `get_console_message` | Get specific console message by ID |
| `list_console_messages` | List all console messages (log, warn, error, etc.) |
| `take_screenshot` | Take screenshot (PNG/JPEG/WebP) |
| `take_snapshot` | Take text snapshot based on accessibility tree |

---

## 🎯 Use Cases per z21-Terminal

### 1. Performance Monitoring

#### WebSocket Latency Analysis

```javascript
// Valutare latenza media WebSocket
await mcp__chrome_devtools__evaluate_script({
  function: `() => {
    const resources = performance.getEntriesByType('resource');
    const wsConnections = resources.filter(r =>
      r.name.includes('ws://') || r.name.includes('wss://')
    );

    return wsConnections.map(conn => ({
      url: conn.name,
      duration: conn.duration, // ms
      transferSize: conn.transferSize, // bytes
      tcpConnectionTime: conn.connectEnd - conn.connectStart,
      tlsNegotiationTime: conn.secureConnectionStart > 0 ?
        conn.connectEnd - conn.secureConnectionStart : 0
    }));
  }`
});
```

**Threshold consigliati**:
- TCP connection: < 50ms (LAN), < 200ms (remote/Tailscale)
- Total duration: < 100ms per messaggio WebSocket

---

#### Performance Trace Recording

```javascript
// 1. Avvia trace
await mcp__chrome_devtools__performance_start_trace({
  filePath: "/tmp/z21-trace.json",
  reload: true,
  autoStop: false
});

// 2. Naviga e usa l'app
// ... azioni utente ...

// 3. Ferma trace
await mcp__chrome_devtools__performance_stop_trace();

// 4. Analizza insights
await mcp__chrome_devtools__performance_analyze_insight({
  insightSetId: "...",  // dall'output del trace
  insightName: "DocumentLatency"
});
```

---

### 2. Memory Leak Detection

```javascript
// Snapshot memoria prima e dopo
const before = await mcp__chrome_devtools__evaluate_script({
  function: `() => performance.memory.usedJSHeapSize`
});

// Simula 10 minuti di streaming
await new Promise(resolve => setTimeout(resolve, 600000));

const after = await mcp__chrome_devtools__evaluate_script({
  function: `() => performance.memory.usedJSHeapSize`
});

const growthMB = (after - before) / (1024 * 1024);
console.log(`Memory growth: ${growthMB.toFixed(2)} MB`);

// Allarme se crescita > 50 MB in 10 min
if (growthMB > 50) {
  console.warn('⚠️ Potential memory leak detected!');
}
```

**Best practices**:
- Limitare dimensione buffer `<img>` src
- Usare `loading="lazy"` per frame fuori viewport
- Cleanup event listeners su unmount

---

### 3. E2E Testing - Locomotive Control

```javascript
// 1. Naviga alla dashboard
await mcp__chrome_devtools__navigate_page({
  type: "url",
  url: "http://localhost:5173"
});

// 2. Aspetta caricamento
await mcp__chrome_devtools__wait_for({
  text: "Consist Controller"
});

// 3. Screenshot iniziale
await mcp__chrome_devtools__take_screenshot({
  filePath: "/tmp/z21-initial.png"
});

// 4. Imposta velocità via slider
await mcp__chrome_devtools__fill({
  uid: "speed-slider",  // dallo snapshot
  value: "50"
});

// 5. Click direzione forward
await mcp__chrome_devtools__click({
  uid: "btn-forward",
  dblClick: false
});

// 6. Verifica stato WebSocket
await mcp__chrome_devtools__evaluate_script({
  function: `() => {
    const ws = performance.getEntriesByType('resource')
      .filter(r => r.name.includes('ws://'));
    return {
      connected: ws.length > 0,
      url: ws[0]?.name
    };
  }`
});

// 7. Screenshot finale
await mcp__chrome_devtools__take_screenshot({
  filePath: "/tmp/z21-after-control.png"
});
```

---

### 4. Network Analysis - API Endpoints

```javascript
// Lista tutte le richieste network
const requests = await mcp__chrome_devtools__list_network_requests({
  resourceTypes: ["xhr", "fetch"]
});

// Filtra endpoint analytics
const analyticsCalls = requests.filter(r =>
  r.name.includes('/api/analytics/')
);

console.log('Analytics calls:', analyticsCalls.length);
console.log('Avg response time:',
  analyticsCalls.reduce((sum, r) => sum + r.duration, 0) / analyticsCalls.length
);

// Dettagli singola richiesta
const detail = await mcp__chrome_devtools__get_network_request({
  reqid: analyticsCalls[0].id
});
```

---

### 5. Console Monitoring - Error Detection

```javascript
// Lista tutti i messaggi console
const messages = await mcp__chrome_devtools__list_console_messages({
  types: ["error", "warn"]  // log, debug, info, error, warn
});

// Filtra errori critici
const criticalErrors = messages.filter(m =>
  m.level === "error" &&
  (m.text.includes('WebSocket') || m.text.includes('Z21'))
);

console.log('Critical errors found:', criticalErrors.length);

// Leggi messaggio specifico
for (const msg of criticalErrors) {
  const detail = await mcp__chrome_devtools__get_console_message({
    msgid: msg.id
  });
  console.error('Error:', detail.text);
  console.error('Stack:', detail.stackTrace);
}
```

---

## ⚠️ Limitazioni e Troubleshooting

### Sandbox Limitation

Se il client MCP usa sandbox (macOS Seatbelt, Linux containers):
- **Problema**: Non può avviare Chrome automaticamente
- **Soluzione**: Disabilita sandbox O usa `--browser-url`

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "chrome-devtools-mcp@latest",
        "--browser-url=http://127.0.0.1:9222"
      ]
    }
  }
}
```

### Security Warning

⚠️ **Remote debugging porta apre accesso completo al browser**. Non navigare su siti sensibili con la porta di debugging aperta.

Usa sempre un **profilo dedicato** con `--user-data-dir`.

### Troubleshooting Comuni

| Problema | Soluzione |
|----------|----------|
| Browser non si avvia | Verifica Node.js v20+, installa Chrome stable |
| Connessione fallisce | Controlla che nessun altro Chrome stia usando la porta |
| Profilo sporca il tuo Chrome | Usa `--isolated=true` per profilo temporaneo |
| Sandbox error | Usa `--browser-url` per connetterti a Chrome manuale |

---

## 📚 Risorse Ufficiali

- **GitHub Repo**: https://github.com/ChromeDevTools/chrome-devtools-mcp
- **Chrome DevTools Protocol**: https://chromedevtools.github.io/devtools-protocol/
- **Puppeteer Docs**: https://pptr.dev/
- **MCP Specification**: https://modelcontextprotocol.io/

---

## 🔄 Changelog

| Versione | Data | Modifiche |
|----------|------|-----------|
| 2.0.0 | 2026-01-27 | Rewrite basato su repo ufficiale ChromeDevTools |
| 1.0.0 | 2026-01-27 | Versione iniziale |

---

**End of Document**
