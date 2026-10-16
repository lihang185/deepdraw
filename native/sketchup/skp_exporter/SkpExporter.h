#include <windows.h>
#include <DeepDrawAPI.h>
#include <SketchUpAPI/sketchup.h>
#include <vector>
#include <set>
#include <map>

std::string StringWideCharToMultiByte(const std::wstring& wstr, UINT codePage);

class SkpExporter
{
public:
	SkpExporter();
	~SkpExporter();


	bool ExportSceneToFile(CModelPublic* model, const char* filename);
	bool ExportSelectionToFile(CModelPublic* model, const char* filename);

	void WalkComponent(CComponentPublic* comp);
	void WalkComponentBySelection(std::vector<CEntityPublic*>& entities);
	void ExportComponentDefinition(CComponentDefinitionPublic* compdef);

	SUMaterialRef ExportMaterial(CMaterialPublic* mtl);

	void ExportEntities(CComponentPublic* comp, SUEntitiesRef out_comp);
	void ExportEntitiesBySelection(std::vector<CEntityPublic*>& entities, SUEntitiesRef out_comp);
	void ExportInstance(CComponentInstancePublic* inst, SVector3D& center_point, SUEntitiesRef out_comp);

	void ExportCompGeometry(std::vector<CEntityPublic*>& entities, SVector3D& center_point, SUEntitiesRef out_comp);
	int conv_loop(SUGeometryInputRef geo, CLoopPublic* loop, SVector3D& center_point, std::vector<CVertexPublic*>& vert_ls, SULoopInputRef* out_loop);
	int find_vertex_idx(std::vector<CVertexPublic*>& vert_ls, int start_index, CVertexPublic* v);



	int compute_center_point(std::vector<CEntityPublic*>& entities, SVector3D* center_point);
	bool find_material_map(CMaterialPublic* mtl, SUMaterialRef* out);
	int find_tc_verts(CLoopPublic* loop, CUVHelperPublic* uv_helper, CVertexPublic* out[]);


	std::wstring temp_dir;

	// need clear pre pass
	SUModelRef su_model;
	std::map< CMaterialPublic*, SUMaterialRef> material_map;
	std::set< CComponentDefinitionPublic* > compdef_set;
	std::vector< CComponentDefinitionPublic* > compdef_ls;
	std::map< CComponentDefinitionPublic*, SUComponentDefinitionRef> compdef_map;
};