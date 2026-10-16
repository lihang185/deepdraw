#include <tchar.h>
#include <stdexcept>
#define assert(test) do { if (!(test)) throw std::runtime_error("SketchUp SDK: " #test); } while (false)
#include <vector>
#include <set>
#include <string>
#include <stdio.h>
#include <stdarg.h>
#include <map>
#include "model.h"
#include <windows.h>


#include <SketchUpAPI/sketchup.h>

const double min_tol = 1e-10;

//=====================
//  wstring
//
//=====================
std::wstring SUStringToSTLString(SUStringRef string)
{
    size_t length = 0, copied = 0;
    std::wstring value;
    if (SUStringGetUTF16Length(string, &length) == SU_ERROR_NONE) {
        value.resize(length + 1);
        if (SUStringGetUTF16(string, value.size(), (unichar*)value.data(), &copied) == SU_ERROR_NONE)
            value.resize(length);
        else value.clear();
    }
    SUStringRelease(&string);
    return value;
}

//=====================
//  CVector3D
//
//=====================
CVector3D CVector3D::operator*(double scale)
{
	CVector3D out;
	out.x = x * scale;
	out.y = y * scale;
	out.z = z * scale;
	return out;
}

CVector3D CVector3D::operator+(CVector3D& R)
{
	CVector3D out;
	out.x = x + R.x;
	out.y = y + R.y;
	out.z = z + R.z;
	return out;
}

CVector3D CVector3D::operator-(CVector3D& R)
{
	CVector3D out;
	out.x = x - R.x;
	out.y = y - R.y;
	out.z = z - R.z;
	return out;
}

CVector3D CVector3D::operator-()
{
	CVector3D out;
	out.x = -x;
	out.y = -y;
	out.z = -z;
	return out;
}

double CVector3D::DotProduct(CVector3D& R)
{
	return x * R.x + y * R.y + z * R.z;
}

CVector3D CVector3D::CrossProduct(CVector3D& R)
{
	CVector3D out;
	out.x = y * R.z - z * R.y;
	out.y = z * R.x - x * R.z;
	out.z = x * R.y - y * R.x;
	return out;
}

CVector3D CVector3D::MoveForward(CVector3D& dir, double dist)
{
	CVector3D out;
	out.x = x + dir.x * dist;
	out.y = y + dir.y * dist;
	out.z = z + dir.z * dist;
	return out;
}

//=====================
//  CVector4D
//
//=====================
CPlane::CPlane(CVector3D& normal, CVector3D& orig)
{
	x = normal.x;
	y = normal.y;
	z = normal.z;
	w = -orig.DotProduct(normal);
}

CVector3D CPlane::GetNormal()
{
	return CVector3D(x, y, z);
}

double CPlane::IntersectWithRay(CVector3D& orig, CVector3D& dir)
{
	double dot_dir, dot_orig, s;

	dot_dir = x * dir.x + y * dir.y + z * dir.z;
	dot_orig = x * orig.x + y * orig.y + z * orig.z;

	s = (dot_orig + w) / -dot_dir;

	return s;
}

//=====================
//  CMatrix33
//
//=====================
CMatrix33::CMatrix33()
{
	m[0][0] = 1.0;
	m[0][1] = 0.0;
	m[0][2] = 0.0;

	m[1][0] = 0.0;
	m[1][1] = 1.0;
	m[1][2] = 0.0;

	m[2][0] = 0.0;
	m[2][1] = 0.0;
	m[2][2] = 1.0;
}

std::vector<double> CMatrix33::GetData()
{
	std::vector<double> data(9);
	data[0] = m[0][0];
	data[1] = m[0][1];
	data[2] = m[0][2];
	data[3] = m[1][0];
	data[4] = m[1][1];
	data[5] = m[1][2];
	data[6] = m[2][0];
	data[7] = m[2][1];
	data[8] = m[2][2];
	return data;
}

//=====================
//  CMatrix43
//
//=====================
CMatrix43::CMatrix43()
{
	m[0][0] = 1.0;
	m[0][1] = 0.0;
	m[0][2] = 0.0;

	m[1][0] = 0.0;
	m[1][1] = 1.0;
	m[1][2] = 0.0;

	m[2][0] = 0.0;
	m[2][1] = 0.0;
	m[2][2] = 1.0;

	m[3][0] = 0.0;
	m[3][1] = 0.0;
	m[3][2] = 0.0;

	scale = 1.0;
	is_identity = true;
	flags = true;
}


//=====================
//  CMatrix
//
//=====================
CMatrix::CMatrix()
{
	m[0][0] = 1.0;
	m[0][1] = 0.0;
	m[0][2] = 0.0;
	m[0][3] = 0.0;

	m[1][0] = 0.0;
	m[1][1] = 1.0;
	m[1][2] = 0.0;
	m[1][3] = 0.0;

	m[2][0] = 0.0;
	m[2][1] = 0.0;
	m[2][2] = 1.0;
	m[2][3] = 0.0;

	m[3][0] = 0.0;
	m[3][1] = 0.0;
	m[3][2] = 0.0;
	m[3][3] = 1.0;
}

CVector3D CMatrix::TransformPoint(CVector3D& R)
{
	CVector3D out;
	out.x = m[0][0] * R.x + m[1][0] * R.y + m[2][0] * R.z + m[3][0];
	out.y = m[0][1] * R.x + m[1][1] * R.y + m[2][1] * R.z + m[3][1];
	out.z = m[0][2] * R.x + m[1][2] * R.y + m[2][2] * R.z + m[3][2];
	return out;
}

CMatrix CMatrix::Multiply2(CMatrix& R)
{
	CMatrix out;
	out.m[0][0] = m[0][0] * R.m[0][0] + m[1][0] * R.m[0][1] + m[2][0] * R.m[0][2];
	out.m[0][1] = m[0][1] * R.m[0][0] + m[1][1] * R.m[0][1] + m[2][1] * R.m[0][2];
	out.m[0][2] = m[0][2] * R.m[0][0] + m[1][2] * R.m[0][1] + m[2][2] * R.m[0][2];
	out.m[0][3] = 0.0;

	out.m[1][0] = m[0][0] * R.m[1][0] + m[1][0] * R.m[1][1] + m[2][0] * R.m[1][2];
	out.m[1][1] = m[0][1] * R.m[1][0] + m[1][1] * R.m[1][1] + m[2][1] * R.m[1][2];
	out.m[1][2] = m[0][2] * R.m[1][0] + m[1][2] * R.m[1][1] + m[2][2] * R.m[1][2];
	out.m[1][3] = 0.0;

	out.m[2][0] = m[0][0] * R.m[2][0] + m[1][0] * R.m[2][1] + m[2][0] * R.m[2][2];
	out.m[2][1] = m[0][1] * R.m[2][0] + m[1][1] * R.m[2][1] + m[2][1] * R.m[2][2];
	out.m[2][2] = m[0][2] * R.m[2][0] + m[1][2] * R.m[2][1] + m[2][2] * R.m[2][2];
	out.m[2][3] = 0.0;

	out.m[3][0] = m[0][0] * R.m[3][0] + m[1][0] * R.m[3][1] + m[2][0] * R.m[3][2] + m[3][0];
	out.m[3][1] = m[0][1] * R.m[3][0] + m[1][1] * R.m[3][1] + m[2][1] * R.m[3][2] + m[3][1];
	out.m[3][2] = m[0][2] * R.m[3][0] + m[1][2] * R.m[3][1] + m[2][2] * R.m[3][2] + m[3][2];
	out.m[3][3] = 1.0;
	return out;
}

CMatrix CMatrix::Multiply(CMatrix& R)
{
	CMatrix out;
	out.m[0][0] = m[0][0] * R.m[0][0] + m[1][0] * R.m[0][1] + m[2][0] * R.m[0][2] + m[3][0] * R.m[0][3];
	out.m[0][1] = m[0][1] * R.m[0][0] + m[1][1] * R.m[0][1] + m[2][1] * R.m[0][2] + m[3][1] * R.m[0][3];
	out.m[0][2] = m[0][2] * R.m[0][0] + m[1][2] * R.m[0][1] + m[2][2] * R.m[0][2] + m[3][2] * R.m[0][3];
	out.m[0][3] = m[0][3] * R.m[0][0] + m[1][3] * R.m[0][1] + m[2][3] * R.m[0][2] + m[3][3] * R.m[0][3];

	out.m[1][0] = m[0][0] * R.m[1][0] + m[1][0] * R.m[1][1] + m[2][0] * R.m[1][2] + m[3][0] * R.m[1][3];
	out.m[1][1] = m[0][1] * R.m[1][0] + m[1][1] * R.m[1][1] + m[2][1] * R.m[1][2] + m[3][1] * R.m[1][3];
	out.m[1][2] = m[0][2] * R.m[1][0] + m[1][2] * R.m[1][1] + m[2][2] * R.m[1][2] + m[3][2] * R.m[1][3];
	out.m[1][3] = m[0][3] * R.m[1][0] + m[1][3] * R.m[1][1] + m[2][3] * R.m[1][2] + m[3][3] * R.m[1][3];

	out.m[2][0] = m[0][0] * R.m[2][0] + m[1][0] * R.m[2][1] + m[2][0] * R.m[2][2] + m[3][0] * R.m[2][3];
	out.m[2][1] = m[0][1] * R.m[2][0] + m[1][1] * R.m[2][1] + m[2][1] * R.m[2][2] + m[3][1] * R.m[2][3];
	out.m[2][2] = m[0][2] * R.m[2][0] + m[1][2] * R.m[2][1] + m[2][2] * R.m[2][2] + m[3][2] * R.m[2][3];
	out.m[2][3] = m[0][3] * R.m[2][0] + m[1][3] * R.m[2][1] + m[2][3] * R.m[2][2] + m[3][3] * R.m[2][3];

	out.m[3][0] = m[0][0] * R.m[3][0] + m[1][0] * R.m[3][1] + m[2][0] * R.m[3][2] + m[3][0] * R.m[3][3];
	out.m[3][1] = m[0][1] * R.m[3][0] + m[1][1] * R.m[3][1] + m[2][1] * R.m[3][2] + m[3][1] * R.m[3][3];
	out.m[3][2] = m[0][2] * R.m[3][0] + m[1][2] * R.m[3][1] + m[2][2] * R.m[3][2] + m[3][2] * R.m[3][3];
	out.m[3][3] = m[0][3] * R.m[3][0] + m[1][3] * R.m[3][1] + m[2][3] * R.m[3][2] + m[3][3] * R.m[3][3];
	return out;
}



std::vector<double> CMatrix::GetData()
{
	std::vector<double> data(16);
	data[0] = m[0][0];
	data[1] = m[0][1];
	data[2] = m[0][2];
	data[3] = m[0][3];

	data[4] = m[1][0];
	data[5] = m[1][1];
	data[6] = m[1][2];
	data[7] = m[1][3];

	data[8] = m[2][0];
	data[9] = m[2][1];
	data[10] = m[2][2];
	data[11] = m[2][3];

	data[12] = m[3][0];
	data[13] = m[3][1];
	data[14] = m[3][2];
	data[15] = m[3][3];
	return data;
}
CMatrix CMatrix::NewFromData(std::vector<double>& data)
{
	CMatrix out;
	out.m[0][0] = data[0];
	out.m[0][1] = data[1];
	out.m[0][2] = data[2];
	out.m[0][3] = data[3];

	out.m[1][0] = data[4];
	out.m[1][1] = data[5];
	out.m[1][2] = data[6];
	out.m[1][3] = data[7];

	out.m[2][0] = data[8];
	out.m[2][1] = data[9];
	out.m[2][2] = data[10];
	out.m[2][3] = data[11];

	out.m[3][0] = data[12];
	out.m[3][1] = data[13];
	out.m[3][2] = data[14];
	out.m[3][3] = data[15];
	return out;
}

CMatrix CMatrix::NewFromTranslate(CVector3D& translate)
{
	CMatrix out;
	out.m[3][0] = translate.x;
	out.m[3][1] = translate.y;
	out.m[3][2] = translate.z;
	return out;
}

CMatrix CMatrix::NewFromRotate(CVector3D& rotate)
{
	CMatrix out;
	return out;
}

CMatrix CMatrix::NewFromScale(CVector3D& scale)
{
	CMatrix out;
	return out;
}

//=====================
//  SUEntity
//
//=====================
int SUEntity::GetType()
{
	SURefType rtype;

	rtype = SUEntityGetType(SUAPI(this));
	if (rtype == SURefType_Edge) {
		return 16;
	}
	else if (rtype == SURefType_Face) {
		return 18;
	}
	return 0;

}

int SUEntity::GetID()
{
	int id=0;
	SUEntityGetID(SUAPI(this), &id);
	return id;
}


int SUEntity::GetNumAttributeDictionaries()
{
	size_t count = 0;
	SUEntityGetNumAttributeDictionaries(SUAPI(this), &count);
	return (int)count;
}

std::vector<SUAttributeDictionary*> SUEntity::GetAttributeDictionaries()
{
	size_t count = 0;
	SUEntityGetNumAttributeDictionaries(SUAPI(this), &count);

	std::vector<SUAttributeDictionary*> dicts;

	if (count > 0) {
		dicts.resize(count);
		size_t copy_number;
		SUResult result = SUEntityGetAttributeDictionaries(SUAPI(this), count, (SUAttributeDictionaryRef*)dicts.data(), &copy_number);
		if (result == SU_ERROR_NONE && copy_number == count) {
			return dicts;
		}
	}
	return dicts;
}


//=====================
//  SUAttributeDictionary
//
//=====================
std::wstring SUAttributeDictionary::GetName()
{
	SUResult result;
	SUStringRef name = SU_INVALID;
	SUStringCreate(&name);

	std::wstring out_str;

	result = SUAttributeDictionaryGetName(SUAPI(this), &name);
	if (result == SU_ERROR_NONE) {
		out_str = SUStringToSTLString(name);
	}
	return out_str;
}

int SUAttributeDictionary::GetNumKeys()
{
	size_t count = 0;
	SUAttributeDictionaryGetNumKeys(SUAPI(this), &count);
	return (int)count;
}

std::vector<std::wstring> SUAttributeDictionary::GetKeys()
{
	SUResult result;
	size_t count = 0;
	SUAttributeDictionaryGetNumKeys(SUAPI(this), &count);

	std::vector<std::wstring> keys_out;

	if (count > 0) {
		std::vector<SUStringRef> keys;
		keys.resize(count);
		for (int i = 0; i < count; i++) {
			SUStringCreate(&keys[i]);
		}
		size_t copy_number;
		result = SUAttributeDictionaryGetKeys(SUAPI(this), count, (SUStringRef*)keys.data(), &copy_number);
		
		
		
		for (int i = 0; i < count; i++) {
			std::wstring key_name = SUStringToSTLString(keys[i]);
			keys_out.push_back(key_name);
		}
	}
	return keys_out;
}

//=====================
//  SUDrawingElement
//
//=====================
bool SUDrawingElement::GetHidden()
{
	bool value;
	SUResult result = SUDrawingElementGetHidden(SUAPI(this), &value);
	return value;
}

SULayer* SUDrawingElement::GetLayer()
{
	SULayerRef layer;
	SUResult result = SUDrawingElementGetLayer(SUAPI(this), &layer);
	return cast_SULayer(layer);
}

//=====================
//  SUVertex
//
//=====================
CVector3D SUVertex::GetPosition()
{
	SUPoint3D pos;
	SUVertexGetPosition(SUAPI(this), &pos);
	return CVector3D(pos.x, pos.y, pos.z);
}

//=====================
//  SUEdge
//
//=====================
SUVertex* SUEdge::GetStartVertex()
{
	SUVertexRef vertex = SU_INVALID;
	SUEdgeGetStartVertex(SUAPI(this), &vertex);
	return cast_SUVertex(vertex);
}

SUVertex* SUEdge::GetEndVertex()
{
	SUVertexRef vertex = SU_INVALID;
	SUEdgeGetEndVertex(SUAPI(this), &vertex);
	return cast_SUVertex(vertex);
}

bool SUEdge::GetSoft()
{
	bool value;
	SUEdgeGetSoft(SUAPI(this), &value);
	return value;
}

bool SUEdge::GetSmooth()
{
	bool value;
	SUEdgeGetSmooth(SUAPI(this), &value);
	return value;
}

//=====================
//  SUEdgeUse
//
//=====================
SUEdge* SUEdgeUse::GetEdge()
{
	SUEdgeRef edge = SU_INVALID;
	SUEdgeUseGetEdge(SUAPI(this),&edge);
	return cast_SUEdge(edge);
}

SUVertex* SUEdgeUse::GetStartVertex()
{
	SUVertexRef vertex = SU_INVALID;
	SUEdgeUseGetStartVertex(SUAPI(this), &vertex);
	return cast_SUVertex(vertex);
}

CVector3D SUEdgeUse::GetStartVertexNormal()
{
	SUVector3D n;
	SUEdgeUseGetStartVertexNormal(SUAPI(this), &n);
	return CVector3D(n.x, n.y, n.z);
}


SUVertex* SUEdgeUse::GetEndVertex()
{
	SUVertexRef vertex = SU_INVALID;
	SUEdgeUseGetEndVertex(SUAPI(this), &vertex);
	return cast_SUVertex(vertex);
}


CVector3D SUEdgeUse::GetEndVertexNormal()
{
	SUVector3D n;
	SUEdgeUseGetEndVertexNormal(SUAPI(this), &n);
	return CVector3D(n.x, n.y, n.z);
}

bool SUEdgeUse::IsReversed()
{
	bool value = false;
	SUEdgeUseIsReversed(SUAPI(this), &value);
	return value;
}


SUFace* SUEdgeUse::GetFace()
{
	SUFaceRef face = SU_INVALID;
	SUEdgeUseGetFace(SUAPI(this), &face);
	return cast_SUFace(face);
}

SULoop* SUEdgeUse::GetLoop()
{
	SULoopRef loop = SU_INVALID;
	SUEdgeUseGetLoop(SUAPI(this), &loop);
	return cast_SULoop(loop);
}

//=====================
//  SULoop
//
//=====================
int SULoop::GetNumVertices()
{
	size_t count = 0;
	SULoopGetNumVertices(SUAPI(this), &count);
	return (int)count;
}

std::vector<SUVertex*> SULoop::GetVertices()
{
	SUResult result;

	size_t count = 0;
	SULoopGetNumVertices(SUAPI(this), &count);

	std::vector<SUVertex*> vert_ls;
	if (count > 0) {
		vert_ls.resize(count);
		size_t copy_number = 0;
		result = SULoopGetVertices(SUAPI(this), count, (SUVertexRef*)vert_ls.data(), &copy_number);
		if (result == SU_ERROR_NONE) {
			return vert_ls;
		}
	}
	return vert_ls;
}

std::vector<SUEdge*> SULoop::GetEdges()
{
	SUResult result;

	size_t count = 0;
	SULoopGetNumVertices(SUAPI(this), &count);

	std::vector<SUEdge*> edge_ls;
	if (count > 0) {
		edge_ls.resize(count);
		size_t copy_number = 0;
		result = SULoopGetEdges(SUAPI(this), count, (SUEdgeRef*)edge_ls.data(), &copy_number);
		if (result == SU_ERROR_NONE) {
			return edge_ls;
		}
	}
	return edge_ls;
}

std::vector<SUEdgeUse*> SULoop::GetEdgeUses()
{
	SUResult result;

	size_t count = 0;
	SULoopGetNumVertices(SUAPI(this), &count);

	std::vector<SUEdgeUse*> edgeuse_ls;
	if (count > 0) {
		edgeuse_ls.resize(count);
		size_t copy_number=0;
		result = SULoopGetEdgeUses(SUAPI(this), count, (SUEdgeUseRef*)edgeuse_ls.data(),&copy_number);
		if (result == SU_ERROR_NONE) {
			return edgeuse_ls;
		}
	}
	return edgeuse_ls;
}

bool SULoop::IsOuterLoop()
{
	bool value = false;
	SULoopIsOuterLoop(SUAPI(this), &value);
	return value;
}

bool SULoop::IsConvex()
{
	bool value = false;
	SULoopIsConvex(SUAPI(this), &value);
	return value;
}

SUFace* SULoop::GetFace()
{
	SUResult result;

	SUFaceRef face = SU_INVALID;
	result = SULoopGetFace(SUAPI(this), &face);
	if (result == SU_ERROR_NONE) {
		return cast_SUFace(face);
	}
	return 0;
}


//=====================
//  SUFace
//
//=====================
SULoop* SUFace::GetOuterLoop()
{
	SULoopRef loop = SU_INVALID;
	SUFaceGetOuterLoop(SUAPI(this), &loop);
	return cast_SULoop(loop);
}

std::vector<SULoop*> SUFace::GetInnerLoops()
{
	size_t count = 0;
	SUFaceGetNumInnerLoops(SUAPI(this), &count);

	std::vector<SULoop*> loops;
	if (count > 0) {
		loops.resize(count);
		size_t copy_number;
		SUFaceGetInnerLoops(SUAPI(this), count, (SULoopRef*)loops.data(), &copy_number);
		assert(copy_number == count);
	}
	return loops;
}

CPlane SUFace::GetPlane()
{
	SUPlane3D plane;
	SUFaceGetPlane(SUAPI(this), &plane);
	return CPlane(plane.a, plane.b, plane.c, plane.d);
}

CVector3D SUFace::GetNormal()
{
	SUVector3D normal;
	SUFaceGetNormal(SUAPI(this), &normal);
	return CVector3D(normal.x, normal.y, normal.z);
}

SUMaterial* SUFace::GetFrontMaterial()
{
	SUResult result;
	SUMaterialRef material=SU_INVALID;

	result = SUFaceGetFrontMaterial(SUAPI(this),&material);
	if (result == SU_ERROR_NONE) {
		return cast_SUMaterial(material);
	}
	return 0;
}

void SUFace::SetFrontMaterial(SUMaterial* mtl)
{
	SUResult result;
	SUMaterialRef material = SU_INVALID;

	result = SUFaceSetFrontMaterial(SUAPI(this), SUAPI(mtl));
	assert(result == SU_ERROR_NONE);
}

SUMaterial* SUFace::GetBackMaterial()
{
	SUResult result;
	SUMaterialRef material;

	result = SUFaceGetBackMaterial(SUAPI(this), &material);
	if (result == SU_ERROR_NONE) {
		return cast_SUMaterial(material);
	}
	return 0;
}

void SUFace::SetBackMaterial(SUMaterial* mtl)
{
	SUResult result;
	SUMaterialRef material = SU_INVALID;

	result = SUFaceSetBackMaterial(SUAPI(this), SUAPI(mtl));
	assert(result == SU_ERROR_NONE);
}





SUUVHelper* SUFace::GetUVHelper()
{
	SUUVHelper * uvHelper;
	SUResult result = SUFaceGetUVHelper(SUAPI(this), true, false, SU_INVALID, (SUUVHelperRef*)&uvHelper);
	if (result == SU_ERROR_NONE) {
		return uvHelper;
	}
	return 0;
}

void SUUVHelper::Release()
{
	SUUVHelperRef uvHelper = SUAPI(this);
	SUUVHelperRelease(&uvHelper);
}

CMatrix33 SUUVHelper::GetFrontTextureMatrix()
{
	return tm1;
}

CMatrix33 SUUVHelper::GetBackTextureMatrix()
{
	return tm2;
}
















//=====================
//  SUMaterial
//
//=====================

SUMaterial* SUMaterial::Create()
{
	SUResult result;
	SUMaterialRef material = SU_INVALID;
	result = SUMaterialCreate(&material);
	assert(result == SU_ERROR_NONE);
	return cast_SUMaterial(material);
}

std::wstring SUMaterial::GetName()
{
	SUResult result;
	SUStringRef name = SU_INVALID;
	SUStringCreate(&name);

	std::wstring out_str;

	result = SUMaterialGetName(SUAPI(this), &name);
	assert(result == SU_ERROR_NONE);
	return SUStringToSTLString(name);
}

void SUMaterial::SetName(std::string& name)
{
	SUResult result;
	result = SUMaterialSetName(SUAPI(this), name.c_str());
	assert(result == SU_ERROR_NONE);
}


SUTexture* SUMaterial::GetTexture()
{
	SUResult result;
	SUTextureRef texture;

	result = SUMaterialGetTexture(SUAPI(this), &texture);
	//这里不能改
	if (result == SU_ERROR_NONE) {
		return cast_SUTexture(texture);
	}
	else
		return 0;
}

void SUMaterial::SetTexture(SUTexture* tex)
{
	SUResult result;
	result = SUMaterialSetTexture(SUAPI(this), SUAPI(tex));
	assert(result == SU_ERROR_NONE);
}

CVector3D SUMaterial::GetColor()
{
	SUResult result;
	SUColor color;

	result = SUMaterialGetColor(SUAPI(this), &color);
	assert(result == SU_ERROR_NONE);
	CVector3D out;
	out.x = (double)color.red / 255;
	out.y = (double)color.green / 255;
	out.z = (double)color.blue / 255;
	return out;
}

void SUMaterial::SetColor(CVector3D& color)
{
	SUResult result;
	SUColor rgb;
	rgb.red = (SUByte)(color.x * 255);
	rgb.green = (SUByte)(color.y * 255);
	rgb.blue = (SUByte)(color.z * 255);
	rgb.alpha = 255;

	result = SUMaterialSetColor(SUAPI(this), &rgb);
	assert(result == SU_ERROR_NONE);
}


bool SUMaterial::GetUseOpacity()
{
	bool value;
	SUResult result = SUMaterialGetUseOpacity(SUAPI(this), &value);
	assert(result == SU_ERROR_NONE);
	return value;
}

void SUMaterial::SetUseOpacity(bool value)
{
	SUResult result = SUMaterialSetUseOpacity(SUAPI(this), value);
	assert(result == SU_ERROR_NONE);
}

double SUMaterial::GetOpacity()
{
	double value;
	SUResult result = SUMaterialGetOpacity(SUAPI(this), &value);
	assert(result == SU_ERROR_NONE);
	return value;
}

void SUMaterial::SetOpacity(double value)
{
	SUResult result = SUMaterialSetOpacity(SUAPI(this), value);
	assert(result == SU_ERROR_NONE);
}

//=====================
//  SUTexture
//
//=====================

SUTexture* SUTexture::CreateFromFile(std::string& file_path, double u_size, double v_size)
{
	SUResult result;
	SUTextureRef texture = SU_INVALID;
	result = SUTextureCreateFromFile(&texture, file_path.c_str(), u_size, v_size);
	assert(result == SU_ERROR_NONE);
	return cast_SUTexture(texture);
}


std::wstring SUTexture::GetFileName()
{
	SUResult result;
	SUStringRef name = SU_INVALID;
	SUStringCreate(&name);

	std::wstring out_str;

	result = SUTextureGetFileName(SUAPI(this), &name);
	if (result == SU_ERROR_NONE) {
		out_str = SUStringToSTLString(name);
		return out_str;
	}
	return out_str;
}

double SUTexture::GetScaleU()
{
	SUResult result;
	double u_scale, v_scale;
	size_t width, height;

	result = SUTextureGetDimensions(SUAPI(this), &width, &height, &u_scale, &v_scale);
	if (result == SU_ERROR_NONE) {
		return u_scale;
	}
	return 1.0;
}

double SUTexture::GetScaleV()
{
	SUResult result;
	double u_scale, v_scale;
	size_t width, height;

	result = SUTextureGetDimensions(SUAPI(this), &width, &height, &u_scale, &v_scale);
	if (result == SU_ERROR_NONE) {
		return v_scale;
	}
	return 1.0;
}

bool SUTexture::WriteToFile(std::string filepath)
{
	SUResult result;

	result = SUTextureWriteToFile(SUAPI(this), filepath.c_str());
	if (result == SU_ERROR_NONE) {
		return true;
	}
	return false;
}

int SUTexture::GetImageDataSize()
{
	SUResult result;
	size_t data_size = 0;
	size_t bits_per_pixel = 0;


	SUImageRepRef image = SU_INVALID;
	SUImageRepCreate(&image);

	result = SUTextureGetImageRep(SUAPI(this), &image);

	if (result == SU_ERROR_NONE) {
		SUImageRepGetDataSize(image, &data_size, &bits_per_pixel);
	}

	SUImageRepRelease(&image);
	return (int)data_size;
}

std::vector<char> SUTexture::GetImageData()
{
	SUResult result;
	size_t data_size = 0;
	size_t bits_per_pixel = 0;
	std::vector<char> data;

	SUImageRepRef image = SU_INVALID;

	SUImageRepCreate(&image);

	result = SUTextureGetImageRep(SUAPI(this), &image);
	if (result == SU_ERROR_NONE) {
		SUImageRepGetDataSize(image, &data_size, &bits_per_pixel);
		data.resize(data_size);
		SUImageRepGetData(image, data_size, (SUByte*)data.data());
	}

	SUImageRepRelease(&image);

	return data;
}

//=====================
// SULayer
//
//=====================

std::wstring SULayer::GetName()
{
	SUResult result;
	SUStringRef name = SU_INVALID;
	SUStringCreate(&name);

	result = SULayerGetName(SUAPI(this), &name);
	assert(result == SU_ERROR_NONE);
	return SUStringToSTLString(name);
}


void SULayer::SetName(std::string& name)
{
	SUResult result;
	result = SULayerSetName(SUAPI(this), name.c_str());
	assert(result == SU_ERROR_NONE);
}

bool SULayer::GetVisable()
{
	SUResult result;
	bool vis;

	result = SULayerGetVisibility(SUAPI(this), &vis);
	assert(result == SU_ERROR_NONE);
	return vis;
}

void SULayer::SetVisable(bool vis)
{
	SUResult result;

	result = SULayerSetVisibility(SUAPI(this), vis);
	assert(result == SU_ERROR_NONE);
}


//=====================
// SUEntities
//
//=====================




int SUEntities::GetNumEdges()
{
	SUResult result;
	size_t count;

	result = SUEntitiesGetNumEdges(SUAPI(this), false, &count);
	if (result == SU_ERROR_NONE) {
		return (int)count;
	}
	return 0;
}


int SUEntities::GetNumFaces()
{
	SUResult result;
	size_t count;

	result = SUEntitiesGetNumFaces(SUAPI(this), &count);
	if (result == SU_ERROR_NONE) {
		return (int)count;
	}
	return 0;
}

int SUEntities::GetNumInstances()
{
	SUResult result;
	size_t count;

	result = SUEntitiesGetNumInstances(SUAPI(this), &count);
	if (result == SU_ERROR_NONE) {
		return (int)count;
	}
	return 0;
}

int SUEntities::GetNumGroups()
{
	SUResult result;
	size_t count;

	result = SUEntitiesGetNumGroups(SUAPI(this), &count);
	if (result == SU_ERROR_NONE) {
		return (int)count;
	}
	return 0;
}

int SUEntities::GetNumImages()
{
	SUResult result;
	size_t count;

	result = SUEntitiesGetNumImages(SUAPI(this), &count);
	if (result == SU_ERROR_NONE) {
		return (int)count;
	}
	return 0;
}

std::vector<SUEdge*> SUEntities::GetEdges()
{
	SUResult result;
	size_t copy_number;

	int number = GetNumEdges();
	if (!number) {
		return std::vector<SUEdge*>();
	}

	std::vector<SUEdge*> list1;
	list1.resize(number);

	result = SUEntitiesGetEdges(SUAPI(this), false, number, (SUEdgeRef*)list1.data(), &copy_number);
	if (result == SU_ERROR_NONE) {
		return list1;
	}
	return std::vector<SUEdge*>();
}

std::vector<SUFace*> SUEntities::GetFaces()
{
	SUResult result;
	size_t copy_number;

	int number = GetNumFaces();
	if (!number) {
		return std::vector<SUFace*>();
	}

	std::vector<SUFace*> list1;
	list1.resize(number);

	result = SUEntitiesGetFaces(SUAPI(this), number, (SUFaceRef*)list1.data(), &copy_number);
	if (result == SU_ERROR_NONE) {
		return list1;
	}
	return std::vector<SUFace*>();
}


std::vector<SUComponentInstance*> SUEntities::GetInstances()
{
	SUResult result;
	size_t copy_number;

	int number = GetNumInstances();
	if (!number) {
		return std::vector<SUComponentInstance*>();
	}

	std::vector<SUComponentInstance*> list1;
	list1.resize(number);

	result = SUEntitiesGetInstances(SUAPI(this), number, (SUComponentInstanceRef*)list1.data(), &copy_number);
	if (result == SU_ERROR_NONE) {
		return list1;
	}
	return std::vector<SUComponentInstance*>();
}

std::vector<SUComponentInstance*> SUEntities::GetGroups()
{
	SUResult result;
	size_t copy_number;

	int number = GetNumGroups();
	if (!number) {
		return std::vector<SUComponentInstance*>();
	}

	std::vector<SUComponentInstance*> list1;
	list1.resize(number);

	result = SUEntitiesGetGroups(SUAPI(this), number, (SUGroupRef*)list1.data(), &copy_number);
	if (result == SU_ERROR_NONE) {
		return list1;
	}
	return std::vector<SUComponentInstance*>();
}

std::vector<SUComponentInstance*> SUEntities::GetImages()
{
	SUResult result;
	size_t copy_number;

	int number = GetNumImages();
	if (!number) {
		return std::vector<SUComponentInstance*>();
	}

	std::vector<SUComponentInstance*> list1;
	list1.resize(number);

	result = SUEntitiesGetImages(SUAPI(this), number, (SUImageRef*)list1.data(), &copy_number);
	if (result == SU_ERROR_NONE) {
		return list1;
	}
	return std::vector<SUComponentInstance*>();
}

void SUEntities::Fill(SUGeometryInput* geom, bool weld_vertices)
{
	SUResult result;

	SUGeometryInputRef edges[] = { SUAPI(geom) };

	result = SUEntitiesFill(SUAPI(this), SUAPI(geom), weld_vertices);
	assert(result == SU_ERROR_NONE);
}

void SUEntities::AddEdge(SUEdge* edge)
{
	SUResult result;

	SUEdgeRef edges[] = { SUAPI(edge) };

	result = SUEntitiesAddEdges(SUAPI(this), 1, edges);
	assert(result == SU_ERROR_NONE);
}

void SUEntities::AddFace(SUFace* face)
{
	SUResult result;

	SUFaceRef faces[] = { SUAPI(face) };

	result = SUEntitiesAddFaces(SUAPI(this), 1, faces);
	assert(result == SU_ERROR_NONE);
}

void SUEntities::AddInstance(SUComponentInstance* inst)
{
	SUResult result;
	SUStringRef name = SU_INVALID;

	SUStringCreate(&name);
	result = SUEntitiesAddInstance(SUAPI(this), SUAPI(inst), 0);
	assert(result == SU_ERROR_NONE);
}





//=====================
// SUComponentDefinition
//
//=====================
SUComponentDefinition* SUComponentDefinition::Create()
{
	SUComponentDefinitionRef comp = SU_INVALID;
	SUResult result = SUComponentDefinitionCreate(&comp);
	assert(result == SU_ERROR_NONE);
	return (SUComponentDefinition*)comp.ptr;
}

SUEntities* SUComponentDefinition::GetEntities()
{
	SUResult result;

	SUEntitiesRef entities = SU_INVALID;

	result = SUComponentDefinitionGetEntities(SUAPI(this), &entities);
	if (result == SU_ERROR_NONE) {
		return cast_SUEntities(entities);
	}
	return 0;
}

std::wstring SUComponentDefinition::GetName()
{
	SUResult result;
	SUStringRef name = SU_INVALID;
	SUStringCreate(&name);
	result = SUComponentDefinitionGetName(SUAPI(this), &name);
	assert(result == SU_ERROR_NONE);
	return SUStringToSTLString(name);
}

void SUComponentDefinition::SetName(std::string& name)
{
	SUResult result;
	result = SUComponentDefinitionSetName(SUAPI(this), name.c_str());
	assert(result == SU_ERROR_NONE);
}

std::wstring SUComponentDefinition::GetDescription()
{
	SUResult result;

	SUStringRef desc = SU_INVALID;
	SUStringCreate(&desc);

	result = SUComponentDefinitionGetDescription(SUAPI(this), &desc);
	if (result == SU_ERROR_NONE) {
		return SUStringToSTLString(desc);
	}
	else {
		return std::wstring();
	}
}

void SUComponentDefinition::SetDescription(std::string& desc)
{
	SUResult result;
	result = SUComponentDefinitionSetDescription(SUAPI(this), desc.c_str());
	assert(result == SU_ERROR_NONE);
}



SUComponentInstance* SUComponentDefinition::CreateInstance()
{
	SUResult result;
	SUComponentInstanceRef inst = SU_INVALID;

	result = SUComponentDefinitionCreateInstance(SUAPI(this), &inst);
	if (result == SU_ERROR_NONE) {
		return cast_SUComponentInstance(inst);
	}
	return 0;
}


bool SUComponentDefinition::IsInternal()
{
	SUResult result;

	bool is_internal;

	result = SUComponentDefinitionIsInternal(SUAPI(this), &is_internal);
	if (result == SU_ERROR_NONE) {
		return is_internal;
	}
	return false;
}

std::wstring SUComponentDefinition::GetPath()
{
	SUResult result;

	SUStringRef path = SU_INVALID;
	SUStringCreate(&path);

	result = SUComponentDefinitionGetPath(SUAPI(this), &path);
	if (result == SU_ERROR_NONE) {
		return SUStringToSTLString(path);
	}
	return std::wstring();
}


//=====================
// SUComponentInstance
//
//=====================
std::wstring SUComponentInstance::GetName()
{
	SUStringRef name = SU_INVALID;
	SUStringCreate(&name);

	SUResult result = SUComponentInstanceGetName(SUAPI(this), &name);
	if (result == SU_ERROR_NONE) {
		return SUStringToSTLString(name);
	}
	else {
		return std::wstring();
	}
	return std::wstring();
}

SUComponentDefinition* SUComponentInstance::GetDefinition()
{
	SUResult result;

	SUComponentDefinitionRef comp_def;

	result = SUComponentInstanceGetDefinition(SUAPI(this), &comp_def);
	if (result == SU_ERROR_NONE) {
		return cast_SUComponentDefinition(comp_def);
	}
	return 0;
}

CMatrix SUComponentInstance::GetTransform()
{
	SUResult result;

	SUTransformation transform;

	result = SUComponentInstanceGetTransform(SUAPI(this), &transform);
	if (result == SU_ERROR_NONE) {
		bool is_identity;
		SUTransformationIsIdentity(&transform, &is_identity);
		if(is_identity)
			return CMatrix();
		CMatrix m;
		m.m[0][0] = transform.values[0];
		m.m[0][1] = transform.values[1];
		m.m[0][2] = transform.values[2];
		m.m[0][3] = transform.values[3];

		m.m[1][0] = transform.values[4];
		m.m[1][1] = transform.values[5];
		m.m[1][2] = transform.values[6];
		m.m[1][3] = transform.values[7];

		m.m[2][0] = transform.values[8];
		m.m[2][1] = transform.values[9];
		m.m[2][2] = transform.values[10];
		m.m[2][3] = transform.values[11];

		m.m[3][0] = transform.values[12];
		m.m[3][1] = transform.values[13];
		m.m[3][2] = transform.values[14];
		m.m[3][3] = transform.values[15];
		return m;
	}
	return CMatrix();
}

void SUComponentInstance::SetTransform(CMatrix& m)
{
	SUResult result;

	SUTransformation transform;
	transform.values[0] = m.m[0][0];
	transform.values[1] = m.m[0][1];
	transform.values[2] = m.m[0][2];
	transform.values[3] = m.m[0][3];

	transform.values[4] = m.m[1][0];
	transform.values[5] = m.m[1][1];
	transform.values[6] = m.m[1][2];
	transform.values[7] = m.m[1][3];

	transform.values[8] = m.m[2][0];
	transform.values[9] = m.m[2][1];
	transform.values[10] = m.m[2][2];
	transform.values[11] = m.m[2][3];

	transform.values[12] = m.m[3][0];
	transform.values[13] = m.m[3][1];
	transform.values[14] = m.m[3][2];
	transform.values[15] = m.m[3][3];

	result = SUComponentInstanceSetTransform(SUAPI(this), &transform);
}

SUMaterial* SUComponentInstance::GetMaterial()
{
	SUResult result;
	SUMaterialRef material = SU_INVALID;

	SUDrawingElementRef draw_ele = SUComponentInstanceToDrawingElement(SUAPI(this));
	result = SUDrawingElementGetMaterial(draw_ele, &material);
	if (result == SU_ERROR_NONE) {
		return cast_SUMaterial(material);
	}
	else if (result == SU_ERROR_NO_DATA) {
		return 0;
	}
	else {
		assert(false);
		return 0;
	}
}

void SUComponentInstance::SetMaterial(SUMaterial* mtl)
{
	SUResult result;
	SUDrawingElementRef draw_ele = SUComponentInstanceToDrawingElement(SUAPI(this));
	result = SUDrawingElementSetMaterial(draw_ele, SUAPI(mtl));
	assert(result == SU_ERROR_NONE);
}

//=====================
// SULoopInput
//
//=====================
SULoopInput* SULoopInput::Create()
{
	SUResult result;
	SUGeometryInputRef geo_input = SU_INVALID;
	result = SUGeometryInputCreate(&geo_input);
	assert(result == SU_ERROR_NONE);
	return (SULoopInput*)geo_input.ptr;
}

void SULoopInput::Release()
{
	SUResult result;
	SULoopInputRef self = SUAPI(this);
	result = SULoopInputRelease(&self);
	assert(result == SU_ERROR_NONE);
}

void SULoopInput::AddVertexIndex(int vertex_index)
{
	SUResult result;
	result = SULoopInputAddVertexIndex(SUAPI(this), (size_t)vertex_index);
	assert(result == SU_ERROR_NONE);
}

void SULoopInput::EdgeSetHidden(int edge_index, bool hidden)
{
	SUResult result;
	result = SULoopInputEdgeSetHidden(SUAPI(this), (size_t)edge_index, hidden);
	assert(result == SU_ERROR_NONE);
}

void SULoopInput::EdgeSetSoft(int edge_index, bool soft)
{
	SUResult result;
	result = SULoopInputEdgeSetSoft(SUAPI(this), (size_t)edge_index, soft);
	assert(result == SU_ERROR_NONE);
}

void SULoopInput::EdgeSetSmooth(int edge_index, bool smooth)
{
	SUResult result;
	result = SULoopInputEdgeSetSmooth(SUAPI(this), (size_t)edge_index, smooth);
	assert(result == SU_ERROR_NONE);
}

//=====================
// SUTextureCoordInput
//
//=====================
SUTextureCoordInput::SUTextureCoordInput()
{
	num_uv_coords = 0;
	for (int i = 0; i < 4; i++) {
		uv_coords[i] = CVector2D();
		vertex_indices[i] = 0;
	}
}

SUTextureCoordInput::~SUTextureCoordInput()
{
}

void SUTextureCoordInput::AddTexCoord(int vertex_index, CVector2D& uv)
{
	assert(num_uv_coords < 4);

	vertex_indices[num_uv_coords] = vertex_index;
	uv_coords[num_uv_coords] = uv;
	num_uv_coords++;
}

//=====================
// SUGeometryInput
//
//=====================
void SUGeometryInput::AddVertex(CVector3D& point)
{
	SUResult result;
	result = SUGeometryInputAddVertex(SUAPI(this), (const struct SUPoint3D*)&point);
	assert(result == SU_ERROR_NONE);
}

int SUGeometryInput::AddEdge(int v0_idx, int v1_idx)
{
	SUResult result;
	size_t edge_idx;
	result = SUGeometryInputAddEdge(SUAPI(this), (size_t)v0_idx, (size_t)v1_idx, &edge_idx);
	assert(result == SU_ERROR_NONE);
	return (int)edge_idx;
}

void SUGeometryInput::EdgeSetSoft(int edge_idx, bool soft)
{
	SUResult result;
	result = SUGeometryInputEdgeSetSoft(SUAPI(this), (size_t)edge_idx, soft);
	assert(result == SU_ERROR_NONE);
}

void SUGeometryInput::EdgeSetSmooth(int edge_idx, bool smooth)
{
	SUResult result;
	result = SUGeometryInputEdgeSetSmooth(SUAPI(this), (size_t)edge_idx, smooth);
	assert(result == SU_ERROR_NONE);
}

int SUGeometryInput::AddFace(SULoopInput* loop)
{
	SUResult result;
	size_t face_idx;
	SULoopInputRef loop_ref = SUAPI(loop);
	result = SUGeometryInputAddFace(SUAPI(this), &loop_ref, &face_idx);
	assert(result == SU_ERROR_NONE);
	return (int)face_idx;
}

void SUGeometryInput::FaceAddInnerLoop(int face_idx, SULoopInput* loop)
{
	SUResult result;
	SULoopInputRef loop_ref = SUAPI(loop);
	result = SUGeometryInputFaceAddInnerLoop(SUAPI(this), face_idx, &loop_ref);
	assert(result == SU_ERROR_NONE);
}

void SUGeometryInput::FaceSetFrontMaterial(int face_idx, SUMaterial* mtl, SUTextureCoordInput* tc)
{
	SUResult result;
	SUMaterialInput mi;
	mi.material = SUAPI(mtl);
	mi.num_uv_coords = 0;
	if (tc) {
		mi.num_uv_coords = tc->num_uv_coords;
		for (int i = 0; i < tc->num_uv_coords; i++) {
			mi.vertex_indices[i] = (size_t)tc->vertex_indices[i];
			mi.uv_coords[i] = { tc->uv_coords[i].x,tc->uv_coords[i].y };
		}
	}
	result = SUGeometryInputFaceSetFrontMaterial(SUAPI(this), face_idx, &mi);
	assert(result == SU_ERROR_NONE);
}

void SUGeometryInput::FaceSetBackMaterial(int face_idx, SUMaterial* mtl, SUTextureCoordInput* tc)
{
	SUResult result;
	SUMaterialInput mi;
	mi.material = SUAPI(mtl);
	mi.num_uv_coords = 0;
	if (tc) {
		mi.num_uv_coords = tc->num_uv_coords;
		for (int i = 0; i < tc->num_uv_coords; i++) {
			mi.vertex_indices[i] = (size_t)tc->vertex_indices[i];
			mi.uv_coords[i] = { tc->uv_coords[i].x,tc->uv_coords[i].y };
		}
	}
	result = SUGeometryInputFaceSetBackMaterial(SUAPI(this), face_idx, &mi);
	assert(result == SU_ERROR_NONE);
}

SUGeometryInput* SUGeometryInput::Create()
{
	SUResult result;
	SUGeometryInputRef geo_input = SU_INVALID;
	result = SUGeometryInputCreate(&geo_input);
	assert(result == SU_ERROR_NONE);
	return (SUGeometryInput*)geo_input.ptr;
}

void SUGeometryInput::Release()
{
	SUResult result;
	SUGeometryInputRef geo_input = SUAPI(this);
	result = SUGeometryInputRelease(&geo_input);
	assert(result == SU_ERROR_NONE);
}

//=====================
// SUModel
//
//=====================

SUModel* SUModel::Create()
{
	SUResult result;

	SUModelRef model = SU_INVALID;

	result = SUModelCreate(&model);
	if (result == SU_ERROR_NONE) {
		return (SUModel*)model.ptr;
	}
	return 0;
}

void SUModel::Release()
{
	SUModelRef model = SUAPI(this);
	SUModelRelease(&model);
}

unsigned long long SUModel::GetPtr()
{
	return (unsigned long long)this;
}

SUModel* SUModel::LoadFromFile(std::string file_path)
{
	SUResult result;

	SUModelRef model = SU_INVALID;

	result = SUModelCreateFromFile(&model, file_path.c_str());

	if (result == SU_ERROR_NONE) {
		return (SUModel*)model.ptr;
	}
	return 0;
}

SUModel* SUModel::cLoadFromBuffer(const unsigned char* buffer, size_t buffer_size)
{
	SUResult result;

	SUModelRef model = SU_INVALID;

	result = SUModelCreateFromBuffer(&model, buffer, buffer_size);

	if (result == SU_ERROR_NONE) {
		return (SUModel*)model.ptr;
	}
	return 0;
}

bool SUModel::SaveToFile(std::string& filepath)
{
	SUResult result;
	result = SUModelSaveToFile(SUAPI(this), filepath.c_str());
	if (result == SU_ERROR_NONE) {
		return true;
	}
	return false;
}

bool SUModel::SaveToFile2015(std::string& filepath)
{
	SUResult result;
	result = SUModelSaveToFileWithVersion(SUAPI(this), filepath.c_str(), SUModelVersion_SU2015);
	if (result == SU_ERROR_NONE) {
		return true;
	}
	return false;
}
bool SUModel::SaveToFile2017(std::string& filepath)
{
	SUResult result;
	result = SUModelSaveToFileWithVersion(SUAPI(this), filepath.c_str(), SUModelVersion_SU2017);
	if (result == SU_ERROR_NONE) {
		return true;
	}
	return false;
}

SUEntities* SUModel::GetEntities()
{
	SUResult result;

	SUEntitiesRef entities = SU_INVALID;

	result = SUModelGetEntities(SUAPI(this),&entities);

	if (result == SU_ERROR_NONE) {
		return cast_SUEntities(entities);
	}
	return 0;
}

std::string SUModel::GetName()
{
    SUStringRef name = SU_INVALID;
    SUStringCreate(&name);
    auto result = SUModelGetName(SUAPI(this), &name);
    size_t length = 0, copied = 0;
    std::string value;
    if (result == SU_ERROR_NONE) {
        SUStringGetUTF8Length(name, &length);
        value.resize(length + 1);
        SUStringGetUTF8(name, value.size(), value.data(), &copied);
        value.resize(length);
    }
    SUStringRelease(&name);
    return value;
}

std::vector<SUMaterial*> SUModel::GetMaterialList()
{
	SUResult result;

	size_t num_materials;
	result = SUModelGetNumMaterials(SUAPI(this), &num_materials);

	std::vector<SUMaterial*> material_list(num_materials);

	size_t copy_count;
	result = SUModelGetMaterials(SUAPI(this), num_materials, (SUMaterialRef*)material_list.data(), &copy_count);
	//这里不能改
	if (result == SU_ERROR_NONE) {
		return material_list;
	}
	return std::vector<SUMaterial*>();
}

std::vector<SUComponentDefinition*> SUModel::GetComponentDefinitionList()
{
	SUResult result;

	size_t number;
	result = SUModelGetNumComponentDefinitions(SUAPI(this), &number);

	std::vector<SUComponentDefinition*> comp_list(number);

	size_t copy_count;
	result = SUModelGetComponentDefinitions(SUAPI(this), number, (SUComponentDefinitionRef*)comp_list.data(), &copy_count);
	//这里不能改
	if (result == SU_ERROR_NONE) {
		return comp_list;
	}
	return std::vector<SUComponentDefinition*>();
}


std::vector<SUComponentDefinition*> SUModel::GetGroupDefinitionList()
{
	SUResult result;

	size_t number;
	result = SUModelGetNumGroupDefinitions(SUAPI(this), &number);

	std::vector<SUComponentDefinition*> comp_list(number);

	size_t copy_count;
	result = SUModelGetGroupDefinitions(SUAPI(this), number, (SUComponentDefinitionRef*)comp_list.data(), &copy_count);
	//这里不能改
	if (result == SU_ERROR_NONE) {
		return comp_list;
	}
	return std::vector<SUComponentDefinition*>();
}

std::vector<SULayer*> SUModel::GetLayers()
{
	SUResult result;

	size_t number;
	result = SUModelGetNumLayers(SUAPI(this), &number);

	std::vector<SULayer*> layer_list(number);

	size_t copy_count;
	result = SUModelGetLayers(SUAPI(this), number, (SULayerRef*)layer_list.data(), &copy_count);
	//这里不能改
	if (result == SU_ERROR_NONE) {
		return layer_list;
	}
	return std::vector<SULayer*>();
}

void SUModel::AddComponentDefinition(SUComponentDefinition*comp_def)
{
	SUResult result;

	SUComponentDefinitionRef comps[] = { SUAPI(comp_def) };

	result = SUModelAddComponentDefinitions(SUAPI(this), 1, comps);
	assert(result == SU_ERROR_NONE);
}

void SUModel::AddMaterial(SUMaterial* mat)
{
	SUResult result;
	SUMaterialRef mats[] = { SUAPI(mat) };
	result = SUModelAddMaterials(SUAPI(this), 1, mats);
	assert(result == SU_ERROR_NONE);
}

