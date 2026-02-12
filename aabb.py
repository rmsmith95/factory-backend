import heapq
from typing import List, Tuple

# Axis-aligned bounding box (obstacle)
class AABB:
    def __init__(self, xmin, ymin, zmin, xmax, ymax, zmax):
        self.xmin, self.ymin, self.zmin = xmin, ymin, zmin
        self.xmax, self.ymax, self.zmax = xmax, ymax, zmax

    def contains_xy(self, x: float, y: float, radius: float = 0.0) -> bool:
        """Check if (x,y) collides with this box when projected to XY plane"""
        return (self.xmin - radius <= x <= self.xmax + radius and
                self.ymin - radius <= y <= self.ymax + radius)

# A* pathfinding in 2D
def astar_2d(start: Tuple[float,float], goal: Tuple[float,float],
             obstacles: List[AABB], bounds, step: float = 5.0, radius: float = 2.0):
    (xmin, xmax), (ymin, ymax) = bounds
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: abs(goal[0]-start[0]) + abs(goal[1]-start[1])}

    while open_set:
        _, current = heapq.heappop(open_set)
        if abs(current[0]-goal[0]) < step and abs(current[1]-goal[1]) < step:
            # Reconstruct path
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            return path[::-1]

        for dx, dy in [(step,0), (-step,0), (0,step), (0,-step)]:
            nx, ny = current[0]+dx, current[1]+dy
            if not (xmin <= nx <= xmax and ymin <= ny <= ymax):
                continue
            if any(obs.contains_xy(nx, ny, radius) for obs in obstacles):
                continue
            neighbor = (nx, ny)
            tentative_g = g_score[current] + step
            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + abs(goal[0]-nx) + abs(goal[1]-ny)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return None

# Full planner: safeZ -> XY A* -> descend
def plan_path(start: Tuple[float,float,float],
              goal: Tuple[float,float,float],
              obstacles: List[AABB],
              workspace: Tuple[Tuple[float,float],Tuple[float,float]],
              safe_z: float = 50.0,
              step: float = 5.0,
              radius: float = 2.0) -> List[Tuple[float,float,float]]:
    """
    Returns a list of (x,y,z) waypoints for LitePlacer end effector
    """
    sx, sy, sz = start
    gx, gy, gz = goal

    # 1. Move straight up to safe_z
    path3d = [(sx, sy, safe_z)]

    # 2. Plan XY path at safe_z
    xy_path = astar_2d((sx, sy), (gx, gy), obstacles, workspace, step=step, radius=radius)
    if xy_path is None:
        raise RuntimeError("No XY path found!")

    for (x, y) in xy_path:
        path3d.append((x, y, safe_z))

    # 3. Descend straight to goal
    path3d.append((gx, gy, gz))

    return path3d
