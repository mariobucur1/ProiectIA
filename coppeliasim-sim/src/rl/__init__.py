"""
Componenta de Reinforcement Learning pentru rezolvarea labirintului Arena.

Robotul învață singur ruta de la START la STOP printr-un mediu grid rapid
(MazeEnv) antrenat cu Q-learning tabular. Politica învățată este apoi
transferată în CoppeliaSim, unde robotul fizic parcurge drumul (vezi deploy.py).

Antrenarea rulează headless (fără CoppeliaSim) pentru viteză — mii de episoade
în câteva secunde, în loc de minute/ore în simulatorul real-time.
"""

from .maze_env import MazeEnv
from .qlearning import QLearningAgent

__all__ = ["MazeEnv", "QLearningAgent"]
