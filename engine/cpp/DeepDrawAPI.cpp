#include "model.h"
#include "DeepDrawAPI.h"
#include <cstdlib>
#include <cstring>
#include <limits>
#include <memory>
#include <stdexcept>

//========================
//   CEntityPublic
//
//========================
int CEntityPublic::GetID()
{
	CEntity* This = (CEntity*)this;
	return This->GetID();
}

int CEntityPublic::GetType()
{
	CEntity* This = (CEntity*)this;
	return This->Type();
}

//========================
//   CDrawingElementPublic
//
//========================
bool CDrawingElementPublic::IsHide()
{
	CDrawingElement* This = (CDrawingElement*)this;
	return This->IsHide();
}


//========================
//   CVertexPublic
//
//========================
CVertexPublic* CVertexPublic::Create(SVector3D& p)
{
	CVector3D pos(p.x, p.y, p.z);
	CVertex* This = new CVertex(pos);
	return (CVertexPublic*)This;
}

void CVertexPublic::Release()
{
	CEdge* This = (CEdge*)this;
	This->DeleteThis();
}


SVector3D CVertexPublic::Pos()
{
	CVertex* This = (CVertex*)this;
	CVector3D p = This->Pos();
	SVector3D result = { p.x, p.y, p.z };
	return result;
}


//========================
//   CEdgePublic
//
//========================
CEdgePublic* CEdgePublic::Create(CVertexPublic* start, CVertexPublic* end)
{
	CVertex* pStart = (CVertex*)start;
	CVertex* pEnd = (CVertex*)end;
	CEdge* This = new CEdge(pStart,pEnd);
	return (CEdgePublic*)This;
}

void CEdgePublic::Release()
{
	CEdge* This = (CEdge*)this;
	This->DeleteThis();
}


bool CEdgePublic::IsSoft()
{
	CEdge* This = (CEdge*)this;
	return This->IsSoft();
}

bool CEdgePublic::IsSmooth()
{
	CEdge* This = (CEdge*)this;
	return This->IsSmooth();
}

CVertexPublic* CEdgePublic::GetStartVertex()
{
	CEdge* This = (CEdge*)this;
	return (CVertexPublic * )This->GetStartVertex();
}

CVertexPublic* CEdgePublic::GetEndVertex()
{
	CEdge* This = (CEdge*)this;
	return (CVertexPublic*)This->GetEndVertex();
}

bool CEdgePublic::Isolated()
{
	CEdge* This = (CEdge*)this;
	CEdgeUse* pEdgeUse = This->GetEdgeUseHead();
	return (pEdgeUse == NULL);
}

//========================
//   CEdgeUsePublic
//
//========================
CEdgeUsePublic* CEdgeUsePublic::Create(CEdgePublic* _edge, bool reversed)
{
	CEdgeUse* This = new CEdgeUse((CEdge*)_edge, reversed);
	return (CEdgeUsePublic*)This;
}

void CEdgeUsePublic::Release()
{
	CEdgeUse* This = (CEdgeUse*)this;
	This->DeleteThis();
}


CVertexPublic* CEdgeUsePublic::GetStartVertex()
{
	CEdgeUse* This = (CEdgeUse*)this;
	return (CVertexPublic*)This->GetStartVertex();
}

CVertexPublic* CEdgeUsePublic::GetEndVertex()
{
	CEdgeUse* This = (CEdgeUse*)this;
	return (CVertexPublic*)This->GetEndVertex();
}

CEdgePublic* CEdgeUsePublic::GetEdge()
{
	CEdgeUse* This = (CEdgeUse*)this;
	return (CEdgePublic*)This->GetEdge();
}


//========================
//   CLoopPublic
//
//========================
CLoopPublic* CLoopPublic::Create()
{
	CLoop* This = new CLoop();
	return (CLoopPublic*)This;
}

void CLoopPublic::Release()
{
	CLoop* This = (CLoop*)this;
	This->DeleteThis();
}


int CLoopPublic::GetNumEdges()
{
	CLoop* This = (CLoop*)this;
	return This->GetEdgeCount();
}

IEntityIteratorPublic* CLoopPublic::EnumEdgeUse()
{
	CLoop* This = (CLoop*)this;
	return (IEntityIteratorPublic*)This->EnumEdgeUse();
}

IEntityIteratorPublic* CLoopPublic::EnumVertices()
{
	CLoop* This = (CLoop*)this;
	return (IEntityIteratorPublic*)This->EnumVertices();
}

//========================
//   CFacePublic
//
//========================
CFacePublic* CFacePublic::Create()
{
	CFace* This = new CFace();
	return (CFacePublic*)This;
}

void CFacePublic::Release()
{
	CFace* This = (CFace*)this;
	This->DeleteThis();
}


int CFacePublic::GetNumLoops()
{
	CFace* This = (CFace*)this;
	return This->GetNumLoops();
}

CLoopPublic* CFacePublic::GetOuterLoop()
{
	CFace* This = (CFace*)this;
	return (CLoopPublic*)This->GetOuterLoop();
}

CLoopPublic* CFacePublic::GetLoop(int idx)
{
	CFace* This = (CFace*)this;
	return (CLoopPublic*)This->GetLoop(idx);
}

CMaterialPublic* CFacePublic::GetMaterial()
{
	CFace* This = (CFace*)this;
	return (CMaterialPublic*)This->GetMaterial();
}

void CFacePublic::ComputeMesh(TriangleMeshPublic* trimesh)
{
	CFace* This = (CFace*)this;
	This->ComputeMesh((TriangleMesh*)trimesh);
}

IEntityIteratorPublic* CFacePublic::EnumEdges()
{
	CFace* This = (CFace*)this;
	return (IEntityIteratorPublic*)This->EnumEdges();
}

//========================
//   TriangleMeshPublic
//
//========================
TriangleMeshPublic* TriangleMeshPublic::Create()
{
	TriangleMesh* This = new TriangleMesh();
	return (TriangleMeshPublic*)This;
}

void TriangleMeshPublic::Release()
{
	TriangleMesh* This = (TriangleMesh*)this;
	delete This;
}


int TriangleMeshPublic::GetNumVertexIndices()
{
	TriangleMesh* This = (TriangleMesh*)this;
	return This->GetNumVertexIndices();
}

int TriangleMeshPublic::GetVertexIndex(int i)
{
	TriangleMesh* This = (TriangleMesh*)this;
	return This->GetVertexIndex(i);
}


int TriangleMeshPublic::GetNumVertices()
{
	TriangleMesh* This = (TriangleMesh*)this;
	return This->GetNumVertices();
}

SVector3D TriangleMeshPublic::GetVertex(int i)
{
	TriangleMesh* This = (TriangleMesh*)this;
	CVector3D p = This->GetVertex(i);
	SVector3D r = { p.x,p.y,p.z };
	return r;
}

SVector3D TriangleMeshPublic::GetNormal(int i)
{
	TriangleMesh* This = (TriangleMesh*)this;
	CVector3D p = This->GetNormal(i);
	SVector3D r = { p.x,p.y,p.z };
	return r;
}

SVector3D TriangleMeshPublic::GetFrontUV(int i)
{
	TriangleMesh* This = (TriangleMesh*)this;
	CVector3D p = This->GetFrontUV(i);
	SVector3D r = { p.x,p.y,p.z };
	return r;
}


//========================
//   CUVHelperPublic
//
//========================
CUVHelperPublic* CUVHelperPublic::Create(CFacePublic* face, CMaterialPublic* mtl)
{
	UVHelper* This = new UVHelper((CFace*)face, (CMaterial*)mtl);
	return (CUVHelperPublic*)This;
}

void CUVHelperPublic::Release()
{
	UVHelper* This = (UVHelper*)this;
	delete This;
}


SVector3D CUVHelperPublic::ProjVertex(SVector3D& pos)
{
	UVHelper* This = (UVHelper*)this;
	CVector3D p2(pos.x, pos.y, pos.z);
	CVector3D r = This->ProjVertex(p2);
	SVector3D st = { r.x, r.y, r.z };
	return st;
}

//========================
//   CDibPublic
//
//========================
CDibPublic* CDibPublic::Create()
{
	CDib* This = new CDib();
	return (CDibPublic*)This;
}

void CDibPublic::Release()
{
	CDib* This = (CDib*)this;
	This->DeleteThis();
}


int CDibPublic::GetLength()
{
	CDib* This = (CDib*)this;
	return This->GetLength();
}

void CDibPublic::GetData(void* buf, int buf_len)
{
	CDib* This = (CDib*)this;
	assert(This->len <= buf_len);
	memcpy(buf, This->pBuf, This->len);
}



//========================
//   CTexturePublic
//
//========================
CTexturePublic* CTexturePublic::Create()
{
	CTexture* This = new CTexture();
	return (CTexturePublic*)This;
}

void CTexturePublic::Release()
{
	CTexture* This = (CTexture*)this;
	This->DeleteThis();
}


std::wstring CTexturePublic::GetName()
{
	CTexture* This = (CTexture*)this;
	return This->name;
}

CDibPublic* CTexturePublic::GetDib()
{
	CTexture* This = (CTexture*)this;
	return (CDibPublic *)This->GetDib();
}

double CTexturePublic::GetSizeU()
{
	CTexture* This = (CTexture*)this;
	return This->size_u;
}

double CTexturePublic::GetSizeV()
{
	CTexture* This = (CTexture*)this;
	return This->size_v;
}


//========================
//   CMaterialPublic
//
//========================
CMaterialPublic* CMaterialPublic::Create()
{
	CMaterial* This = new CMaterial();
	return (CMaterialPublic*)This;
}

void CMaterialPublic::Release()
{
	CMaterial* This = (CMaterial*)this;
	This->DeleteThis();
}


std::wstring CMaterialPublic::GetName()
{
	CMaterial* This = (CMaterial*)this;
	return This->name;
}

SVector3D CMaterialPublic::GetColor()
{
	CMaterial* This = (CMaterial*)this;
	SVector3D color = { This->color.x, This->color.y, This->color.z };
	return color;
}

bool CMaterialPublic::IsOpacity()
{
	CMaterial* This = (CMaterial*)this;
	return This->use_opacity;
}

double CMaterialPublic::GetOpacity()
{
	CMaterial* This = (CMaterial*)this;
	return This->opacity;
}

CTexturePublic* CMaterialPublic::GetTexture()
{
	CMaterial* This = (CMaterial*)this;
	return (CTexturePublic *)This->GetTexture();
}


//========================
//   IEntityIteratorPublic
//
//========================
void IEntityIteratorPublic::Release()
{
	EntityIterator* This = (EntityIterator*)this;
	delete This;
}

bool IEntityIteratorPublic::Next(CEntityPublic** out)
{
	EntityIterator* This = (EntityIterator*)this;
	return This->next((CEntity**)out);
}

bool IEntityIteratorPublic::Next(CVertexPublic** out)
{
	EntityIterator* This = (EntityIterator*)this;
	return This->next2((CVertex**)out);
}

bool IEntityIteratorPublic::Next(CEdgePublic** out)
{
	EntityIterator* This = (EntityIterator*)this;
	return This->next2((CEdge**)out);
}

bool IEntityIteratorPublic::Next(CEdgeUsePublic** out)
{
	EntityIterator* This = (EntityIterator*)this;
	return This->next2((CEdgeUse**)out);
}

bool IEntityIteratorPublic::Next(CLoopPublic** out)
{
	EntityIterator* This = (EntityIterator*)this;
	return This->next2((CLoop**)out);
}

bool IEntityIteratorPublic::Next(CFacePublic** out)
{
	EntityIterator* This = (EntityIterator*)this;
	return This->next2((CFace**)out);
}

bool IEntityIteratorPublic::Next(CComponentInstancePublic** out)
{
	EntityIterator* This = (EntityIterator*)this;
	return This->next2((CComponentInstance**)out);
}


//========================
//   CComponentPublic
//
//========================
CComponentPublic* CComponentPublic::Create()
{
	CComponent* This = new CComponent();
	return (CComponentPublic*)This;
}

void CComponentPublic::Release()
{
	CComponent* This = (CComponent*)this;
	This->DeleteThis();
}

SBoundingBox CComponentPublic::GetBoundingBox()
{
	CComponent* This = (CComponent*)this;
	CBoundingBox bbox = This->GetBoundingBox();
	SBoundingBox bbox2;
	memcpy(&bbox2, &bbox, sizeof(bbox));
	return bbox2;
}

int CComponentPublic::GetNumEntities()
{
	CComponent* This = (CComponent*)this;
	return This->GetNumEntities();
}

int CComponentPublic::GetNumChildren()
{
	CComponent* This = (CComponent*)this;
	return This->GetNumChildren();
}

IEntityIteratorPublic* CComponentPublic::EnumEntities()
{
	CComponent* This = (CComponent*)this;
	return (IEntityIteratorPublic*)This->EnumEntities();
}

IEntityIteratorPublic* CComponentPublic::EnumChildren()
{
	CComponent* This = (CComponent*)this;
	return (IEntityIteratorPublic*)This->EnumChildren();
}

//========================
// CComponentDefinitionPublic
//
//========================
CComponentDefinitionPublic* CComponentDefinitionPublic::Create()
{
	CComponentDefinition* This = new CComponentDefinition();
	return (CComponentDefinitionPublic*)This;
}

void CComponentDefinitionPublic::Release()
{
	CComponentDefinition* This = (CComponentDefinition*)this;
	This->DeleteThis();
}

std::wstring CComponentDefinitionPublic::GetName()
{
	CComponentDefinition* This = (CComponentDefinition*)this;
	return This->name;
}

std::wstring CComponentDefinitionPublic::GetDescription()
{
	CComponentDefinition* This = (CComponentDefinition*)this;
	return This->description;
}


//========================
// CComponentInstancePublic
//
//========================
CComponentInstancePublic* CComponentInstancePublic::Create()
{
	CComponentInstance* This = new CComponentInstance();
	return (CComponentInstancePublic*)This;
}

void CComponentInstancePublic::Release()
{
	CComponentInstance* This = (CComponentInstance*)this;
	This->DeleteThis();
}


CComponentDefinitionPublic* CComponentInstancePublic::GetDefinition()
{
	CComponentInstance* This = (CComponentInstance*)this;
	return (CComponentDefinitionPublic*)This->GetDefinition();
}

SMatrix CComponentInstancePublic::GetTransform()
{
	CComponentInstance* This = (CComponentInstance*)this;
	CMatrix m = This->GetTransform();
	SMatrix m2 = {
		m.m[0][0], m.m[1][0], m.m[2][0], 0,
		m.m[0][1], m.m[1][1], m.m[2][1], 0,
		m.m[0][2], m.m[1][2], m.m[2][2], 0,
		m.m[3][0], m.m[3][1], m.m[3][2], m.scale,
	};
	return m2;
}

SMatrix2 CComponentInstancePublic::GetTransform2()
{
	CComponentInstance* This = (CComponentInstance*)this;
	CMatrix m = This->GetTransform();
	SMatrix2 m2;
	memcpy(&m2, &m, sizeof(m));
	return m2;
}

CMaterialPublic* CComponentInstancePublic::GetMaterial()
{
	CComponentInstance* This = (CComponentInstance*)this;
	return (CMaterialPublic*)This->GetMaterial();
}

//========================
//   GeomFilterVolumePublic
//
//========================
bool GeomFilterVolumePublic::TestBoundingBox(SBoundingBox& bbox)
{
	CGeomFilterVolume* This = (CGeomFilterVolume*)this;
	CBoundingBox bbox2;
	memcpy(&bbox2, &bbox, sizeof(bbox));
	return This->TestBoundingBox(bbox2);
}

//========================
//   CModelPublic
//
//========================
CModelPublic* CModelPublic::Create()
{
	CModel* This = new CModel();
	return (CModelPublic*)This;
}

CModelPublic* CModelPublic::GetAcitveModel()
{
	CModel* This = CModel::GetActiveModel();
	return (CModelPublic*)This;
}

void CModelPublic::Release()
{
	CModel* This = (CModel*)this;
	delete This;
}

CComponentPublic* CModelPublic::GetTopComponent()
{
	CModel* This = (CModel*)this;
	CComponent* result = This->GetTopComponent();
	return (CComponentPublic*)result;
}

std::vector<CEntityPublic*> CModelPublic::GetSelection()
{
	CModel* This = (CModel*)this;
	std::vector<CEntity*> result = This->GetSelection();
	std::vector<CEntityPublic*> copy;
	copy.reserve(result.size());
	for (auto it = result.begin(); it != result.end(); ++it) {
		CEntity* e = *it;
		copy.push_back((CEntityPublic*)e);
	}
	return copy;
}
// Native loading entry points. Delegate topology initialization to engine Load.
namespace {
template<class Native, class Public>
std::vector<Native*> NativePointers(const std::vector<Public*>& source)
{
    std::vector<Native*> result;
    result.reserve(source.size());
    for (auto* item : source) result.push_back(reinterpret_cast<Native*>(item));
    return result;
}

CNamedEntitySets::Map NativeNamedSets(const CNamedEntitySetsPublic::Map& source)
{
    CNamedEntitySets::Map result;
    for (const auto& entry : source) {
        auto& members = result[entry.first];
        for (auto* entity : entry.second)
            members.push_back(reinterpret_cast<CEntity*>(entity));
    }
    return result;
}
}

CVertexPublic* CVertexPublic::Load(const SVector3D& position)
{
    CVector3D p(position.x, position.y, position.z);
    return reinterpret_cast<CVertexPublic*>(CVertex::Load(p));
}

CEdgePublic* CEdgePublic::Load(bool hidden, CVertexPublic* start, CVertexPublic* end, bool soft, bool smooth)
{ return Load(hidden,nullptr,start,end,soft,smooth); }
CEdgePublic* CEdgePublic::Load(bool hidden, CLayerPublic* layer, CVertexPublic* start, CVertexPublic* end, bool soft, bool smooth)
{
    return reinterpret_cast<CEdgePublic*>(CEdge::Load(hidden,reinterpret_cast<CLayer*>(layer),
        reinterpret_cast<CVertex*>(start), reinterpret_cast<CVertex*>(end), soft, smooth));
}

CEdgeUsePublic* CEdgeUsePublic::Load(CEdgePublic* edge, bool reversed)
{
    return reinterpret_cast<CEdgeUsePublic*>(CEdgeUse::Load(reinterpret_cast<CEdge*>(edge), reversed));
}

CLoopPublic* CLoopPublic::Load(bool outer, bool convex, const std::vector<CEdgeUsePublic*>& edges)
{
    auto values = NativePointers<CEdgeUse>(edges);
    return reinterpret_cast<CLoopPublic*>(CLoop::Load(outer, convex, values));
}

CFacePublic* CFacePublic::Load(bool hidden, const SPlane& plane, const std::vector<CLoopPublic*>& loops,
    CMaterialPublic* material, CFaceTextureCoordsPublic* coords)
{ return Load(hidden,nullptr,plane,loops,material,coords); }
CFacePublic* CFacePublic::Load(bool hidden, CLayerPublic* layer, const SPlane& plane, const std::vector<CLoopPublic*>& loops,
    CMaterialPublic* material, CFaceTextureCoordsPublic* coords)
{
    CPlane p;
    p.x=plane.x; p.y=plane.y; p.z=plane.z; p.w=plane.w;
    auto values = NativePointers<CLoop>(loops);
    return reinterpret_cast<CFacePublic*>(CFace::Load(hidden, reinterpret_cast<CLayer*>(layer), p, values,
        reinterpret_cast<CMaterial*>(material), reinterpret_cast<CFaceTextureCoords*>(coords)));
}

CFaceTextureCoordsPublic* CFaceTextureCoordsPublic::Load(const SMatrix33& matrix)
{
    std::vector<double> values;
    values.reserve(9);
    for (int i=0; i<3; ++i) for (int j=0; j<3; ++j) values.push_back(matrix.m[i][j]);
    CMatrix33 m = CMatrix33::Load(values);
    return reinterpret_cast<CFaceTextureCoordsPublic*>(CFaceTextureCoords::Load(m));
}

CDibPublic* CDibPublic::Load(const void* data, std::size_t length)
{
    if (length > static_cast<std::size_t>((std::numeric_limits<int>::max)()))
        throw std::length_error("CDib length exceeds engine int capacity");
    if (length && !data) throw std::invalid_argument("CDib data is null");
    std::unique_ptr<CDib> dib(new CDib());
    // CDibPublic is already a friend. Match CDib's malloc/free ownership.
    if (length) {
        void* buffer = std::malloc(length);
        if (!buffer) throw std::bad_alloc();
        std::memcpy(buffer, data, length);
        dib->pBuf = buffer;
        dib->len = static_cast<int>(length);
    }
    return reinterpret_cast<CDibPublic*>(dib.release());
}

CTexturePublic* CTexturePublic::Load(const std::wstring& name, double size_u, double size_v, CDibPublic* dib)
{
    std::wstring text(name);
    return reinterpret_cast<CTexturePublic*>(CTexture::Load(text, size_u, size_v, reinterpret_cast<CDib*>(dib)));
}

CMaterialPublic* CMaterialPublic::Load(const std::wstring& name, const SVector3D& color,
    bool use_opacity, double opacity, CTexturePublic* texture)
{
    std::wstring text(name);
    CVector3D rgb(color.x, color.y, color.z);
    return reinterpret_cast<CMaterialPublic*>(CMaterial::Load(text, rgb, use_opacity, opacity,
        reinterpret_cast<CTexture*>(texture)));
}

CNamedEntitySetsPublic* CNamedEntitySetsPublic::Load(const Map& sets)
{
    auto values = NativeNamedSets(sets);
    return reinterpret_cast<CNamedEntitySetsPublic*>(CNamedEntitySets::Load(values));
}

CComponentDefinitionPublic* CComponentDefinitionPublic::Load(const std::wstring& name,
    const std::wstring& description, const std::wstring& agent_hint, const std::wstring& file_path,
    const std::vector<CEntityPublic*>& entities, const CNamedEntitySetsPublic::Map& named_sets,
    bool is_dynamic_comp, const std::wstring& dynamic_comp)
{
    std::wstring n(name), d(description), hint(agent_hint), path(file_path), dynamic(dynamic_comp);
    auto values = NativePointers<CEntity>(entities);
    auto sets = NativeNamedSets(named_sets);
    return reinterpret_cast<CComponentDefinitionPublic*>(CComponentDefinition::Load(
        n, d, hint, path, values, sets, is_dynamic_comp, dynamic));
}

CComponentInstancePublic* CComponentInstancePublic::Load(bool hidden, const std::wstring& name,
    const SMatrix2& transform, CMaterialPublic* material, CComponentDefinitionPublic* definition,
    bool is_group, bool is_image)
{ return Load(hidden,nullptr,name,transform,material,definition,is_group,is_image); }
CComponentInstancePublic* CComponentInstancePublic::Load(bool hidden, CLayerPublic* layer, const std::wstring& name,
    const SMatrix2& transform, CMaterialPublic* material, CComponentDefinitionPublic* definition,
    bool is_group, bool is_image)
{
    std::wstring text(name);
    CMatrix m;
    m.scale=transform.scale; m.is_identity=transform.is_identity; m.is_orthogonal=transform.is_orthogonal;
    for (int i=0; i<4; ++i) for (int j=0; j<3; ++j) m.m[i][j]=transform.m[i][j];
    return reinterpret_cast<CComponentInstancePublic*>(CComponentInstance::Load(hidden, reinterpret_cast<CLayer*>(layer), text, m,
        reinterpret_cast<CMaterial*>(material), reinterpret_cast<CComponentDefinition*>(definition),
        is_group, is_image));
}

// Native file writer accessors. Keep these in the engine, not in the cereal DLL.
bool CEntityPublic::IsMarkedDeleted() { return ((CEntity*)this)->IsMarkedDeleted(); }
bool CDrawingElementPublic::HasLayer() { return ((CDrawingElement*)this)->GetLayer()!=nullptr; }
bool CEdgePublic::HasCurve() { return ((CEdge*)this)->GetCurve()!=nullptr; }
bool CEdgeUsePublic::IsEdgeReversed() { return ((CEdgeUse*)this)->IsEdgeReversed(); }
bool CLoopPublic::IsOuterLoop() { return ((CLoop*)this)->IsOuterLoop(); }
bool CLoopPublic::IsConvex() { return ((CLoop*)this)->IsConvex(); }
SPlane CFacePublic::GetPlane() {
    CPlane p=((CFace*)this)->GetPlane();return {p.x,p.y,p.z,p.w};
}
CFaceTextureCoordsPublic* CFacePublic::GetTextureCoords() {
    return (CFaceTextureCoordsPublic*)((CFace*)this)->GetTextureCoords();
}
SMatrix33 CFaceTextureCoordsPublic::GetFrontTextureCoords() {
    CMatrix33 m=((CFaceTextureCoords*)this)->GetFrontTextureCoords();SMatrix33 result;
    for(int i=0;i<3;++i)for(int j=0;j<3;++j)result.m[i][j]=m.m[i][j];
    return result;
}
std::wstring CComponentDefinitionPublic::GetAgentHint() {return ((CComponentDefinition*)this)->agent_hint;}
std::wstring CComponentDefinitionPublic::GetFilePath() {return ((CComponentDefinition*)this)->file_path;}
bool CComponentDefinitionPublic::IsDynamicComponent() {return ((CComponentDefinition*)this)->is_dynamic_comp;}
std::wstring CComponentDefinitionPublic::GetDynamicComponent() {return ((CComponentDefinition*)this)->dynamic_comp;}
std::map<std::wstring,std::vector<CEntityPublic*>> CComponentDefinitionPublic::GetNamedSets() {
    auto* comp=(CComponentDefinition*)this;
    std::map<std::wstring,std::vector<CEntityPublic*>> result;
    for(auto name:comp->GetNamedSetNames()) {
        auto& members=result[name];
        for(auto* entity:comp->GetNamedSet(name))
            if(entity && !entity->IsMarkedDeleted())members.push_back((CEntityPublic*)entity);
    }
    return result;
}
std::wstring CComponentInstancePublic::GetName() {return ((CComponentInstance*)this)->name;}
bool CComponentInstancePublic::IsGroup() {return ((CComponentInstance*)this)->is_group;}
bool CComponentInstancePublic::IsImage() {return ((CComponentInstance*)this)->is_image;}
std::vector<CMaterialPublic*> CModelPublic::GetMaterials() {
    auto* model=(CModel*)this;std::vector<CMaterialPublic*> result;
    for(int i=0;i<model->getNumMaterials();++i) {
        auto* m=model->getMaterial(i);if(m && !m->IsMarkedDeleted())result.push_back((CMaterialPublic*)m);
    }return result;
}
std::vector<CComponentDefinitionPublic*> CModelPublic::GetDefinitions() {
    auto* model=(CModel*)this;std::vector<CComponentDefinitionPublic*> result;
    for(int i=0;i<model->getNumDefinition();++i) {
        auto* d=model->getDefinition(i);if(d && !d->IsMarkedDeleted())result.push_back((CComponentDefinitionPublic*)d);
    }return result;
}
bool CModelPublic::HasLayers() {
    for(auto* layer:((CModel*)this)->GetLayers())if(layer && !layer->IsMarkedDeleted())return true;
    return false;
}

void CEntityPublic::DeleteDetached() { ((CEntity*)this)->DeleteThis(); }
void CComponentPublic::AddLoadedEntity(CEntityPublic* entity) {
    ((CComponent*)this)->AddEntity((CEntity*)entity);
}
void CComponentPublic::ReleaseLoadedComponent() { ((CComponent*)this)->Release(); }
void CComponentDefinitionPublic::SetLoadedNamedSet(const std::wstring& name,
    const std::vector<CEntityPublic*>& entities) {
    std::wstring key(name);auto values=NativePointers<CEntity>(entities);
    ((CComponentDefinition*)this)->SetNamedSet(key,values);
}
CModelDataPublic* CModelDataPublic::Load(const std::vector<CMaterialPublic*>& materials,
    const std::vector<CLayerPublic*>& layers,
    const std::vector<CComponentDefinitionPublic*>& definitions,CComponentDefinitionPublic* top) {
    auto m=NativePointers<CMaterial>(materials);
    auto l=NativePointers<CLayer>(layers);
    auto d=NativePointers<CComponentDefinition>(definitions);
    return (CModelDataPublic*)CModelData::Load(m,l,d,(CComponentDefinition*)top);
}
void CModelDataPublic::Release() {delete (CModelData*)this;}

void CComponentPublic::FinishNativeLoad() { ((CComponent*)this)->MarkBoundingBoxDirty(); }

CLayerPublic* CDrawingElementPublic::GetLayer(){return (CLayerPublic*)((CDrawingElement*)this)->GetLayer();}
std::vector<CLayerPublic*> CModelPublic::GetLayers(){
    std::vector<CLayerPublic*> out;for(auto* p:((CModel*)this)->GetLayers())if(p&&!p->IsMarkedDeleted())out.push_back((CLayerPublic*)p);return out;
}
CLayerPublic* CLayerPublic::Load(const std::wstring& name,bool hidden,CMaterialPublic* material){
    std::wstring n(name);return (CLayerPublic*)CLayer::Load(n,hidden,(CMaterial*)material);
}
std::wstring CLayerPublic::GetName(){return ((CLayer*)this)->name;}
bool CLayerPublic::IsHide(){return ((CLayer*)this)->is_hide;}
CMaterialPublic* CLayerPublic::GetMaterial(){return (CMaterialPublic*)((CLayer*)this)->mtl;}
CCurvePublic* CEdgePublic::GetCurve(){return (CCurvePublic*)((CEdge*)this)->GetCurve();}
void CEdgePublic::SetLoadedCurve(CCurvePublic* curve){((CEdge*)this)->SetCurve((CCurve*)curve);}
bool CCurvePublic::IsArc(){return dynamic_cast<CArcCurve*>((CCurve*)this)!=nullptr;}
bool CCurvePublic::IsPolygon(){return ((CCurve*)this)->is_polygon;}
CEdgePublic* CCurvePublic::GetFirstEdge(){return (CEdgePublic*)((CCurve*)this)->GetFirstEdge();}
CEdgePublic* CCurvePublic::GetLastEdge(){return (CEdgePublic*)((CCurve*)this)->GetLastEdge();}
std::vector<CEdgePublic*> CCurvePublic::GetEdges(){
    std::vector<CEdgePublic*> out;for(auto* e:((CCurve*)this)->GetEdges())out.push_back((CEdgePublic*)e);return out;
}
void CCurvePublic::SetLoadedParent(CComponentPublic* parent){((CCurve*)this)->SetParentComponent((CComponent*)parent);}
SArcData CCurvePublic::GetArc(){
    auto* curve=dynamic_cast<CArcCurve*>((CCurve*)this);if(!curve)throw std::invalid_argument("Not an arc curve");
    auto& a=curve->arc;return {{a.center.x,a.center.y,a.center.z},{a.xaxis.x,a.xaxis.y,a.xaxis.z},
        {a.yaxis.x,a.yaxis.y,a.yaxis.z},{a.plane.x,a.plane.y,a.plane.z,a.plane.w},a.radius,a.start_angle,a.end_angle};
}
CCurvePublic* CCurvePublic::Load(const SArcData* data,CEdgePublic* first,CEdgePublic* last,int count,bool polygon){
    if(!data)return (CCurvePublic*)CCurve::Load((CEdge*)first,(CEdge*)last,count,polygon);
    CArc3d a;a.center=CVector3D(data->center.x,data->center.y,data->center.z);
    a.xaxis=CVector3D(data->xaxis.x,data->xaxis.y,data->xaxis.z);
    a.yaxis=CVector3D(data->yaxis.x,data->yaxis.y,data->yaxis.z);
    a.plane.x=data->plane.x;a.plane.y=data->plane.y;a.plane.z=data->plane.z;a.plane.w=data->plane.w;
    a.radius=data->radius;a.start_angle=data->start_angle;a.end_angle=data->end_angle;
    return (CCurvePublic*)CArcCurve::Load(&a,(CEdge*)first,(CEdge*)last,count,polygon);
}
