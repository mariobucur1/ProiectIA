"""
Execută o secvență de waypoints world calculate de A* prin controlul P
(proporțional) al vitezelor liniare și unghiulare ale Pioneer P3-DX.

Strategie de control:
1. Pentru fiecare waypoint țintă:
   - Calculează diferența de unghi față de țintă (heading_error).
   - Calculează distanța rămasă până la țintă (distance_error).
2. Comenzi de viteză:
   - v_angular = Kp_angular · heading_error  (rotește spre țintă)
   - v_linear  = Kp_linear · distance_error · cos(heading_error)
     (avansează doar când e aliniat; factorul cos previne mișcarea
      laterală când robotul nu este orientat corect)
3. Trece la următorul waypoint când distance_error < waypoint_tolerance.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Sequence

from .pioneer import PioneerController


@dataclass
class ExecutorConfig:
    """Parametri tunabili pentru controlerul de drum."""
    waypoint_tolerance: float = 0.12          # m
    final_tolerance: float = 0.10              # m
    kp_linear: float = 0.8
    kp_angular: float = 2.5
    max_linear: float = 0.4                    # m/s
    max_angular: float = 1.5                   # rad/s
    align_threshold_rad: float = math.radians(30)
    control_dt: float = 0.05                   # s
    timeout_seconds: float = 60.0


class PathExecutor:
    """Trimite robotului comenzi pentru a urma o listă de waypoints."""

    def __init__(self, controller: PioneerController, config: ExecutorConfig | None = None):
        self.controller = controller
        self.config = config or ExecutorConfig()

    def follow(self, waypoints: Sequence[tuple[float, float]]) -> bool:
        """
        Parcurge waypoints unul după altul. Returnează True la succes.

        În mod stepping CoppeliaSim avansează simularea cu `step()` între
        comenzi — apelantul trebuie să fi pornit deja simularea.
        """
        if not waypoints:
            return True

        cfg = self.config
        start_time = time.perf_counter()

        for idx, (wx, wy) in enumerate(waypoints):
            is_last = idx == len(waypoints) - 1
            tolerance = cfg.final_tolerance if is_last else cfg.waypoint_tolerance

            while True:
                if (time.perf_counter() - start_time) > cfg.timeout_seconds:
                    self.controller.stop()
                    return False

                x, y, theta = self.controller.get_pose()
                dx = wx - x
                dy = wy - y
                distance = math.hypot(dx, dy)

                if distance < tolerance:
                    break

                target_angle = math.atan2(dy, dx)
                heading_error = self.controller.normalize_angle(target_angle - theta)

                v_angular = cfg.kp_angular * heading_error
                alignment_factor = max(0.0, math.cos(heading_error))
                if abs(heading_error) > cfg.align_threshold_rad:
                    v_linear = 0.0
                else:
                    v_linear = cfg.kp_linear * distance * alignment_factor

                v_linear = max(-cfg.max_linear, min(cfg.max_linear, v_linear))
                v_angular = max(-cfg.max_angular, min(cfg.max_angular, v_angular))

                self.controller.set_velocity(v_linear, v_angular)
                self.controller.step()

        self.controller.stop()
        return True
