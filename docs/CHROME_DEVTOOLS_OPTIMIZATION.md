# Chrome DevTools Optimization Guide

**Version**: 1.0.0
**Last Updated**: 2026-01-27
**Author**: Riccardo Sallusti
**Project**: z21-Terminal

---

## 📋 Overview

Questo documento descrive come utilizzare gli **MCP Chrome DevTools** per ottimizzare, monitorare e testare il progetto z21-Terminal. Chrome DevTools, accessibile tramite MCP (Model Context Protocol), permette di automatizzare operazioni di debugging, performance analysis e end-to-end testing direttamente da CLI.

### Target Audience
- Developers che vogliono ottimizzare performance frontend/backend
- QA automation per testing E2E
- Sysadmin per monitoraggio produzione

### Prerequisiti
- MCP Chrome DevTools installato e configurato
- Browser Chrome/Chromium in esecuzione
- Backend z21-Terminal avviato (porta 8000)

---

## 🚀 1. Performance Monitoring

### 1.1 WebSocket Latency Analysis

**Obiettivo**: Misurare la latenza delle comunicazioni WebSocket tra backend e frontend.

**Use Case**: Ottimizzare il real-time sync multi-device per consist controller.

```javascript
// MCP: Valutare latenza media WebSocket
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

**Metriche da monitorare**:
- `duration`: Tempo totale connessione
- `tcpConnectionTime`: Handshake TCP
- `tlsNegotiationTime`: Negoziazione TLS (WSS)
- `transferSize`: Dimensione dati scambiati

**Threshold consigliati**:
- TCP connection: < 50ms (LAN), < 200ms (remote/Tailscale)
- Total duration: < 100ms per messaggio WebSocket

---

### 1.2 Memory Leak Detection - Video Feed MJPEG

**Obiettivo**: Identificare memory growth nel video stream a lungo termine.

**Use Case**: Il video feed MJPEG in streaming continuo può causare memory leak se non gestito correttamente.

```javascript
// MCP: Snapshot memoria prima e dopo
async function checkMemoryLeak() {
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
}
```

**Best practices**:
- Limitare dimensione buffer `<img>` src
- Usare `loading="lazy"` per frame fuori viewport
- Cleanup event listeners su unmount

---

### 1.3 Analytics Chart Rendering Profiling

**Obiettivo**: Misurare FPS e rendering time dei grafici Recharts.

**Use Case**: Ottimizzare `max_chart_events` per bilanciare performance vs granularity.

```javascript
// MCP: Avvia performance trace
await mcp__chrome_devtools__performance_start_trace({
  reload: true,
  autoStop: true,
  filePath: 'analytics-trace.json'
});

// Dopo navigazione in Analytics panel:
await mcp__chrome_devtools__navigate_page({
  type: 'url',
  url: 'http://localhost:5173/#analytics'
});

// Attendere rendering completo
await mcp__chrome_devtools__wait_for({ text: 'Δt Trends' });

// Analizza trace JSON per:
// - Frame rate (target: > 30 FPS)
// - Long tasks (> 50ms)
// - Scripting time vs Rendering time
```

**Metriche chiave**:
- **FPS**: > 30 FPS durante scroll chart
- **Long Tasks**: < 50ms per task JavaScript
- **Total Blocking Time**: < 200ms

**Ottimizzazioni**:
- Ridurre `max_chart_events` se FPS < 30
- Usare `React.memo()` per CustomTooltip component
- Virtualization per > 1000 punti (react-window)

---

## 🐛 2. Debugging & Troubleshooting

### 2.1 Console Error Monitoring

**Obiettivo**: Catturare errori console in produzione.

**Use Case**: Identificare errori WebSocket, RTSP stream, o YOLO tracking failures.

```javascript
// MCP: Lista ultimi 100 errori/warnings
await mcp__chrome_devtools__list_console_messages({
  types: ['error', 'warn'],
  pageSize: 100,
  includePreservedMessages: true
});

// Output esempio:
// [
//   { msgid: 42, type: 'error', text: 'WebSocket closed unexpectedly' },
//   { msgid: 43, type: 'warn', text: 'YOLO model not found, falling back to .onnx' }
// ]

// Recupera dettagli errore specifico
await mcp__chrome_devtools__get_console_message({
  msgid: 42
});
```

**Errori comuni da monitorare**:
- `WebSocket closed` → Check Z21 connectivity
- `RTSP stream timeout` → Verify camera credentials
- `YOLO inference error` → Model file missing/corrupted

---

### 2.2 WebSocket Connection Diagnostics

**Obiettivo**: Verificare stato connessione WebSocket multi-device.

**Use Case**: Debug sync issues tra Mac (dev) e PC (production).

```javascript
// MCP: Lista tutte le richieste WebSocket
await mcp__chrome_devtools__list_network_requests({
  resourceTypes: ['websocket'],
  includePreservedRequests: true
});

// MCP: Dettagli connessione WebSocket attiva
await mcp__chrome_devtools__get_network_request({
  reqid: 0 // Prima richiesta WS
});
```

**Parametri da verificare**:
- **Status**: 101 Switching Protocols (successo)
- **Headers**: `Upgrade: websocket`, `Connection: Upgrade`
- **URL**: `ws://localhost:8000/ws/control` o `wss://gaming-pc.tail9350d7.ts.net/ws/control`

---

### 2.3 Network Request Waterfall Analysis

**Obiettivo**: Identificare bottleneck nel caricamento risorse frontend.

**Use Case**: Ottimizzare first contentful paint (FCP) e largest contentful paint (LCP).

```javascript
// MCP: Lista tutte le richieste network (ultime 50)
await mcp__chrome_devtools__list_network_requests({
  pageSize: 50,
  includePreservedRequests: true
});

// MCP: Analizza singola richiesta (es. bundle.js)
await mcp__chrome_devtools__get_network_request({
  reqid: 5
});
```

**Metriche ottimizzazione**:
- **TTFB** (Time to First Byte): < 600ms
- **Download Time**: < 1s per bundle.js
- **Total Load Time**: < 3s (3G), < 1s (WiFi)

---

## 🧪 3. End-to-End Testing Automation

### 3.1 Consist Controller Flow Test

**Obiettivo**: Automatizzare test flusso completo controllo locomotiva.

**Use Case**: Regression testing dopo modifiche WebSocket handlers.

```javascript
// MCP: Test completo consist controller
async function testConsistController() {
  // 1. Snapshot stato iniziale
  const snapshot1 = await mcp__chrome_devtools__take_snapshot();

  // 2. Apri consist controller (seleziona consist 10)
  await mcp__chrome_devtools__click({ uid: 'consist-10-button' });

  // 3. Imposta velocità a 70%
  await mcp__chrome_devtools__fill({
    uid: 'speed-input',
    value: '70'
  });

  // 4. Verifica update UI
  await mcp__chrome_devtools__wait_for({ text: 'Speed: 70%' });

  // 5. Toggle direzione (forward)
  await mcp__chrome_devtools__click({ uid: 'direction-toggle' });

  // 6. Accendi funzione F0 (light)
  await mcp__chrome_devtools__click({ uid: 'function-f0' });

  // 7. Snapshot finale e confronto
  const snapshot2 = await mcp__chrome_devtools__take_snapshot();

  // 8. Screenshot per documentazione
  await mcp__chrome_devtools__take_screenshot({
    filePath: 'test-consist-controller-final.png',
    fullPage: true
  });

  console.log('✅ Consist controller test completed');
}
```

**Assert da verificare**:
- Speed slider aggiornato al valore corretto
- Direction toggle mostra icona corretta (↑/↓)
- Funzione F0 highlighted (attiva)
- WebSocket messaggi inviati (check network log)

---

### 3.2 Analytics Panel Toggle Test

**Obiettivo**: Testare apertura/chiusura Analytics panel via hotkey.

**Use Case**: Verificare che hotkey `A` funzioni correttamente.

```javascript
// MCP: Test toggle Analytics
async function testAnalyticsToggle() {
  // 1. Stato iniziale: panel chiuso
  await mcp__chrome_devtools__take_snapshot();

  // 2. Premi hotkey 'A'
  await mcp__chrome_devtools__press_key({ key: 'A' });

  // 3. Attendi rendering chart
  await mcp__chrome_devtools__wait_for({ text: 'Δt Trends' });

  // 4. Screenshot panel aperto
  await mcp__chrome_devtools__take_screenshot({
    filePath: 'test-analytics-open.png'
  });

  // 5. Premi 'A' di nuovo per chiudere
  await mcp__chrome_devtools__press_key({ key: 'A' });

  // 6. Verifica scomparsa panel
  await new Promise(resolve => setTimeout(resolve, 500));
  const snapshotClosed = await mcp__chrome_devtools__take_snapshot();

  console.log('✅ Analytics toggle test completed');
}
```

---

### 3.3 Speed Table Editor E2E Test

**Obiettivo**: Testare modifica CV via Speed Table Editor.

**Use Case**: Verificare scrittura CV67-94 e aggiornamento decoder.

```javascript
// MCP: Test scrittura CV
async function testSpeedTableWrite() {
  // 1. Naviga a Settings > Locomotives > Loco 1
  await mcp__chrome_devtools__navigate_page({
    type: 'url',
    url: 'http://localhost:5173/#settings'
  });

  // 2. Apri accordion Loco 1
  await mcp__chrome_devtools__click({ uid: 'loco-1-accordion' });

  // 3. Clicca tab "Speed Table"
  await mcp__chrome_devtools__click({ uid: 'speed-table-tab' });

  // 4. Clicca barra CV67 (step 2)
  await mcp__chrome_devtools__click({ uid: 'cv67-bar' });

  // 5. Modifica valore tramite slider
  await mcp__chrome_devtools__fill({
    uid: 'cv-value-slider',
    value: '50'
  });

  // 6. Clicca "Write to Decoder"
  await mcp__chrome_devtools__click({ uid: 'write-cv-button' });

  // 7. Attendi conferma
  await mcp__chrome_devtools__wait_for({ text: 'CV written successfully' });

  // 8. Screenshot finale
  await mcp__chrome_devtools__take_screenshot({
    filePath: 'test-speed-table-write.png'
  });

  console.log('✅ Speed table write test completed');
}
```

---

## 📊 4. Network Optimization

### 4.1 WebSocket Message Frequency Analysis

**Obiettivo**: Analizzare frequenza e dimensione messaggi WebSocket broadcast.

**Use Case**: Ottimizzare `broadcast_interval` per ridurre carico network.

```javascript
// MCP: Cattura messaggi WebSocket per 30 secondi
async function analyzeWebSocketTraffic() {
  const startTime = Date.now();
  const messages = [];

  while (Date.now() - startTime < 30000) {
    const requests = await mcp__chrome_devtools__list_network_requests({
      resourceTypes: ['websocket'],
      pageSize: 10
    });

    messages.push(...requests);
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  // Analizza risultati
  const avgSize = messages.reduce((sum, r) =>
    sum + (r.transferSize || 0), 0) / messages.length;

  const freqPerSecond = messages.length / 30;

  console.log(`Average message size: ${avgSize} bytes`);
  console.log(`Message frequency: ${freqPerSecond.toFixed(2)} msg/s`);

  // Raccomandazioni:
  // - Se avgSize > 1KB: Considera compressione (gzip)
  // - Se freqPerSecond > 10: Riduce broadcast_interval
}
```

---

### 4.2 Video Stream Buffering Analysis

**Obiettivo**: Identificare buffering e latenza nello stream MJPEG.

**Use Case**: Ottimizzare `video.fps` e RTSP stream parameters.

```javascript
// MCP: Analisi richieste media (video feed)
await mcp__chrome_devtools__list_network_requests({
  resourceTypes: ['media'],
  pageSize: 50,
  includePreservedRequests: true
});

// MCP: Dettagli singolo frame MJPEG
await mcp__chrome_devtools__get_network_request({
  reqid: 10 // Esempio frame ID
});
```

**Metriche da ottimizzare**:
- **Frame size**: < 50 KB per frame (720p MJPEG)
- **Frame interval**: 33ms (30 FPS) o 66ms (15 FPS)
- **Buffer underruns**: 0 eventi

**Ottimizzazioni**:
- Ridurre FPS a 15 se frame size > 50 KB
- Usare stream1 (resolution minore) se bandwidth limitata
- Abilitare hardware acceleration (GPU rendering)

---

### 4.3 API Response Time Profiling

**Obiettivo**: Misurare tempi di risposta endpoint backend FastAPI.

**Use Case**: Identificare endpoint lenti da ottimizzare.

```javascript
// MCP: Analizza tutte le richieste XHR/Fetch
const xhrRequests = await mcp__chrome_devtools__list_network_requests({
  resourceTypes: ['xhr', 'fetch'],
  pageSize: 100
});

// Calcola statistiche
const responseTimes = xhrRequests.map(r => r.duration - r.responseEnd);
const avgTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
const maxTime = Math.max(...responseTimes);

console.log(`Average API response: ${avgTime.toFixed(0)}ms`);
console.log(`Slowest endpoint: ${maxTime}ms`);

// Endpoint critici:
// - GET /api/config: < 100ms ( caricamento iniziale)
// - GET /api/analytics/events: < 500ms (dashboard)
// - POST /api/settings/update: < 200ms (salvataggio settings)
// - WebSocket messages: < 50ms (real-time control)
```

---

## 🎯 5. Use Case Specifici per z21-Terminal

### 5.1 YOLO Tracking Lag Optimization

**Scenario**: Misurare il lag tra gate crossing fisico e update UI.

**Obiettivo**: Ridurre latenza totchain: Camera → YOLO → WebSocket → UI → Chart update.

```javascript
// MCP: Profiling completo YOLO pipeline
async function profileYOLOTracking() {
  // 1. Avvia performance trace
  await mcp__chrome_devtools__performance_start_trace({
    reload: false,
    autoStop: false,
    filePath: 'yolo-tracking-trace.json'
  });

  // 2. Simula gate crossing (attendi 10 secondi)
  await new Promise(resolve => setTimeout(resolve, 10000));

  // 3. Stop trace
  await mcp__chrome_devtools__performance_stop_trace({
    filePath: 'yolo-tracking-trace.json'
  });

  // 4. Analizza trace per:
  //    - WebSocket receive time (T1)
  //    - UI re-render time (T2)
  //    - Total latency = T1 + T2

  console.log('✅ YOLO tracking profile saved');
}
```

**Target**:
- WebSocket receive: < 50ms
- UI re-render: < 100ms
- **Total latency**: < 150ms

---

### 5.2 Multi-Device Sync Latency (Tailscale)

**Scenario**: Testare latenza sync tra Mac (localhost) e PC (Tailscale HTTPS).

**Obiettivo**: Verificare che broadcast WebSocket arrivi a tutti device < 200ms.

```javascript
// MCP: Test connessione Tailscale
async function testTailscaleSync() {
  // 1. Naviga a URL Tailscale
  await mcp__chrome_devtools__navigate_page({
    type: 'url',
    url: 'https://gaming-pc.tail9350d7.ts.net'
  });

  // 2. Attendi caricamento WebSocket
  await mcp__chrome_devtools__wait_for({ text: 'Connected' });

  // 3. Analizza connessione WebSocket
  const wsRequests = await mcp__chrome_devtools__list_network_requests({
    resourceTypes: ['websocket']
  });

  // 4. Verifica latenza
  const wsConn = wsRequests[0];
  console.log(`Tailscale WS latency: ${wsConn.duration}ms`);

  // Target: < 200ms per messaggio su Tailscale
  if (wsConn.duration > 200) {
    console.warn('⚠️ High latency detected on Tailscale');
  }
}
```

---

### 5.3 Speed Table Drag Responsiveness

**Scenario**: Misurare responsiveness durante drag slider CV.

**Obiettivo**: Garantire FPS > 60 durante interazione utente.

```javascript
// MCP: Profiling drag interaction
async function profileDragInteraction() {
  // 1. Avvia performance trace
  await mcp__chrome_devtools__performance_start_trace({
    reload: false,
    autoStop: false,
    filePath: 'drag-trace.json'
  });

  // 2. Simula drag (10 click sequenziali su slider)
  for (let i = 0; i < 10; i++) {
    await mcp__chrome_devtools__click({ uid: 'cv-value-slider' });
    await new Promise(resolve => setTimeout(resolve, 100));
  }

  // 3. Stop trace
  await mcp__chrome_devtools__performance_stop_trace({
    filePath: 'drag-trace.json'
  });

  // 4. Analizza: FPS durante drag, long tasks
  console.log('✅ Drag interaction profile saved');
}
```

---

### 5.4 Analytics Downsampling Performance

**Scenario**: Confrontare performance con diversi `max_chart_events` (100, 500, 2000).

**Obiettivo**: Trovare bilanciamento ottimale granularity vs performance.

```javascript
// MCP: Benchmark downsampling
async function benchmarkDownsampling() {
  const configs = [100, 500, 2000];

  for (const maxEvents of configs) {
    // 1. Modifica config
    await mcp__chrome_devtools__evaluate_script({
      function: `(max) => localStorage.setItem('analytics_max_events', max)`,
      args: [{ value: maxEvents }]
    });

    // 2. Reload pagina
    await mcp__chrome_devtools__navigate_page({
      type: 'reload',
      ignoreCache: true
    });

    // 3. Attendi caricamento chart
    await mcp__chrome_devtools__wait_for({ text: 'Δt Trends' });

    // 4. Misura FPS
    const fps = await mcp__chrome_devtools__evaluate_script({
      function: `() => {
        // Calcola FPS dagli ultimi 100 frame
        return performance.getEntriesByType('frame')
          .slice(-100)
          .reduce((sum, f) => sum + f.duration, 0) / 100;
      }`
    });

    console.log(`max_events=${maxEvents}: FPS=${fps}`);
  }

  // Output esempio:
  // max_events=100: FPS=58.2
  // max_events=500: FPS=52.1  ← Bilanciamento ottimale
  // max_events=2000: FPS=38.4
}
```

---

### 5.5 Virtual Mode Toggle Edge Cases

**Scenario**: Testare toggle Virtual Mode con Z21 offline.

**Obiettivo**: Verificare graceful degradation e messaggi errore utente.

```javascript
// MCP: Test Z21 offline scenario
async function testZ21Offline() {
  // 1. Simula Z21 offline (disconnect network o stop Z21)
  // ... (operazione manuale)

  // 2. Tenta toggle Virtual Mode
  await mcp__chrome_devtools__click({ uid: 'virtual-mode-toggle' });

  // 3. Verifica messaggio errore
  await mcp__chrome_devtools__wait_for({
    text: 'Z21 not connected'
  });

  // 4. Cattura console errori
  const errors = await mcp__chrome_devtools__list_console_messages({
    types: ['error']
  });

  // 5. Verifica che non ci siano uncaught exceptions
  const hasUncaught = errors.some(e =>
    e.text.includes('Uncaught') ||
    e.text.includes('TypeError')
  );

  if (hasUncaught) {
    console.error('❌ Uncaught exception detected!');
  } else {
    console.log('✅ Graceful degradation working');
  }

  // 6. Screenshot per documentazione
  await mcp__chrome_devtools__take_screenshot({
    filePath: 'test-z21-offline-error.png'
  });
}
```

---

## 📈 6. Continuous Monitoring Setup

### 6.1 Performance Regression Testing

**Integrare in CI/CD pipeline** per automatizzare test performance:

```bash
#!/bin/bash
# scripts/performance_test.sh

# 1. Avvia backend e frontend
z21-backend &
BACKEND_PID=$!
z21-frontend &
FRONTEND_PID=$!

# 2. Attendi startup
sleep 10

# 3. Esegui test E2E via MCP Chrome DevTools
# (chiama script Python che usa MCP SDK)

python scripts/mcp_performance_tests.py

# 4. Analizza risultati
# - Se FPS < 30: Fail build
# - Se memory leak > 50MB: Fail build
# - Se WebSocket latency > 200ms: Fail build

# 5. Cleanup
kill $BACKEND_PID $FRONTEND_PID
```

---

### 6.2 Production Monitoring Dashboard

**Setup monitoring automatizzato** in production (PC Windows):

```javascript
// MCP: Script monitoraggio produzione (esegue ogni 5 minuti)
async function productionHealthCheck() {
  const results = {
    timestamp: new Date().toISOString(),
    websocket_latency: null,
    memory_usage: null,
    console_errors: [],
    api_response_times: []
  };

  // 1. WebSocket latency
  const ws = await mcp__chrome_devtools__list_network_requests({
    resourceTypes: ['websocket'],
    pageSize: 1
  });
  if (ws.length > 0) {
    results.websocket_latency = ws[0].duration;
  }

  // 2. Memory usage
  results.memory_usage = await mcp__chrome_devtools__evaluate_script({
    function: `() => performance.memory.usedJSHeapSize / (1024*1024)`
  });

  // 3. Console errors (ultimi 10)
  const errors = await mcp__chrome_devtools__list_console_messages({
    types: ['error'],
    pageSize: 10
  });
  results.console_errors = errors.map(e => e.text);

  // 4. API response times
  const xhr = await mcp__chrome_devtools__list_network_requests({
    resourceTypes: ['xhr'],
    pageSize: 20
  });
  results.api_response_times = xhr.map(r => ({
    url: r.name,
    duration: r.duration
  }));

  // 5. Salva risultati in database o file log
  await saveToDatabase(results);

  // 6. Allarme se soglie superate
  if (results.memory_usage > 500) {
    sendAlert('High memory usage: ' + results.memory_usage + ' MB');
  }
  if (results.websocket_latency > 500) {
    sendAlert('WebSocket latency high: ' + results.websocket_latency + 'ms');
  }
}
```

---

## 🛠️ 7. Tooling & Automation Scripts

### 7.1 Python Wrapper per MCP Chrome DevTools

```python
# scripts/mcp_devtools_helper.py
"""
Helper script per automatizzare operazioni Chrome DevTools via MCP.
Requisiti: pip install mcp-python-sdk
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def measure_websocket_latency(url: str) -> dict:
    """Misura latenza connessione WebSocket."""
    async with stdio_client() as (read, write):
        async with ClientSession(read, write) as session:
            # Lista richieste WebSocket
            result = await session.call_tool(
                "chrome-devtools",
                "list_network_requests",
                arguments={"resourceTypes": ["websocket"]}
            )
            return result

async def capture_console_errors() -> list:
    """Cattura errori console."""
    async with stdio_client() as (read, write):
        async with ClientSession(read, write) as session:
            result = await session.call_tool(
                "chrome-devtools",
                "list_console_messages",
                arguments={"types": ["error", "warn"], "pageSize": 100}
            )
            return result

async def take_screenshot(filepath: str) -> bool:
    """Cattura screenshot pagina."""
    async with stdio_client() as (read, write):
        async with ClientSession(read, write) as session:
            result = await session.call_tool(
                "chrome-devtools",
                "take_screenshot",
                arguments={"filePath": filepath, "fullPage": True}
            )
            return result

# Esempio utilizzo
async def main():
    # Test WebSocket latency
    ws_latency = await measure_websocket_latency("ws://localhost:8000/ws/control")
    print(f"WebSocket latency: {ws_latency}")

    # Cattura errori console
    errors = await capture_console_errors()
    print(f"Console errors: {len(errors)} found")

    # Screenshot per documentazione
    await take_screenshot("test-screenshot.png")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 7.2 Bash Alias per Quick Testing

```bash
# ~/.bash_aliases (Mac) o $PROFILE (PC Windows)

# Avvia Chrome con remote debugging (porta 9222)
chrome-debug() {
  /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --remote-debugging-port=9222 \
    --user-data-dir=/tmp/chrome-debug \
    "$@"
}

# Test performance z21-Terminal
z21-perf-test() {
  echo "🚀 Avviando performance test..."
  python ~/Documents/_PROGETTI/z21-Terminal/scripts/mcp_devtools_helper.py
}

# Screenshot automatico ogni 30 secondi (monitoring)
z21-screenshot-monitor() {
  local dir="$1"
  mkdir -p "$dir"
  while true; do
    local timestamp=$(date +%s)
    # Chiama MCP tool per screenshot
    mcp__chrome_devtools__take_screenshot \
      --filePath "$dir/screenshot-${timestamp}.png"
    sleep 30
  done
}
```

---

## 📚 8. Riferimenti & Risorse

### Documentazione Chrome DevTools Protocol
- **CDP Documentation**: https://chromedevtools.github.io/devtools-protocol/
- **Performance API**: https://developer.mozilla.org/en-US/docs/Web/API/Performance
- **WebSocket API**: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket

### MCP Client SDK
- **mcp-python-sdk**: https://github.com/modelcontextprotocol/python-sdk
- **MCP Specification**: https://modelcontextprotocol.io/

### Tool Similari
- **Puppeteer**: Headless Chrome automation (Node.js)
- **Playwright**: Cross-browser automation (Microsoft)
- **Selenium**: Legacy browser automation

---

## 🔄 9. Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-27 | Initial document creation |

---

## 📝 TODO & Future Enhancements

- [ ] Implementare Python wrapper completo per tutti i tool MCP
- [ ] Integrare performance tests in GitHub Actions CI/CD
- [ ] Creare dashboard Grafana per metriche production
- [ ] Aggiungere esempi per mobile debugging (Chrome DevTools Remote)
- [ ] Documentare edge case specifici per Tailscale HTTPS
- [ ] Creare script automatizzato per confronto prima/dopo ottimizzazioni

---

**End of Document**
