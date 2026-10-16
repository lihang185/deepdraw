"""Read-only geometric evidence. Shape labels are not semantic roles."""
from collections import Counter
import math
import numpy as np
from engine import core


def xyz(p):
    return [p.x, p.y, p.z]


def bounds(points):
    if not len(points):
        return None
    points = np.asarray(points, dtype=float)
    lo,hi = points.min(axis=0),points.max(axis=0)
    return dict(min=lo.tolist(), max=hi.tolist(), size=(hi-lo).tolist())


class Bounds:
    def __init__(self, context):
        self.s = context

    def bounds(self, target):
        """Fast parent-space AABB, without topology/shape analysis of library meshes."""
        native = self.s.single(target)
        inst = native if isinstance(native, core.CComponentInstance) else None
        comp = inst.GetDefinition() if inst else native
        if isinstance(comp, core.CComponent):
            seen = set()
            def compute(container):
                if container.GetID() in seen:
                    return
                seen.add(container.GetID())
                for child in container.EnumEntities():
                    if isinstance(child, core.CComponentInstance) and not child.IsMarkedDeleted():
                        compute(child.GetDefinition())
                container.ComputeBoundingBox()
            compute(comp)
        box = comp.GetBoundingBox()
        lo = [box.min_x, box.min_y, box.min_z]
        hi = [box.max_x, box.max_y, box.max_z]
        if not all(math.isfinite(v) for v in lo+hi) or any(a>b for a,b in zip(lo,hi)):
            return None
        if inst:
            matrix = inst.GetTransform()
            return bounds([xyz(matrix.Transform(core.CVector3D(x,y,z)))
                           for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])])
        return dict(min=lo, max=hi, size=[b-a for a,b in zip(lo,hi)])
