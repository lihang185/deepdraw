"""Editor overlays. Engine objects supply geometry/inference, never GL calls.

These helpers preserve GL state; they are excluded from material and future
shadow passes. Inference remains in CInputPointFinder, its presentation is here.
"""
from engine.coordinates import inverse_matrix
import numpy as np
from engine import core
from engine.qt import QtGui


def draw_guide(gl, origin, direction, length):
    direction = direction.Normalized()
    a, b = origin - direction * length, origin + direction * length
    gl.glBegin(gl.GL_LINES)
    gl.glVertex3d(a.x, a.y, a.z)
    gl.glVertex3d(b.x, b.y, b.z)
    gl.glEnd()


def draw_diamond(gl, point, size):
    vertices = [(point.x + dx*size, point.y + dy*size, point.z + dz*size)
                for dx, dy, dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))]
    gl.glBegin(gl.GL_LINES)
    for i, j in ((0,2),(2,1),(1,3),(3,0),(0,4),(1,4),(2,4),(3,4),
                 (0,5),(1,5),(2,5),(3,5)):
        gl.glVertex3d(*vertices[i]); gl.glVertex3d(*vertices[j])
    gl.glEnd()


def draw_inference(view, finder, gl):
    snap = finder.snap_type
    if snap == core.SnapType.none:
        return
    point = finder.Position()
    local = view.ComputeCameraMatrix()[0].map(QtGui.QVector3D(point.x, point.y, point.z))
    if local.z() >= 0:
        return
    size = view.ComputeHightAtRayDepth(-local.z()) / max(1, view.height()) * 5
    # Stable screen-size markers: vertices green, midpoints cyan, faces blue,
    # intersections magenta, unconstrained/axis inference orange.
    color = {core.SnapType.vertex: (.1,.8,.2), core.SnapType.edge_center: (0,.8,.8),
             core.SnapType.face: (.2,.4,1), core.SnapType.intersection: (.8,.1,.8),
             core.SnapType.ref_point_intersect: (.8,.1,.8)}.get(snap, (1,.55,.05))
    gl.glPushAttrib(gl.GL_ENABLE_BIT | gl.GL_CURRENT_BIT | gl.GL_LINE_BIT | gl.GL_DEPTH_BUFFER_BIT)
    try:
        gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glDepthMask(False)
        gl.glColor3f(*color)
        gl.glLineWidth(2)
        from engine.coordinates import active_matrix
        from .matrices import gl_matrix
        gl.glPushMatrix()
        try:
            gl.glMultMatrixd(gl_matrix(inverse_matrix(active_matrix(view))))
            draw_diamond(gl, point, size)
        finally:
            gl.glPopMatrix()
    finally:
        gl.glPopAttrib()


class FaceOverlayCache:
    """CPU triangles for selected faces, invalidated by model/cache revision."""
    def __init__(self):
        self.key = None
        self.triangles = {}
        self.mesh_builds = 0

    def clear(self):
        self.key = None
        self.triangles.clear()

    def draw(self, gl, faces, revision):
        if revision != self.key:
            self.clear()
            self.key = revision
        ids = {face.GetID() for face in faces}
        self.triangles = {key: value for key, value in self.triangles.items() if key in ids}
        for face in faces:
            ident = face.GetID()
            if ident not in self.triangles:
                mesh = core.TriangleMesh()
                face.ComputeMesh(mesh)
                points = [mesh.GetVertex(mesh.GetVertexIndex(i)) for i in range(mesh.GetNumVertexIndices())]
                self.triangles[ident] = np.ascontiguousarray([(p.x,p.y,p.z) for p in points], dtype=np.float64)
                self.mesh_builds += 1
        gl.glPushClientAttrib(gl.GL_CLIENT_VERTEX_ARRAY_BIT)
        previous = int(gl.glGetIntegerv(gl.GL_ARRAY_BUFFER_BINDING))
        try:
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
            gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
            for state in (gl.GL_NORMAL_ARRAY, gl.GL_TEXTURE_COORD_ARRAY, gl.GL_COLOR_ARRAY):
                gl.glDisableClientState(state)
            for points in self.triangles.values():
                if len(points):
                    gl.glVertexPointer(3, gl.GL_DOUBLE, 0, points)
                    gl.glDrawArrays(gl.GL_TRIANGLES, 0, len(points))
        finally:
            gl.glPopClientAttrib()
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, previous)
