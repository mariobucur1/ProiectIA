"""
Controller pentru robotul Pioneer P3-DX folosind ZMQ Remote API.

Robotul are tracțiune diferențială (2 roți + caster) — viteza fiecărei roți
se setează independent. Translația și rotația sunt calculate din diferența
și suma celor două viteze:

    v_linear  = (v_left + v_right) * R / 2          [m/s]
    v_angular = (v_right - v_left) * R / L          [rad/s]

unde R = raza roții, L = distanța dintre roți.

Pentru Pioneer P3-DX:
    R ≈ 0.0975 m
    L ≈ 0.381 m
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from coppeliasim_zmqremoteapi_client import RemoteAPIClient


@dataclass
class PioneerSpec:
    """Parametri fizici robot diferential (default: Diff_Drive_Bot din Arena.ttt)."""
    wheel_radius: float = 0.04        # m — masurat din scena
    wheel_base: float = 0.21          # m — distanta intre roti
    max_wheel_speed: float = 8.0      # rad/s — Diff_Drive_Bot suporta viteze mai mari decat Pioneer


class PioneerController:
    """
    Wrapper peste ZMQ Remote API pentru controlul Pioneer P3-DX.

    Folosire tipică:
        controller = PioneerController()
        controller.connect()
        controller.start_simulation()
        controller.set_velocity(linear=0.2, angular=0.0)
        x, y, theta = controller.get_pose()
        controller.stop_simulation()
    """

    LEFT_MOTOR = "/Diff_Drive_Bot/left_joint"
    RIGHT_MOTOR = "/Diff_Drive_Bot/right_joint"
    ROBOT_HANDLE = "/Diff_Drive_Bot"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 23000,
        spec: PioneerSpec | None = None,
    ):
        self.host = host
        self.port = port
        self.spec = spec or PioneerSpec()
        self._client: RemoteAPIClient | None = None
        self._sim = None
        self._left_handle: int | None = None
        self._right_handle: int | None = None
        self._robot_handle: int | None = None

    def connect(self) -> None:
        """Stabilește conexiunea ZMQ și obține handle-urile."""
        self._client = RemoteAPIClient(self.host, self.port)
        self._sim = self._client.require("sim")
        self._left_handle = self._sim.getObject(self.LEFT_MOTOR)
        self._right_handle = self._sim.getObject(self.RIGHT_MOTOR)
        self._robot_handle = self._sim.getObject(self.ROBOT_HANDLE)

    @property
    def sim(self):
        """Obiectul `sim` ZMQ (pentru operații avansate: senzori, capturi)."""
        self._ensure_connected()
        return self._sim

    def disconnect(self) -> None:
        self._client = None
        self._sim = None
        self._left_handle = None
        self._right_handle = None
        self._robot_handle = None

    def start_simulation(self) -> None:
        self._ensure_connected()
        self._sim.setStepping(True)
        self._sim.startSimulation()

    def stop_simulation(self) -> None:
        self._ensure_connected()
        self._sim.stopSimulation()

    def step(self) -> None:
        """Avansează simularea cu un pas (mod stepping)."""
        self._ensure_connected()
        self._sim.step()

    def set_wheel_velocities(self, left: float, right: float) -> None:
        """Setează direct vitezele celor două roți (rad/s)."""
        self._ensure_connected()
        left = max(-self.spec.max_wheel_speed, min(self.spec.max_wheel_speed, left))
        right = max(-self.spec.max_wheel_speed, min(self.spec.max_wheel_speed, right))
        self._sim.setJointTargetVelocity(self._left_handle, left)
        self._sim.setJointTargetVelocity(self._right_handle, right)

    def set_velocity(self, linear: float, angular: float) -> None:
        """
        Comandă unificată: viteză liniară (m/s) + viteză unghiulară (rad/s).

        Conversie inversă din modelul diferențial:
            v_left  = (v_linear - v_angular · L/2) / R
            v_right = (v_linear + v_angular · L/2) / R
        """
        R = self.spec.wheel_radius
        L = self.spec.wheel_base
        v_left = (linear - angular * L / 2.0) / R
        v_right = (linear + angular * L / 2.0) / R
        self.set_wheel_velocities(v_left, v_right)

    def stop(self) -> None:
        self.set_wheel_velocities(0.0, 0.0)

    def get_pose(self) -> tuple[float, float, float]:
        """Returnează (x, y, theta) — poziție în plan și orientare yaw (rad)."""
        self._ensure_connected()
        pos = self._sim.getObjectPosition(self._robot_handle, -1)
        ori = self._sim.getObjectOrientation(self._robot_handle, -1)
        return float(pos[0]), float(pos[1]), float(ori[2])

    def get_position_2d(self) -> tuple[float, float]:
        x, y, _ = self.get_pose()
        return x, y

    @staticmethod
    def normalize_angle(angle: float) -> float:
        """Normalizează un unghi în intervalul [-π, π]."""
        return math.atan2(math.sin(angle), math.cos(angle))

    def _ensure_connected(self) -> None:
        if self._client is None or self._sim is None:
            raise RuntimeError("Controller-ul nu este conectat. Apelează connect() întâi.")
