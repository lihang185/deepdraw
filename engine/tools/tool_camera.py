from engine.viewer.overlays import draw_inference
import math
from engine.qt import QtGui, QtCore
QVector3D = QtGui.QVector3D
Qt = QtCore.Qt

from engine import core


class CameraCtrlMode:
    normal = 1, 
    orbit = 2, 
    pan = 3, 

class CameraTool(core.IBaseTool):
    @property
    def is_begin(self):
        return False

    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view3d = view
        self.mode = CameraCtrlMode.normal
    
    def draw(self, gl):
        pass
    
    def drawTarget(self, gl):
        p = self.view3d.camera.target
        
        gl.glColor3f(1.0, 0.0, 0.0);
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(p.x()-1,  p.y(),  p.z()  )
        gl.glVertex3d(p.x()+1,  p.y(),  p.z() )
        gl.glEnd()
        
        gl.glColor3f(0.0, 1.0, 0.0);
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(p.x(),  p.y()-1,  p.z()  )
        gl.glVertex3d(p.x(),  p.y()+1,  p.z() )
        gl.glEnd()
        
        gl.glColor3f(0.0, 0.0, 1.0);
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(p.x(),  p.y(),  p.z()  )
        gl.glVertex3d(p.x(),  p.y(),  p.z() +4 )
        gl.glEnd()
        pass
    
    def on_left_button_down(self, pos, mod):
        camera = self.view3d.camera
        self.last_pos = pos
        self.ds_longitude, self.ds_latitude = self.computeOrbit()
        self.ds_distance = (camera.target-camera.position).length()
        self.ds_target = camera.target
    
    def on_left_button_up(self, pos):
        pass
 
    def on_mouse_move(self, pos, modifiers):
        camera = self.view3d.camera
        
        diff = pos - self.last_pos
        
        if self.mode == CameraCtrlMode.normal:
            if modifiers & Qt.ShiftModifier:
                do_mode = CameraCtrlMode.pan
            else:
                do_mode = CameraCtrlMode.orbit
        else:
            do_mode = self.mode
        
        if do_mode == CameraCtrlMode.pan:
            distance = (camera.target-camera.position).length()
            forward = camera.forward
            right = camera.right
            #forward = (camera.target-camera.position).normalized()
            #right = QVector3D.crossProduct(forward, camera.up)
            factor = distance / 1000
            camera.target += -right * diff.x()*factor + camera.up * diff.y()*factor
            camera.position = camera.target - forward*self.ds_distance
            
            self.view3d.onViewChanged()
            
        elif do_mode == CameraCtrlMode.orbit:
            self.ds_longitude += - diff.x()*0.1
            
            # rotY
            self.ds_latitude += - diff.y()*0.1
            if self.ds_latitude > 90:
                self.ds_latitude = 90
            if self.ds_latitude < -90:
                self.ds_latitude = -90;
            self.updatePosition(self.ds_longitude, self.ds_latitude )
            
            self.view3d.onViewChanged()
        
        self.last_pos = pos

    
    def doZoom(self, pos, delta, modifiers=Qt.NoModifier):
        camera = self.view3d.camera
        if delta == 0:
            return
        # 第一步： 把鼠标位置 转换为 index
        #X = self.layout.UnProjectX(sx)
        
        forward = (camera.target-camera.position).normalized()
        distance = (camera.target-camera.position).length()

        factor = 0.03 if modifiers & Qt.ControlModifier else 0.2

        # 第二步： 缩放
        if delta < 0 :
            distance += distance * factor
        else:
            distance -= distance * factor
            
        camera.position = camera.target - forward*distance
        
        # 第三步 鼠标位置 - 屏幕坐标 = 开始位置
        #diff = self.layout.ProjectX(X) - sx
        #self.layout.tx += diff
        
        self.view3d.onViewChanged()
        
    def computeOrbit(self):
        camera = self.view3d.camera
        forward = (camera.target-camera.position).normalized()
        latitude = math.degrees(math.asin(forward.z()))
        if latitude > 90:
            latitude = latitude-180
        longitude = math.degrees(math.atan2(forward.y(),forward.x()))
        #distance = (self.target-self.position).length()
        return(longitude,  latitude)

    def updatePosition(self,  d_longitude, d_latitude ):
        camera = self.view3d.camera
        longitude = math.radians(d_longitude)
        latitude = math.radians(d_latitude)
        z = math.sin(latitude)
        theta = math.cos(latitude)
        x = math.cos(longitude) * theta
        y = math.sin(longitude) * theta

        forward = QVector3D(x, y, z).normalized()
        rot_longitude = math.radians(d_longitude-90)
        right = QVector3D(math.cos(rot_longitude), math.sin(rot_longitude), 0)
        camera.up = QVector3D.crossProduct(right, forward)
        camera.position = camera.target - forward*self.ds_distance
        camera.compute()


class PanTool(CameraTool):
    def __init__(self, view):
        super().__init__(view)
        self.view3d = view
        self.mode = CameraCtrlMode.pan

class OrbitTool(CameraTool):
    def __init__(self, view):
        super().__init__(view)
        self.view3d = view
        self.mode = CameraCtrlMode.orbit


class LookTool(CameraTool):
    """Turn the human camera about its eye, preserving position and target distance."""
    def doZoom(self, pos, delta, modifiers=Qt.NoModifier):
        if not modifiers & Qt.ControlModifier:
            return super().doZoom(pos,delta,modifiers)
        if delta == 0:return
        camera = self.view3d.camera
        # ComputeFOV expands the vertical angle in portrait viewports.
        aspect = self.view3d.width()/max(1,self.view3d.height())
        maximum = min(100.,150.*min(aspect,1.))
        minimum = min(10.,maximum)
        camera.fov = max(minimum,min(maximum,camera.fov-delta/120.*2.))
        self.view3d.onViewChanged()

        self.view3d.setStatusBar('视场角 FOV：%.1f°'%camera.fov)

    def activate(self):
        self.dragging = False
        self.view3d.setStatusBar('观察：按住左键拖动改变朝向，摄像机位置保持不变')

    def deactivate(self):
        self.dragging = False

    def on_left_button_down(self, pos, mod):
        camera = self.view3d.camera
        self.eye = QVector3D(camera.position)
        self.ds_distance = max((camera.target-camera.position).length(), .001)
        self.ds_longitude,self.ds_latitude = self.computeOrbit()
        self.last_pos = pos
        self.dragging = True

    def on_left_button_up(self, pos):
        self.dragging = False

    def on_cancel(self):
        self.dragging = False

    def on_mouse_move(self, pos, modifiers):
        if not getattr(self, 'dragging', False):return
        diff = pos-self.last_pos
        self.last_pos = pos
        self.ds_longitude -= diff.x()*.1
        self.ds_latitude = max(-89.9,min(89.9,self.ds_latitude-diff.y()*.1))
        longitude,latitude = math.radians(self.ds_longitude),math.radians(self.ds_latitude)
        forward = QVector3D(math.cos(longitude)*math.cos(latitude),
                            math.sin(longitude)*math.cos(latitude),math.sin(latitude))
        right = QVector3D(math.sin(longitude),-math.cos(longitude),0)
        camera = self.view3d.camera
        camera.position = QVector3D(self.eye)
        camera.target = self.eye+forward*self.ds_distance
        camera.up = QVector3D.crossProduct(right,forward).normalized()
        camera.compute()
        self.view3d.onViewChanged()

class WalkTool(LookTool):
    """Yaw and ground-plane walking; Ctrl switches to lateral/vertical motion."""
    MOVE_SPEED = 0.5  # cm per mouse pixel
    def activate(self):
        self.dragging = False
        self.view3d.setStatusBar('漫游：按住左键，左右转向、上下前后移动；Ctrl 拖动左右平移、上下升降')

    def doZoom(self, pos, delta, modifiers=Qt.NoModifier):
        return CameraTool.doZoom(self,pos,delta,modifiers)

    def on_mouse_move(self, pos, modifiers):
        if not getattr(self,'dragging',False):return
        diff=pos-self.last_pos
        self.last_pos=pos
        camera=self.view3d.camera
        direction=camera.target-camera.position
        # Translation speed is independent of orbit target distance.
        if modifiers & Qt.ControlModifier:
            yaw=math.radians(self.ds_longitude)
            right=QVector3D(math.sin(yaw),-math.cos(yaw),0)
            delta=right*diff.x()+QVector3D(0,0,-diff.y())
        else:
            angle=math.radians(-diff.x()*.1)
            self.ds_longitude-=diff.x()*.1
            def rotate(v):
                return QVector3D(v.x()*math.cos(angle)-v.y()*math.sin(angle),
                                 v.x()*math.sin(angle)+v.y()*math.cos(angle),v.z())
            direction=rotate(direction)
            camera.up=rotate(camera.up)
            yaw=math.radians(self.ds_longitude)
            forward=QVector3D(math.cos(yaw),math.sin(yaw),0)
            delta=forward*(-diff.y())
        camera.position+=delta*self.MOVE_SPEED
        camera.target=camera.position+direction
        camera.compute()
        self.view3d.onViewChanged()


class PositionCameraTool(CameraTool):
    """Place the human eye 170 cm above a picked point, then look around."""
    wants_hover = True

    def activate(self):
        self.input = core.CInputPointFinder(self.view3d.view_proxy)
        self.hover = None
        self.view3d.setMouseTracking(True)
        self.view3d.setStatusBar('定位相机：捕获一点并单击，相机升高 170 cm 后进入观察工具')

    def deactivate(self):
        self.view3d.setMouseTracking(False)

    def point(self, pos):
        from .drawing_support import infer
        try:
            return infer(self.view3d,self.input,pos)
        except ValueError:
            return None

    def on_mouse_move(self, pos, modifiers):
        self.hover = self.point(pos)

    def on_left_button_down(self, pos, mod):
        point = self.point(pos)
        if point is None:return
        from engine.coordinates import to_world
        point = to_world(self.view3d,point)
        camera = self.view3d.camera
        direction = camera.target-camera.position
        camera.position = QVector3D(point.x,point.y,point.z+170.)
        camera.target = camera.position+direction
        camera.compute()
        self.view3d.onViewChanged()
        self.view3d.SetActiveTool(LookTool(self.view3d))

    def draw(self, gl):
        draw_inference(self.view3d, self.input, gl)
        if self.hover is not None:
            core.draw_target_with_size(self.hover,self.view3d.camera_zoom*.01,gl)

    def on_cancel(self):
        self.hover = None

