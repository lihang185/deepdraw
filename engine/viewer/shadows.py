"""Directional shadow passes. Scene geometry is shared; light visibility is independent."""
import numpy as np
from engine import core
from . import render_backend

# Keep ambient + direct energy unchanged while lifting sun-facing-away walls.
SHADOW_AMBIENT = 0.6
SHADOW_DIFFUSE = 0.3


def affine(matrix):
    v = np.asarray(render_backend.affine12(matrix)).reshape(4, 3)
    m = np.eye(4); m[:3, :3] = v[:3]; m[:3, 3] = v[3]
    return m


def qt_matrix(matrix):
    return np.asarray([[getattr(matrix.row(r), axis)() for axis in ('x','y','z','w')]
                       for r in range(4)], dtype=float)


def camera_light_direction(camera, world_from_frame):
    """World direction toward the light; camera coordinates belong to the edit frame."""
    backward = camera.position - camera.target
    direction = np.asarray(world_from_frame)[:3, :3] @ np.array(
        (backward.x(), backward.y(), backward.z()))
    length = np.linalg.norm(direction)
    if not np.isfinite(direction).all() or length < 1e-12:
        raise ValueError('当前视角无法确定光源方向')
    return tuple(float(v) for v in direction / length)


def light_projection(bounds, direction):
    """Fit an orthographic light camera to world bounds, in engine centimetres."""
    box = np.asarray(bounds, dtype=float).reshape(3, 2)
    toward_light = np.asarray(direction, dtype=float)
    if (not np.isfinite(box).all() or np.any(box[:, 0] > box[:, 1])
            or toward_light.shape != (3,) or not np.isfinite(toward_light).all()
            or np.linalg.norm(toward_light) < 1e-12):
        raise ValueError('Invalid shadow bounds or light direction')
    toward_light = toward_light / np.linalg.norm(toward_light)
    up = np.array((0., 0., 1.)) if abs(toward_light[2]) < .95 else np.array((0., 1., 0.))
    right = np.cross(up, toward_light); right /= np.linalg.norm(right)
    up = np.cross(toward_light, right)
    center = box.mean(axis=1)
    radius = max(float(np.linalg.norm(box[:,1]-box[:,0])), 1.)
    eye = center + toward_light * (radius * 2)
    view = np.eye(4); view[:3,:3] = np.array((right,up,toward_light))
    view[:3,3] = -view[:3,:3] @ eye
    corners = np.asarray([(x,y,z) for x in box[0] for y in box[1] for z in box[2]])
    local = corners @ view[:3,:3].T + view[:3,3]
    pad = max(radius*.02, 1.)
    lo, hi = local.min(axis=0)-pad, local.max(axis=0)+pad
    near, far = -hi[2], -lo[2]
    projection = np.eye(4)
    projection[0,0], projection[1,1], projection[2,2] = 2/(hi[0]-lo[0]),2/(hi[1]-lo[1]),-2/(far-near)
    projection[0,3] = -(hi[0]+lo[0])/(hi[0]-lo[0])
    projection[1,3] = -(hi[1]+lo[1])/(hi[1]-lo[1])
    projection[2,3] = -(far+near)/(far-near)
    return projection @ view


def planes(matrix):
    return [tuple(matrix[3] + sign*matrix[axis]) for axis in range(3) for sign in (1,-1)]


class ShadowPass:
    def __init__(self, owner):
        if not hasattr(render_backend.native, 'ShadowMap'):
            raise RuntimeError('请先安装支持阴影的 deepdraw_render.pyd，再重新启动客户端')
        self.owner = owner
        self.native = render_backend.native.ShadowMap()
        self.scene = None
        self.geometry_revision = None
        self.key = None
        self.changed = set()
        self.light_clip = None

    def close(self):
        self.native.close()
        self.scene = None
        self.key = self.geometry_revision = None
        self.changed.clear()

    def prepare(self):
        owner, view = self.owner, self.owner.view
        direction = tuple(getattr(view, 'shadow_direction', (.5,-.7,1.)))
        resolution = getattr(view, 'shadow_resolution', 2048)
        key = (owner.resource_revision, owner.transform_revision, direction, resolution)
        if key == self.key:
            return self.light_clip is not None
        if self.geometry_revision != owner.resource_revision or self.scene is None:
            nodes = list(owner.RecursiveRnumInstance(None, owner.top_comp, core.CMatrix(), None))
            self.scene = render_backend.SceneDrawList(owner, nodes)
            self.geometry_revision = owner.resource_revision
        elif self.changed:
            self.scene.update_instances(self.changed)
        self.changed.clear()
        bounds = self.scene.native.bounds()
        if any(bounds[2*i] > bounds[2*i+1] for i in range(3)):
            self.light_clip = None; self.key = key
            return False
        light_clip = light_projection(bounds, direction)
        self.scene.cull(planes(light_clip), owner)
        self.native.configure(resolution)
        self.native.render(self.scene.native, light_clip.flatten(order='F').tolist())
        self.light_clip, self.key = light_clip, key
        return True

    def set_light(self, pipeline, world_from_frame):
        direction = np.asarray(getattr(self.owner.view,'shadow_direction',(.5,-.7,1.)),dtype=float)
        direction /= np.linalg.norm(direction)
        local = np.linalg.solve(world_from_frame[:3,:3], direction)
        gl = pipeline.view.gl
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (*local, 0.))
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, (SHADOW_AMBIENT,)*3 + (1.,))
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, (SHADOW_DIFFUSE,)*3 + (1.,))

    def receive(self, pipeline, world_from_frame, draw):
        eye_to_frame = qt_matrix(pipeline.view.ComputeCameraMatrix()[1])
        bias = np.diag((.5,.5,.5,1.)); bias[:3,3] = .5
        matrix = bias @ self.light_clip @ world_from_frame @ eye_to_frame
        self.native.begin_receive(matrix.flatten(order='F').tolist(),
                                  getattr(self.owner.view,'shadow_strength',.45), .00025)
        try:
            draw()
        finally:
            self.native.end_receive()
