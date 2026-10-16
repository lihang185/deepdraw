#ifndef _DeepDrawAPI_h
#define _DeepDrawAPI_h

#ifdef _DLL_EXPORTS
#define DEEPDRAW_API _declspec(dllexport)
#else
#define DEEPDRAW_API _declspec(dllimport)
#endif

#include <string>
#include <vector>

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
class CEdgePublic;
class CEdgeUsePublic;
class CLoopPublic;
class CFacePublic;
class TriangleMeshPublic;
class CComponentInstancePublic;
class CMaterialPublic;


struct SVector3D
{
	double x, y, z;
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
    bool IsMarkedDeleted();
	CEntityPublic() {}
	~CEntityPublic() {}

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
    bool HasLayer();
	CDrawingElementPublic() {}
	~CDrawingElementPublic() {}

	bool IsHide();
};


class DEEPDRAW_API CVertexPublic : public CEntityPublic
{
public:
	CVertexPublic() {}
	~CVertexPublic() {}

	static CVertexPublic* Create(SVector3D& p);
	void Release();

	SVector3D Pos();
};


class DEEPDRAW_API CEdgePublic : public CDrawingElementPublic
{
public:
	CEdgePublic() {}
	~CEdgePublic() {}

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

	static CModelPublic* Create();
	static CModelPublic* GetAcitveModel();
	void Release();

	CComponentPublic* GetTopComponent();
	std::vector<CEntityPublic*> GetSelection();
};

#endif
