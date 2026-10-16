from PySide2.QtCore import Qt, QPoint, QRect, QTimer
from PySide2.QtGui import QPainter, QMatrix4x4, QVector3D, QVector4D, QOpenGLVersionProfile, QOpenGLFunctions, QPen, QColor
#from PySide2.QtGui import QOpenGLFramebufferObjectFormat, QOpenGLFramebufferObject
from PySide2.QtWidgets import QOpenGLWidget, QMessageBox
from time import perf_counter
import OpenGL.GL
import OpenGL.GLU
#import time
import numpy as np
import math
import gc

import core
from render_pipeline import RenderPipeline

def q2c(d):
    return core.CVector3D(*d.toTuple())
from tool_camera import CameraTool

class ModeEnum:
    default = 1
    pick = 2
    render_buffer = 3

def testMatrixMultiply():
    m1 = QMatrix4x4()
    m1.translate(50, 0, 0)
    m2 = QMatrix4x4()
    m2.rotate(45, 1.0,  0.0, 0.0)
    m12 = m1 * m2
    m21 = m2 * m1
    
    r = [m12, m21]
    return r
    

def toQtMatrix2(m):
    out = []
    out.extend(( m.get(0, 0), m.get(0, 1), m.get(0, 2), m.get(3, 0)))
    out.extend(( m.get(1, 0), m.get(1, 1), m.get(1, 2), m.get(3, 1)))
    out.extend(( m.get(2, 0), m.get(2, 1), m.get(2, 2), m.get(3, 2)))
    out.extend((0.0, 0.0, 0.0, 1.0))
    return QMatrix4x4(out)

def matToList(m):
    out = []
    out.extend(( m.get(0, 0), m.get(0, 1), m.get(0, 2) ))
    out.extend(( m.get(1, 0), m.get(1, 1), m.get(1, 2) ))
    out.extend(( m.get(2, 0), m.get(2, 1), m.get(2, 2) ))
    out.extend(( m.get(3, 0), m.get(3, 1), m.get(3, 2) ))
    return out

    
#testMatrixMultiply()

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
        self.forward = (self.target-self.position).normalized()
        self.right = QVector3D.crossProduct(self.forward, self.up).normalized()
    
    def transform(self, m):
        qm = toQtMatrix2(m)
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
        
    def GetModel(self):
        return self.view.model

    def GetActivateComponent(self):
        return self.view.model.GetActiveComponent()

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
        self.model = model
        self.pipeline = RenderPipeline(model, self)

    ############
    # Release Model
    #
    ############
    def ReleaseModel(self):
        self.model = None
        del self.pipeline
        self.pipeline = None
        gc.collect()

    ############
    # 创建OpenGL环境
    # Qt6 和 Qt5的主要区别在这里
    ############
    def initializeGL(self):
        gl = QOpenGLFunctions()
        gl.initializeOpenGLFunctions()
        self.qtgl = gl
        
        self.gl = OpenGL.GL
        self.glu = OpenGL.GLU
        
        core.init_opengl()
        
        if False:
            version_profile = QOpenGLVersionProfile()
            version_profile.setVersion(2, 0)
            self.gl = self.context().versionFunctions(version_profile)
            self.gl.initializeOpenGLFunctions()
   
    def setStatusBar(self, msg):
        statusbar = self.mainWindow.statusBar
        statusbar.showMessage(msg)
    
    def enableMeasureInput(self):
        mainWindow = self.mainWindow
        mainWindow.enable_input = True
        
    def disableMeasureInput(self):
        mainWindow = self.mainWindow
        mainWindow.enable_input = False
        mainWindow.clearKeyInput()
        
    ############
    # paintEvent
    ############
    def paintEvent(self, event):
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
                self.pipeline.draw()
            self.pc.end(2)
            
            # Step 4
            self.pc.start(3)
            if self.active_tool:
                self.active_tool.draw(self.gl)
            self.pc.end(3)
        
        self.pc.start(4)
        self.gl.glFlush()
        self.gl.glFinish()
        self.pc.end(4)
        
        # draw 2D
        self.draw2d()
    

    ########################
    # Render Off-screen
    #
    ########################
    def paint_off_screen(self):

        # Step 1
        self.gl.glClearColor(1, 1, 1, 1)
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
        self.gl.glFinish()
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
        
        forward = (camera.target-camera.position).normalized()
        
        self.camera_zoom = (camera.target-camera.position).length()

        right = QVector3D.crossProduct(forward, camera.up)
        
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
        aspectRatio = w/h
        if w >= h:
            fov_h = fov
            fov_w = fov * aspectRatio
        else:
            fov_w = fov
            fov_h = fov / aspectRatio
        return fov_w, fov_h, aspectRatio
    
    def ComputeProjectMatrix(self):
        fov_w, fov_h, aspectRatio = self.ComputeFOV()
        pm = QMatrix4x4()
        pm.perspective(fov_h,  aspectRatio,  5,  80000)
        return pm
    
    def ComputeHightAtRayDepth(self, at_ray_depth):
        fov_w, fov_h, aspectRatio = self.ComputeFOV()
        rad = math.radians(fov_h)
        height = math.tan(rad)*at_ray_depth*2
        return height
    
    def GetCameraForward(self):
        return q2c(self.camera.forward)
    
    def GetCameraUp(self):
        return q2c(self.camera.up)
    
    def MarkDirty(self):
        self.pipeline.mark_dirty()
        
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
        view_width = self.width()
        view_height = self.height()
        imageAspectRatio = view_width / view_height
        fov = self.camera.fov
        scale = math.tan(math.radians(fov * 0.5));
        px = (2*((float(x)+0.5)/view_width)-1) * scale * imageAspectRatio
        py = (1.0-2*(float(y)+0.5)/view_height) * scale
        
        ray_origin = QVector3D(0, 0, 0)
        ray_dir = QVector3D(px, py, -1).normalized()
        
        inv_matrix = self.camera_matrix_inv
        world_ray_origin = inv_matrix.map(ray_origin)
        world_ray_dir = inv_matrix.map(ray_dir)
        
        a = (world_ray_dir - world_ray_origin).normalized()
        ray_dir = q2c(a)
        ray_start = q2c(world_ray_origin)
        ray_end = ray_start + ray_dir* 1000
        return ray_start, ray_dir, ray_end

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
    def mousePressEvent(self,event):
        #self.grabMouse()
        
        self.pressButton = event.button()
        
        mod = event.modifiers()
        
        if self.pressButton == 1:
            if self.model and not self.model.HasError():
                if self.active_tool:
                    self.active_tool.on_left_button_down(event.pos(), mod)
                    
                    #====================
                    # Error Check
                    #====================
                    self.CheckValidityMessage()

        elif self.pressButton == 4:
            self.camera_tool.on_left_button_down(event.pos(), mod)
            
        elif self.pressButton == 2:
            pass
            
        #self.releaseMouse()
            
        self.repaint()

    
    def mouseReleaseEvent(self, event):
        self.pressButton = 1

        if event.button() == 1:
            if self.model and not self.model.HasError():
                if self.active_tool:
                    self.active_tool.on_left_button_up(event.pos())
                
                    #====================
                    # Error Check
                    #====================
                    self.CheckValidityMessage()

        elif event.button() == 4:
            self.camera_tool.on_left_button_up(event.pos())
            
        elif event.button() == 2:
            pass
        
        #self.releaseMouse()

        self.repaint()
        
    def mouseMoveEvent(self, event):
        mod = event.modifiers()
        
        if self.pressButton == 1:
            if self.model and not self.model.HasError():
                if self.active_tool:
                    self.active_tool.on_mouse_move(event.pos(), mod)
            
        elif self.pressButton == 4:
            self.camera_tool.on_mouse_move(event.pos(), mod)
            
        else:
            pass
        
        # Refresh Screen
        self.repaint()

    def wheelEvent(self, event):
        point = event.position().toPoint()
        delta = event.angleDelta().y()
        
        self.camera_tool.doZoom(point,  delta)
        
        # Refresh Screen
        self.repaint()
        
    def ctrlKeyPress(self):
        self.active_tool.on_ctrl_press()
    
    def shiftKeyPress(self):
        print("Shift key press")
    
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            print("press ESC")
            if self.active_tool and hasattr(self.active_tool, "on_cancel"):
                self.active_tool.on_cancel()
    
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
    def SetActiveTool(self, tool):
        if self.active_tool:
            self.active_tool.deactivate()
        
        self.active_tool = tool
        
        self.active_tool.activate()
        
        self.repaint()





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
