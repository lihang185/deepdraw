#ifndef _MODEL_H
#define _MODEL_H

#include <tchar.h>
#include <vector>
#include <string>
#include <map>
#include <memory>

#define SUAPI(ptr) {ptr}
#define cast_SUEntity(ref) ((SUEntity*)ref.ptr)
#define cast_SUAttributeDictionary(ref) ((SUAttributeDictionary*)ref.ptr)
#define cast_SUDrawingElement(ref) ((SUDrawingElement*)ref.ptr)
#define cast_SUVertex(ref) ((SUVertex*)ref.ptr)
#define cast_SUEdge(ref) ((SUEdge*)ref.ptr)
#define cast_SUEdgeUse(ref) ((SUEdgeUse*)ref.ptr)
#define cast_SULoop(ref) ((SULoop*)ref.ptr)
#define cast_SUFace(ref) ((SUFace*)ref.ptr)
#define cast_SUTexture(ref) ((SUTexture*)ref.ptr)
#define cast_SUMaterial(ref) ((SUMaterial*)ref.ptr)
#define cast_SULayer(ref) ((SULayer*)ref.ptr)
#define cast_SUEntities(ref) ((SUEntities*)ref.ptr)
#define cast_SUComponentInstance(ref) ((SUComponentInstance*)ref.ptr)
#define cast_SUComponentDefinition(ref) ((SUComponentDefinition*)ref.ptr)


class SUAttributeDictionary;
class SULoop;
class SUFace;
class SUTexture;
class SUMaterial;
class SULayer;
class SUComponentInstance;
class SUGeometryInput;


struct CVector2D {
	CVector2D() : x(0), y(0) {}
	CVector2D(double ix, double iy) : x(ix), y(iy) {}

	double x;
	double y;
};

struct CVector3D {
	CVector3D() : x(0), y(0), z(0) {}
	CVector3D(double ix, double iy, double iz) : x(ix), y(iy), z(iz) {}

	CVector3D operator+(CVector3D& R);
	CVector3D operator-(CVector3D& R);
	CVector3D operator*(double scale);
	CVector3D operator-();

	double DotProduct(CVector3D& R);
	CVector3D CrossProduct(CVector3D& R);
	CVector3D MoveForward(CVector3D& dir, double dist);


	double x;
	double y;
	double z;
};

class CPlane {
public:
	CPlane() :x(0), y(0), z(0), w(1) {}
	CPlane(double _x, double _y, double _z, double _w) :x(_x), y(_y), z(_z), w(_w) {}
	CPlane(CVector3D& _p, double _w) :x(_p.x), y(_p.y), z(_p.z), w(_w) {}
	CPlane(CVector3D& normal, CVector3D& orig);
	~CPlane() {}
	CVector3D GetNormal();

	double IntersectWithRay(CVector3D& orig, CVector3D& dir);

	double x;
	double y;
	double z;
	double w;
};

class CMatrix33 {
public:
	CMatrix33();
	double get(int i, int j) { return m[i][j]; }
	std::vector<double> GetData();
private:
	double m[3][3];
};

struct CMatrix43 {
	CMatrix43();
	~CMatrix43() {}

	double m[4][3];
	double scale;
	bool is_identity;
	bool flags;
};

struct CMatrix {
	CMatrix();
	~CMatrix() {}

	CVector3D TransformPoint(CVector3D& point);
	CMatrix Multiply(CMatrix& R);
	CMatrix Multiply2(CMatrix& R);

	std::vector<double> GetData();
	static CMatrix NewFromData(std::vector<double>& data);

	static CMatrix NewFromTranslate(CVector3D& translate);
	static CMatrix NewFromRotate(CVector3D& rotate);
	static CMatrix NewFromScale(CVector3D& scale);

	double m[4][4];
};

class SUEntity
{
public:
	SUEntity() {}
	virtual ~SUEntity() {}

	int GetType();
	int GetID();

	int GetNumAttributeDictionaries();
	std::vector<SUAttributeDictionary*> GetAttributeDictionaries();
};

class SUAttributeDictionary
{
public:
	SUAttributeDictionary() {}
	~SUAttributeDictionary() {}

	std::wstring GetName();
	int GetNumKeys();
	std::vector<std::wstring> GetKeys();
};

class SUDrawingElement : public SUEntity
{
public:
	SUDrawingElement() {}
	~SUDrawingElement() {}

	bool GetHidden();
	SULayer* GetLayer();
};

class SUVertex : public SUEntity
{
public:
	SUVertex() {}
	~SUVertex() {}

	CVector3D GetPosition();

};


class SUEdge : public SUDrawingElement
{
public:
	SUEdge() {}
	~SUEdge() {}

	SUVertex* GetStartVertex();
	SUVertex* GetEndVertex();
	bool GetSoft();
	bool GetSmooth();
};

class SUEdgeUse : public SUEntity
{
public:
	SUEdgeUse() {}
	~SUEdgeUse() {}

	SUEdge* GetEdge();
	SUVertex* GetStartVertex();
	CVector3D GetStartVertexNormal();
	SUVertex* GetEndVertex();
	CVector3D GetEndVertexNormal();
	bool IsReversed();

	SUFace* GetFace();
	SULoop* GetLoop();
};

class SULoop : public SUEntity
{
public:
	SULoop() {}
	~SULoop() {}

	int GetNumVertices();
	std::vector<SUVertex*> GetVertices();
	std::vector<SUEdge*> GetEdges();
	std::vector<SUEdgeUse*> GetEdgeUses();
	bool IsOuterLoop();
	bool IsConvex();


	SUFace* GetFace();
};



class SUUVHelper;

class SUFace : public SUDrawingElement
{
public:
	SUFace() {}
	~SUFace() {}

	SULoop* GetOuterLoop();
	std::vector<SULoop*> GetInnerLoops();

	CPlane GetPlane();
	CVector3D GetNormal();
	SUMaterial* GetFrontMaterial();
	void SetFrontMaterial(SUMaterial* mtl);
	SUMaterial* GetBackMaterial();
	void SetBackMaterial(SUMaterial* mtl);

	SUUVHelper* GetUVHelper();
};

class SUUVHelper
{
public:
	SUUVHelper() {}
	~SUUVHelper() {}

	void Release();

	CMatrix33 GetFrontTextureMatrix();
	CMatrix33 GetBackTextureMatrix();

private:
	CMatrix43 m1;
	CMatrix43 m2;
	CMatrix33 tm1;
	CMatrix33 tm2;
	CPlane unknow1;
	CPlane unknow2;
};



class SUMaterial : public SUEntity
{
public:
	SUMaterial() {}
	~SUMaterial() {}

	static SUMaterial* Create();

	std::wstring GetName();
	void SetName(std::string& name);
	SUTexture* GetTexture();
	void SetTexture(SUTexture* tex);
	CVector3D GetColor();
	void SetColor(CVector3D& color);
	bool GetUseOpacity();
	void SetUseOpacity(bool value);
	double GetOpacity();
	void SetOpacity(double value);
};

class SUTexture : public SUEntity
{
public:
	SUTexture() {}
	~SUTexture() {}

	static SUTexture* CreateFromFile(std::string& file_path, double u_size, double v_size);

	std::wstring GetFileName();
	double GetScaleU();
	double GetScaleV();

	bool WriteToFile(std::string filepath);
	int GetImageDataSize();
	std::vector<char> GetImageData();
};

class SULayer : public SUEntity
{
public:
	SULayer() {}
	~SULayer() {}

	std::wstring GetName();
	void SetName(std::string& name);
	bool GetVisable();
	void SetVisable(bool vis);
};




class SUEntities : public SUDrawingElement
{
public:
	SUEntities() {}
	~SUEntities() {}

	int GetNumEdges();
	int GetNumFaces();
	int GetNumInstances();
	int GetNumGroups();
	int GetNumImages();
	std::vector<SUEdge*> GetEdges();
	std::vector<SUFace*> GetFaces();
	std::vector<SUComponentInstance*> GetInstances();
	std::vector<SUComponentInstance*> GetGroups();
	std::vector<SUComponentInstance*> GetImages();

	void Fill(SUGeometryInput* geom, bool weld_vertices);
	void AddEdge(SUEdge* edge);
	void AddFace(SUFace* face);
	void AddInstance(SUComponentInstance* inst);
};

class SUComponentDefinition : public SUEntities
{
public:
	SUComponentDefinition() {}
	~SUComponentDefinition() {}
	static SUComponentDefinition* Create();

	SUEntities* GetEntities();
	std::wstring GetName();
	void SetName(std::string& name);
	std::wstring GetDescription();
	void SetDescription(std::string& desc);

	SUComponentInstance* CreateInstance();

	bool IsInternal();
	std::wstring GetPath();
};

class SUComponentInstance : public SUDrawingElement
{
public:
	SUComponentInstance() {}
	~SUComponentInstance() {}

	std::wstring GetName();
	SUComponentDefinition* GetDefinition();
	CMatrix GetTransform();
	void SetTransform(CMatrix& m);
	SUMaterial* GetMaterial();
	void SetMaterial(SUMaterial* mtl);
};

class SULoopInput
{
public:
	SULoopInput() {}
	~SULoopInput() {}

	static SULoopInput* Create();
	void Release();

	void AddVertexIndex(int vertex_index);
	void EdgeSetHidden(int edge_index, bool hidden);
	void EdgeSetSoft(int edge_index, bool soft);
	void EdgeSetSmooth(int edge_index, bool smooth);

};

class SUTextureCoordInput
{
public:
	SUTextureCoordInput();
	~SUTextureCoordInput();

	void AddTexCoord(int vertex_index, CVector2D& uv);

private:
	int num_uv_coords;
	CVector2D uv_coords[4];
	int vertex_indices[4];

	friend class SUGeometryInput;
};

class SUGeometryInput
{
public:
	SUGeometryInput() {}
	~SUGeometryInput() {}

	static SUGeometryInput* Create();
	void Release();

	void AddVertex(CVector3D& point);
	int AddEdge(int v0_idx, int v1_idx);
	void EdgeSetSoft(int edge_idx, bool soft);
	void EdgeSetSmooth(int edge_idx, bool smooth);
	// 如果成功，loop自动释放
	int AddFace(SULoopInput* loop);
	void FaceAddInnerLoop(int face_idx, SULoopInput* loop);
	void FaceSetFrontMaterial(int face_idx, SUMaterial* mtl, SUTextureCoordInput* texcoord);
	void FaceSetBackMaterial(int face_idx, SUMaterial* mtl, SUTextureCoordInput* texcoord);
};

class SUModel
{
public:
	SUModel() {}
	~SUModel() {}

	static SUModel* Create();
	void Release();
	unsigned long long GetPtr();

	bool SaveToFile(std::string& filepath);
	bool SaveToFile2017(std::string& filepath);
	bool SaveToFile2015(std::string& filepath);

	SUEntities* GetEntities();
	std::string GetName();

	std::vector<SUMaterial*> GetMaterialList();
	std::vector<SUComponentDefinition*> GetComponentDefinitionList();
	std::vector<SUComponentDefinition*> GetGroupDefinitionList();
	std::vector<SULayer*> GetLayers();

	void AddComponentDefinition(SUComponentDefinition* comp);
	void AddMaterial(SUMaterial* mat);

	static SUModel* LoadFromFile(std::string file_path);
	static SUModel* cLoadFromBuffer(const unsigned char* buffer, size_t buffer_size);
};

#endif // _MODEL_H
