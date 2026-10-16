import math
from PySide2.QtGui import QVector3D
from PySide2.QtCore import Qt

import core


class CameraCtrlMode:
    normal = 1, 
    orbit = 2, 
    pan = 3, 

class CameraTool(core.IBaseTool):
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

    
    def doZoom(self, pos, delta):
        camera = self.view3d.camera
        # 第一步： 把鼠标位置 转换为 index
        #X = self.layout.UnProjectX(sx)
        
        forward = (camera.target-camera.position).normalized()
        distance = (camera.target-camera.position).length()
        
        # 第二步： 缩放
        if delta < 0 :
            distance += distance * 0.2
        else:
            distance -= distance * 0.2
            
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

