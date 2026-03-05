"""
ROS2 publisher service — gracefully degrades if rclpy is not available.

Publishes FSM command dicts as JSON strings to /mycobot/fsm_command
using std_msgs/String.
"""

import json
import threading

# ---------------------------------------------------------------------------
# Optional ROS2 import — app keeps running without a ROS2 environment
# ---------------------------------------------------------------------------
try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String as RosString
    _ROS2_AVAILABLE = True
except ImportError:
    _ROS2_AVAILABLE = False
    print("[ros2_publisher] WARNING: rclpy not found — publisher disabled (no-op mode).")

# ---------------------------------------------------------------------------
# Singleton state
# ---------------------------------------------------------------------------
_node = None          # rclpy Node instance
_publisher = None     # rclpy Publisher instance
_spin_thread = None   # background daemon thread running rclpy.spin()


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------

def start_ros2_publisher() -> None:
    """Initialise rclpy, create the publisher node, and start spinning."""
    global _node, _publisher, _spin_thread

    if not _ROS2_AVAILABLE:
        print("[ros2_publisher] ROS2 unavailable — skipping publisher startup.")
        return

    try:
        rclpy.init()
        _node = rclpy.create_node("mycobot_fsm_publisher")
        _publisher = _node.create_publisher(RosString, "/mycobot/fsm_command", 10)

        _spin_thread = threading.Thread(    
            target=rclpy.spin,
            args=(_node,),
            daemon=True,
            name="ros2-spin",
        )
        _spin_thread.start()

        print("[ros2_publisher] Publisher started on /mycobot/fsm_command")
    except Exception as exc:  # noqa: BLE001
        print(f"[ros2_publisher] ERROR during startup: {exc}")


def stop_ros2_publisher() -> None:
    """Shutdown rclpy and wait for the spin thread to exit."""
    global _node, _publisher, _spin_thread

    if not _ROS2_AVAILABLE:
        return

    try:
        if rclpy.ok():
            rclpy.shutdown()
        if _spin_thread is not None and _spin_thread.is_alive():
            _spin_thread.join(timeout=2.0)
        print("[ros2_publisher] Publisher stopped.")
    except Exception as exc:  # noqa: BLE001
        print(f"[ros2_publisher] ERROR during shutdown: {exc}")
    finally:
        _node = None
        _publisher = None
        _spin_thread = None


def get_ros2_publisher():
    """Return the singleton publisher node (may be None if ROS2 unavailable)."""
    return _node


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def publish_command(payload: dict) -> None:
    """
    Serialize *payload* to a JSON string and publish it to /mycobot/fsm_command.

    No-ops with a warning if ROS2 is unavailable or the publisher is not yet
    initialised.
    """
    if not _ROS2_AVAILABLE:
        print("[ros2_publisher] WARNING: ROS2 not available — command NOT published.")
        return

    if _publisher is None:
        print("[ros2_publisher] WARNING: publisher not initialised — command NOT published.")
        return

    try:
        msg = RosString()
        msg.data = json.dumps(payload)
        _publisher.publish(msg)
        print(f"[ros2_publisher] Published FSM command to /mycobot/fsm_command")
    except Exception as exc:  # noqa: BLE001
        print(f"[ros2_publisher] ERROR publishing command: {exc}")
