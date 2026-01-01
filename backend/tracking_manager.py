"""
TrackingManager - Intelligent process control for YOLO tracking daemon
"""
import asyncio
from pathlib import Path
from typing import Optional
import sys

# Import daemon in-process (not subprocess) for frame queue sharing
sys.path.insert(0, str(Path(__file__).parent))
from tracking_daemon import TrackingDaemon


class TrackingManager:
    """
    Manages YOLO tracking daemon lifecycle with intelligent activation (in-process asyncio.Task)
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
        self.daemon: Optional[TrackingDaemon] = None
        self.daemon_task: Optional[asyncio.Task] = None

        print("🎯 TrackingManager initialized (in-process asyncio.Task for frame queue sharing)")

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
        if self.should_track() and not self.daemon_task:
            await self.start_tracking()

    async def start_tracking(self):
        """Start tracking daemon as asyncio.Task (in-process for frame queue sharing)"""
        if self.daemon_task:
            print("⚠️  Tracking already running")
            return

        try:
            print("🚀 Starting tracking daemon (in-process asyncio.Task)...")

            # Create daemon instance
            self.daemon = TrackingDaemon()

            # Start daemon as asyncio task
            self.daemon_task = asyncio.create_task(self.daemon.run())

            print(f"  ✓ Tracking daemon started (frame_queue accessible for video feed)")

        except Exception as e:
            print(f"  ✗ Failed to start tracking daemon: {e}")
            self.daemon = None
            self.daemon_task = None

    async def stop_tracking(self):
        """Stop tracking daemon (asyncio.Task)"""
        if not self.daemon_task:
            return

        try:
            print("🛑 Stopping tracking daemon...")

            # Signal daemon to stop
            if self.daemon:
                self.daemon.running = False

            # Cancel task and wait for cleanup
            self.daemon_task.cancel()
            try:
                await self.daemon_task
            except asyncio.CancelledError:
                pass  # Expected

            print("  ✓ Tracking daemon stopped")

        except Exception as e:
            print(f"  ✗ Error stopping tracking daemon: {e}")

        finally:
            self.daemon = None
            self.daemon_task = None
            print("  ✓ Tracking daemon cleanup complete")

    async def on_client_connected(self):
        """Called when a client connects"""
        print(f"👤 Client connected (total: {len(self.connected_clients)})")

        # Start tracking daemon
        if self.should_track() and not self.daemon_task:
            await self.start_tracking()

    async def on_client_disconnected(self):
        """Called when a client disconnects"""
        print(f"👤 Client disconnected (remaining: {len(self.connected_clients)})")

        # Stop tracking if no clients remain
        if len(self.connected_clients) == 0 and self.daemon_task:
            print("   → No clients remaining, stopping tracking...")
            await self.stop_tracking()

    async def shutdown(self):
        """Cleanup on backend shutdown"""
        print("🧹 TrackingManager shutting down...")

        # Stop tracking daemon
        if self.daemon_task:
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
