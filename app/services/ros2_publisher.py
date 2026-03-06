"""
ROS2 publisher service — gracefully degrades if rclpy is not available.

Publishes FSM command dicts as JSON strings to /mycobot/fsm_command
using std_msgs/String.
"""

import json
import logging
import threading

logger = logging.getLogger(__name__)
try:
    import rclpy
    from std_msgs.msg import String as RosString
    _ROS2_AVAILABLE = True
except ImportError:
    _ROS2_AVAILABLE = False
    logger.warning("[ros2_publisher] rclpy not found - publisher disabled (no-op mode)")

_node = None
_publisher = None
_spin_thread = None
_last_error = None

def start_ros2_publisher() -> None:
    """Initialise rclpy, create the publisher node, and start spinning."""
    global _node, _publisher, _spin_thread, _last_error

    if not _ROS2_AVAILABLE:
        logger.warning("[ros2_publisher] ROS2 unavailable - skipping publisher startup")
        _last_error = "ROS2 runtime not available"
        return

    try:
        _last_error = None
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

        logger.info("[ros2_publisher] Publisher started on /mycobot/fsm_command")
    except Exception:
        _last_error = "Failed to initialize ROS2 publisher"
        logger.exception("[ros2_publisher] ERROR during startup")


def stop_ros2_publisher() -> None:
    """Shutdown rclpy and wait for the spin thread to exit."""
    global _node, _publisher, _spin_thread, _last_error

    if not _ROS2_AVAILABLE:
        return

    try:
        if rclpy.ok():
            rclpy.shutdown()
        if _spin_thread is not None and _spin_thread.is_alive():
            _spin_thread.join(timeout=2.0)
        logger.info("[ros2_publisher] Publisher stopped")
    except Exception:
        _last_error = "Failed to shutdown ROS2 publisher cleanly"
        logger.exception("[ros2_publisher] ERROR during shutdown")
    finally:
        _node = None
        _publisher = None
        _spin_thread = None


def get_ros2_publisher():
    """Return the singleton publisher node (may be None if ROS2 unavailable)."""
    return _node


def get_ros2_status() -> dict:
    """Return ROS2 availability and publisher readiness state."""
    is_ready = _ROS2_AVAILABLE and _publisher is not None
    return {
        "available": _ROS2_AVAILABLE,
        "ready": is_ready,
        "publisher_initialized": _publisher is not None,
        "spinning": _spin_thread is not None and _spin_thread.is_alive(),
        "last_error": _last_error,
    }

def publish_command(payload: dict) -> dict:
    """
    Serialize *payload* to a JSON string and publish it to /mycobot/fsm_command.

    No-ops with a warning if ROS2 is unavailable or the publisher is not yet
    initialised.
    """
    if not _ROS2_AVAILABLE:
        logger.warning("[ros2_publisher] ROS2 not available - command NOT published")
        return {
            "published": False,
            "reason": "ros2_unavailable",
        }

    if _publisher is None:
        logger.warning("[ros2_publisher] publisher not initialised - command NOT published")
        return {
            "published": False,
            "reason": "publisher_not_initialised",
        }

    try:
        msg = RosString()
        msg.data = json.dumps(payload)
        _publisher.publish(msg)
        logger.info("[ros2_publisher] Published FSM command to /mycobot/fsm_command")
        return {
            "published": True,
            "reason": "ok",
        }
    except Exception:
        logger.exception("[ros2_publisher] ERROR publishing command")
        return {
            "published": False,
            "reason": "publish_error",
        }
