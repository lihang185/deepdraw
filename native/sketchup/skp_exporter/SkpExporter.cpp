#include <stdexcept>
#define assert(test) do { if (!(test)) throw std::runtime_error("SketchUp exporter: " #test); } while(false)
#include "SkpExporter.h"
#include <string>


std::string StringWideCharToMultiByte(const std::wstring& wstr, UINT codePage) {
    if (wstr.empty()) return std::string();
    int size = WideCharToMultiByte(codePage, 0, wstr.c_str(), -1, NULL, 0, NULL, NULL);
    if (size == 0) return std::string(); // 转换失败
    std::string str;
    str.resize(size);
    WideCharToMultiByte(codePage, 0, wstr.c_str(), -1, (LPSTR)str.data(), size, NULL, NULL);
    return str;
}

SkpExporter::SkpExporter() : su_model(SU_INVALID) {}

SkpExporter::~SkpExporter() { if (SUIsValid(su_model)) SUModelRelease(&su_model); }



//===================
//  Main Interface
//
//===================
bool SkpExporter::ExportSceneToFile(CModelPublic* model, const char* filename)
{
    SUResult result;
    SUModelRef su_model = SU_INVALID;
    result = SUModelCreate(&su_model);
    assert(result == SU_ERROR_NONE);
    this->su_model = su_model;

    CComponentPublic* top_comp = model->GetTopComponent();

    WalkComponent(top_comp);
    for (auto it = this->compdef_ls.begin(); it != this->compdef_ls.end(); ++it) {
        CComponentDefinitionPublic* compdef = (*it);
        ExportComponentDefinition(compdef);
    }

    SUEntitiesRef out_comp;
    result = SUModelGetEntities(this->su_model, &out_comp);
    assert(result == SU_ERROR_NONE);

    ExportEntities(top_comp, out_comp);

    result = SUModelSaveToFileWithVersion(this->su_model, filename, SUModelVersion_SU2017);
    if (result == SU_ERROR_NONE) {
        return true;
    }
    else {
        return false;
    }
}

bool SkpExporter::ExportSelectionToFile(CModelPublic* model, const char* filename)
{
    SUResult result;
    SUModelRef su_model = SU_INVALID;
    result = SUModelCreate(&su_model);
    assert(result == SU_ERROR_NONE);
    this->su_model = su_model;

    std::vector<CEntityPublic*> selection = model->GetSelection();

    WalkComponentBySelection(selection);
    for (auto it = this->compdef_ls.begin(); it != this->compdef_ls.end(); ++it) {
        CComponentDefinitionPublic* compdef = (*it);
        ExportComponentDefinition(compdef);
    }

    SUEntitiesRef out_comp;
    result = SUModelGetEntities(this->su_model, &out_comp);
    assert(result == SU_ERROR_NONE);

    ExportEntitiesBySelection(selection, out_comp);

    result = SUModelSaveToFileWithVersion(this->su_model, filename, SUModelVersion_SU2017);
    if (result == SU_ERROR_NONE) {
        return true;
    }
    else {
        return false;
    }
}


//===================
//  CMaterial
//
//===================
SUMaterialRef SkpExporter::ExportMaterial(CMaterialPublic* mtl)
{
    SUResult result;

    if (!mtl)
        return SU_INVALID;

    SUMaterialRef su_mtl = SU_INVALID;
    if (find_material_map(mtl, &su_mtl)) {
        return su_mtl;
    }

    result = SUMaterialCreate(&su_mtl);
    assert(result == SU_ERROR_NONE);

    result = SUModelAddMaterials(this->su_model, 1, &su_mtl);
    assert(result == SU_ERROR_NONE);

    std::wstring src_name = mtl->GetName();
    std::string name = StringWideCharToMultiByte(src_name, CP_UTF8);
    result = SUMaterialSetName(su_mtl, name.c_str());
    assert(result == SU_ERROR_NONE);

    SVector3D color = mtl->GetColor();
    SUColor rgb;
    rgb.red = (SUByte)(color.x * 255);
    rgb.green = (SUByte)(color.y * 255);
    rgb.blue = (SUByte)(color.z * 255);
    rgb.alpha = 255;
    result = SUMaterialSetColor(su_mtl, &rgb);
    assert(result == SU_ERROR_NONE);

    result = SUMaterialSetUseOpacity(su_mtl, mtl->IsOpacity());
    assert(result == SU_ERROR_NONE);

    result = SUMaterialSetOpacity(su_mtl, mtl->GetOpacity());
    assert(result == SU_ERROR_NONE);

    CTexturePublic* texture = mtl->GetTexture();
    if (texture) {
        std::wstring tex_path = temp_dir + L"\\" + texture->GetName();
        CDibPublic* dib = texture->GetDib();
        FILE* hf = _wfopen(tex_path.c_str(), L"wb");
        if (hf) {
            int len = dib->GetLength();
            void* data = malloc(len);
            dib->GetData(data, len);
            fwrite(data, 1, len, hf);
            fclose(hf);
            free(data);
        }

        std::string tex_path_utf8 = StringWideCharToMultiByte(tex_path, CP_UTF8);
        double size_u = texture->GetSizeU() / 2.54;
        double size_v = texture->GetSizeV() / 2.54;

        SUTextureRef su_tex = SU_INVALID;

        result = SUTextureCreateFromFile(&su_tex, tex_path_utf8.c_str(), size_u, size_v);
        assert(result == SU_ERROR_NONE);

        result = SUMaterialSetTexture(su_mtl, su_tex);
        assert(result == SU_ERROR_NONE);
    }

    this->material_map[mtl] = su_mtl;

    return su_mtl;
}


//===================
//  Walk Tree
//
//===================
void SkpExporter::WalkComponent(CComponentPublic* comp)
{
    CEntityPublic* pEntity;
    std::set< CComponentDefinitionPublic* > set1;

    IEntityIteratorPublic* iter = comp->EnumChildren();
    while (iter->Next(&pEntity)) {
        CComponentInstancePublic* inst = (CComponentInstancePublic*)pEntity;
        CComponentDefinitionPublic* child_comp = inst->GetDefinition();
        set1.insert(child_comp);
    }
    iter->Release();

    for (auto it = set1.begin(); it != set1.end(); ++it) {
        CComponentDefinitionPublic* child_comp = (*it);
        auto find = this->compdef_set.find(child_comp);
        if (find == this->compdef_set.end()) {
            WalkComponent(child_comp);
            this->compdef_set.insert(child_comp);
            compdef_ls.push_back(child_comp);
        }
    }
}

void SkpExporter::WalkComponentBySelection(std::vector<CEntityPublic*>& entities)
{
    std::set< CComponentDefinitionPublic* > set1;

    for( auto it = entities.begin(); it != entities.end(); ++it) {
        CEntityPublic* pEntity = *it;
        if (pEntity->GetType() == DEEPDRAW_CComponentInstance) {
            CComponentInstancePublic* inst = (CComponentInstancePublic*)pEntity;
            CComponentDefinitionPublic* child_comp = inst->GetDefinition();
            set1.insert(child_comp);

        }
    }

    for (auto it = set1.begin(); it != set1.end(); ++it) {
        CComponentDefinitionPublic* child_comp = (*it);
        auto find = this->compdef_set.find(child_comp);
        if (find == this->compdef_set.end()) {
            WalkComponent(child_comp);
            this->compdef_set.insert(child_comp);
            compdef_ls.push_back(child_comp);
        }
    }
}

//===================
// ComponentDefinition
//
//===================
void SkpExporter::ExportComponentDefinition(CComponentDefinitionPublic* compdef)
{
    SUResult result;
    SUComponentDefinitionRef su_compdef = SU_INVALID;

    result = SUComponentDefinitionCreate(&su_compdef);
    assert(result == SU_ERROR_NONE);
    //ComponentDefinition创建好后要立刻加入到Model中
    //否则后面添加到组件的点线面会出问题

    result = SUModelAddComponentDefinitions(this->su_model, 1, &su_compdef );
    assert(result == SU_ERROR_NONE);

    std::string name = StringWideCharToMultiByte(compdef->GetName(), CP_UTF8);
    result = SUComponentDefinitionSetName(su_compdef, name.c_str());
    assert(result == SU_ERROR_NONE);

    std::string desc = StringWideCharToMultiByte(compdef->GetDescription(), CP_UTF8);
    result = SUComponentDefinitionSetDescription(su_compdef, desc.c_str());
    assert(result == SU_ERROR_NONE);

    SUEntitiesRef entities = SU_INVALID;
    result = SUComponentDefinitionGetEntities(su_compdef, &entities);
    assert(result == SU_ERROR_NONE);

    ExportEntities(compdef, entities);

    this->compdef_map[compdef] = su_compdef;
}

//===================
//  Entities
//
//===================
void SkpExporter::ExportEntities(CComponentPublic* comp, SUEntitiesRef out_comp)
{
    SVector3D center_point = { 0,0,0 };

    if (comp->GetNumEntities() > comp->GetNumChildren()) {
        std::vector<CEntityPublic*> entities;
        entities.reserve(comp->GetNumEntities());
        CEntityPublic* pEntity;
        IEntityIteratorPublic* iter = comp->EnumEntities();
        while (iter->Next(&pEntity)) {
            entities.push_back(pEntity);
        }
        iter->Release();

        ExportCompGeometry(entities, center_point, out_comp);
    }

    CEntityPublic* pEntity;
    IEntityIteratorPublic* iter = comp->EnumChildren();
    while (iter->Next(&pEntity)) {
        CComponentInstancePublic* inst = (CComponentInstancePublic*)pEntity;
        ExportInstance(inst, center_point, out_comp);
    }
    iter->Release();

}

void SkpExporter::ExportEntitiesBySelection(std::vector<CEntityPublic*>& entities, SUEntitiesRef out_comp)
{
    bool has_geom;
    SVector3D center_point = { 0,0,0 };

    std::vector<CEdgePublic*> con_edges;

    std::set<CEntityPublic*> set1;
    for (auto it = entities.begin(); it != entities.end(); ++it) {
        CEntityPublic* pEntity = *it;
        if (pEntity->GetType() == DEEPDRAW_CFace) {
            CFacePublic* face = (CFacePublic*)pEntity;
            CEdgePublic* edge;
            IEntityIteratorPublic* iter = face->EnumEdges();
            while (iter->Next(&edge)) {
                con_edges.push_back(edge);
            }
            iter->Release();
        }

        set1.insert(pEntity);
    }

    for (auto it = con_edges.begin(); it != con_edges.end(); ++it) {
        CEdgePublic* edge = *it;
        set1.insert(edge);
    }

    entities.clear();
    for (auto it = set1.begin(); it != set1.end(); ++it) {
        CEntityPublic* pEntity = *it;
        entities.push_back(pEntity);
    }


    has_geom = compute_center_point(entities, &center_point);
    if (has_geom) {
        ExportCompGeometry(entities, center_point, out_comp);
    }

    CEntityPublic* pEntity;
    for (auto it = entities.begin(); it != entities.end(); ++it) {
        pEntity = *it;
        if (pEntity->GetType() == DEEPDRAW_CComponentInstance) {
            CComponentInstancePublic* inst = (CComponentInstancePublic*)pEntity;
            ExportInstance(inst, center_point, out_comp);
        }
    }

}

//===================
//  ComponentInstance
//
//===================
void SkpExporter::ExportInstance(CComponentInstancePublic* inst, SVector3D& center_point, SUEntitiesRef out_comp)
{
    SUResult result;

    CComponentDefinitionPublic* compdef = inst->GetDefinition();
    SUComponentDefinitionRef su_compdef = this->compdef_map[compdef];

    SUComponentInstanceRef su_inst = SU_INVALID;
    result = SUComponentDefinitionCreateInstance(su_compdef, &su_inst);
    assert(result == SU_ERROR_NONE);

    SMatrix m1 = inst->GetTransform();
    m1.m[12] = (m1.m[12] - center_point.x) / 2.54;
    m1.m[13] = (m1.m[13] - center_point.y) / 2.54;
    m1.m[14] = (m1.m[14] - center_point.z) / 2.54;
    SUTransformation m2;
    memcpy(&m2, &m1, sizeof(m1));

    result = SUComponentInstanceSetTransform(su_inst, &m2);
    assert(result == SU_ERROR_NONE);

    CMaterialPublic* mtl = inst->GetMaterial();
    if (mtl) {
        SUMaterialRef su_mtl = ExportMaterial(mtl);

        SUDrawingElementRef draw_elem = SUComponentInstanceToDrawingElement(su_inst);
        result = SUDrawingElementSetMaterial(draw_elem, su_mtl);
        assert(result == SU_ERROR_NONE);
    }

    result = SUEntitiesAddInstance(out_comp, su_inst, 0);
    assert(result == SU_ERROR_NONE);
}


//===================
// Geometry
//
//===================
void SkpExporter::ExportCompGeometry(std::vector<CEntityPublic*>& entities, SVector3D& center_point, SUEntitiesRef out_comp)
{
    SUResult result;
    CEntityPublic* pEntity;

    SUGeometryInputRef geo = SU_INVALID;
    result = SUGeometryInputCreate(&geo);
    assert(result == SU_ERROR_NONE);

    std::vector<CVertexPublic*> vert_ls;

    //==================
    // 收集所有Edge
    //==================
    for (auto it = entities.begin(); it != entities.end(); ++it) {
        pEntity = (*it);
        if (pEntity->GetType() == DEEPDRAW_CEdge) {
            CEdgePublic* pEdge = (CEdgePublic*)pEntity;
            if (pEdge->Isolated()) {
                SVector3D p;
                SUPoint3D p2;
                size_t idx = vert_ls.size();
                CVertexPublic* v1 = pEdge->GetStartVertex();
                vert_ls.push_back(v1);
                p = v1->Pos();
                p2;
                p2.x = (p.x - center_point.x) / 2.54;
                p2.y = (p.y - center_point.y) / 2.54;
                p2.z = (p.z - center_point.z) / 2.54;
                result = SUGeometryInputAddVertex(geo, &p2);
                assert(result == SU_ERROR_NONE);

                CVertexPublic* v2 = pEdge->GetEndVertex();
                vert_ls.push_back(v2);
                p = v2->Pos();
                p2;
                p2.x = (p.x - center_point.x) / 2.54;
                p2.y = (p.y - center_point.y) / 2.54;
                p2.z = (p.z - center_point.z) / 2.54;
                result = SUGeometryInputAddVertex(geo, &p2);
                assert(result == SU_ERROR_NONE);

                size_t edge_idx;
                result = SUGeometryInputAddEdge(geo, idx, idx+1, &edge_idx);
                assert(result == SU_ERROR_NONE);
            }
        }
    }

    //==================
    // 收集所有Face
    //==================
    int start_index = 0;

    for (auto it = entities.begin(); it != entities.end(); ++it) {
        pEntity = (*it);
        if (pEntity->GetType() == DEEPDRAW_CFace) {
            CFacePublic* face = (CFacePublic*)pEntity;
            CLoopPublic* loop = face->GetOuterLoop();

            SULoopInputRef loop_input;

            start_index = (int)vert_ls.size();
            this->conv_loop(geo, loop, center_point, vert_ls, &loop_input);

            size_t face_idx;
            result = SUGeometryInputAddFace(geo, &loop_input, &face_idx);
            assert(result == SU_ERROR_NONE);

            int num_loops = face->GetNumLoops();
            for (int i = 1; i < num_loops; i++) {
                loop = face->GetLoop(i);
                this->conv_loop(geo, loop, center_point, vert_ls, &loop_input);

                result = SUGeometryInputFaceAddInnerLoop(geo, face_idx, &loop_input);
                assert(result == SU_ERROR_NONE);
            }

            CMaterialPublic* mtl = face->GetMaterial();
            if (mtl) {
                SUMaterialRef su_mtl = this->ExportMaterial(mtl);

                CTexturePublic* texture = mtl->GetTexture();
                if (texture) {
                    SUMaterialInput mtl_input;
                    mtl_input.material = su_mtl;

                    CUVHelperPublic* uv_helper = CUVHelperPublic::Create(face, mtl);
                    loop = face->GetOuterLoop();
                    int num_edges = loop->GetNumEdges();
                    if (num_edges > 4) {
                        CVertexPublic* tc_verts[4];
                        int num_verts = this->find_tc_verts(loop, uv_helper, tc_verts);
                        for (int j = 0; j < num_verts; j++) {
                            CVertexPublic* v = tc_verts[j];
                            mtl_input.vertex_indices[j] = this->find_vertex_idx(vert_ls, start_index, v);
                            SVector3D pos = v->Pos();
                            SVector3D st = uv_helper->ProjVertex(pos);
                            mtl_input.uv_coords[j] = { st.x,st.y };
                        }

                        mtl_input.num_uv_coords = num_verts;
                    }
                    else {
                        CVertexPublic* v;
                        IEntityIteratorPublic* iter = loop->EnumVertices();
                        int j = 0;
                        while (iter->Next(&v)) {
                            SVector3D pos = v->Pos();
                            SVector3D st = uv_helper->ProjVertex(pos);
                            mtl_input.vertex_indices[j] = this->find_vertex_idx(vert_ls, start_index, v);
                            mtl_input.uv_coords[j] = { st.x,st.y };
                            j++;
                        }

                        mtl_input.num_uv_coords = num_edges;
                        iter->Release();
                    }
                    uv_helper->Release();
                    result = SUGeometryInputFaceSetFrontMaterial(geo, face_idx, &mtl_input);
                    assert(result == SU_ERROR_NONE);
                    result = SUGeometryInputFaceSetBackMaterial(geo, face_idx, &mtl_input);
                    assert(result == SU_ERROR_NONE);
                }
                else {
                    SUMaterialInput mtl_input;
                    mtl_input.material = su_mtl;
                    mtl_input.num_uv_coords = 0;
                    result = SUGeometryInputFaceSetFrontMaterial(geo, face_idx, &mtl_input);
                    assert(result == SU_ERROR_NONE);
                    result = SUGeometryInputFaceSetBackMaterial(geo, face_idx, &mtl_input);
                    assert(result == SU_ERROR_NONE);
                }
            }
        }
    }

    result = SUEntitiesFill(out_comp, geo, true);
    assert(result == SU_ERROR_NONE);

    result = SUGeometryInputRelease(&geo);
    assert(result == SU_ERROR_NONE);
}

int SkpExporter::find_vertex_idx(std::vector<CVertexPublic*>& vert_ls, int start_index, CVertexPublic* v)
{
    auto find = std::find(vert_ls.begin()+ start_index, vert_ls.end(), v);
    if (find == vert_ls.end()) {
        return -1;
    }
    else {
        return (int)std::distance(vert_ls.begin(), find);
    }
}

int SkpExporter::conv_loop(SUGeometryInputRef geo, CLoopPublic* loop, SVector3D& center_point, std::vector<CVertexPublic*>& vert_ls, SULoopInputRef* out_loop)
{
    SUResult result;
    SULoopInputRef loop_input = SU_INVALID;
    CEdgeUsePublic* pEu;

    result = SULoopInputCreate(&loop_input);
    assert(result == SU_ERROR_NONE);

    int idx = 0;
    IEntityIteratorPublic* iter = loop->EnumEdgeUse();
    while (iter->Next(&pEu)) {
        CVertexPublic* v = pEu->GetStartVertex();
        CEdgePublic* e = pEu->GetEdge();

        int v_idx = (int)vert_ls.size();
        vert_ls.push_back(v);

        SVector3D p = v->Pos();
        SUPoint3D p2;
        p2.x = (p.x - center_point.x) / 2.54;
        p2.y = (p.y - center_point.y) / 2.54;
        p2.z = (p.z - center_point.z) / 2.54;
        result = SUGeometryInputAddVertex(geo, &p2);
        assert(result == SU_ERROR_NONE);

        result = SULoopInputAddVertexIndex(loop_input, v_idx);
        assert(result == SU_ERROR_NONE);
        bool soft = e->IsSoft();
        result = SULoopInputEdgeSetSoft(loop_input, idx, soft);
        assert(result == SU_ERROR_NONE);
        bool smooth = e->IsSmooth();
        result = SULoopInputEdgeSetSmooth(loop_input, idx, smooth);
        assert(result == SU_ERROR_NONE);

        idx++;
    }

    *out_loop = loop_input;

    return idx;
}




SVector3D vec3_add_noz(SVector3D& a, SVector3D& b) {
    SVector3D r;
    r.x = a.x + b.x;
    r.y = a.y + b.y;
    r.z = 0;
    return r;
}

int SkpExporter::compute_center_point(std::vector<CEntityPublic*>& entities, SVector3D* center_point)
{
    bool has_geom = false;
    CEntityPublic* pEntity;
    int total = 0;

    SVector3D center = { 0,0,0 };

    for (auto it = entities.begin(); it != entities.end(); ++it) {
        pEntity = *it;
        if (pEntity->GetType() == DEEPDRAW_CEdge) {
            CEdgePublic* edge = (CEdgePublic*)pEntity;
            SVector3D p1 = edge->GetStartVertex()->Pos();
            center = vec3_add_noz(center, p1);
            SVector3D p2 = edge->GetEndVertex()->Pos();
            center = vec3_add_noz(center, p2);
            total +=2;
            has_geom = true;
        }
        else if (pEntity->GetType() == DEEPDRAW_CFace) {
            has_geom = true;
        }
        else if (pEntity->GetType() == DEEPDRAW_CComponentInstance) {
            CComponentInstancePublic* inst = (CComponentInstancePublic*)pEntity;
            SMatrix m = inst->GetTransform();
            SVector3D tx = { m.m[12],m.m[13], m.m[14] };
            center = vec3_add_noz(center, tx);
            total++;
        }

    }

    double scale = total ? 1.0 / total : 1.0;
    center.x *= scale;
    center.y *= scale;
    center.z = 0;

    *center_point = center;
    return has_geom;
}



bool SkpExporter::find_material_map(CMaterialPublic* mtl, SUMaterialRef* out)
{
    auto find = material_map.find(mtl);
    if (find != material_map.end()) {
        *out = find->second;
        return true;
    }
    return false;
}

int SkpExporter::find_tc_verts(CLoopPublic* loop, CUVHelperPublic* uv_helper, CVertexPublic* out[])
{
    double s_min, s_max, t_min, t_max;
    CVertexPublic *s_min_v, *s_max_v, *t_min_v, *t_max_v, *v;
    double s, t;

    s_min = 1e10;
    s_max = -1e10;
    t_min = 1e10;
    t_max = -1e10;

    s_min_v = s_max_v = 0;
    t_min_v = t_max_v = 0;

    IEntityIteratorPublic* iter = loop->EnumVertices();
    while (iter->Next(&v)) {
        SVector3D pos = v->Pos();
        SVector3D st = uv_helper->ProjVertex(pos);
        s = st.x;
        if (s < s_min) {
            s_min = s;
            s_min_v = v;
        }

        if (s > s_max) {
            s_max = s;
            s_max_v = v;
        }

        t = st.y;
        if (t < t_min) {
            t_min = t;
            t_min_v = v;
        }

        if (t > t_max) {
            t_max = t;
            t_max_v = v;
        }
    }
    iter->Release();

    out[0] = s_min_v;
    out[1] = s_max_v;
    int count = 2;
    if (t_min_v != s_min_v && t_min_v != s_max_v) {
        out[count] = t_min_v;
        count++;
    }
    if (t_max_v != s_min_v && t_max_v != s_max_v) {
        out[count] = t_max_v;
        count++;
    }

    return count;
}





