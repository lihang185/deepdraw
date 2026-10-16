import os, sys
from PySide2.QtGui import QImage, QOpenGLTexture

import core

#import render
import time


#
DEBUG_INFO = False
Print_Time = False


class RMaterial(core.RBaseMaterial):
    def __init__(self):
        super().__init__()
        self.m = None
        self.gl_tex = 0
        
    Type_Default = 0
    Type_Color = 1
    Type_Texture = 2

    def LoadMaterial(self, m, gl):
        self.gl = gl
        self.m = m
        
        if m is None:
            self.type = RMaterial.Type_Default
        else:
            texture = m.GetTexture()
            if texture:
                texname = texture.GetName();
                print("Material:%s load texture"%texname)
                #imgpath = abspath(texname)
                dib = texture.GetDib()
                ok, self.gl_tex_obj = self.LoadImageFromDib(dib)
                if ok:
                    self.type = RMaterial.Type_Texture
                    self.gl_tex = self.gl_tex_obj.textureId()
                else:
                    self.type = RMaterial.Type_Color
            else:
                self.type = RMaterial.Type_Color
                
            if self.type == RMaterial.Type_Color:
                self.m.use_opacity = self.m.opacity < 0.95
    
    ############
    # Material Binding
    # Lighting
    # 材质 & 灯光
    ############
    def LoadImageFromFile(self, filepath):
        fix_path = os.path.join(sys.data_path, os.path.basename(filepath))
        try:
            with open(fix_path, 'rb') as hf:
                data = hf.read()
        except Exception as e:
            print(f"load texture {fix_path} exception, {e}")
            return False, None
        
        image = QImage()
        valid = image.loadFromData(data)
        if not valid:
            return False, None
            
        gl_tex_obj = QOpenGLTexture(image.mirrored())
        return True, gl_tex_obj
    
    def LoadImageFromDib(self, dib):
        data = dib.GetData()
        
        image = QImage()
        valid = image.loadFromData(data)
        if not valid:
            return False, None
        
        if image.hasAlphaChannel():
            self.m.use_opacity = True
        else:
            self.m.use_opacity = False
            
        gl_tex_obj = QOpenGLTexture(image.mirrored())
        return True, gl_tex_obj


class RenderComponent:
    def __init__(self, comp, model):
        self.comp = comp
        self.model = model
        self.dirty = True
        #
        self.instances = []
        
        self.clear_geom()
        self.model_cache = core.RVBOCache()
    
    def is_dirty(self):
        return self.dirty
    
    def mark_dirty(self):
        self.dirty = True
    
    def clear_geom(self):
        self.nomat_ls = []
        self.dict_mats_normal = {}
        self.dict_mats_opacity = {}
        self.edge_group_ls = []
    
    def add_node(self, node):
        self.classify_face(node)
        self.add_edge_group(node)
    
    def classify_face(self, node):
        comp = node.comp
        
        # classify by material
        nomat = []
        dict_mats = {}
        
        for e in comp.EnumEntities():
            if type(e) is core.CFace:
                #if e.GetHidden(): continue

                mtl = e.GetMaterial() or node.mtl
                if mtl is None:
                    nomat.append(e)
                else:
                    rm = self.model.get_rt_material(mtl)
                    ls = dict_mats.setdefault(rm, [])
                    ls.append(e)
        
        if nomat:
            item = nomat, node
            self.nomat_ls.append(item)

        for mtl, list1 in dict_mats.items():
            if mtl:
                self.add_faces(list1, mtl, node)

    
    def add_edge_group(self, node):
        edge_ls = []
        # 这里针对image要特殊处理一下
        inst = node.get_inst()
        if inst and inst.is_image:
            return
        for e in node.comp.EnumEntities():
            if type(e) is core.CEdge:
                edge_ls.append(e)
        if edge_ls:
            self.add_edges(edge_ls, node.matrix)

    def add_faces(self, face_ls, mtl, node):
        if not face_ls:
            return
        
        # 分类&过滤
        if mtl and mtl.IsOpacity():
            target_dict = self.dict_mats_opacity
        else:
            target_dict = self.dict_mats_normal
            
        if mtl not in target_dict:
            target_dict[mtl] = []
        
        item = face_ls, node
        
        target_dict[mtl].append(item)
    
    def add_edges(self, edge_ls, m ):
        item = edge_ls, m
        self.edge_group_ls.append(item)

    def build(self, gl):
        if self.dirty:
            self.build_by_cpp()
            self.clear_geom()
            self.dirty = False
    
    def build_by_cpp(self):
        face_groups = []
        all_face_groups = []
        #
        if self.nomat_ls:
            cpp_nomat_ls = []
            for face_ls, node in self.nomat_ls:
                item = core.RFaceGroup(face_ls, node.matrix)
                cpp_nomat_ls.append(item)
            mtlGroup = core.RMaterialGroup(cpp_nomat_ls, None)
            all_face_groups.extend(cpp_nomat_ls)
            face_groups.append(mtlGroup)
        #
        for mtl, group_ls in self.dict_mats_normal.items():
            faceGroups = []
            for face_ls, node in group_ls:
                item = core.RFaceGroup(face_ls, node.matrix)
                # 这里针对image要特殊处理一下
                inst = node.get_inst()
                if inst and inst.is_image:
                    item.is_image = True
                faceGroups.append(item)
            mtlGroup = core.RMaterialGroup(faceGroups, mtl)
            all_face_groups.extend(faceGroups)
            face_groups.append(mtlGroup)
        for mtl, group_ls in self.dict_mats_opacity.items():
            faceGroups = []
            for face_ls, node in group_ls:
                item = core.RFaceGroup(face_ls, node.matrix)
                faceGroups.append(item)
            mtlGroup = core.RMaterialGroup(faceGroups, mtl)
            all_face_groups.extend(faceGroups)
            face_groups.append(mtlGroup)
        #
        edge_groups = []
        for edge_ls, matrix in self.edge_group_ls:
            item = core.REdgeGroup(edge_ls, matrix)
            edge_groups.append(item)
        #
        self.model_cache.Clear()
        self.model_cache.Build(face_groups, edge_groups)
        
        self.face_groups = face_groups

class RenderPipeline(core.IChangeListener):
    ##
    def __init__(self, model, view):
        super().__init__()
        
        self.model = model
        self.view = view
        self.open_path = []
        
        # draw options
        self.is_draw_camera_target = False

        #----------------------#
        # Materials
        self.material_map = {}
        # default Material
        m = RMaterial()
        m.LoadMaterial(None, view.gl)
        self.default_material = m
        self.material_map[None] = m

        #----------------------#
        # ComponentDefinitions
        self.component_map = {}
        
        #----------------------#
        # TopComponent
        self.top_comp = self.model.GetTopComponent()
        self.outer_part = RenderComponent(self.top_comp, self)
        
        # draw_mode
        self.use_stencil = False
        self.xray_mode = False
        
    ########################
    # IChangeListener
    #
    ########################
    def ContainerUpdate(self, comp):
        self.mark_comp_dirty(comp)
    
    ########################
    # mark_dirty
    #
    ########################
    def mark_dirty(self):
        comp = self.model.GetActiveComponent()
        comp_d = self.get_rt_component(comp)
        comp_d.mark_dirty()
    
    def mark_comp_dirty(self, comp):
        dd = self.get_rt_component(comp)
        dd.mark_dirty()
    
    def mark_outer_path_dirty(self):
        dd = self.outer_part
        dd.mark_dirty()
    
    ########################
    # Load & Save
    #
    ########################
    def get_rt_material(self, m):
        if m not in self.material_map:
            rm = RMaterial()
            rm.LoadMaterial(m, self.view.gl)
            self.material_map[m] = rm
            return rm
        else:
            return self.material_map[m]
    
    def get_rt_component(self, comp):
        if comp not in self.component_map:
            d = RenderComponent(comp, self)
            self.component_map[comp] = d
            return d
        else:
            return self.component_map[comp]

    def InitRT(self):
        for m in self.model.GetMaterials():
            self.get_rt_material(m)
        
        for comp_def in self.model.GetDefinitionList():
            self.get_rt_component(comp_def)
        
        # top comp
        self.top_comp = self.model.GetTopComponent()
       
        # root node
        #self.open_inst = self.get_root()

    def add_new_instance(self, comp_def):
        fac = core.CEntityFactory(self.model)
        inst = fac.NewComponentInstance()
        tm = core.CMatrix()
        tm.setRow(3, core.CVector3D(0, 0, 0));
        inst.SetTransform(tm)
        inst.SetMaterial(None)
        inst.SetDefinition(comp_def)

        self.GetTopComponent().AddEntity(inst)
        return inst

    ########################
    # Recursive
    # 
    ########################
    class InstancePathNode:
        def __init__(self, inst_path, comp, matrix, mtl):
            self.is_top = ( not inst_path )
            self.inst_path = inst_path
            self.comp = comp
            self.matrix = matrix
            self.mtl = mtl
        
        def get_inst(self):
            if self.inst_path:
                return self.inst_path[-1]
            return None

        def has_entities(self):
            return self.comp.getNumEntities() > self.comp.getNumChildren()

    def RecursiveRnumInstance(self, inst_path, comp, matrix, mtl):
        node = RenderPipeline.InstancePathNode(inst_path, comp, matrix, mtl)
        yield node
        #
        for inst2 in comp.EnumChildren():
            if inst2.IsHide():
                continue
            m2 = matrix.Multiply(inst2.GetTransform())
            if inst_path is None:
                inst_path2 = [inst2]
            else:
                inst_path2 = inst_path + [inst2]
            mtl2 = inst2.GetMaterial() or mtl
            n_comp = inst2.GetDefinition()
            yield from self.RecursiveRnumInstance(inst_path2, n_comp, m2, mtl2)

    def RecursiveRnumInstance2(self, active_path, inst_path, comp, matrix, mtl):
        #
        if self.compare_instance_path(active_path, inst_path):
            return
        #
        node = RenderPipeline.InstancePathNode(inst_path, comp, matrix, mtl)
        yield node
        #
        for inst2 in comp.EnumChildren():
            if inst2.IsHide():
                continue
            m2 = matrix.Multiply(inst2.GetTransform())
            if inst_path is None:
                inst_path2 = [inst2]
            else:
                inst_path2 = inst_path + [inst2]
            mtl2 = inst2.GetMaterial() or mtl
            n_comp = inst2.GetDefinition()
            yield from self.RecursiveRnumInstance2(active_path, inst_path2, n_comp, m2, mtl2)

    def compare_instance_path(self, active_path, inst_path ):
        if not inst_path:
            return active_path.Length() == 0
        
        if len(inst_path) != active_path.Length():
            return False
        #
        path_len = len(inst_path)
        for i in range(path_len):
            a = inst_path[i]
            b = active_path.Get(i)
            if a != b:
                return False
        #
        return True;
        
    ########################
    # ViewClip
    #
    ########################
    def ComputeViewClip(self):
        width = self.view.width()
        height = self.view.height()
        cx = width/2
        cy = height/2
        
        camera_forward = self.view.GetCameraForward()
        camera_up = self.view.GetCameraUp()
        camera_right = camera_forward.Cross(camera_up)
        camera_right.Normalize()
        
        orig, dir, end = self.view.ComputeCameraRay(0, cy)
        normal = dir.Cross(camera_up)
        p1 = core.CPlane(normal, orig)
        
        orig, dir, end = self.view.ComputeCameraRay(width, cy)
        normal = camera_up.Cross(dir)
        p2 = core.CPlane(normal, orig)
        
        orig, dir, end = self.view.ComputeCameraRay(cx, 0)
        normal = dir.Cross(camera_right)
        p3 = core.CPlane(normal, orig)
        
        orig, dir, end = self.view.ComputeCameraRay(cx, height)
        normal = camera_right.Cross(dir)
        p4 = core.CPlane(normal, orig)

        orig, dir, end = self.view.ComputeCameraRay(cx, cy)
        p5 = core.CPlane(dir, orig)
        p6 = core.CPlane(-dir, end)
        
        geomfilter = core.CGeomFilterVolume(p1, p2, p3, p4, p5)
        geomfilter.SetFarClip(p6)
        
        return geomfilter
    
    def ComputePickVolume(self, x, y, width, height):
        
        camera_forward = self.view.GetCameraForward()
        camera_up = self.view.GetCameraUp()
        camera_right = camera_forward.Cross(camera_up)
        camera_right.Normalize()
        
        orig, dir, end = self.ComputeCameraRay(x-(width/2), y)
        normal = dir.Cross(camera_up)
        p1 = core.CPlane(normal, orig)
        
        orig, dir, end = self.ComputeCameraRay(x+(width/2), y)
        normal = camera_up.Cross(dir)
        p2 = core.CPlane(normal, orig)
        
        orig, dir, end = self.ComputeCameraRay(x, y-(height/2))
        normal = dir.Cross(camera_right)
        p3 = core.CPlane(normal, orig)
        
        orig, dir, end = self.ComputeCameraRay(x, y+(height/2))
        normal = camera_right.Cross(dir)
        p4 = core.CPlane(normal, orig)

        orig, dir, end = self.ComputeCameraRay(x, y)
        p5 = core.CPlane(dir, orig)
        #p6 = plane_from_normal_point(-dir, end)
        
        geomfilter = core.CGeomFilterVolume(p1, p2, p3, p4, p5)
        
        return geomfilter
        

    ########################
    # Draw
    #
    ########################
    def draw(self):
        gl = self.view.gl
        view = self.view
        
        total_st = time.perf_counter()
        self.draw_inst = 0.0
        
        # camera
        cam_pos = view.camera.position
        cam_dir = view.camera.forward
        light_pos = cam_pos + cam_dir * -2000
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (light_pos.x(), light_pos.y(), light_pos.z(), 1.0))
        
        # draw target
        if self.is_draw_camera_target:
            gl.glDisable(gl.GL_TEXTURE_2D)
            target_pos = view.camera.GetTarget()
            self.draw_camera_target(target_pos, gl)
        
        # filter by viewclipo
        st = time.perf_counter()
        viewclip = self.ComputeViewClip()
        active_comp = self.model.GetActiveComponent()
        self.filted_inst = core.RFilteredInstance()
        self.filted_inst.DoFilter(active_comp, viewclip)
        self.filted_list = self.filted_inst.EnumInstances()
        time_filter_inst = (time.perf_counter() - st) * 1000
        
        # update
        st = time.perf_counter()
        self.update_model_cache(viewclip, gl)
        time_update = (time.perf_counter() - st) * 1000
        
        #
        st = time.perf_counter()
        self.SetLighting(True, gl)
        self.default_material.Bind()

        # 绘制面
        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(1, 1)
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_NORMAL_ARRAY)
        gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)
        
        if not self.xray_mode:
            self.draw_pass(0, viewclip, gl)
        self.draw_pass(1, viewclip, gl)
        
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glDisableClientState(gl.GL_NORMAL_ARRAY)
        gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)

        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)
        
        self.SetLighting(False, gl)
        gl.glDisable(gl.GL_TEXTURE_2D)
        
        time_draw_pass0 = (time.perf_counter() - st) * 1000

        # 绘制线
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        
        st = time.perf_counter()
        gl.glColor3f(0, 0, 0)
        self.draw_pass(2, viewclip, gl)
        time_draw_pass1 = (time.perf_counter() - st) * 1000
        
        #==============
        #  绘制Selection
        #==============
        self.draw_selected(gl)

        #==============
        #  绘制BoundingBox
        #==============
        for e in self.model.GetSelection():
            if type(e) is core.CComponentInstance:
                pass
                #utils.draw_boundingbox_transformed(e, gl)
        
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        
        # 绘制半透明的面
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_NORMAL_ARRAY)
        gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)
        
        st = time.perf_counter()
        gl.glDisable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA,gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glDepthMask(gl.GL_FALSE)
        
        if self.xray_mode:
            gl.glDisable(gl.GL_TEXTURE_2D);
            gl.glColor4f(1, 1, 1, 0.3);
            #gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_DIFFUSE, (1.0, 1.0, 1.0, 0.3));
            self.draw_pass(0, viewclip, gl)
        self.draw_pass(3, viewclip, gl)
        
        gl.glDisable(gl.GL_BLEND)
        gl.glDepthMask(gl.GL_TRUE)
        
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glDisableClientState(gl.GL_NORMAL_ARRAY)
        gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)
        
        # restore
        self.default_material.Bind()
        time_draw_pass2 = (time.perf_counter() - st) * 1000
        
        total_dt = (time.perf_counter() - total_st) * 1000
        add_part = (time_filter_inst + time_draw_pass0 + time_draw_pass1 + time_draw_pass2) / total_dt * 100
        if Print_Time:
            print(f"filter: {time_filter_inst:.2f}, update: {time_update:.2f}, pass0: {time_draw_pass0:.2f}, pass1: {time_draw_pass1:.2f}, pass2: {time_draw_pass2:.2f}, totoal: {total_dt:.2f}, add: {add_part:.2f}")
            print(f"draw time: {self.draw_inst*1000:.2f}")

    def draw_camera_target(self, target, gl):
        #S = self.view.camera_zoom * 0.02
        S = 4
        p = target
        
        gl.glColor3f(1.0, 0.0, 0.0)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(p.x-S, p.y, p.z )
        gl.glVertex3d(p.x+S, p.y, p.z )
        gl.glEnd()
        

        gl.glColor3f(0.0, 1.0, 0.0)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(p.x,  p.y-S,  p.z )
        gl.glVertex3d(p.x,  p.y+S,  p.z )
        gl.glEnd()
        
        gl.glColor3f(0.0, 0.0, 1.0)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(p.x,  p.y,  p.z  )
        gl.glVertex3d(p.x,  p.y,  p.z+S*4 )
        gl.glEnd()
        
        pt = target
        pt.z +=  S*4 + S*0.5
        core.CSimpleDraw.draw_diamond_with_size(pt, S * 0.5)

    
    def update_model_cache(self, view_clip, gl):
        # top
        if self.model.GetActivePathLength() > 0:
            top_comp = self.model.GetTopComponent()
            outer_part = self.outer_part
            if outer_part.dirty:
                active_path = self.model.GetActiveComponentPath()
                for node in self.RecursiveRnumInstance2(active_path, None, top_comp, core.CMatrix(), None):
                    outer_part.add_node(node)
                outer_part.build(gl)
        # active
        active_comp = self.model.GetActiveComponent()
        active_comp_d = self.get_rt_component(active_comp)
        if active_comp_d.dirty:
            active_node = RenderPipeline.InstancePathNode(None, active_comp, core.CMatrix(), None)
            active_comp_d.add_node(active_node)
            active_comp_d.build(gl)
        # insts
        selection = self.model.GetSelection()
        for item in self.filted_list:
            inst = item.inst
            comp = inst.GetDefinition()
            comp_d = self.get_rt_component(comp)
            if comp_d.dirty:
                for node in self.RecursiveRnumInstance([inst], comp, core.CMatrix(), None):
                    comp_d.add_node(node)
                comp_d.build(gl)
            #
            mtl = inst.GetMaterial()
            item.material = self.get_rt_material(mtl)
            item.model_cache = comp_d.model_cache
            if inst in selection:
                item.is_selected = True
            else:
                item.is_selected = False
    
    def SetLighting(self, on_off, gl):
        #gl.glEnable(gl.GL_AUTO_NORMAL)
        #gl.glEnable(gl.GL_CULL_FACE)
        #gl.glFrontFace(gl.GL_CCW)

        if on_off:
            gl.glEnable(gl.GL_NORMALIZE)
            gl.glEnable(gl.GL_LIGHTING)
            gl.glEnable(gl.GL_LIGHT0)
            gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, (0.6, 0.6, 0.6, 1.0))
            gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, (0.3, 0.3, 0.3, 1.0))
            gl.glLightModeli(gl.GL_LIGHT_MODEL_TWO_SIDE, gl.GL_TRUE)
            gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0) )       
            gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT, (1.0, 1.0, 1.0, 1.0) )       
        else:
            gl.glDisable(gl.GL_NORMALIZE)
            gl.glDisable(gl.GL_LIGHTING)
            gl.glDisable(gl.GL_LIGHT0)

    
    def draw_pass(self, ipass, viewclip, gl):
        #===================
        # Outer Part
        #===================
        if self.model.GetActivePathLength() > 0:
            active_path = self.model.GetActiveComponentPath()
            m = active_path.ComputeMatrix()
            im = m.Inverted()
            gl.glPushMatrix()
            core.CSimpleDraw.multiply_matrix(im)
            self.draw_outer_part(ipass, gl)
            gl.glPopMatrix()
        
        #===================
        # Active Component
        #===================
        active_comp = self.model.GetActiveComponent()

        self.draw_active_comp(active_comp, ipass, gl)
        
        #===================
        # Child Instance
        #===================
        #self.draw_insts(ipass, gl)
        self.filted_inst.DrawPass(ipass)
    
    def draw_insts(self, ipass, gl):
        selection = self.model.GetSelection()

        for item in self.filted_list:
            inst = item.inst
            m = inst.GetTransform()
            mtl = inst.GetMaterial()
            gl.glPushMatrix()
            core.CSimpleDraw.multiply_matrix(m)
            # test mirror
            mirror = self.test_mirror(m)
            if mirror:
                gl.glFrontFace(gl.GL_CW)
            else:
                gl.glFrontFace(gl.GL_CCW)
            
            rm = self.get_rt_material(mtl)
            
            #comp_d = self.get_rt_component(comp)
            mc = item.model_cache
            
            if ipass == 0:
                rm.Bind()
            elif ipass == 1:
                rm.Bind()
            elif ipass == 2:
                if inst in selection:
                    gl.glColor3f(0, 1, 0)
                else:
                    gl.glColor3f(0, 0, 0)
            else:
                rm.Bind()

            st = time.perf_counter()
            mc.Draw(ipass)
            self.draw_inst += time.perf_counter() - st
            
            if mirror:
                gl.glFrontFace(gl.GL_CCW)

            gl.glPopMatrix()
    
    def test_mirror(self, m):
        xaxis = m.GetAxis(0)
        yaxis = m.GetAxis(1)
        zaxis = m.GetAxis(2)
        
        dir = xaxis.Cross(yaxis)
        if dir.Dot(zaxis) < 0.0:
            return True
        
        return False

    def draw_outer_part(self, ipass, gl):
        comp_d = self.outer_part
        mc = comp_d.model_cache
        if ipass == 2:
            gl.glColor3f(0.5, 0.8, 0.8)
        
        st = time.perf_counter()
        mc.Draw(ipass)
        self.draw_inst += time.perf_counter() - st
    
    def draw_active_comp(self, comp, ipass, gl):
        #
        comp_d = self.get_rt_component(comp)
        mc = comp_d.model_cache
        
        if ipass == 2:
            gl.glColor3f(0, 0, 0)
        
        st = time.perf_counter()
        mc.Draw(ipass)
        self.draw_inst += time.perf_counter() - st

        #==============
        #  绘制辅助线
        #==============
        if ipass == 2:
            scale = self.view.GetCameraZoom()
            if scale < 200:
                scale = 200
            core.CSimpleDraw.draw_guide_lines(comp, 2000)

    def draw_comp_faces(self, comp, gl):
        for node in self.RecursiveRnumInstance(None, comp, core.CMatrix(), None):
            if node.comp and node.has_entities():
                gl.glPushMatrix()
                core.CSimpleDraw.multiply_matrix(node.matrix)
                self.draw_faces(node.comp, node.mtl, gl)
                gl.glPopMatrix()

    def draw_comp_edges(self, comp, gl):
        for node in self.RecursiveRnumInstance(None, comp, core.CMatrix(), None):
            if node.comp and node.has_entities():
                gl.glPushMatrix()
                core.CSimpleDraw.multiply_matrix(node.matrix)
                core.CSimpleDraw.draw_edges(node.comp)
                gl.glPopMatrix()
    
    ########################
    # 绘制选择的
    # 面/线/辅助线
    ########################
    def draw_selected(self, gl):
        # Face
        if self.use_stencil:
            self.draw_face_selected_stencil(gl)
        else:
            self.draw_face_selected(gl)
        
        # Edge
        self.draw_edges_selected(gl)
        
        # Guide
        self.draw_guide_line_selected(gl)
    
    def draw_inst_selected(self, gl):
        gl.glDisable(gl.GL_TEXTURE_2D)
        #gl.glLineWidth(2)
        gl.glDepthFunc(gl.GL_LEQUAL)
        gl.glColor3f(0.0, 1.0, 0.0);
        
        top_node = self.get_root_node()
        for node in self.RecurEnumInstsFilterBySelect(top_node, False):
            if node.is_selected:
                gl.glPushMatrix()
                core.CSimpleDraw.multiply_matrix(node.inst)
                #gl.glMultMatrixf(node.m.data())
                core.CSimpleDraw.draw_edges(node.comp)
                gl.glPopMatrix()

        gl.glDepthFunc(gl.GL_LESS)
        gl.glLineWidth(1)

    ########################
    # draw_faces
    # 绘制面
    ########################
    def draw_faces(self, comp, pm, gl):
        #pm = None
        
        # 分类&过滤
        dict_mats = {}
        #ls = dict_mats.setdefault(None, [])
        for e in comp.EnumEntities():
            if e.IsHide(): continue
            #
            if type(e) is core.CFace:
                m = e.GetMaterial() or pm
                if m and not m.use_opacity or not m:
                    ls = dict_mats.setdefault(m, [])
                    ls.append(e)
        
        #gl.glDisable(gl.GL_TEXTURE_2D)
        #gl.glColor3f(1.0, 1.0, 1.0);

        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(1, 1)
                
        for m, list1 in dict_mats.items():
            rm = self.get_rt_material(m)
            rm.Bind()
            core.CSimpleDraw.draw_face_by_same_material(list1, pm)
        
        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)

    ########################
    # Selected
    # 被选择的面
    ########################
    def draw_face_selected(self, gl):
        selection = self.model.GetSelection()
        
        face_ls = list(
            filter(lambda e:type(e) is core.CFace, selection)
        )
        
        if not face_ls:
            return
        
        gl.glDisable(gl.GL_TEXTURE_2D)

        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(1, 1)
        
        gl.glDepthFunc(gl.GL_LEQUAL)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        gl.glColor4f(0.43, 0.57, 0.74, 0.65)
        #gl.glColor4f(0.92, 0.74, 0.56, 0.5)
        for face in face_ls:
            core.CSimpleDraw.draw_single_face(face)
        
        gl.glDepthFunc(gl.GL_LESS)
        gl.glDisable(gl.GL_BLEND)

        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)

    def draw_face_selected_stencil(self, gl):
        selection = self.model.GetSelection()
        
        face_ls = list(
            filter(lambda e:type(e) is core.CFace, selection)
        )
        
        if not face_ls:
            return

        gl.glDisable(gl.GL_TEXTURE_2D)

        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(1, 1)
        
        gl.glDepthFunc(gl.GL_LEQUAL)
        
        gl.glEnable(gl.GL_STENCIL_TEST)
        gl.glStencilFunc(gl.GL_EQUAL, 1, 0xFF)

        gl.glColor3f(0, 0, 1)
        for face in face_ls:
            core.CSimpleDraw.draw_single_face(face)
        gl.glDepthFunc(gl.GL_LESS)

        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glDisable(gl.GL_STENCIL_TEST)

    def draw_edges_selected(self, gl):
        selection = self.model.GetSelection()
        
        gl.glLineWidth(2)
        gl.glColor3f(0, 0, 1)
        gl.glBegin(gl.GL_LINES)
        for e in filter(lambda e:type(e) is core.CEdge, selection):
            v1 = e.GetStartVertex()
            v2 = e.GetEndVertex()
            gl.glVertex3f(v1.p.x, v1.p.y, v1.p.z )
            gl.glVertex3f(v2.p.x, v2.p.y, v2.p.z )
        gl.glEnd()
        gl.glLineWidth(1)

    ########################
    # draw_guide_lines_selected
    # 绘制辅助线
    ########################
    def draw_guide_line_selected(self, gl):
        selection = self.model.GetSelection()
        
        # Stripple
        stipple = 0x0707
        gl.glLineStipple(1, stipple)
        gl.glEnable(gl.GL_LINE_STIPPLE)
        #
        gl.glLineWidth(2)
        gl.glColor3f(0.0, 0.0, 1.0)
        for e in filter(lambda e:type(e) is core.CGuideLine, selection):
            core.CSimpleDraw.draw_single_guide_line(e.orig, e.dir, 2000)
        gl.glLineWidth(1)
        gl.glDisable(gl.GL_LINE_STIPPLE)

