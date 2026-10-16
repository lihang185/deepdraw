"""World-space view/native picking; explicit component-local editing boundary."""
from contextlib import contextmanager
from engine import core
import numpy as np


def affine(matrix):
    origin = matrix.Transform(core.CVector3D())
    columns = [matrix.Transform(core.CVector3D(*p))-origin
               for p in ((1,0,0),(0,1,0),(0,0,1))]
    result = np.eye(4)
    result[:3,:3] = np.array([p.ToTuple() for p in columns]).T
    result[:3,3] = origin.ToTuple()
    return result


def inverse_matrix(matrix):
    # Native Inverted assumes an orthogonal basis in some binding versions.
    try:
        values = np.linalg.inv(affine(matrix))
    except np.linalg.LinAlgError:
        raise ValueError('当前组件矩阵不可逆，无法转换拾取坐标')
    result = core.CMatrix()
    for i in range(3):
        result.SetAxis(i,core.CVector3D(*values[:3,i]))
    result.SetRow(3,core.CVector3D(*values[:3,3]))
    return result


def transform_plane(matrix, plane):
    equation = np.linalg.solve(affine(matrix).T,[plane.x,plane.y,plane.z,plane.w])
    equation /= np.linalg.norm(equation[:3])
    return core.CPlane.Load(*equation)


def transform_bounds(matrix, box):
    if box is None:return None
    from itertools import product
    points = [matrix.Transform(core.CVector3D(*p)).ToTuple()
              for p in product(*zip(box['min'],box['max']))]
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    return dict(min=lo,max=hi,size=[b-a for a,b in zip(lo,hi)])


def active_matrix(view):
    return view.model.GetActiveComponentPath().ComputeMatrix()


def hit_in_active(view, hit):
    """A shared definition is editable only through the opened occurrence."""
    if hit is None:return False
    active = view.model.GetActiveComponentPath()
    path = [e.GetID() for e in hit.inst_path if isinstance(e,core.CComponentInstance)]
    prefix = [active.Get(i).GetID() for i in range(active.Length())]
    return path[:len(prefix)] == prefix


def to_world(view, point):
    return None if point is None else active_matrix(view).Transform(point)


def to_local(view, point):
    return None if point is None else inverse_matrix(active_matrix(view)).Transform(point)


def local_vector(view, vector):
    inverse = inverse_matrix(active_matrix(view))
    return inverse.Transform(vector)-inverse.Transform(core.CVector3D())


def local_plane(view, plane):
    return transform_plane(inverse_matrix(active_matrix(view)),plane)


def local_ray(view, x, y):
    ray = view.ComputePickRay(x, y)
    return core.CStraightLine(to_local(view, ray.PointAt(0)),
                              local_vector(view, ray.dir).Normalized())


def local_projection(view):
    from engine.viewer.view3d import toQtMatrix2
    return view.ComputeProjectMatrix()*view.ComputeCameraMatrix()[0]*toQtMatrix2(active_matrix(view))


@contextmanager
def local_drawing(view, gl):
    """Local geometry stays local; only its model matrix enters the world view."""
    from engine.viewer.matrices import gl_matrix
    gl.glPushMatrix()
    gl.glPushAttrib(gl.GL_POLYGON_BIT)
    try:
        matrix = active_matrix(view)
        gl.glMultMatrixd(gl_matrix(matrix))
        x, y, z = (matrix.Transform(core.CVector3D(*p))-matrix.Transform(core.CVector3D())
                   for p in ((1,0,0),(0,1,0),(0,0,1)))
        gl.glFrontFace(gl.GL_CW if x.Cross(y).Dot(z)<0 else gl.GL_CCW)
        yield
    finally:
        gl.glPopAttrib()
        gl.glPopMatrix()


def world_vector(view, vector):
    matrix=active_matrix(view)
    return matrix.Transform(vector)-matrix.Transform(core.CVector3D())


def world_length(view, vector):
    return world_vector(view,vector).Length()


def local_distance(view, direction, distance):
    scale=world_length(view,direction.Normalized())
    if scale<1e-12:raise ValueError('当前方向的组件缩放为零')
    return distance/scale
