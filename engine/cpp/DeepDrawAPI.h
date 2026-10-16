#ifndef _DeepDrawAPI_h
#define _DeepDrawAPI_h

#ifdef _DLL_EXPORTS
#define DEEPDRAW_API _declspec(dllexport)
#else
#define DEEPDRAW_API _declspec(dllimport)

#endif

#include <string>
#include <vector>
#include <map>
#include <cstddef>

#define DEEPDRAW_CEntity				0
#define DEEPDRAW_CArcCurve				1
#define DEEPDRAW_CComponent				2
#define DEEPDRAW_CComponentBehavior		3
#define DEEPDRAW_CComponentDefinition	4
#define DEEPDRAW_CComponentInstance		5
#define DEEPDRAW_CConstructionGeometry	6
#define DEEPDRAW_CConstructionLine		7
#define DEEPDRAW_CConstructionPoint		8
#define DEEPDRAW_CCurve					9
#define DEEPDRAW_CDrawingElement		15
#define DEEPDRAW_CEdge					16
#define DEEPDRAW_CEdgeUse				17
#define DEEPDRAW_CFace					18
#define DEEPDRAW_CGroup					20
#define DEEPDRAW_CImage					21
#define DEEPDRAW_CLoop					24
#define DEEPDRAW_CMaterial				25
#define DEEPDRAW_CTexture				37
#define DEEPDRAW_CVertex				39

class CVertexPublic;
class CLayerPublic;
class CCurvePublic;
class CEdgePublic;
class CEdgeUsePublic;
class CLoopPublic;
class CFacePublic;
class TriangleMeshPublic;
class CComponentInstancePublic;
class CMaterialPublic;
class CTexturePublic;
class CFaceTextureCoordsPublic;


struct SVector3D
{
	double x, y, z;
};

struct SPlane
{
	double x, y, z, w;
};

struct SMatrix33
{
	double m[3][3];
};

struct SMatrix
{
	double m[16];
};

struct SMatrix2
{
	double scale;
	bool is_identity;
	bool is_orthogonal;
	double m[4][3];
};

struct SBoundingBox
{
	double min_x, max_x;
	double min_y, max_y;
	double min_z, max_z;
};

class DEEPDRAW_API CEntityPublic
{
public:
	CEntityPublic() {}
	~CEntityPublic() {}

	bool IsMarkedDeleted();
	// For entities not owned by a component/model.
	void DeleteDetached();

	int GetID();
	int GetType();
};

class DEEPDRAW_API IEntityIteratorPublic
{
public:
	IEntityIteratorPublic() {}
	~IEntityIteratorPublic() {}

	void Release();

	bool Next(CEntityPublic** out);
	bool Next(CVertexPublic** out);
	bool Next(CEdgePublic** out);
	bool Next(CEdgeUsePublic** out);
	bool Next(CLoopPublic** out);
	bool Next(CFacePublic** out);
	bool Next(CComponentInstancePublic** out);
};


class DEEPDRAW_API CDrawingElementPublic : public CEntityPublic
{
public:
	CDrawingElementPublic() {}
	~CDrawingElementPublic() {}

	bool HasLayer();
    CLayerPublic* GetLayer();

	bool IsHide();
};


class DEEPDRAW_API CVertexPublic : public CEntityPublic
{
public:
	CVertexPublic() {}
	~CVertexPublic() {}

	static CVertexPublic* Load(const SVector3D& position);

	static CVertexPublic* Create(SVector3D& p);
	void Release();

	SVector3D Pos();
};


class DEEPDRAW_API CEdgePublic : public CDrawingElementPublic
{
public:
	CEdgePublic() {}
	~CEdgePublic() {}

	bool HasCurve();
    CCurvePublic* GetCurve();
    void SetLoadedCurve(CCurvePublic* curve);

	static CEdgePublic* Load(bool hidden, CVertexPublic* start, CVertexPublic* end, bool soft, bool smooth);
    static CEdgePublic* Load(bool hidden, CLayerPublic* layer, CVertexPublic* start, CVertexPublic* end, bool soft, bool smooth);

	static CEdgePublic* Create(CVertexPublic* start, CVertexPublic* end);
	void Release();

	bool IsSoft();
	bool IsSmooth();

	CVertexPublic* GetStartVertex();
	CVertexPublic* GetEndVertex();

	//int GetNumAssociatedFaces();
	bool Isolated();
};

class DEEPDRAW_API CEdgeUsePublic : public CEntityPublic
{
public:
	CEdgeUsePublic() {}
	~CEdgeUsePublic() {}

	bool IsEdgeReversed();

	static CEdgeUsePublic* Load(CEdgePublic* edge, bool reversed);

	static CEdgeUsePublic* Create(CEdgePublic* _edge, bool reversed);
	void Release();

	CVertexPublic* GetStartVertex();
	CVertexPublic* GetEndVertex();
	CEdgePublic* GetEdge();
};

class DEEPDRAW_API CLoopPublic : public CEntityPublic
{
public:
	CLoopPublic() {}
	~CLoopPublic() {}

	bool IsOuterLoop();
	bool IsConvex();

	static CLoopPublic* Load(bool outer, bool convex, const std::vector<CEdgeUsePublic*>& edges);

	static CLoopPublic* Create();
	void Release();

	int GetNumEdges();
	IEntityIteratorPublic* EnumEdgeUse();
	IEntityIteratorPublic* EnumVertices();
};

class DEEPDRAW_API CFacePublic : public CDrawingElementPublic
{
public:
	CFacePublic() {}
	~CFacePublic() {}

	SPlane GetPlane();
	CFaceTextureCoordsPublic* GetTextureCoords();

	static CFacePublic* Load(bool hidden, const SPlane& plane, const std::vector<CLoopPublic*>& loops, CMaterialPublic* material, CFaceTextureCoordsPublic* coords);
    static CFacePublic* Load(bool hidden, CLayerPublic* layer, const SPlane& plane, const std::vector<CLoopPublic*>& loops, CMaterialPublic* material, CFaceTextureCoordsPublic* coords);

	static CFacePublic* Create();
	void Release();

	int GetNumLoops();
	CLoopPublic* GetOuterLoop();
	CLoopPublic* GetLoop(int idx);
	CMaterialPublic* GetMaterial();

	void ComputeMesh(TriangleMeshPublic* trimesh);

	IEntityIteratorPublic* EnumEdges();
};

class DEEPDRAW_API TriangleMeshPublic
{
public:
	TriangleMeshPublic() {}
	~TriangleMeshPublic() {}

	static TriangleMeshPublic* Create();
	void Release();

	int GetNumVertexIndices();
	int GetVertexIndex(int i);

	int GetNumVertices();
	SVector3D GetVertex(int i);
	SVector3D GetNormal(int i);
	SVector3D GetFrontUV(int i);
};

class DEEPDRAW_API CUVHelperPublic : public CDrawingElementPublic
{
public:
	CUVHelperPublic() {}
	~CUVHelperPublic() {}

	static CUVHelperPublic* Create(CFacePublic* face, CMaterialPublic* mtl);
	void Release();

	SVector3D ProjVertex(SVector3D& pos);
};


class DEEPDRAW_API CDibPublic : public CEntityPublic
{
public:
	CDibPublic() {}
	~CDibPublic() {}

	// Copies bytes; caller retains ownership. Empty data may be null.
	static CDibPublic* Load(const void* data, std::size_t length);

	static CDibPublic* Create();
	void Release();

	int GetLength();
	void GetData(void* buf, int buf_len);
};

class DEEPDRAW_API CTexturePublic : public CEntityPublic
{
public:
	CTexturePublic() {}
	~CTexturePublic() {}

	static CTexturePublic* Load(const std::wstring& name, double size_u, double size_v, CDibPublic* dib);

	static CTexturePublic* Create();
	void Release();

	std::wstring GetName();
	CDibPublic* GetDib();
	double GetSizeU();
	double GetSizeV();
};

class DEEPDRAW_API CMaterialPublic : public CEntityPublic
{
public:
	CMaterialPublic() {}
	~CMaterialPublic() {}

	static CMaterialPublic* Load(const std::wstring& name, const SVector3D& color, bool use_opacity, double opacity, CTexturePublic* texture);

	static CMaterialPublic* Create();
	void Release();

	std::wstring GetName();
	SVector3D GetColor();
	bool IsOpacity();
	double GetOpacity();
	CTexturePublic* GetTexture();
};



class DEEPDRAW_API CComponentPublic : public CDrawingElementPublic
{
public:
	CComponentPublic() {}
	~CComponentPublic() {}

	void AddLoadedEntity(CEntityPublic* entity);
	void ReleaseLoadedComponent();
	void FinishNativeLoad();

	static CComponentPublic* Create();
	void Release();

	SBoundingBox GetBoundingBox();

	int GetNumEntities();
	int GetNumChildren();
	IEntityIteratorPublic* EnumEntities();
	IEntityIteratorPublic* EnumChildren();
};


class DEEPDRAW_API CComponentDefinitionPublic : public CComponentPublic
{
public:
	CComponentDefinitionPublic() {}
	~CComponentDefinitionPublic() {}

	void SetLoadedNamedSet(const std::wstring& name, const std::vector<CEntityPublic*>& entities);

	std::wstring GetAgentHint();
	std::wstring GetFilePath();
	bool IsDynamicComponent();
	std::wstring GetDynamicComponent();
	std::map<std::wstring, std::vector<CEntityPublic*>> GetNamedSets();

	static CComponentDefinitionPublic* Load(const std::wstring& name, const std::wstring& description,
		const std::wstring& agent_hint, const std::wstring& file_path,
		const std::vector<CEntityPublic*>& entities,
		const std::map<std::wstring, std::vector<CEntityPublic*>>& named_sets,
		bool is_dynamic_comp, const std::wstring& dynamic_comp);

	static CComponentDefinitionPublic* Create();
	void Release();

	std::wstring GetName();
	std::wstring GetDescription();
};


class DEEPDRAW_API CComponentInstancePublic : public CDrawingElementPublic
{
public:
	CComponentInstancePublic() {}
	~CComponentInstancePublic() {}

	std::wstring GetName();
	bool IsGroup();
	bool IsImage();

	static CComponentInstancePublic* Load(bool hidden, const std::wstring& name, const SMatrix2& transform,
		CMaterialPublic* material, CComponentDefinitionPublic* definition, bool is_group, bool is_image);
    static CComponentInstancePublic* Load(bool hidden, CLayerPublic* layer, const std::wstring& name, const SMatrix2& transform,
        CMaterialPublic* material, CComponentDefinitionPublic* definition, bool is_group, bool is_image);

	static CComponentInstancePublic* Create();
	void Release();

	CComponentDefinitionPublic* GetDefinition();
	SMatrix GetTransform();
	SMatrix2 GetTransform2();
	CMaterialPublic* GetMaterial();
};


class DEEPDRAW_API GeomFilterVolumePublic
{
public:
	GeomFilterVolumePublic() {}
	~GeomFilterVolumePublic() {}

	bool TestBoundingBox(SBoundingBox& bbox);
};

class DEEPDRAW_API CModelPublic
{
public:
	CModelPublic() {}
	~CModelPublic() {}

	std::vector<CMaterialPublic*> GetMaterials();
    std::vector<CLayerPublic*> GetLayers();
	std::vector<CComponentDefinitionPublic*> GetDefinitions();
	bool HasLayers();

	static CModelPublic* Create();
	static CModelPublic* GetAcitveModel();
	void Release();

	CComponentPublic* GetTopComponent();
	std::vector<CEntityPublic*> GetSelection();
};


// Native loading bridges. No Python or cereal types cross this API.
class DEEPDRAW_API CFaceTextureCoordsPublic : public CEntityPublic
{
public:
    static CFaceTextureCoordsPublic* Load(const SMatrix33& matrix);
    SMatrix33 GetFrontTextureCoords();
};

class DEEPDRAW_API CNamedEntitySetsPublic : public CEntityPublic
{
public:
    using Map = std::map<std::wstring, std::vector<CEntityPublic*>>;
    static CNamedEntitySetsPublic* Load(const Map& sets);
};

// Container wrapper only; the loaded entity graph is owned separately until adopted.
struct SArcData {
    SVector3D center,xaxis,yaxis;
    SPlane plane;
    double radius,start_angle,end_angle;
};
class DEEPDRAW_API CLayerPublic : public CEntityPublic {
public:
    static CLayerPublic* Load(const std::wstring& name,bool hidden,CMaterialPublic* material);
    std::wstring GetName(); bool IsHide(); CMaterialPublic* GetMaterial();
};
class DEEPDRAW_API CCurvePublic : public CEntityPublic {
public:
    static CCurvePublic* Load(const SArcData* arc,CEdgePublic* first,CEdgePublic* last,int count,bool polygon);
    bool IsArc(); bool IsPolygon(); SArcData GetArc();
    CEdgePublic* GetFirstEdge(); CEdgePublic* GetLastEdge();
    std::vector<CEdgePublic*> GetEdges();
    void SetLoadedParent(CComponentPublic* parent);
};
class DEEPDRAW_API CModelDataPublic
{
public:
    static CModelDataPublic* Load(const std::vector<CMaterialPublic*>& materials,
        const std::vector<CLayerPublic*>& layers,
        const std::vector<CComponentDefinitionPublic*>& definitions,
        CComponentDefinitionPublic* top);
    void Release();
};

#endif
