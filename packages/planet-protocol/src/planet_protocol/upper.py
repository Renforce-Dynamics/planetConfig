"""Joint-position target client; radians, increasing sequence and activation token.

The receiver owns the activation and holds its most recent accepted target. A
receipt acknowledges mailbox reception only, not execution by a robot.
"""

from .client import JOINT_TARGET_SCHEMA, JointTargetClient

__all__ = ["JOINT_TARGET_SCHEMA", "JointTargetClient"]
