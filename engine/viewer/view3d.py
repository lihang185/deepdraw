from engine.mutation_guard import human_callback, check_mutation
from engine.qt import QtCore, QtGui, QtWidgets, QOpenGLWidget
Qt, QPoint, QRect, QTimer = QtCore.Qt, QtCore.QPoint, QtCore.QRect, QtCore.QTimer
QPainter, QMatrix4x4 = QtGui.QPainter, QtGui.QMatrix4x4
QVector3D, QVector4D = QtGui.QVector3D, QtGui.QVector4D
QPen, QColor, QMessageBox = QtGui.QPen, QtGui.QColor, QtWidgets.QMessageBox
from time import perf_counter
import OpenGL.GL
import OpenGL.GLU
#import time
import numpy as np
import math
#import gc

from engine import core
from .render_pipeline import RenderPipeline

def q2c(d):
    return core.CVector3D(d.x(), d.y(), d.z())
from engine.tools.tool_camera import CameraTool

class ModeEnum:
    default = 1
    pick = 2
    render_buffer = 3

def toQtMatrix2(m):
    # Evaluate the native mapping, including scale stored separately from rows.
    origin = m.Transform(core.CVector3D(0, 0, 0))
    axes = [m.Transform(core.CVector3D(*xyz)) - origin
            for xyz in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    out = [value for attr in ('x', 'y', 'z')
           for value in [getattr(axis, attr) for axis in axes] + [getattr(origin, attr)]]
    return QMatrix4x4(out + [0.0, 0.0, 0.0, 1.0])

def matToList(m):
    out = []
    out.extend(( m.get(0, 0), m.get(0, 1), m.get(0, 2) ))
    out.extend(( m.get(1, 0), m.get(1, 1), m.get(1, 2) ))
    out.extend(( m.get(2, 0), m.get(2, 1), m.get(2, 2) ))
    out.extend(( m.get(3, 0), m.get(3, 1), m.get(3, 2) ))
    return out

    

class SuCamera:
    def __init__(self):
        self.position = QVector3D(175, -369, 198)
        self.target   = QVector3D(69, 45, 66)
        self.fov = 45.0
        
        self.forward = (self.target-self.position).normalized()
        up = QVector3D(0, 0, 1.0)
        self.right = QVector3D.crossProduct(self.forward, up).normalized()
        self.up = QVector3D.crossProduct(self.right, self.forward).normalized()

        self.compute()
    
    def compute(self):
        direction = self.target-self.position
        if direction.lengthSquared() < 1e-12:
            direction = QVector3D(0, 1, 0)
        self.forward = direction.normalized()
        right = QVector3D.crossProduct(self.forward, self.up)
        if right.lengthSquared() < 1e-12:
            # Top/bottom views need an up reference not parallel to the view.
            reference = QVector3D(0, 0, 1) if abs(self.forward.z()) < .9 else QVector3D(0, 1, 0)
            right = QVector3D.crossProduct(self.forward, reference)
        self.right = right.normalized()
        self.up = QVector3D.crossProduct(self.right, self.forward).normalized()

    def fit_bounds(self, box, vertical_fov, aspect):
        """Fit all eight corners with perspective, preserving view direction/FOV."""
        self.compute()
        target = QVector3D((box.min_x+box.max_x)/2, (box.min_y+box.max_y)/2,
                           (box.min_z+box.max_z)/2)
        tan_vertical = math.tan(math.radians(vertical_fov/2))
        tan_horizontal = tan_vertical * aspect
        distance = 1.0
        for x in (box.min_x, box.max_x):
            for y in (box.min_y, box.max_y):
                for z in (box.min_z, box.max_z):
                    offset = QVector3D(x,y,z)-target
                    depth = QVector3D.dotProduct(offset,self.forward)
                    horizontal = abs(QVector3D.dotProduct(offset,self.right))
                    vertical = abs(QVector3D.dotProduct(offset,self.up))
                    distance = max(distance, horizontal*1.1/tan_horizontal-depth,
                                   vertical*1.1/tan_vertical-depth, 12.0-depth)
        self.target = target
        self.position = target-self.forward*distance
        self.compute()
    
    def transform(self, m, inverse=False):
        qm = toQtMatrix2(m)
        if inverse:
            qm, invertible = qm.inverted()
            if not invertible:
                raise ValueError('组件变换不可逆，无法进入组件')
        self.position = qm.map(self.position)
        self.target = qm.map(self.target)
        self.up = qm.mapVector(self.up)
        self.compute()
    
    def GetTarget(self):
        p = self.target
        return core.CVector3D(p.x(), p.y(), p.z())
        
#class IViewObserver:
#    def onViewChanged(view):
#        pass

class IViewProxy(core.IView):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.tmp_PickVolume = None
    
    def ComputeCameraRay(self, x, y):
        orig, dir, end = self.view.ComputeCameraRay(x, y)
        return core.CStraightLine(orig, dir)
        
    def ComputeHightAtRayDepth(self, z):
        return self.view.ComputeHightAtRayDepth(z)
    
    def GetViewWidth(self):
        return self.view.width()
        
    def GetViewHeight(self):
        return self.view.height()
        
    def GetCameraForward(self):
        return self.view.GetCameraForward()
        
    def GetCameraUp(self):
        return self.view.GetCameraUp()
        
    def GetActivateComponent(self):
        return self.view.model.GetActiveComponent()
        
    def GetModel(self):
        return self.view.model

############
# GLWidget
# OpenGL 窗口通用程序框架
#   1、创建OpenGL环境
#   2、设置矩阵
#   3、控制窗口视角
#   4、调用 draw 绘图主函数
############
class View3D(QOpenGLWidget):
    def __init__(self, parent):
        super(View3D, self).__init__( parent)
        self.view_proxy = IViewProxy(self)
        self.view_observer = []
        
        self.setFocusPolicy(Qt.StrongFocus);
        
        self.pressButton = 0
        self.lastPos = QPoint()
        
        self.first_click = False
        self.double_click = False
        self.third_click = False
        
        self.mode = ModeEnum.default
        
        self.pc = PerformanceCounter()
        self.draw_pc = True

        self.active_tool = None
        self.camera_tool = CameraTool(self)
        
        self.camera = SuCamera()
        self.camera_zoom = 1.0
        
        self.model = None
        self.pipeline = None
        
        self.pick_window_pos = QPoint()
        self.pick_size = 9
        
        self.last_width = 0
        self.last_height = 0
        
        self.is_offscreen_render = False
        self.shadows_enabled = False
        self.shadow_resolution = 2048
        self.shadow_strength = .4
        self.shadow_direction = (.5, -.7, 1.)
        self.offscreen_width = 0
        self.offscreen_height = 0
        
    def GetCameraZoom(self):
        return self.camera_zoom
        
    ############
    # 截屏
    # 
    ############
    def GrabScreen(self):
        self.draw_pc = False
        self.paintEvent(None)
        self.draw_pc = True
        
        width = self.width()
        height = self.height()
        
        #self.makeCurrent()
        
        gl = self.gl
        data = gl.glReadPixels(0, 0, width, height, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
        return data

    ############
    # Bind Model
    #
    ############
    def BindModel(self, model):
        self.ReleaseModel()
        self.model = model
        self.pipeline = RenderPipeline(model, self)

    def ReleaseModel(self):
        self.active_tool = None
        if self.pipeline is not None:
            self.pipeline.Release()
            self.pipeline = None
        self.model = None

    ############
    # 创建OpenGL环境
    # Qt6 和 Qt5的主要区别在这里
    ############
    def initializeGL(self):
        self.gl = OpenGL.GL
        self.glu = OpenGL.GLU
        
        from .render_backend import init_opengl
        init_opengl()
        from . import render_backend
        self.context().aboutToBeDestroyed.connect(self.release_render_context)

    def release_render_context(self):
        from . import render_backend
        self.makeCurrent()
        try:
            pipelines = {self.pipeline}
            for pipeline in pipelines:
                if pipeline is not None:
                    pipeline.release_gl_resources()
            render_backend.native.release_context()
        finally:
            self.doneCurrent()
        
   
    def setStatusBar(self, msg):
        self.window().statusBar().showMessage(msg)
        
    ############
    # paintEvent
    ############
    def paintEvent(self, event):
        if getattr(self, "loading_model", False):return
        if not self.isVisible():
            return
        self.pc.start(5)
        
        # GL Context
        self.pc.start(0)
        self.makeCurrent()
        self.pc.end(0)
        
        #gc.collect()
        
        # Step 1
        self.pc.start(1)
        self.gl.glClearColor(0.85, 0.85, 0.85, 1.0)
        self.gl.glClear(self.gl.GL_COLOR_BUFFER_BIT | self.gl.GL_DEPTH_BUFFER_BIT )
        self.gl.glEnable(self.gl.GL_DEPTH_TEST)
        self.gl.glDisable(self.gl.GL_STENCIL_TEST)
        
        # Step 2
        self.SetupMatrix()
        
        # Step 3
        self.gl.glDisable(self.gl.GL_TEXTURE_2D)
        self.drawGird(self.gl)
        self.pc.end(1)
        
        # Draw model
        if self.model and not self.model.HasError():
            self.pc.start(2)
            if self.pipeline:
                stats=getattr(self,'render_stats',None)
                if stats is not None:
                    stats.begin()
                    try:self.pipeline.draw()
                    finally:stats.end(self.pipeline)
                else:self.pipeline.draw()
            self.pc.end(2)
            
            # Step 4
            self.pc.start(3)
            if self.active_tool:
                from engine.coordinates import local_drawing
                with local_drawing(self,self.gl):
                    self.active_tool.draw(self.gl)
            self.pc.end(3)
        
        self.pc.start(4)
        self.gl.glFlush()
        # Readback synchronizes captures; interactive frames must not wait for GPU completion.
        self.pc.end(4)
        
        self.draw2d()
    

    ########################
    # Render Off-screen
    #
    ########################
    def paint_off_screen(self):

        # Step 1
        self.gl.glClearColor(*getattr(self, 'offscreen_background', (1, 1, 1, 1)))
        self.gl.glClear(self.gl.GL_COLOR_BUFFER_BIT | self.gl.GL_DEPTH_BUFFER_BIT )
        self.gl.glEnable(self.gl.GL_DEPTH_TEST)
        
        # Step 2
        self.SetupMatrix()
        
        # Step 3
        self.gl.glDisable(self.gl.GL_TEXTURE_2D)
        #self.drawGird(self.gl)

        
        # Draw model
        if self.model and not self.model.HasError():
            self.pc.start(2)
            if self.pipeline:
                self.pipeline.draw()
            self.pc.end(2)
            
            # Step 4
            self.pc.start(3)
            self.pc.end(3)
            
        self.gl.glDisable(self.gl.GL_DEPTH_TEST)
        
        self.pc.start(4)
        self.gl.glFlush()
        # Readback synchronizes captures; interactive frames must not wait for GPU completion.
        self.pc.end(4)
        
    def RenderOffScreen(self, width, height):
        gl = self.gl
        
        self.offscreen_width = width
        self.offscreen_height = height
        self.is_offscreen_render = True
        
        # Frame Buffer
        frame_buffer = gl.glGenFramebuffers(1)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, frame_buffer)
        
        # texture image
        texture = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, width, height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, None)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR);
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR);
        gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, texture, 0)
        #gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        
        # render buffer
        render_buffer = gl.glGenRenderbuffers(1)
        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, render_buffer)
        gl.glRenderbufferStorage(gl.GL_RENDERBUFFER, gl.GL_DEPTH_COMPONENT, width, height)
        gl.glFramebufferRenderbuffer(gl.GL_FRAMEBUFFER, gl.GL_DEPTH_ATTACHMENT, gl.GL_RENDERBUFFER, render_buffer)
        #gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, 0)
        
        status = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)
        if status != gl.GL_FRAMEBUFFER_COMPLETE:
            print("Error: Framebuffer is not complate")
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, frame_buffer)
        
        self.paint_off_screen()
        
        img_data = gl.glReadPixels(0, 0, width, height, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE);
        
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        self.is_offscreen_render = False
        return img_data

    ############
    # Draw 2D
    ############
    def draw2d(self):
        self.pc.start(5)
        
        # draw 2D
        from .dimension_labels import has_labels, prepare_label_depth
        if has_labels(self):
            prepare_label_depth(self)
        else:
            self._label_visibility = {}

        
        w = self.width()
        h = self.height()
        painter = QPainter(self)
        #================
        # 后面部分是绘制2D图形
        # 需要精确到像素点上
        # 一个小Hack可解决OpenGL
        # 绘制二维图像浮点数不
        # 能精确到像素的问题
        #================
        painter.resetTransform()
        painter.translate(0.5, 0.5)
        from .dimension_labels import has_labels, draw_labels
        if has_labels(self):
            draw_labels(self,painter)
        #self.draw2dPickFrame(painter)
        if hasattr(self.active_tool, "draw_2d"):
            self.active_tool.draw_2d(painter)
        
        if False:
            painter.setPen(Qt.black)
            painter.drawLine(0, 0, w-1, 0)
            painter.drawLine(0, h-1, w-1, h-1)
            painter.drawLine(0, 0, 0, h-1)
            painter.drawLine(w-1, 0, w-1, h-1)
        
        
        self.pc.end(5)
        
        if self.draw_pc:
            self.DrawPC(painter)

    ############
    # 显示性能数据
    ############
    def DrawPC(self,  painter):
        # PC
        PC_WIDTH = 120
        PC_HEIGHT = 100
        sx = self.width()-PC_WIDTH -1
        sy = self.height()-PC_HEIGHT- 1
        pc_rect = QRect( sx,  sy, PC_WIDTH, PC_HEIGHT)
        self.pc.rect = pc_rect
        #painter.setClipRect(pc_rect)
        painter.translate(pc_rect.x(),  pc_rect.y())
        painter.setPen(Qt.black)
        self.pc.Draw(painter)
        painter.resetTransform()

    def build_stencil_patten(self, block_size=96):
        
        self.makeCurrent()
        
        #if self.width() == self.last_width and self.height() == self.last_height:
        #    return
        
        self.last_width = self.width()
        self.last_height = self.height()
        
        bs = block_size
        
        width = self.width()
        height = self.height()
        self.gl.glViewport(0, 0, width, height)  
        self.gl.glMatrixMode(self.gl.GL_PROJECTION)
        self.gl.glLoadIdentity()
        self.gl.glOrtho( 0, width, 0, height, 0, 1)
        self.gl.glMatrixMode(self.gl.GL_MODELVIEW)
        self.gl.glLoadIdentity()

        data = np.zeros((bs, bs), dtype=np.uint8 )
        
        for y in range(int(bs/4)):
            py = y*4
            if py >= bs: 
                continue
            for x in range(int(bs/4)):
                if y & 1 == 0:
                    px = x*4
                else:
                    px = x*4+2
                if px >= bs: 
                    continue
                data[py][px] = 1
        
        self.gl.glRasterPos2i(0, 0)
        self.gl.glDrawPixels(bs, bs, self.gl.GL_STENCIL_INDEX, self.gl.GL_BYTE, data)
        
        for y in range(int(height/bs)+1):
            for x in range(int(width/bs)+1):
                self.gl.glRasterPos2i(x*bs, y*bs)
                self.gl.glCopyPixels(0, 0, bs, bs, self.gl.GL_STENCIL)
        
    ############
    # 设置矩阵
    # 透视矩阵和Camera矩阵
    ############
    def SetupMatrix(self):
        w = self.width()
        h = self.height()

        # Viewport
        if self.is_offscreen_render:
            w = self.offscreen_width    
            h = self.offscreen_height    
        self.gl.glViewport(0, 0, w, h)  
        
        # Projection
        self.gl.glMatrixMode(self.gl.GL_PROJECTION)
        pm = self.ComputeProjectMatrix()
        self.gl.glLoadMatrixf(pm.data())
        
        # Camera
        self.SetupCameraMatrix()
    
    def SetupCameraMatrix(self):
        self.gl.glMatrixMode(self.gl.GL_MODELVIEW)
        m, invm = self.ComputeCameraMatrix()
        self.camera_matrix_inv = invm
        self.gl.glLoadMatrixf(m.data())

    def ComputeCameraMatrix(self):
        camera = self.camera
        camera.compute()
        
        forward = camera.forward
        
        self.camera_zoom = (camera.target-camera.position).length()

        right = camera.right
        
        qm = QMatrix4x4()
        z_axis = -forward
        qm.setColumn(0,  right.toVector4D())
        qm.setColumn(1,  camera.up.toVector4D())
        qm.setColumn(2,  z_axis.toVector4D())
        
        pos = camera.position
        qm.setColumn(3,  QVector4D(pos.x(), pos.y(), pos.z(),  1.0))

        (inv, ok) = qm.inverted()
        return inv, qm
    
    def ComputeFOV(self):
        w = self.width()
        h = self.height()
        if self.is_offscreen_render:
            w = self.offscreen_width
            h = self.offscreen_height
        fov = self.camera.fov
        aspectRatio = max(1,w)/max(1,h)
        tangent = math.tan(math.radians(fov/2))
        if w >= h:
            fov_h = fov
            fov_w = math.degrees(2*math.atan(tangent*aspectRatio))
        else:
            fov_w = fov
            fov_h = math.degrees(2*math.atan(tangent/aspectRatio))
        return fov_w, fov_h, aspectRatio
    
    def ComputeProjectMatrix(self):
        fov_w, fov_h, aspectRatio = self.ComputeFOV()
        pm = QMatrix4x4()
        # Fit can place the eye far beyond the old fixed 20000 cm clip plane.
        # Scale both planes for distant views to retain useful depth precision.
        distance = (self.camera.GetTarget()-q2c(self.camera.position)).Length()
        far = max(20000., distance*4.)
        near = max(10., far/20000.)
        pm.perspective(fov_h, aspectRatio, near, far)
        return pm
    
    def ComputeHightAtRayDepth(self, at_ray_depth):
        fov_w, fov_h, aspectRatio = self.ComputeFOV()
        rad = math.radians(fov_h)
        height = math.tan(rad/2)*at_ray_depth*2
        return height
    
    def GetCameraForward(self):
        return q2c(self.camera.forward)
    
    def GetCameraUp(self):
        return q2c(self.camera.up)
    
    def MarkDirty(self):
        self.pipeline.mark_dirty()
        self.MarkViewDirty()

    def MarkViewDirty(self):
        """Selection/navigation changes do not invalidate component geometry."""
        self.pipeline.mark_outer_path_dirty()
        
    #=======================
    # For D5 Render
    #
    #=======================
    def GetCameraInfo(self):
        pos = q2c(self.camera.position)
        forward = q2c(self.camera.forward)
        up = q2c(self.camera.up)
        return pos, forward, up
    
    def AddObserver(self, i_observer):
        self.view_observer.append(i_observer)
    
    def RemoveObserver(self, i_observer):
        self.view_observer.remove(i_observer)
    
    def onViewChanged(self):
        if self.view_observer:
            for x in self.view_observer:
                x.onViewChanged(self)
        
    def ComputePickRay(self, x, y):
        ray_start, ray_dir, ray_end = self.ComputeCameraRay(x, y)
        return core.CStraightLine(ray_start, ray_dir)

    def ComputeCameraRay(self, x, y):
        # Use the same FOV and current camera as rendering, including portrait views.
        _, fov_h, aspect = self.ComputeFOV()
        scale = math.tan(math.radians(fov_h * .5))
        px = (2*((float(x)+.5)/self.width())-1)*scale*aspect
        py = (1-2*((float(y)+.5)/self.height()))*scale
        inverse = self.ComputeCameraMatrix()[1]
        origin = inverse.map(QVector3D())
        endpoint = inverse.map(QVector3D(px,py,-1))
        direction = (endpoint-origin).normalized()
        start, direction = q2c(origin), q2c(direction)
        return start, direction, start+direction*1000

    def ComputeCameraRay2(self, x, y):   
        orig, dir, end = self.ComputeCameraRay(x, y)
        return core.CStraightLine(orig, dir)
    
    def CheckValidityMessage(self):
        model = self.model
        msg = model.GetLastError()
        if not msg:
            return
        if msg.error > 0:
            msg_string = msg.GetErrorMessage()
            print(msg_string)
        if msg.error >= 2:
            QMessageBox.information(None, "Error", msg_string)

    ############
    # 视角控制
    # 1、左键旋转
    # 2、中间缩放
    # 3、平移 **TODO**
    ############
    @human_callback
    def mousePressEvent(self,event):
        if event.button() != Qt.MiddleButton and not self.camera_tool_active() and not self.allow_tool_input():
            event.accept()
            return
        #self.grabMouse()
        
        self.pressButton = event.button()
        
        mod = event.modifiers()
        
        if self.pressButton == Qt.LeftButton:
            if self.model and not self.model.HasError():
                if self.active_tool:
                    self.active_tool.on_left_button_down(event.pos(), mod)
                    
                    #====================
                    # Error Check
                    #====================
                    self.CheckValidityMessage()

        elif self.pressButton == Qt.MiddleButton:
            self.camera_tool.on_left_button_down(event.pos(), mod)
            
        elif self.pressButton == Qt.RightButton:
            pass
            
        #self.releaseMouse()
            
        self.repaint()

    
    @human_callback
    def contextMenuEvent(self, event):
        if not self.allow_tool_input() or self.model is None:
            event.accept()
            return
        from app.ui.view_context_menu import ViewContextMenu
        entities = [entity for entity in self.model.GetSelection() if not entity.IsMarkedDeleted()]
        menu = ViewContextMenu(self, entities)
        try:
            menu.exec_(event.globalPos())
        finally:
            menu.deleteLater()
        event.accept()

    @human_callback
    def mouseDoubleClickEvent(self, event):
        if not self.allow_tool_input():
            event.accept()
            return
        if (event.button() == Qt.LeftButton and self.model
                and not self.model.HasError()
                and hasattr(self.active_tool, 'on_left_button_double_click')):
            self.pressButton = Qt.NoButton
            try:
                self.active_tool.on_left_button_double_click(event.pos(), event.modifiers())
            except Exception as error:
                self.setStatusBar(str(error))
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    @human_callback
    def mouseReleaseEvent(self, event):
        pressed = self.pressButton
        self.pressButton = Qt.NoButton

        if event.button() != Qt.MiddleButton and ((not self.camera_tool_active() and not self.allow_tool_input()) or pressed != event.button()):
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            if self.model and not self.model.HasError():
                if self.active_tool:
                    self.active_tool.on_left_button_up(event.pos())
                
                    #====================
                    # Error Check
                    #====================
                    self.CheckValidityMessage()

        elif event.button() == Qt.MiddleButton:
            self.camera_tool.on_left_button_up(event.pos())
            
        elif event.button() == Qt.RightButton:
            pass
        
        #self.releaseMouse()

        self.repaint()
        
    @human_callback
    def mouseMoveEvent(self, event):
        if self.pressButton != Qt.MiddleButton and not self.camera_tool_active() and not self.allow_tool_input(notify=False):
            event.accept()
            return
        mod = event.modifiers()
        
        if self.pressButton == Qt.LeftButton:
            if self.model and not self.model.HasError():
                if self.active_tool:
                    self.active_tool.on_mouse_move(event.pos(), mod)
            
        elif self.pressButton == Qt.MiddleButton:
            self.camera_tool.on_mouse_move(event.pos(), mod)
            
        elif self.active_tool and getattr(self.active_tool, 'wants_hover', False):
            if self.model and not self.model.HasError():
                self.active_tool.on_mouse_move(event.pos(), mod)
        else:
            pass
        
        # Refresh Screen
        self.repaint()

    @human_callback
    def wheelEvent(self, event):
        point = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        delta = event.angleDelta().y()
        
        tool = self.active_tool if self.camera_tool_active() else self.camera_tool
        tool.doZoom(point, delta, event.modifiers())
        
        # Refresh Screen
        self.repaint()
        
    def ctrlKeyPress(self):
        if not self.allow_tool_input():
            return
        if self.active_tool and hasattr(self.active_tool, 'on_ctrl_press'):
            self.active_tool.on_ctrl_press()
    
    def shiftKeyPress(self):
        print("Shift key press")
    
    @human_callback
    def keyPressEvent(self, event):
        if not self.allow_tool_input():
            event.accept()
            return
        key = event.key()
        if key in (Qt.Key_Left,Qt.Key_Right,Qt.Key_Up) and hasattr(self.active_tool,'on_axis_key'):
            if not event.isAutoRepeat():self.active_tool.on_axis_key(key)
            event.accept()
            return
        if key == Qt.Key_Control and not event.isAutoRepeat():
            self.ctrlKeyPress()
            event.accept()
            return
        if key in (Qt.Key_Return, Qt.Key_Enter) and hasattr(self.active_tool, 'enterValue'):
            from engine.qt import QtWidgets
            from engine.units import parse_length
            tool = self.active_tool
            revision = self.mainWindow.editing.revision
            prompt = getattr(tool, 'input_prompt', '距离（可带 cm、mm、m）')
            if type(tool).__name__ == 'RotateTool': prompt = '角度（度）'
            value, accepted = QtWidgets.QInputDialog.getText(self, '精确输入', prompt)
            if accepted and self.active_tool is tool and revision == self.mainWindow.editing.revision:
                try:
                    check_mutation()
                    if hasattr(tool, 'input_prompt'): tool.enterValue(value)
                    else:
                        import math
                        number = float(value) if type(tool).__name__ == 'RotateTool' else parse_length(value, getattr(self,'display_unit','cm'))
                        if not math.isfinite(number): raise ValueError('请输入有限数值')
                        tool.enterValue(number)
                except (ValueError, RuntimeError) as error: self.setStatusBar(str(error))
                self.update()
            event.accept()
            return
        if event.modifiers() & Qt.ControlModifier and key in (Qt.Key_Z,Qt.Key_Y):
            if not getattr(self.mainWindow, 'history_enabled', True):
                event.accept()
                return
            session=getattr(self.mainWindow,'editing',None)
            if session is not None:
                try:
                    redo=key==Qt.Key_Y or bool(event.modifiers() & Qt.ShiftModifier)
                    result=session.edit.redo() if redo else session.edit.undo()
                    self.setStatusBar(('重做' if redo else '撤销')+'：'+result['validation']['status'])
                except Exception as error:
                    self.setStatusBar(str(error))
                event.accept()
                return
        if key == Qt.Key_Escape:
            if self.active_tool and hasattr(self.active_tool, "on_cancel"):
                self.active_tool.on_cancel()
            from engine.tools.tool_select import SelectTool
            if not isinstance(self.active_tool, SelectTool):
                self.SetActiveTool(SelectTool(self))
            event.accept()
    
    ############
    # Draw Grid
    # 绘制坐标轴
    ############
    def drawGird(self, gl):

        inf = 100000
        
        stipple = 0x1111
        gl.glLineStipple(1, stipple)
        
        # x
        gl.glColor3f(1.0, 0.0, 0.0);
        gl.glDisable(gl.GL_LINE_STIPPLE)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(0, 0, 0)
        gl.glVertex3d(inf, 0, 0)
        gl.glEnd()

        gl.glEnable(gl.GL_LINE_STIPPLE) 
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(0, 0, 0)
        gl.glVertex3d(-inf, 0, 0)
        gl.glEnd()
        
        # y
        gl.glColor3f(0.0, 1.0, 0.0);
        gl.glDisable(gl.GL_LINE_STIPPLE)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(0, 0, 0)
        gl.glVertex3d(0, inf, 0)
        gl.glEnd()

        gl.glEnable(gl.GL_LINE_STIPPLE) 
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(0, 0, 0)
        gl.glVertex3d(0, -inf, 0)
        gl.glEnd()
        
        # z
        gl.glColor3f(0.0, 0.0, 1.0);
        gl.glDisable(gl.GL_LINE_STIPPLE)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(0, 0, 0)
        gl.glVertex3d(0, 0, inf)
        gl.glEnd()

        gl.glEnable(gl.GL_LINE_STIPPLE) 
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(0, 0, 0)
        gl.glVertex3d(0, 0, -inf)
        gl.glEnd()
        
        gl.glDisable(gl.GL_LINE_STIPPLE)

    ############
    # Tools
    # 1、selection tool
    # 2、raytrace tool
    # 3、move tools
    ############
    def camera_tool_active(self):
        from engine.tools.tool_camera import CameraTool
        return isinstance(self.active_tool, CameraTool)

    def allow_tool_input(self, notify=True):
        """All tool input, including selection and context navigation, is exclusive."""
        try:
            check_mutation()
            if getattr(self.mainWindow, 'input_busy', False):
                raise RuntimeError('Animation is using the model')
            return True
        except RuntimeError:
            if notify:
                self.setStatusBar('动画播放中，请稍候；可以旋转、平移和缩放视角')
            return False

    def SetActiveTool(self, tool):
        check_mutation()
        if self.active_tool:
            self.active_tool.deactivate()
        
        self.active_tool = tool
        
        if self.active_tool is not None:
            self.active_tool.activate()
        
        self.repaint()

    def OpenComponent(self, instance):
        check_mutation()
        from engine.tools.tool_select import SelectTool
        self.mainWindow.activate_tool(SelectTool)
        if instance.GetParentComponent() != self.model.GetActiveComponent():
            raise ValueError('只能进入当前编辑层的组件')
        self.model.OpenComponent(instance)
        self.model.ClearSelection()
        self.MarkViewDirty()
        self.update()

    def CloseComponent(self):
        check_mutation()
        from engine.tools.tool_select import SelectTool
        self.mainWindow.activate_tool(SelectTool)
        if self.model.GetActivePathLength() == 0:
            return
        transform = self.model.GetActiveComponentInstance().GetTransform()
        self.mainWindow.editing.edit.flush_deferred_bounds()
        self.model.CloseComponent()
        self.model.ClearSelection()
        self.MarkViewDirty()
        self.update()






class PerformanceCounter:
    MAX_PC = 6
    STICK_WIDTH = 10
    STICK_SCALE = 4.0
    
    def __init__(self):
        self.counter = [0, 0, 0, 0, 0, 0]
        pass
        
    def start(self,  i):
        self.counter[i] = perf_counter()
    def end(self, i):
        self.counter[i] = (perf_counter() - self.counter[i]) * 1000
        
    def GetColor(index):
        if index == 0:
            return Qt.GlobalColor.red
        elif index==1:
            return Qt.GlobalColor.darkGreen
        elif index==2:
            return Qt.GlobalColor.darkBlue
        elif index==3:
            return QColor(0, 128, 128)
        elif index==4:
            return Qt.GlobalColor.darkMagenta
        else:
            return Qt.GlobalColor.gray
            
        
    def Draw(self,  painter):
        self.WIDTH = self.rect.width()
        self.HEIGHT = self.rect.height()
        
        for i in range(self.MAX_PC):
            x = (i * 2 + 1) * self.STICK_WIDTH
            
            v = self.counter[i]
            py = int(v * self.STICK_SCALE)
            
            #if py > self.HEIGHT:
            #    py = self.HEIGHT;
            
            color = PerformanceCounter.GetColor(i)
            #painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            
            painter.drawRect(x, self.HEIGHT-py,  self.STICK_WIDTH,  py)
        
        self.DrawFrame(painter)
        self.DrawText(painter)
        

    def DrawFrame(self, painter):
        #######################
        # 绘制边框
        #######################    
        pen = QPen(Qt.GlobalColor.black)
        painter.setPen(pen)
        painter.drawLine(0, 0,    5,  0)
        painter.drawLine(0, 0,    0,  self.HEIGHT-1)
        
        for y in range(0, self.HEIGHT,  20):
            if y == 0: continue
            py = self.HEIGHT-y
            painter.drawLine(0, py, -3, py)
        
    def DrawText(self, painter):
        font=painter.font()
        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(Qt.GlobalColor.black))
        painter.drawText(-70,self.HEIGHT-1,"time:%2.0f ms"%(self.counter[5]))

        for y in range(0, self.HEIGHT,  20):
            if y == 0: continue
            py = self.HEIGHT-y
            value = int(y/self.STICK_SCALE)
            text = str(value)
            painter.drawText(-18, py+4,text)
