#!/bin/bash
# z21-Terminal Full Memory Test Suite
#
# This script orchestrates complete memory testing for backend + frontend.
# It monitors:
# 1. Backend Python process (psutil)
# 2. Frontend React app (Chrome DevTools MCP)
# 3. YOLO model memory (if tracking is active)
#
# Usage: ./run_full_memory_test.sh [--duration MINUTES] [--backend-only]

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RESULTS_DIR="$SCRIPT_DIR/results"

# Default arguments
DURATION_MINUTES=${DURATION_MINUTES:-10}
BACKEND_ONLY=${BACKEND_ONLY:-false}
FRONTEND_ONLY=${FRONTEND_ONLY:-false}
INTERVAL_SECONDS=5

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --duration|-d)
            DURATION_MINUTES="$2"
            shift 2
            ;;
        --backend-only)
            BACKEND_ONLY=true
            shift
            ;;
        --frontend-only)
            FRONTEND_ONLY=true
            shift
            ;;
        --interval|-i)
            INTERVAL_SECONDS="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --duration, -d MINUTES    Test duration in minutes (default: 10)"
            echo "  --interval, -i SECONDS    Measurement interval (default: 5)"
            echo "  --backend-only            Test backend only"
            echo "  --frontend-only           Test frontend only"
            echo "  --help, -h                Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# ============================================================================
# FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

check_dependencies() {
    print_header "Checking Dependencies"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found"
        exit 1
    fi
    log_success "Python 3: $(python3 --version)"

    # Check psutil
    if ! python3 -c "import psutil" 2>/dev/null; then
        log_warning "psutil not found. Installing..."
        pip3 install psutil
    fi
    log_success "psutil: installed"

    # Check if backend is running
    if ! $FRONTEND_ONLY; then
        if ! pgrep -f "python.*main.py" > /dev/null; then
            log_warning "Backend not running. Start with: z21-backend"
        else
            log_success "Backend: running (PID: $(pgrep -f 'python.*main.py'))"
        fi
    fi

    # Check if frontend is running
    if ! $BACKEND_ONLY; then
        FRONTEND_URL="http://localhost:5173"
        if ! curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" | grep -q "200\|302"; then
            log_warning "Frontend not accessible at $FRONTEND_URL"
            log_info "Start with: z21-frontend"
        else
            log_success "Frontend: running at $FRONTEND_URL"
        fi
    fi
}

run_backend_monitor() {
    print_header "Backend Memory Monitor"

    local output_file="$RESULTS_DIR/backend_memory_$(date +%Y%m%d_%H%M%S).csv"

    log_info "Starting backend memory monitor..."
    log_info "Output: $output_file"
    log_info "Duration: ${DURATION_MINUTES} minutes"
    log_info "Interval: ${INTERVAL_SECONDS}s"

    python3 "$SCRIPT_DIR/backend_memory_monitor.py" \
        --interval "$INTERVAL_SECONDS" \
        --duration "$DURATION_MINUTES" \
        --output "$output_file"

    log_success "Backend monitoring complete: $output_file"
}

run_frontend_tests() {
    print_header "Frontend Memory Tests (Chrome DevTools MCP)"

    log_warning "Frontend testing requires Chrome DevTools MCP server"
    log_info "See: frontend_memory_test.js for manual MCP commands"
    log_info ""
    log_info "Quick test sequence:"
    log_info "  1. Open dashboard in Chrome: http://localhost:5173"
    log_info "  2. In Claude Code, run:"
    log_info "     mcp__chrome-devtools__evaluate_script"
    log_info "     function: '() => { return getHeapSize(); }'"
    log_info ""
    log_info "  3. For continuous monitoring, see:"
    log_info "     $SCRIPT_DIR/frontend_memory_test.js"

    # Create a simple HTML test page for manual testing
    local test_page="$RESULTS_DIR/memory_test.html"
    cat > "$test_page" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>z21-Terminal Memory Test</title>
    <style>
        body { font-family: monospace; padding: 20px; background: #1e1e1e; color: #d4d4d4; }
        h1 { color: #4ec9b0; }
        .section { background: #252526; padding: 15px; margin: 10px 0; border-radius: 5px; }
        button { background: #0e639c; color: white; border: none; padding: 10px 20px; margin: 5px; cursor: pointer; border-radius: 3px; }
        button:hover { background: #1177bb; }
        pre { background: #1e1e1e; padding: 10px; border-radius: 3px; overflow-x: auto; }
        .good { color: #4ec9b0; }
        .warn { color: #dcdcaa; }
        .bad { color: #f48771; }
    </style>
</head>
<body>
    <h1>🔍 z21-Terminal Memory Test Dashboard</h1>

    <div class="section">
        <h2>1. Heap Size</h2>
        <button onclick="testHeapSize()">Test Heap Size</button>
        <pre id="heap-result">Run test to see results...</pre>
    </div>

    <div class="section">
        <h2>2. React Stats</h2>
        <button onclick="testReactStats()">Test React Stats</button>
        <pre id="react-result">Run test to see results...</pre>
    </div>

    <div class="section">
        <h2>3. Memory Snapshots</h2>
        <button onclick="takeSnapshot()">Take Snapshot</button>
        <button onclick="compareSnapshots()">Compare Snapshots</button>
        <pre id="snapshot-result">Run test to see results...</pre>
    </div>

    <div class="section">
        <h2>4. Full Diagnostic Report</h2>
        <button onclick="generateReport()">Generate Report</button>
        <pre id="report-result">Run test to see results...</pre>
    </div>

    <script>
        // Copy functions from frontend_memory_test.js
        function getHeapSize() {
            if (performance.memory) {
                return {
                    used_mb: (performance.memory.usedJSHeapSize / 1024 / 1024).toFixed(2),
                    total_mb: (performance.memory.totalJSHeapSize / 1024 / 1024).toFixed(2),
                    limit_mb: (performance.memory.jsHeapSizeLimit / 1024 / 1024).toFixed(2),
                    percent: ((performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit) * 100).toFixed(2)
                };
            } else {
                return { error: "Enable Chrome with --enable-precise-memory-info" };
            }
        }

        function getReactStats() {
            const root = document.getElementById('root');
            if (!root) return { error: "React root not found (not on dashboard page?)" };
            const allNodes = root.querySelectorAll('*');
            return {
                total_dom_nodes: allNodes.length,
                root_inner_html_length: root.innerHTML.length
            };
        }

        function takeMemorySnapshot(label) {
            const heap = getHeapSize();
            if (!window.__memory_snapshots__) window.__memory_snapshots__ = [];
            const snapshot = {
                label: label || `snap_${window.__memory_snapshots__.length + 1}`,
                timestamp: new Date().toISOString(),
                used_mb: heap.used_mb,
                percent: heap.percent
            };
            window.__memory_snapshots__.push(snapshot);
            return snapshot;
        }

        function compareMemorySnapshots() {
            if (!window.__memory_snapshots__ || window.__memory_snapshots__.length < 2) {
                return { error: "Need at least 2 snapshots" };
            }
            const first = window.__memory_snapshots__[0];
            const last = window.__memory_snapshots__[window.__memory_snapshots__.length - 1];
            const growth = (parseFloat(last.used_mb) - parseFloat(first.used_mb)).toFixed(2);
            return { first, last, growth_mb: growth, count: window.__memory_snapshots__.length };
        }

        function generateDiagnosticReport() {
            return {
                timestamp: new Date().toISOString(),
                url: window.location.href,
                heap: getHeapSize(),
                react: getReactStats(),
                snapshots: window.__memory_snapshots__ || null
            };
        }

        // UI Handlers
        function testHeapSize() {
            const result = getHeapSize();
            document.getElementById('heap-result').textContent = JSON.stringify(result, null, 2);
        }

        function testReactStats() {
            const result = getReactStats();
            document.getElementById('react-result').textContent = JSON.stringify(result, null, 2);
        }

        function takeSnapshot() {
            const label = prompt("Snapshot label:", `snap_${(window.__memory_snapshots__?.length || 0) + 1}`);
            if (label) {
                const result = takeMemorySnapshot(label);
                document.getElementById('snapshot-result').textContent =
                    `Snapshot taken: ${label}\n` + JSON.stringify(result, null, 2);
            }
        }

        function compareSnapshots() {
            const result = compareMemorySnapshots();
            document.getElementById('snapshot-result').textContent = JSON.stringify(result, null, 2);
        }

        function generateReport() {
            const result = generateDiagnosticReport();
            document.getElementById('report-result').textContent = JSON.stringify(result, null, 2);
        }

        // Auto-test on load
        window.onload = () => {
            console.log("Memory Test Dashboard loaded");
            console.log("Tip: Open Chrome DevTools (F12) for more detailed memory profiling");
        };
    </script>
</body>
</html>
EOF

    log_success "Created test dashboard: file://$test_page"
    log_info "Open this file in Chrome for manual frontend testing"
}

generate_summary_report() {
    print_header "Generating Summary Report"

    local report_file="$RESULTS_DIR/summary_report_$(date +%Y%m%d_%H%M%S).md"

    cat > "$report_file" << EOF
# z21-Terminal Memory Test Report

**Date**: $(date)
**Duration**: ${DURATION_MINUTES} minutes
**Measurement Interval**: ${INTERVAL_SECONDS}s

## Test Configuration

- **Backend**: Python $(python3 --version)
- **Platform**: $(uname -s) $(uname -m)
- **Total RAM**: $(sysctl hw.memsize 2>/dev/null | awk '{print $2/1024/1024/1024 " GB"}' || echo "Unknown")

## Results

### Backend Memory Usage

CSV file: \`backend_memory_*.csv\`

\`\`\`
$(tail -5 "$RESULTS_DIR"/backend_memory_*.csv 2>/dev/null || echo "No backend data available")
\`\`\`

### Frontend Memory Usage

Manual testing required. See \`frontend_memory_test.js\`

## Recommendations for Jetson Orin Nano

Based on these results, minimum requirements:

- **RAM**: To be determined from test results
- **Storage**: ~2GB for project + models
- **GPU**: TensorRT acceleration recommended for YOLO

## Next Steps

1. Review CSV files in \`results/\`
2. Run frontend tests manually via Chrome DevTools MCP
3. Compare idle vs active vs peak memory usage
4. Update JETSON_DEPLOYMENT.md with final recommendations

EOF

    log_success "Summary report: $report_file"
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    print_header "z21-Terminal Memory Test Suite"

    log_info "Test Duration: ${DURATION_MINUTES} minutes"
    log_info "Measurement Interval: ${INTERVAL_SECONDS}s"

    check_dependencies

    if ! $FRONTEND_ONLY; then
        run_backend_monitor
    fi

    if ! $BACKEND_ONLY; then
        run_frontend_tests
    fi

    generate_summary_report

    print_header "Testing Complete"

    log_success "All test results saved to: $RESULTS_DIR"
    log_info "Review the CSV files and summary report for analysis"
}

main "$@"
