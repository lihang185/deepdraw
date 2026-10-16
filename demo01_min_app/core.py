import sys

try:
    import editor2
except:
    print ("can't load DLL:editor2.pyd\n")
    sys.exit(1)
    
core = editor2

# File IO    
#init_global = editor2.init_global
#LoadFromFile = editor2.LoadFromFile
#SaveToFile = editor2.SaveToFile


#Entity
CVector2D = editor2.CVector2D
CVector3D = editor2.CVector3D
CPlane = editor2.CPlane
CMatrix33 = editor2.CMatrix33
CMatrix = editor2.CMatrix
CBoundingBox = editor2.CBoundingBox
#CBounds2D = editor2.CBounds2D
CStraightLine = editor2.CStraightLine

CEntity = editor2.CEntity
IChangeListener = editor2.IChangeListener
CVertex = editor2.CVertex
CEdge = editor2.CEdge
CCurve = editor2.CCurve
CEdgeUse = editor2.CEdgeUse
CLoop = editor2.CLoop
CFace = editor2.CFace

CCircle3d = editor2.CCircle3d
CArc3d = editor2.CArc3d
CArcCurve = editor2.CArcCurve

TriangleMesh = editor2.TriangleMesh
UVHelper = editor2.UVHelper
CFaceTextureCoords = editor2.CFaceTextureCoords
CGuideLine = editor2.CGuideLine
#CGuidePoint
CDib = editor2.CDib
CTexture = editor2.CTexture
CMaterial = editor2.CMaterial
CComponent = editor2.CComponent
CComponentDefinition = editor2.CComponentDefinition
CComponentInstance = editor2.CComponentInstance
CEntityFactory = editor2.CEntityFactory
CModel = editor2.CModel
CModelData = editor2.CModelData
CGeomFilterVolume = editor2.CGeomFilterVolume
CMergeController = editor2.CMergeController

CSimpleDraw = editor2.CSimpleDraw
RBaseMaterial = editor2.CBaseMaterial
RFaceGroup = editor2.CFaceGroup
RMaterialGroup = editor2.CMaterialGroup
REdgeGroup = editor2.CEdgeGroup
#CDrawListCache = editor2.CDrawListCache
#CVertexArrayCache = editor2.CVertexArrayCache
RVBOCache = editor2.CVBOCache
RFilteredInstance = editor2.CFilteredInstance

IView = editor2.IView
IBaseTool = editor2.IBaseTool
IEntityFilter = editor2.IEntityFilter

CPickHelper = editor2.CPickHelper
CInputPointFinder = editor2.CInputPointFinder
license = editor2.license

init_opengl = editor2.init_opengl

#import ui_manager 
#UIManager = ui_manager.UIManager

#
EPS = 0.001
EPS2 = EPS*EPS

class PressState:
    press_first = 1, 
    press_second = 2

def gEnableUndo():
    m = CEntity.GetUndoManager()
    if m:
        return CEntity.IsUndoEnabled()
    return False

def gUndoManager():
    return CEntity.GetUndoManager()

def EnumTrianglesOfTriMesh(triMesh):
    num = triMesh.GetNumTriangles()
    for i in range(num):
        t = triMesh.GetTriangle(i)
        ti = [t.a, t.b, t.c]
        yield ti

def EnumTriangles(comp):
    count = comp.getNumEntities()
    for i in range(count):
        e = comp.getEntity(i)
        if type(e) is CFace:
            triMesh = e.GetTriangleMesh()
            for triangle in EnumTrianglesOfTriMesh(triMesh):
                ##############
                # each indices in triangle
                vs = [triMesh.GetVertex(idx) for idx in triangle]
                yield vs

class EntityFilter(editor2.IEntityFilter):
    def __init__(self, func):
        super().__init__()
        self.func = func
    
    def Test(self, e):
        if self.func:
            return self.func(e)
        return True

def set_active_model(in_model):
    global model
    model = in_model


model = None

def active_model():
    global model
    return model
    
def set_active_view(in_view):
    global view
    view = in_view

def active_view():
    global view
    return view

class SnapType:
    none = 100
    axis = 1
    vertex = 2
    intersection = 3
    guide_line = 4
    edge_center = 5
    edge = 6
    face = 7
    other_point = 8
    last_point_axis = 9
    ref_point_intersect = 10
    axis_plane = 11
    model_entity = 12




#==================
# utils
#==================
def draw_line( p1, p2, gl):
    gl.glBegin(gl.GL_LINES)
    gl.glVertex3d(p1.x, p1.y, p1.z )
    gl.glVertex3d(p2.x, p2.y, p2.z )
    gl.glEnd()

def draw_target_with_size(p, size, gl):
    if p is None:
        return
    
    S = size
    
    gl.glColor3f(0.0, 0.0, 1.0);
    gl.glBegin(gl.GL_LINES)
    gl.glVertex3d(p.x-S, p.y, p.z )
    gl.glVertex3d(p.x+S, p.y, p.z )
    gl.glEnd()
    
    gl.glBegin(gl.GL_LINES)
    gl.glVertex3d(p.x,  p.y-S,  p.z )
    gl.glVertex3d(p.x,  p.y+S,  p.z )
    gl.glEnd()
    
    gl.glBegin(gl.GL_LINES)
    gl.glVertex3d(p.x,  p.y,  p.z-S  )
    gl.glVertex3d(p.x,  p.y,  p.z+S )
    gl.glEnd()

def draw_target_with_size_color(p, size, gl):
    if p is None:
        return
    
    S = size
    
    gl.glBegin(gl.GL_LINES)
    gl.glVertex3d(p.x-S, p.y, p.z )
    gl.glVertex3d(p.x+S, p.y, p.z )
    gl.glEnd()
    
    gl.glBegin(gl.GL_LINES)
    gl.glVertex3d(p.x,  p.y-S,  p.z )
    gl.glVertex3d(p.x,  p.y+S,  p.z )
    gl.glEnd()
    
    gl.glBegin(gl.GL_LINES)
    gl.glVertex3d(p.x,  p.y,  p.z-S  )
    gl.glVertex3d(p.x,  p.y,  p.z+S )
    gl.glEnd()
    
def edge_to_ray(e):
    p1 = e.GetStartVertex().Pos()
    p2 = e.GetEndVertex().Pos()

    orig = p1
    diff = p2 - p1
    len = diff.Length()
    dir = diff.Normalized()
    
    return orig, dir, len
