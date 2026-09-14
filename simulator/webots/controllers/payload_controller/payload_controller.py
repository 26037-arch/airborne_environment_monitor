from __future__ import annotations

import os
import math
import sys
from datetime import datetime
from pathlib import Path

from controller import Supervisor

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.data_types import PayloadState
from simulator.configuration import load_config
from simulator.runtime import SimulationRuntime


def update_arrow(node, origin, vector) -> None:
    magnitude = math.sqrt(sum(component * component for component in vector))
    if magnitude < 1e-9:
        node.getField("scale").setSFVec3f([1.0, 0.001, 1.0])
        node.getField("translation").setSFVec3f(list(origin))
        return
    unit = tuple(component / magnitude for component in vector)
    display_length = min(20.0, max(0.5, magnitude))
    # Cylinder의 기본 +Y 축을 vector 방향으로 회전합니다.
    axis = (unit[2], 0.0, -unit[0])
    axis_norm = math.hypot(axis[0], axis[2])
    angle = math.acos(max(-1.0, min(1.0, unit[1])))
    if axis_norm < 1e-9:
        rotation = [1.0, 0.0, 0.0, 0.0 if unit[1] >= 0 else math.pi]
    else:
        rotation = [axis[0] / axis_norm, 0.0, axis[2] / axis_norm, angle]
    center = [origin[i] + unit[i] * display_length * 0.5 for i in range(3)]
    node.getField("translation").setSFVec3f(center)
    node.getField("rotation").setSFRotation(rotation)
    node.getField("scale").setSFVec3f([1.0, display_length, 1.0])


def main() -> None:
    robot = Supervisor()
    step_ms = int(robot.getBasicTimeStep())
    config_path = Path(os.environ.get("AEM_SIM_CONFIG", PROJECT_ROOT / "simulator" / "default_config.json"))
    config = load_config(config_path)
    run_root = Path(os.environ.get("AEM_SIM_RUN_DIR", PROJECT_ROOT / "simulator" / "runs"))
    run_directory = run_root / datetime.now().strftime("run_%Y-%m-%d_%H-%M-%S")

    payload = robot.getSelf()
    payload.getField("translation").setSFVec3f([0.0, 0.0, config.initial_altitude_m])
    payload.setVelocity([
        config.initial_velocity_east_mps,
        config.initial_velocity_north_mps,
        config.initial_velocity_vertical_mps,
        0.0, 0.0, 0.0,
    ])
    physics = payload.getField("physics").getSFNode()
    physics.getField("mass").setSFFloat(config.payload_mass_kg)
    emitter = robot.getDevice("xbee emitter")

    trajectory_coord = robot.getFromDef("TRAJECTORY_COORD").getField("point")
    trajectory_index = robot.getFromDef("TRAJECTORY_LINE").getField("coordIndex")
    wind_arrow = robot.getFromDef("WIND_ARROW")
    ground_arrow = robot.getFromDef("GROUND_VELOCITY_ARROW")
    relative_arrow = robot.getFromDef("RELATIVE_AIR_ARROW")
    trajectory_count = 0
    runtime = SimulationRuntime(config, PROJECT_ROOT / "simulator" / "data", run_directory)
    last_trail_time = -1.0

    try:
        while robot.step(step_ms) != -1:
            now = robot.getTime()
            position = tuple(float(value) for value in payload.getPosition())
            velocity = payload.getVelocity()
            rotation = tuple(float(value) for value in payload.getField("rotation").getSFRotation())
            latitude = config.latitude + position[1] / 111_320.0
            longitude = config.longitude + position[0] / max(
                1.0, 111_320.0 * math.cos(math.radians(latitude))
            )
            state = PayloadState(
                now, latitude, longitude, max(0.0, position[2]), position,
                (float(velocity[0]), float(velocity[1]), float(velocity[2])), rotation,
            )
            drag_force, transmitted_rows, environment = runtime.step(state)
            payload.addForce(list(drag_force), False)
            relative_air = tuple(velocity[i] - environment.wind_vector[i] for i in range(3))
            update_arrow(wind_arrow, position, environment.wind_vector)
            update_arrow(ground_arrow, position, state.velocity_ground_mps)
            update_arrow(relative_arrow, position, relative_air)
            for row in transmitted_rows:
                emitter.send((row + "\n").encode("ascii"))

            if now - last_trail_time >= 0.2 and trajectory_count < 5000:
                trajectory_coord.insertMFVec3f(-1, list(position))
                trajectory_index.insertMFInt32(-1, trajectory_count)
                trajectory_count += 1
                last_trail_time = now
            if position[2] <= 0.26 and abs(velocity[2]) < 0.1:
                break
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
