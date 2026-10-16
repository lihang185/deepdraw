#include <assert.h>
#include <memory>
#include <windows.h>
//#include <gl/GL.h>
#include <glad/glad.h>
#include "CModelCache.h"


#define Print_VBO_info 0


//=======================
//  Base Material
//
//=======================
RBaseMaterial::RBaseMaterial()
{
}

RBaseMaterial::~RBaseMaterial()
{
}

bool RBaseMaterial::IsOpacity() { return use_opacity; }

bool  RBaseMaterial::IsDefault()
{
	return this->type == MaterialType_Default;
}

void RBaseMaterial::Bind()
{
	if (type == MaterialType_Default)
		bind_default_type();
	else if (type == MaterialType_Color)
		bind_color_type();
	else if (type == MaterialType_Texture)
		bind_texture_type();
}

void RBaseMaterial::bind_default_type()
{
	float white[] = { 1,1,1,1 };
	float back[] = { 0.8f,1.0f,0.8f,1.0f };
	glDisable(GL_TEXTURE_2D);
	glColor4fv(white);
	glMaterialfv(GL_FRONT, GL_DIFFUSE, white);
	glMaterialfv(GL_BACK, GL_DIFFUSE, back);
	glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, white);
}

void RBaseMaterial::bind_color_type()
{
	
	float rgba[4];
	glDisable(GL_TEXTURE_2D);
	
	rgba[0] = (float)color.x;
	rgba[1] = (float)color.y;
	rgba[2] = (float)color.z;
	if (IsOpacity()) {
		rgba[3] = (float)opacity;;
		glColor4fv(rgba);
		glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, rgba);
		glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, rgba);
	}
	else {
		rgba[3] = 1;
		glColor4fv(rgba);
		glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, rgba);
		glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, rgba);
	}
}

void RBaseMaterial::bind_texture_type()
{
	float rgba[] = { 1,1,1,1 };
	assert(this->gl_tex);
	glEnable(GL_TEXTURE_2D);
	glBindTexture(GL_TEXTURE_2D, this->gl_tex);
	glColor4fv(rgba);
	glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, rgba);
	glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, rgba);
	// texture coord scale
	
	glMatrixMode(GL_TEXTURE);
	glLoadIdentity();
	
	
	
	glScalef(static_cast<float>(1.0 / size_u), static_cast<float>(1.0 / size_v), 1);
	glMatrixMode(GL_MODELVIEW);
}

//=======================
//  Face Group
//
//=======================
RFaceGroup::RFaceGroup(std::vector<CFacePublic*>& ls, CMatrix& m)
	:face_ls(ls), matrix(m), is_image(false)
{
}
RFaceGroup::~RFaceGroup()
{

}

bool RFaceGroup::test_matrix_mirror()
{
	return matrix.TestMirror();
}


RMaterialGroup::RMaterialGroup(std::vector<RFaceGroup*>& ls, RBaseMaterial* mtl)
	:group_ls(ls), material(mtl)
{
}

RMaterialGroup::~RMaterialGroup()
{
}


REdgeGroup::REdgeGroup(std::vector<CEdgePublic*>& ls, CMatrix& m)
	:edge_ls(ls),matrix(m)
{
}

REdgeGroup::~REdgeGroup()
{
}



//=======================
//  VBO Cache
//
//=======================
RVBOCache::RVBOCache()
{
	face_vbo = 0;
	face_ebo = 0;
	edge_vbo = 0;
	Clear();
}

RVBOCache::~RVBOCache()
{

}

bool RVBOCache::InitOpenGL()
{
	return gladLoadGL() != 0;
}

void RVBOCache::Clear()
{
	GLuint buf;

	if (face_vbo) {
		if (Print_VBO_info) printf("Release face_vbo %d\n", face_vbo);
		buf = face_vbo;
		glDeleteBuffers(1, &buf);
		face_vbo = 0;
	}

	if (face_ebo) {
		if (Print_VBO_info == 2) printf("Release face_ebo %d\n", face_ebo);
		buf = face_ebo;
		glDeleteBuffers(1, &buf);
		face_ebo = 0;
	}

	if (edge_vbo) {
		if (Print_VBO_info == 2) printf("Release edge_vbo %d\n", edge_vbo);
		buf = edge_vbo;
		glDeleteBuffers(1, &buf);
		edge_vbo = 0;
	}

	this->has_geom[0] = false;
	this->has_geom[1] = false;
	this->has_geom[2] = false;
	this->has_geom[3] = false;
	this->num_edges = 0;

	nomat_group = RElementGroup();
	normal_group.clear();
	optcity_group.clear();

	face_vert_data.clear();
	face_el_data.clear();
	edge_vert_data.clear();
}

void RVBOCache::Build(std::vector<RMaterialGroup*>& face_groups, std::vector<REdgeGroup*>& edge_groups, MeshBuildSession* session)
{
	Clear();


	if (!face_groups.empty()) {
		build_face(face_groups, session);
	}

	if (!edge_groups.empty()) {
		build_edge(edge_groups);
	}

	face_vert_data.clear();
	face_el_data.clear();
	edge_vert_data.clear();
}

void RVBOCache::build_face(std::vector<RMaterialGroup*>& face_groups, MeshBuildSession* session)
{
	int start, count;
	RBaseMaterial* mtl;

	bool has_face = false;

	for (auto it1 = face_groups.begin(); it1 != face_groups.end(); it1++) {
		RMaterialGroup* mtlGroup = *it1;

		start = (int)face_el_data.size();

		for (auto it2 = mtlGroup->group_ls.begin(); it2 != mtlGroup->group_ls.end(); it2++) {
			RFaceGroup* faceGroup = *it2;

			bool mirror = faceGroup->test_matrix_mirror();
			for (auto it3 = faceGroup->face_ls.begin(); it3 != faceGroup->face_ls.end(); it3++) {
				CFacePublic* face = *it3;
				build_single_face(face, faceGroup->matrix, mirror, face_vert_data, face_el_data, session);
			}
		}

		count = (int)face_el_data.size() - start;
		mtl = mtlGroup->material;

		if (count) {
			has_face = true;

			if (mtl == NULL) {
				nomat_group = RElementGroup(start, count, mtl);
				this->has_geom[0] = true;
			}
			else if (!mtl->IsOpacity()) {
				RElementGroup group1 = RElementGroup(start, count, mtl);
				normal_group.push_back(group1);
				this->has_geom[1] = true;
			}
			else {
				RElementGroup group1 = RElementGroup(start, count, mtl);
				optcity_group.push_back(group1);
				this->has_geom[3] = true;
			}
		}

	}

	if (has_face) {
		GLuint vbo;
		glGenBuffers(1, &vbo);
		glBindBuffer(GL_ARRAY_BUFFER, vbo);
		glBufferData(GL_ARRAY_BUFFER, face_vert_data.size() * sizeof(float), face_vert_data.data(), GL_STATIC_DRAW);
		glBindBuffer(GL_ARRAY_BUFFER, 0);
		this->face_vbo = vbo;
		if (Print_VBO_info) printf("build face_vbo %d\n", face_vbo);

		GLuint ebo;
		glGenBuffers(1, &ebo);
		glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo);
		glBufferData(GL_ELEMENT_ARRAY_BUFFER, face_el_data.size() * sizeof(unsigned int), face_el_data.data(), GL_STATIC_DRAW);
		glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0);
		this->face_ebo = ebo;
		if (Print_VBO_info == 2) printf("build face_ebo %d\n", face_ebo);
	}

}

void RVBOCache::build_edge(std::vector<REdgeGroup*>& edge_groups)
{
	//std::vector<float> vertArray;
	CVector3D p1, p2;

	this->num_edges = 0;

	for (auto it = edge_groups.begin(); it != edge_groups.end(); it++) {
		REdgeGroup* edgeGroup = *it;
		for (auto it2 = edgeGroup->edge_ls.begin(); it2 != edgeGroup->edge_ls.end(); it2++) {
			CEdgePublic* e = *it2;
			if (!e->IsSoft() && !e->IsHide()) {
				p1 = e->GetStartVertex()->Pos();
				p1 = edgeGroup->matrix.Transform(p1);
				edge_vert_data.push_back((float)p1.x);
				edge_vert_data.push_back((float)p1.y);
				edge_vert_data.push_back((float)p1.z);
				//
				p2 = e->GetEndVertex()->Pos();
				p2 = edgeGroup->matrix.Transform(p2);
				edge_vert_data.push_back((float)p2.x);
				edge_vert_data.push_back((float)p2.y);
				edge_vert_data.push_back((float)p2.z);
				//
				this->num_edges++;
			}
		}
	}

	if (this->num_edges>0) {
		this->has_geom[2] = true;

		GLuint vbo;
		glGenBuffers(1, &vbo);
		glBindBuffer(GL_ARRAY_BUFFER, vbo);
		glBufferData(GL_ARRAY_BUFFER, edge_vert_data.size() * sizeof(float), edge_vert_data.data(), GL_STATIC_DRAW);
		glBindBuffer(GL_ARRAY_BUFFER, 0);
		this->edge_vbo = vbo;
		if (Print_VBO_info == 2) printf("build edge_vbo %d\n", edge_vbo);
	}
}

void RVBOCache::Draw(int ipass)
{
	if (ipass == 2 && this->num_edges > 0) {
		if (this->num_edges > 0) {
			draw_edge();
		}
	}

	switch (ipass) {
	case 0:
		if (nomat_group.count > 0) {
			draw_face(&nomat_group);
		}
		break;
	case 1:
		if (!normal_group.empty()) {
			for (auto it = normal_group.begin(); it != normal_group.end(); it++) {
				RElementGroup* group = &(*it);
				draw_face(group);
			}
		}
		break;
	case 3:
		if (!optcity_group.empty()) {
			for (auto it = optcity_group.begin(); it != optcity_group.end(); it++) {
				RElementGroup* group = &(*it);
				draw_face(group);
			}
		}
		break;
	default:
		break;
	}
}

void RVBOCache::DrawOpaque(bool inherited)
{
	if (inherited && nomat_group.count > 0) draw_face(&nomat_group, false);
	for (auto& group : normal_group) draw_face(&group, false);
}

void RVBOCache::draw_face(RElementGroup* group, bool bind_material)
{
	if (bind_material && group->mtl) {
		group->mtl->Bind();
	}

	glBindBuffer(GL_ARRAY_BUFFER, this->face_vbo);
	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, this->face_ebo);

	//glEnableClientState(GL_VERTEX_ARRAY);
	//glEnableClientState(GL_NORMAL_ARRAY);
	//glEnableClientState(GL_TEXTURE_COORD_ARRAY);

	glVertexPointer(3, GL_FLOAT, 32, 0);
	glNormalPointer(GL_FLOAT, 32, (void*)12);
	glTexCoordPointer(2, GL_FLOAT, 32, (void*)24);

	size_t ofs = group->start*4;
	if(render_statistics.enabled) {
		++render_statistics.calls;
		render_statistics.triangles += group->count / 3;
	}
	glDrawElements(GL_TRIANGLES, group->count, GL_UNSIGNED_INT, (void*)ofs);

	//glDisableClientState(GL_VERTEX_ARRAY);
	//glDisableClientState(GL_NORMAL_ARRAY);
	//glDisableClientState(GL_TEXTURE_COORD_ARRAY);

	glBindBuffer(GL_ARRAY_BUFFER, 0);
	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0);
}

void RVBOCache::draw_edge()
{
	glBindBuffer(GL_ARRAY_BUFFER, this->edge_vbo);
	//glEnableClientState(GL_VERTEX_ARRAY);
	glVertexPointer(3, GL_FLOAT, 0, 0);
	if(render_statistics.enabled) {
		++render_statistics.calls;
		render_statistics.lines += this->num_edges;
	}
	glDrawArrays(GL_LINES, 0, this->num_edges * 2);
	//glDisableClientState(GL_VERTEX_ARRAY);
	glBindBuffer(GL_ARRAY_BUFFER, 0);
}

void RVBOCache::build_single_face(CFacePublic* face, CMatrix& m, bool mirror, std::vector<float>& vertArray, std::vector<unsigned int>& indexArray, MeshBuildSession* session)
{
	CVector3D n, p, tc;
	int num_indices, num_verts, num_tris,i, a,b,c;

	if (face->IsHide())
		return;

	unsigned int start_vertex = (unsigned int)vertArray.size() / 8;

	std::shared_ptr<TriangleMeshPublic> trimesh;
	if (session) trimesh = session->get(face);
	else {
		trimesh = std::shared_ptr<TriangleMeshPublic>(TriangleMeshPublic::Create(),
			[](TriangleMeshPublic* mesh) { if (mesh) mesh->Release(); });
		face->ComputeMesh(trimesh.get());
	}

	num_verts = trimesh->GetNumVertices();
	num_indices = trimesh->GetNumVertexIndices();

	for (i = 0; i < num_verts; i++) {
		// pos
		p = trimesh->GetVertex(i);
		p = m.Transform(p);
		vertArray.push_back((float)p.x);
		vertArray.push_back((float)p.y);
		vertArray.push_back((float)p.z);
		// faceNormal
		n = trimesh->GetNormal(i);
		n = m.TransformDir(n);
		n.Normalize();
		vertArray.push_back((float)n.x);
		vertArray.push_back((float)n.y);
		vertArray.push_back((float)n.z);
		// uv
		tc = trimesh->GetFrontUV(i);
		vertArray.push_back((float)tc.x);
		vertArray.push_back((float)tc.y);
	}

	num_tris = num_indices / 3;
	for (i = 0; i < num_tris; i++) {
		a = trimesh->GetVertexIndex(i * 3 + 0);
		b = trimesh->GetVertexIndex(i * 3 + 1);
		c = trimesh->GetVertexIndex(i * 3 + 2);
		if (mirror) {
			indexArray.push_back(start_vertex + c);
			indexArray.push_back(start_vertex + b);
			indexArray.push_back(start_vertex + a);
		}
		else {
			indexArray.push_back(start_vertex + a);
			indexArray.push_back(start_vertex + b);
			indexArray.push_back(start_vertex + c);
		}
	}

}



std::shared_ptr<TriangleMeshPublic> MeshBuildSession::get(CFacePublic* face)
{
    auto found = meshes.find(face);
    if (found != meshes.end()) { ++hits; return found->second; }
    ++misses;
    auto mesh = std::shared_ptr<TriangleMeshPublic>(TriangleMeshPublic::Create(),
        [](TriangleMeshPublic* value) { if (value) value->Release(); });
    face->ComputeMesh(mesh.get());
    // Conservative payload estimate; the private engine controls allocator overhead.
    const size_t cost = size_t(mesh->GetNumVertices()) * sizeof(double) * 12
        + size_t(mesh->GetNumVertexIndices()) * sizeof(unsigned int) + 256;
    if (cost <= limit - bytes) { meshes.emplace(face, mesh); bytes += cost; }
    return mesh;
}
