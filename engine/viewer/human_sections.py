"""Cached render-only cut boundaries for the human camera."""
from engine.coordinates import transform_plane
import numpy as np
from engine import core
from .section_geometry import section_lines
from .render_pipeline import visible_entity


def affine(matrix):
    from .render_backend import affine12
    values = affine12(matrix)
    result = np.eye(4)
    result[:3,:3] = np.asarray(values[:9]).reshape(3,3)
    result[:3,3] = values[9:]
    return result


def boundaries(pipeline, sections):
    model = pipeline.model
    path = model.GetActiveComponentPath()
    frame = path.ComputeMatrix()
    planes = [transform_plane(frame,e.plane) for e in sections]
    equations = [tuple(getattr(p,k) for k in ('x','y','z','w')) for p in planes]
    key = (getattr(pipeline,'section_geometry_revision',0),
           model.GetActiveComponent().GetID(), tuple(affine(frame).flat), tuple(equations))
    cached = getattr(pipeline,'section_boundary_cache',None)
    if cached is not None and cached[0] == key:
        return cached[1]
    chunks = [[] for _ in equations]
    for node in pipeline.RecursiveRnumInstance(None,model.GetTopComponent(),core.CMatrix(),None):
        if node.comp.GetNumFaces() == 0:
            continue
        transform = affine(node.matrix)
        vertices = []
        for face in node.comp.EnumEntities():
            if not isinstance(face,core.CFace) or not visible_entity(face):
                continue
            mesh = core.TriangleMesh()
            face.ComputeMesh(mesh)
            for i in range(mesh.GetNumVertexIndices()):
                p = mesh.GetVertex(mesh.GetVertexIndex(i))
                vertices.append((p.x,p.y,p.z))
        if not vertices:
            continue
        for index,equation in enumerate(equations):
            local = section_lines(vertices, transform.T @ np.asarray(equation))
            if len(local):
                chunks[index].append(local @ transform[:3,:3].T + transform[:3,3])
    result = [np.ascontiguousarray(np.concatenate(parts) if parts else np.empty((0,3)),dtype=np.float64)
              for parts in chunks]
    pipeline.section_boundary_cache = (key,result)
    return result


def draw_boundaries(pipeline, sections):
    if not sections:
        return
    arrays = boundaries(pipeline,sections)
    gl = pipeline.view.gl
    gl.glPushAttrib(gl.GL_ENABLE_BIT | gl.GL_CURRENT_BIT | gl.GL_LINE_BIT | gl.GL_DEPTH_BUFFER_BIT)
    gl.glPushClientAttrib(gl.GL_CLIENT_VERTEX_ARRAY_BIT)
    previous_buffer = int(gl.glGetIntegerv(gl.GL_ARRAY_BUFFER_BINDING))
    try:
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER,0)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LEQUAL)
        gl.glDepthMask(False)
        gl.glColor3f(.95,.35,.03)
        gl.glLineWidth(2.)
        for state in (gl.GL_NORMAL_ARRAY,gl.GL_COLOR_ARRAY,gl.GL_TEXTURE_COORD_ARRAY):
            gl.glDisableClientState(state)
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        for index,points in enumerate(arrays):
            # Avoid numerical self-clipping; all OTHER planes still clip this line.
            gl.glDisable(gl.GL_CLIP_PLANE0+index)
            if len(points):
                gl.glVertexPointer(3,gl.GL_DOUBLE,0,points)
                gl.glDrawArrays(gl.GL_LINES,0,len(points))
            gl.glEnable(gl.GL_CLIP_PLANE0+index)
    finally:
        gl.glPopClientAttrib()
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER,previous_buffer)
        gl.glPopAttrib()
