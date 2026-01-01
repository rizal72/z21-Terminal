"""
TrackingManager - Intelligent process control for YOLO tracking daemon
"""
import asyncio
import subprocess
import signal
from pathlib import Path
from typing import Optional


class TrackingManager:
    """
    Manages YOLO tracking daemon lifecycle with intelligent activation
    """

    def __init__(self, z21_manager, connected_clients_list: list):
        """
        Initialize TrackingManager

        Args:
            z21_manager: Z21Manager instance
            connected_clients_list: Reference to connected_clients list from main.py
        """
        self.z21_manager = z21_manager
        self.connected_clients = connected_clients_list
        self.tracking_process: Optional[subprocess.Popen] = None

        # Path to tracking daemon script
        self.daemon_path = Path(__file__).parent / 'tracking_daemon.py'

        print("🎯 TrackingManager initialized (always-on mode with dynamic FPS)")

    def should_track(self) -> bool:
        """
        Check if tracking should be active

        Daemon stays active as long as at least 1 client is connected.
        FPS dynamically adjusts based on movement (handled by daemon).

        Returns:
            bool: True if tracking should be running
        """
        # Daemon active whenever dashboard is open
        return len(self.connected_clients) > 0

    async def on_speed_change(self, consist_address: int, new_speed: int):
        """
        Called when speed changes (from WebSocket handler)

        No longer stops daemon on speed = 0. Daemon uses dynamic FPS instead.

        Args:
            consist_address: DCC address of consist
            new_speed: New speed value 0-126
        """
        # Start tracking if not already running (client connected but daemon not started yet)
        if self.should_track() and not self.tracking_process:
            await self.start_tracking()

    async def start_tracking(self):
        """Start tracking daemon subprocess"""
        if self.tracking_process:
            print("⚠️  Tracking already running")
            return

        try:
            print("🚀 Starting tracking daemon...")

            # Start daemon as subprocess (inherit stdout/stderr for visible logs)
            self.tracking_process = subprocess.Popen(
                ['python3', str(self.daemon_path)]
            )

            print(f"  ✓ Tracking daemon started (PID {self.tracking_process.pid})")
            print(f"     Daemon logs will appear below:")

        except Exception as e:
            print(f"  ✗ Failed to start tracking daemon: {e}")
            self.tracking_process = None

    async def stop_tracking(self):
        """Stop tracking daemon"""
        if not self.tracking_process:
            return

        try:
            print("🛑 Stopping tracking daemon...")

            # Send SIGTERM for graceful shutdown
            self.tracking_process.send_signal(signal.SIGTERM)

            # Wait up to 5 seconds for graceful shutdown
            try:
                self.tracking_process.wait(timeout=5)
                print(f"  ✓ Tracking daemon stopped (PID {self.tracking_process.pid})")
            except subprocess.TimeoutExpired:
                # Force kill if didn't stop gracefully
                print("  ⚠️  Daemon didn't stop gracefully, force killing...")
                self.tracking_process.kill()
                self.tracking_process.wait()
                print("  ✓ Tracking daemon killed")

        except Exception as e:
            print(f"  ✗ Error stopping tracking daemon: {e}")

        finally:
            self.tracking_process = None
            print("  ✓ Tracking daemon cleanup complete")

    async def on_client_connected(self):
        """Called when a client connects"""
        print(f"👤 Client connected (total: {len(self.connected_clients)})")

        # Start tracking if movement detected
        if self.should_track() and not self.tracking_process:
            await self.start_tracking()

    async def on_client_disconnected(self):
        """Called when a client disconnects"""
        print(f"👤 Client disconnected (remaining: {len(self.connected_clients)})")

        # Stop tracking if no clients remain
        if len(self.connected_clients) == 0 and self.tracking_process:
            print("   → No clients remaining, stopping tracking...")
            await self.stop_tracking()

    async def shutdown(self):
        """Cleanup on backend shutdown"""
        print("🧹 TrackingManager shutting down...")

        # Stop tracking daemon
        if self.tracking_process:
            await self.stop_tracking()

        print("  ✓ TrackingManager cleanup complete")


if __name__ == '__main__':
    # Test tracking manager
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

    from z21_manager import Z21Manager

    async def test():
        # Mock Z21Manager
        z21_mgr = Z21Manager(verbose=False)
        if not z21_mgr.connect():
            print("Failed to connect to Z21")
            return

        # Mock consists
        z21_mgr.consist_state = {
            10: {'speed': 0, 'virtual_mode': False},
            11: {'speed': 0, 'virtual_mode': False}
        }

        # Mock connected clients
        connected_clients = []

        # Initialize tracking manager
        tracker = TrackingManager(z21_mgr, connected_clients)

        # Test 1: No tracking (no clients, no movement)
        print("\n=== Test 1: No tracking ===")
        print(f"Should track: {tracker.should_track()}")  # False

        # Test 2: Client connects (still no movement)
        print("\n=== Test 2: Client connects ===")
        connected_clients.append("mock_client")
        await tracker.on_client_connected()
        print(f"Should track: {tracker.should_track()}")  # False

        # Test 3: Movement starts
        print("\n=== Test 3: Movement starts ===")
        z21_mgr.consist_state[11]['speed'] = 50
        await tracker.on_speed_change(11, 50)
        print(f"Should track: {tracker.should_track()}")  # True
        await asyncio.sleep(2)  # Let daemon start

        # Test 4: Movement stops (cooldown)
        print("\n=== Test 4: Movement stops (cooldown) ===")
        z21_mgr.consist_state[11]['speed'] = 0
        await tracker.on_speed_change(11, 0)
        print(f"Should track: {tracker.should_track()}")  # False
        print("Waiting 11s for cooldown...")
        await asyncio.sleep(11)  # Wait for cooldown

        # Test 5: Shutdown
        print("\n=== Test 5: Shutdown ===")
        await tracker.shutdown()

        z21_mgr.disconnect()
        print("\n✅ All tests complete")

    # Run test
    asyncio.run(test())
