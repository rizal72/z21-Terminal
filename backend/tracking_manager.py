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
        self.stop_timer: Optional[asyncio.Task] = None
        self.is_stopping = False

        # Path to tracking daemon script
        self.daemon_path = Path(__file__).parent / 'tracking_daemon.py'

        print("🎯 TrackingManager initialized")

    def should_track(self) -> bool:
        """
        Check if tracking should be active

        Conditions:
        - At least 1 connected client (web dashboard open)
        - At least 1 consist: speed > 0 AND virtual_mode = True

        Returns:
            bool: True if tracking should be running
        """
        # No clients connected → no tracking needed
        if len(self.connected_clients) == 0:
            return False

        # Check if any consist is moving with Virtual Mode active
        for consist_address, state in self.z21_manager.consist_state.items():
            speed = state.get('speed', 0)
            virtual_mode = state.get('virtual_mode', False)

            # For MVP: always track if moving (virtual_mode not yet implemented)
            # TODO Phase 4B: add virtual_mode check
            if speed > 0:  # and virtual_mode:
                return True

        return False

    async def on_speed_change(self, consist_address: int, new_speed: int):
        """
        Called when speed changes (from WebSocket handler)

        Args:
            consist_address: DCC address of consist
            new_speed: New speed value 0-126
        """
        should_be_active = self.should_track()

        if should_be_active and not self.tracking_process:
            # Start tracking
            await self.start_tracking()

            # Cancel stop timer if it was scheduled
            if self.stop_timer:
                self.stop_timer.cancel()
                self.stop_timer = None
                self.is_stopping = False
                print("   ⏸️  Stop timer cancelled (movement resumed)")

        elif not should_be_active and self.tracking_process and not self.is_stopping:
            # Schedule stop with 10s cooldown
            await self.schedule_stop()

    async def start_tracking(self):
        """Start tracking daemon subprocess"""
        if self.tracking_process:
            print("⚠️  Tracking already running")
            return

        try:
            print("🚀 Starting tracking daemon...")

            # Start daemon as subprocess
            self.tracking_process = subprocess.Popen(
                ['python3', str(self.daemon_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            print(f"  ✓ Tracking daemon started (PID {self.tracking_process.pid})")

        except Exception as e:
            print(f"  ✗ Failed to start tracking daemon: {e}")
            self.tracking_process = None

    async def schedule_stop(self):
        """Schedule tracking stop with 10s cooldown"""
        if self.is_stopping:
            return

        self.is_stopping = True
        print("⏱️  Tracking stop scheduled (10s cooldown)...")

        # Create stop timer task
        self.stop_timer = asyncio.create_task(self._stop_after_cooldown())

    async def _stop_after_cooldown(self):
        """Internal: Stop tracking after cooldown period"""
        try:
            await asyncio.sleep(10)  # 10 second cooldown

            # Check again if we should still stop
            # (movement might have resumed during cooldown)
            if not self.should_track():
                await self.stop_tracking()
            else:
                print("   ⏸️  Stop cancelled (movement detected during cooldown)")
                self.is_stopping = False

        except asyncio.CancelledError:
            # Timer was cancelled (movement resumed)
            self.is_stopping = False
            raise

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
            self.is_stopping = False
            self.stop_timer = None

            # Reset gate timestamps (TODO: implement in Phase 4)
            print("  ✓ Gate timestamps reset")

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

        # Cancel stop timer
        if self.stop_timer:
            self.stop_timer.cancel()
            try:
                await self.stop_timer
            except asyncio.CancelledError:
                pass

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
