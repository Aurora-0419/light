#!/usr/bin/env bash
set -eo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPEN_MANIPULATOR_ROOT="${WORKSPACE_ROOT}/../open_manipulator"
COMPAT_LIB_ROOT="${WORKSPACE_ROOT}/compat_lib"

set +u
source /opt/ros/humble/setup.bash
source "${OPEN_MANIPULATOR_ROOT}/install/setup.bash"
source "${WORKSPACE_ROOT}/install/setup.bash"
set -u

# ROS Humble on this machine must use the system Python runtime.
export PATH="/usr/bin:/bin:${PATH}"

# Local compatibility shim for this machine's MoveIt Servo runtime.
mkdir -p "${COMPAT_LIB_ROOT}"
if [[ ! -e "${COMPAT_LIB_ROOT}/libgeometric_shapes.so.2.3.4" && -e "/opt/ros/humble/lib/libgeometric_shapes.so.2.3.2" ]]; then
  ln -sf /opt/ros/humble/lib/libgeometric_shapes.so.2.3.2 "${COMPAT_LIB_ROOT}/libgeometric_shapes.so.2.3.4"
fi
export LD_LIBRARY_PATH="${COMPAT_LIB_ROOT}:${LD_LIBRARY_PATH:-}"

exec ros2 launch system_coordinator shadow_lamp_sim.launch.py "$@"
