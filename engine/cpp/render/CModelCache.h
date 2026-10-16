#ifndef _CModelCache_H_
#define _CModelCache_H_
#include <string>
#include <vector>
#include <memory>
#include <unordered_map>

#include <DeepDrawAPI.h>
#include "cmath.h"

struct RenderStatistics {
    bool enabled = false;
    unsigned long long calls = 0, triangles = 0, lines = 0;
};
extern thread_local RenderStatistics render_statistics;

// Only valid during one immutable initialization pass. Never retained by VBOs.
class MeshBuildSession {
    std::unordered_map<CFacePublic*, std::shared_ptr<TriangleMeshPublic>> meshes;
public:
    size_t bytes = 0, hits = 0, misses = 0;
    const size_t limit;
    explicit MeshBuildSession(size_t limit) : limit(limit) {}
    std::shared_ptr<TriangleMeshPublic> get(CFacePublic* face);
};


#define MaterialType_Default	0
#define MaterialType_Color		1
#define MaterialType_Texture	2

class RBaseMaterial
{
public:
	RBaseMaterial();
	virtual ~RBaseMaterial();

	virtual void Bind();
	bool IsOpacity();
	bool IsDefault();

	bool use_opacity = false;
	double opacity = 1.0;
	SVector3D color = {1, 1, 1};
	double size_u = 1.0, size_v = 1.0;
	int type = MaterialType_Default;
	int gl_tex = 0;

private:
	void bind_default_type();
	void bind_color_type();
	void bind_texture_type();
};

class RFaceGroup
{
public:
	RFaceGroup(std::vector<CFacePublic*>& ls, CMatrix& m);
	~RFaceGroup();

	bool test_matrix_mirror();
	
	std::vector<CFacePublic*> face_ls;
	CMatrix matrix;
	bool is_image;
};

class RMaterialGroup
{
public:
	RMaterialGroup(std::vector<RFaceGroup*>& ls, RBaseMaterial* mtl);
	~RMaterialGroup();

	std::vector<RFaceGroup*> group_ls;
	RBaseMaterial* material;
};

class REdgeGroup
{
public:
	REdgeGroup(std::vector<CEdgePublic*>& ls, CMatrix& m);
	~REdgeGroup();

	std::vector<CEdgePublic*> edge_ls;
	CMatrix matrix;
};

struct RElementGroup {
	RElementGroup() :start(0), count(0) {}
	RElementGroup(int s, int c, RBaseMaterial* m) :start(s), count(c), mtl(m) {}
	RBaseMaterial* mtl;
	int start;
	int count;
};


class RVBOCache {
public:
	RVBOCache();
	~RVBOCache();

	static bool InitOpenGL();

	void Clear();
	void Build(std::vector<RMaterialGroup*>& face_groups, std::vector<REdgeGroup*>& edge_groups, MeshBuildSession* session = nullptr);
	void Draw(int ipass);
	void DrawOpaque(bool inherited);
	bool HasGeomtry(int ipass) { return has_geom[ipass]; }

private:
	void build_face(std::vector<RMaterialGroup*>& face_groups, MeshBuildSession* session);
	void build_edge(std::vector<REdgeGroup*>& edge_groups);
	void build_single_face(CFacePublic* face, CMatrix& m, bool mirror, std::vector<float>& vertArray, std::vector<unsigned int>& indexArray, MeshBuildSession* session);
	void draw_face(RElementGroup* group, bool bind_material = true);
	void draw_edge();

	bool has_geom[4];

	int num_edges;
	RElementGroup nomat_group;
	std::vector< RElementGroup > normal_group;
	std::vector< RElementGroup > optcity_group;

	std::vector<float> face_vert_data;
	std::vector<unsigned int> face_el_data;
	std::vector<float> edge_vert_data;

	int face_vbo;
	int face_ebo;
	int edge_vbo;
};


#endif // _CModelCache_H_
