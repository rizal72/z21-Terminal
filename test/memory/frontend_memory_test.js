/**
 * Frontend Memory Test Suite for Chrome DevTools MCP
 *
 * This file contains JavaScript snippets to measure React app memory usage
 * via Chrome DevTools Protocol.
 *
 * Usage with MCP Chrome DevTools:
 * 1. Navigate to http://localhost:5173 (or production URL)
 * 2. Use mcp__chrome-devtools__evaluate_script with each function below
 * 3. Results are returned as JSON
 */

// ============================================================================
// 1. BASIC HEAP SIZE MEASUREMENT
// ============================================================================

/**
 * Get current JavaScript heap size.
 * NOTE: Only works in Chromium-based browsers with --enable-precise-memory-info
 *
 * Returns: { usedJSHeapSize, totalJSHeapSize, jsHeapSizeLimit } in bytes
 */
function getHeapSize() {
    if (performance.memory) {
        return {
            used_mb: (performance.memory.usedJSHeapSize / 1024 / 1024).toFixed(2),
            total_mb: (performance.memory.totalJSHeapSize / 1024 / 1024).toFixed(2),
            limit_mb: (performance.memory.jsHeapSizeLimit / 1024 / 1024).toFixed(2),
            percent: ((performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit) * 100).toFixed(2)
        };
    } else {
        return { error: "performance.memory not available. Start Chrome with --enable-precise-memory-info" };
    }
}

// ============================================================================
// 2. REACT COMPONENT COUNT
// ============================================================================

/**
 * Count React DOM nodes and fiber tree complexity.
 * Gives an estimate of React app size.
 */
function getReactStats() {
    const root = document.getElementById('root');
    if (!root) {
        return { error: "React root not found" };
    }

    const allNodes = root.querySelectorAll('*');
    const reactInternalNodes = Array.from(allNodes).filter(
        node => node._reactRootContainer !== undefined || node._reactInternalFiber !== undefined
    );

    // Estimate component count via React DevTools hook
    let componentCount = 0;
    const countComponents = (element) => {
        if (element && element._reactInternalFiber) {
            componentCount++;
        }
        for (const child of element.children) {
            countComponents(child);
        }
    };

    countComponents(root);

    return {
        total_dom_nodes: allNodes.length,
        estimated_components: componentCount,
        root_inner_html_length: root.innerHTML.length
    };
}

// ============================================================================
// 3. WEBSOCKET MESSAGE SIZE
// ============================================================================

/**
 * Monitor WebSocket message traffic.
 * Returns stats on sent/received messages and total bytes.
 */
function getWebSocketStats() {
    // Check if WebSocket is connected
    const ws = window.ws || window.__ws__;  // Adjust based on your app's global WS variable

    if (!ws) {
        return { error: "WebSocket not found in global scope" };
    }

    return {
        url: ws.url,
        readyState: ws.readyState,  // 0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED
        protocol: ws.protocol,
        // Note: Message counts require instrumentation in app code
        // See: trackWebSocketMessages() below
    };
}

// ============================================================================
// 4. CONTINUOUS MONITORING (Auto-instrumentation)
// ============================================================================

/**
 * Instrument WebSocket to track message sizes.
 * Call this ONCE at page load to start tracking.
 */
function trackWebSocketMessages() {
    if (window.__ws_instrumented__) {
        return { status: "already_instrumented" };
    }

    // Find WebSocket in React app (hook into all new WS connections)
    const OriginalWebSocket = window.WebSocket;

    window.WebSocket = function(...args) {
        const ws = new OriginalWebSocket(...args);

        ws.addEventListener('message', (event) => {
            if (!window.__ws_stats__) {
                window.__ws_stats__ = {
                    messages_received: 0,
                    messages_sent: 0,
                    bytes_received: 0,
                    bytes_sent: 0,
                    message_sizes: []
                };
            }

            window.__ws_stats__.messages_received++;
            window.__ws_stats__.bytes_received += event.data.length;
            window.__ws_stats__.message_sizes.push({
                direction: 'received',
                size: event.data.length,
                timestamp: Date.now()
            });
        });

        ws.addEventListener('open', () => {
            console.log('[WS Monitor] WebSocket connected:', args[0]);
        });

        return ws;
    };

    window.__ws_instrumented__ = true;
    return { status: "instrumented", message: "WebSocket tracking enabled" };
}

/**
 * Get WebSocket statistics collected by trackWebSocketMessages()
 */
function getCollectedWebSocketStats() {
    if (!window.__ws_stats__) {
        return { error: "No stats collected. Call trackWebSocketMessages() first." };
    }

    const stats = window.__ws_stats__;
    const recent_sizes = stats.message_sizes.slice(-100);  // Last 100 messages

    return {
        messages_received: stats.messages_received,
        messages_sent: stats.messages_sent,
        total_kb_received: (stats.bytes_received / 1024).toFixed(2),
        total_kb_sent: (stats.bytes_sent / 1024).toFixed(2),
        avg_message_size_bytes: recent_sizes.length > 0
            ? (recent_sizes.reduce((sum, m) => sum + m.size, 0) / recent_sizes.length).toFixed(2)
            : 0,
        recent_messages_sample: recent_sizes.slice(-10).map(m => ({
            direction: m.direction,
            bytes: m.size,
            time: new Date(m.timestamp).toISOString()
        }))
    };
}

// ============================================================================
// 5. MEMORY LEAK DETECTION (Snapshots)
// ============================================================================

/**
 * Take a memory snapshot.
 * Call multiple times during testing to detect leaks.
 */
function takeMemorySnapshot(label = "snapshot") {
    const heap = getHeapSize();

    if (!window.__memory_snapshots__) {
        window.__memory_snapshots__ = [];
    }

    const snapshot = {
        label: label,
        timestamp: new Date().toISOString(),
        used_mb: heap.used_mb,
        total_mb: heap.total_mb,
        percent: heap.percent
    };

    window.__memory_snapshots__.push(snapshot);

    return snapshot;
}

/**
 * Compare memory snapshots to detect leaks.
 */
function compareMemorySnapshots() {
    if (!window.__memory_snapshots__ || window.__memory_snapshots__.length < 2) {
        return { error: "Need at least 2 snapshots. Call takeMemorySnapshot() multiple times." };
    }

    const snapshots = window.__memory_snapshots__;
    const first = snapshots[0];
    const last = snapshots[snapshots.length - 1];

    const growth = parseFloat(last.used_mb) - parseFloat(first.used_mb);
    const growth_percent = ((growth / parseFloat(first.used_mb)) * 100).toFixed(2);

    return {
        first_snapshot: first,
        last_snapshot: last,
        growth_mb: growth.toFixed(2),
        growth_percent: growth_percent,
        total_snapshots: snapshots.length,
        all_snapshots: snapshots
    };
}

// ============================================================================
// 6. FULL DIAGNOSTIC REPORT
// ============================================================================

/**
 * Generate complete memory diagnostic report.
 */
function generateDiagnosticReport() {
    return {
        timestamp: new Date().toISOString(),
        url: window.location.href,
        user_agent: navigator.userAgent,
        heap: getHeapSize(),
        react: getReactStats(),
        websocket: getCollectedWebSocketStats(),
        memory_snapshots: window.__memory_snapshots__ || null,
        snapshot_comparison: window.__memory_snapshots__?.length >= 2
            ? compareMemorySnapshots()
            : null
    };
}

// ============================================================================
// EXPORTS (for MCP usage)
// ============================================================================

// Copy-paste these into mcp__chrome-devtools__evaluate_script calls:

/*
// Example MCP calls:

// 1. Enable WebSocket tracking
mcp__chrome-devtools__evaluate_script:
function: "() => " + trackWebSocketMessages.toString()

// 2. Take baseline snapshot
mcp__chrome-devtools__evaluate_script:
function: "() => " + takeMemorySnapshot.toString() + "('baseline')"

// 3. Get heap size
mcp__chrome-devtools__evaluate_script:
function: "() => " + getHeapSize.toString()

// 4. Generate full report
mcp__chrome-devtools__evaluate_script:
function: "() => " + generateDiagnosticReport.toString()

// 5. Compare snapshots (after taking multiple)
mcp__chrome-devtools__evaluate_script:
function: "() => " + compareMemorySnapshots.toString()
*/
