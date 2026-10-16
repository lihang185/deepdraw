"""Render-only triangle/plane intersections; never creates model entities."""
import numpy as np


def section_lines(points, equation):
    triangles = np.asarray(points, dtype=float).reshape(-1, 3, 3)
    if not len(triangles):
        return np.empty((0, 3), dtype=float)
    plane = np.asarray(equation, dtype=float)
    distance = triangles.dot(plane[:3]) + plane[3]
    distance[np.abs(distance) < 1e-9] = 0
    other = np.roll(triangles, -1, axis=1)
    next_distance = np.roll(distance, -1, axis=1)
    crossing = (distance >= 0) != (next_distance >= 0)
    valid = crossing.sum(axis=1) == 2
    triangles, other = triangles[valid], other[valid]
    distance, next_distance, crossing = distance[valid], next_distance[valid], crossing[valid]
    denominator = distance-next_distance
    t = np.divide(distance, denominator, out=np.zeros_like(distance), where=crossing)
    hits = (triangles + t[:,:,None]*(other-triangles))[crossing].reshape(-1, 2, 3)
    hits = hits[np.linalg.norm(hits[:,1]-hits[:,0],axis=1)>1e-9]
    return np.ascontiguousarray(hits.reshape(-1, 3))
