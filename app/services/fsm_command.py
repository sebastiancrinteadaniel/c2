"""
Shared hardcoded FSM command builder for page task start endpoints.
"""

import json

from app.services.global_settings import get_end_effector_type

_BASE_FSM_COMMAND = {
    "end_effector_type": "gripper",
    "loop": False,
    "states": [
        {
            "type": "SetPositionState",
            "joint_angles": [0.0, 0.0, 1.8, 0.0, 0.0, 0.0],
        },
        {
            "type": "ReachTargetState",
            "point_goal": [0.0, -0.20, 0.04, 0.7071, 0.7071, 0.0, 0.0],
        },
        {
            "type": "EndEffectorState",
            "action": "close",
            "duration": 1.0,
        },
        {
            "type": "ReachTargetState",
            "point_goal": [0.15, -0.13, 0.08, 0.7071, 0.7071, 0.0, 0.0],
        },
        {
            "type": "EndEffectorState",
            "action": "open",
            "duration": 1.0,
        },
    ],
}


def build_hardcoded_fsm_command() -> dict:
    command = json.loads(json.dumps(_BASE_FSM_COMMAND))
    command["end_effector_type"] = get_end_effector_type()
    return command
