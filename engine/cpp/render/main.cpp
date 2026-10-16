#include <windows.h>
#include <array>
#include <cmath>
#include <map>
#include <memory>
#include <set>
#include <vector>
#include <algorithm>
#include <glad/glad.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "CModelCache.h"
#include "entity_capsule.h"

namespace py = pybind11;
thread_local RenderStatistics render_statistics;
namespace {
using Matrix = std::array<double, 12>;
CMatrix matrix_from_values(const Matrix& values) {
    CMatrix result;
    for (int row = 0; row != 4; ++row)
        for (int col = 0; col != 3; ++col) {
            double v = values[row * 3 + col];
            if (!std::isfinite(v)) throw py::value_error("Matrix must be finite");
            result.m[row][col] = v;
        }
    result.is_identity = false;
    result.is_orthogonal = false;
    return result;
}
template<class T> T* entity(py::handle value, int type) {
    void* p = PyCapsule_GetPointer(value.ptr(), deepdraw_bridge::entity_name);
    if (!p) throw py::error_already_set();
    auto* base = static_cast<CEntityPublic*>(p);
    if (base->GetType() != type) throw py::type_error("Wrong entity capsule type");
    return static_cast<T*>(base);
}
void check_pass(int pass) {
    if (pass < 0 || pass > 3) throw py::value_error("pass must be in [0, 3]");
}
HGLRC current_context() {
    HGLRC context = wglGetCurrentContext();
    if (!context) throw std::runtime_error("Render operation requires a current OpenGL context");
    return context;
}
using Pending = std::pair<HGLRC, std::unique_ptr<RVBOCache>>;
std::vector<Pending>& pending() {
    static std::vector<Pending> queue;
    return queue;
}
void collect() {
    auto context = current_context();
    auto& queue = pending();
    for (auto it = queue.begin(); it != queue.end();) {
        if (it->first == context) {
            it->second->Clear();
            it = queue.erase(it);
        } else ++it;
    }
}
HGLRC loaded_context = nullptr;
void initialize_context() {
    auto context = current_context();
    if (!RVBOCache::InitOpenGL()) throw std::runtime_error("Cannot initialize render OpenGL entry points");
    loaded_context = context;
}
void require_context() {
    if (loaded_context != current_context()) initialize_context();
    collect();
}
class ComponentBuildSession {
public:
    std::map<CMaterialPublic*, std::shared_ptr<RBaseMaterial>> materials;
    explicit ComponentBuildSession(py::list values) {
        for (auto value : values) {
            auto item = py::cast<py::tuple>(value);
            materials.emplace(entity<CMaterialPublic>(item[0], DEEPDRAW_CMaterial),
                py::cast<std::shared_ptr<RBaseMaterial>>(item[1]));
        }
    }
};
class MeshCache;
std::set<MeshCache*>& live_caches() {
    static std::set<MeshCache*> caches;
    return caches;
}
class MeshCache {
public:
    std::unique_ptr<RVBOCache> cache;
    std::vector<std::shared_ptr<RBaseMaterial>> materials;
    HGLRC owner = nullptr;
    MeshCache() { live_caches().insert(this); }
    ~MeshCache() {
        // GC may run without a current GL context. Explicit close is preferred.
        if (cache) pending().emplace_back(owner, std::move(cache));
        live_caches().erase(this);
    }
    void close() {
        if (!cache) return;
        require_context();
        if (owner != current_context()) throw std::runtime_error("MeshCache belongs to another GL context");
        cache->Clear();
        cache.reset();
        materials.clear();
        owner = nullptr;
    }
    void build(py::list faces, py::list edges, MeshBuildSession* session) {
        require_context();
        if (owner && owner != current_context()) throw std::runtime_error("MeshCache belongs to another GL context");
        std::vector<std::unique_ptr<RFaceGroup>> face_storage;
        std::vector<std::unique_ptr<REdgeGroup>> edge_storage;
        std::vector<std::unique_ptr<RMaterialGroup>> group_storage;
        std::map<RBaseMaterial*, std::vector<RFaceGroup*>> by_material;
        std::vector<std::shared_ptr<RBaseMaterial>> keep_materials;
        std::vector<REdgeGroup*> edge_groups;
        // Face batch: (capsules, affine12, Material or None).
        for (auto item : faces) {
            auto batch = py::cast<py::tuple>(item);
            if (batch.size() != 3) throw py::value_error("Face batch requires entities, matrix, material");
            auto matrix = matrix_from_values(py::cast<Matrix>(batch[1]));
            std::vector<CFacePublic*> entities;
            for (auto value : py::cast<py::list>(batch[0])) entities.push_back(entity<CFacePublic>(value, DEEPDRAW_CFace));
            auto material = batch[2].is_none() ? std::shared_ptr<RBaseMaterial>() : py::cast<std::shared_ptr<RBaseMaterial>>(batch[2]);
            keep_materials.push_back(material);
            face_storage.emplace_back(new RFaceGroup(entities, matrix));
            by_material[material.get()].push_back(face_storage.back().get());
        }
        // Edge batch: (capsules, affine12).
        for (auto item : edges) {
            auto batch = py::cast<py::tuple>(item);
            if (batch.size() != 2) throw py::value_error("Edge batch requires entities, matrix");
            auto matrix = matrix_from_values(py::cast<Matrix>(batch[1]));
            std::vector<CEdgePublic*> entities;
            for (auto value : py::cast<py::list>(batch[0])) entities.push_back(entity<CEdgePublic>(value, DEEPDRAW_CEdge));
            edge_storage.emplace_back(new REdgeGroup(entities, matrix));
            edge_groups.push_back(edge_storage.back().get());
        }
        std::vector<RMaterialGroup*> groups;
        for (auto& entry : by_material) {
            group_storage.emplace_back(new RMaterialGroup(entry.second, entry.first));
            groups.push_back(group_storage.back().get());
        }
        auto replacement = std::make_unique<RVBOCache>();
        try { replacement->Build(groups, edge_groups, session); }
        catch (...) { replacement->Clear(); throw; }
        close();
        owner = current_context();
        cache = std::move(replacement);
        materials = std::move(keep_materials);
    }
    py::object build_component(py::handle capsule, ComponentBuildSession& session) {
        require_context();
        if (owner && owner != current_context()) throw std::runtime_error("MeshCache belongs to another GL context");
        void* ptr = PyCapsule_GetPointer(capsule.ptr(), deepdraw_bridge::entity_name);
        if (!ptr) throw py::error_already_set();
        auto* base = static_cast<CEntityPublic*>(ptr);
        if (base->GetType() != DEEPDRAW_CComponent && base->GetType() != DEEPDRAW_CComponentDefinition)
            throw py::type_error("Component capsule required");
        auto* comp = static_cast<CComponentPublic*>(base);
        std::map<RBaseMaterial*, std::vector<CFacePublic*>> faces;
        std::vector<CEdgePublic*> edges;
        std::vector<std::shared_ptr<RBaseMaterial>> retained;
        auto release = [](IEntityIteratorPublic* iter) { if (iter) iter->Release(); };
        std::unique_ptr<IEntityIteratorPublic, decltype(release)> iter(comp->EnumEntities(), release);
        CEntityPublic* e = nullptr;
        while (iter->Next(&e)) {
            if (e->IsMarkedDeleted()) continue;
            int type = e->GetType();
            if (type != DEEPDRAW_CFace && type != DEEPDRAW_CEdge) continue;
            auto* drawing = static_cast<CDrawingElementPublic*>(e);
            // Layer visibility is not exposed by the public API. Fall back
            // atomically before replacing any existing GPU cache.
            if (drawing->HasLayer()) return py::none();
            if (drawing->IsHide()) continue;
            if (type == DEEPDRAW_CEdge) edges.push_back(static_cast<CEdgePublic*>(e));
            else {
                auto* face = static_cast<CFacePublic*>(e);
                auto* material = face->GetMaterial();
                RBaseMaterial* snapshot = nullptr;
                if (material) {
                    auto found = session.materials.find(material);
                    if (found == session.materials.end()) return py::none();
                    snapshot = found->second.get();
                }
                faces[snapshot].push_back(face);
            }
        }
        CMatrix identity;
        std::vector<std::unique_ptr<RFaceGroup>> face_storage;
        std::vector<std::unique_ptr<RMaterialGroup>> material_storage;
        std::vector<RMaterialGroup*> groups;
        for (auto& entry : faces) {
            face_storage.emplace_back(new RFaceGroup(entry.second, identity));
            std::vector<RFaceGroup*> one { face_storage.back().get() };
            material_storage.emplace_back(new RMaterialGroup(one, entry.first));
            groups.push_back(material_storage.back().get());
        }
        std::vector<int> material_ids;
        for (auto& entry : session.materials)
            if (faces.count(entry.second.get())) {
                retained.push_back(entry.second);
                material_ids.push_back(entry.first->GetID());
            }
        REdgeGroup edge_group(edges, identity);
        std::vector<REdgeGroup*> edge_groups;
        if (!edges.empty()) edge_groups.push_back(&edge_group);
        auto replacement = std::make_unique<RVBOCache>();
        try { replacement->Build(groups, edge_groups); }
        catch (...) { replacement->Clear(); throw; }
        close();
        owner = current_context();
        cache = std::move(replacement);
        materials = std::move(retained);
        return py::cast(material_ids);
    }
    void draw(int pass) {
        check_pass(pass);
        require_context();
        if (!cache) return;
        if (owner != current_context()) throw std::runtime_error("MeshCache belongs to another GL context");
        cache->Draw(pass);
    }
    bool has_geometry(int pass) {
        check_pass(pass);
        return cache && cache->HasGeomtry(pass);
    }
    void draw_opaque(bool inherited) {
        require_context();
        if(!cache) return;
        if(owner!=current_context()) throw std::runtime_error("MeshCache belongs to another GL context");
        cache->DrawOpaque(inherited);
    }
};
void release_shadows(HGLRC context);
void release_context() {
    auto context = current_context();
    release_shadows(context);
    for (auto* cache : live_caches()) if (cache->owner == context) cache->close();
    collect();
    if (loaded_context == context) loaded_context = nullptr;
}
#include "transform_tree.h"
#include "draw_list.h"
#include "shadow_map.h"
}
PYBIND11_MODULE(deepdraw_render, m) {
    m.def("begin_statistics", []() {render_statistics={};render_statistics.enabled=true;});
    m.def("statistics_snapshot", []() {
        return std::array<unsigned long long,3>{render_statistics.calls,render_statistics.triangles,render_statistics.lines};
    });
    m.def("end_statistics", []() {
        render_statistics.enabled=false;
        py::dict result;
        result["draw_calls"]=render_statistics.calls;
        result["triangles"]=render_statistics.triangles;
        result["lines"]=render_statistics.lines;
        return result;
    });
    m.doc() = "DeepDraw render backend; entity capsules are consumed synchronously";
    m.attr("API_VERSION") = 1;
    py::class_<ShadowMap>(m,"ShadowMap")
        .def(py::init<>()).def("configure",&ShadowMap::configure)
        .def("render",&ShadowMap::render).def("begin_receive",&ShadowMap::begin_receive)
        .def("end_receive",&ShadowMap::end_receive).def("close",&ShadowMap::close)
        .def_readonly("updates",&ShadowMap::updates);
    py::class_<DrawList>(m, "DrawList")
        .def(py::init<>()).def("set", &DrawList::set)
        .def("update", &DrawList::update)
        .def("set_hierarchy", &DrawList::set_hierarchy)
        .def("update_instances", &DrawList::update_instances)
        .def("world_matrix", &DrawList::world_matrix)
        .def("set_pending", &DrawList::pending_indices)
        .def("visible_pending", &DrawList::visible_pending)
        .def("set_editing_data", &DrawList::editing_data)
        .def("update_materials", &DrawList::update_materials)
        .def("set_edit_context", &DrawList::edit_context)
        .def("enabled_indices", &DrawList::enabled_indices, py::arg("part")=-1)
        .def("visible_batch_pending", &DrawList::visible_batch_pending)
        .def("clear_batch_pending", &DrawList::clear_batch_pending)
        .def_property_readonly("transform_revision", &DrawList::transform_revision)
        .def("bounds", &DrawList::bounds).def("draw_opaque", &DrawList::draw_opaque, py::arg("parent_mirror"),py::arg("part")=-1)
        .def("set_selection", &DrawList::selection)
        .def("set_size_filter", &DrawList::size_filter)
        .def("cull", &DrawList::cull).def("visible_indices", &DrawList::indices, py::arg("part")=-1)
        .def("draw", &DrawList::draw)
        .def("statistics", &DrawList::statistics, py::arg("part")=-1);
    // Input planes point inward: n dot p + w >= 0. Return source indices only.
    // Numeric boundary avoids borrowing model/instance/filter pointers.
    m.def("filter_bounds", [](const std::vector<std::array<double, 4>>& planes,
                              const std::vector<std::array<double, 6>>& bounds,
                              const std::vector<Matrix>& transforms) {
        if (bounds.size() != transforms.size()) throw py::value_error("Bounds/transform count mismatch");
        for (const auto& plane : planes) {
            for (double v : plane) if (!std::isfinite(v)) throw py::value_error("Invalid clip plane");
            if (plane[0] == 0 && plane[1] == 0 && plane[2] == 0) throw py::value_error("Zero clip normal");
        }
        std::vector<size_t> result;
        for (size_t i = 0; i < bounds.size(); ++i) {
            const auto& b = bounds[i];
            auto matrix = matrix_from_values(transforms[i]);
            bool empty = false;
            for (int c = 0; c < 3; ++c) {
                if (!std::isfinite(b[2*c]) || !std::isfinite(b[2*c+1])) throw py::value_error("Invalid bounds");
                empty = empty || b[2*c] > b[2*c+1];
            }
            if (empty) continue;
            double lo[3], hi[3];
            for (int r = 0; r < 3; ++r) {
                lo[r] = hi[r] = matrix.m[3][r];
                for (int c = 0; c < 3; ++c) {
                    double a = matrix.m[r][c] * b[2*c];
                    double z = matrix.m[r][c] * b[2*c+1];
                    lo[r] += (std::min)(a, z);
                    hi[r] += (std::max)(a, z);
                }
            }
            bool visible = true;
            for (const auto& p : planes) {
                double distance = p[3];
                for (int c = 0; c < 3; ++c) distance += p[c] * (p[c] >= 0 ? hi[c] : lo[c]);
                if (distance < -1e-7) { visible = false; break; }
            }
            if (visible) result.push_back(i);
        }
        return result;
    });
    m.def("init_opengl", []() { initialize_context(); collect(); });
    m.def("collect_garbage", &collect);
    m.def("release_context", &release_context);
    py::class_<RBaseMaterial, std::shared_ptr<RBaseMaterial>>(m, "Material")
        .def(py::init([](int type, std::array<double, 3> color, bool transparent,
                         double opacity, int texture, std::array<double, 2> size) {
            if (type < 0 || type > 2 || texture < 0 || (type == 2 && texture == 0))
                throw py::value_error("Invalid material type or texture");
            for (double c : color) if (!std::isfinite(c)) throw py::value_error("Invalid color");
            if (!std::isfinite(opacity) || opacity < 0 || opacity > 1)
                throw py::value_error("Opacity must be in [0, 1]");
            for (double v : size) if (!std::isfinite(v) || v <= 0) throw py::value_error("Texture sizes must be positive");
            auto result = std::make_shared<RBaseMaterial>();
            result->type = type;
            result->color = {color[0], color[1], color[2]};
            result->use_opacity = transparent;
            result->opacity = opacity;
            result->gl_tex = texture;
            result->size_u = size[0]; result->size_v = size[1];
            return result;
        }), py::arg("type"), py::arg("color"), py::arg("transparent"),
            py::arg("opacity"), py::arg("texture"), py::arg("texture_size"))
        .def("bind", [](RBaseMaterial& material) { require_context(); material.Bind(); })
        .def("update", [](RBaseMaterial& material, const RBaseMaterial& values) { material = values; })
        .def("is_transparent", &RBaseMaterial::IsOpacity);
    py::class_<ComponentBuildSession>(m, "ComponentBuildSession")
        .def(py::init<py::list>());
    py::class_<MeshBuildSession>(m, "MeshBuildSession")
        .def(py::init<size_t>(), py::arg("limit") = 128 * 1024 * 1024)
        .def_readonly("hits", &MeshBuildSession::hits)
        .def_readonly("misses", &MeshBuildSession::misses)
        .def_readonly("estimated_bytes", &MeshBuildSession::bytes);
    py::class_<MeshCache, std::shared_ptr<MeshCache>>(m, "MeshCache")
        .def(py::init<>())
        .def("build", &MeshCache::build, py::arg("faces"), py::arg("edges"), py::arg("session") = nullptr)
        .def("build_component", &MeshCache::build_component)
        .def("draw", &MeshCache::draw)
        .def("draw_opaque", &MeshCache::draw_opaque)
        .def("close", &MeshCache::close)
        .def("has_geometry", &MeshCache::has_geometry);
}
