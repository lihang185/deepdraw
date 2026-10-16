#include "NativeSceneBridge.h"
#include <stdexcept>

namespace ddfile {
struct NativeLoadedData::Impl {
    struct Owned {CEntityPublic* entity;bool component,attached=false;};
    std::vector<Owned> allocated;
    CModelDataPublic* data=nullptr;
    bool transferred=false;
    ~Impl(){
        if(data)data->Release();
        if(!transferred)for(auto it=allocated.rbegin();it!=allocated.rend();++it)if(!it->attached){
            if(it->component)static_cast<CComponentPublic*>(it->entity)->ReleaseLoadedComponent();
            else it->entity->DeleteDetached();
        }
    }
    template<class T> T* own(T* p,bool component=false){
        if(!p)throw std::runtime_error("Native Load returned null");
        // Storage is reserved before any native object creation.
        allocated.push_back({p,component,false});return p;
    }
    void attach(std::size_t index){allocated.at(index).attached=true;}
};
NativeLoadedData::NativeLoadedData(std::unique_ptr<Impl> p):impl_(std::move(p)){}
NativeLoadedData::~NativeLoadedData()=default;
CModelDataPublic* NativeLoadedData::GetData()const noexcept{return impl_->data;}
void NativeLoadedData::TransferOwnership()noexcept{impl_->transferred=true;}
namespace {
template<class T> T* nullable(const std::vector<T*>& values,Id id){return id==null_id?nullptr:values.at(static_cast<std::size_t>(id));}
std::unique_ptr<NativeLoadedData> build(const Scene& s){
    auto owner=std::make_unique<NativeLoadedData::Impl>();
    const std::size_t count=s.images.size()+s.textures.size()+s.materials.size()+s.definitions.size()+s.vertices.size()+s.edges.size()+s.edge_uses.size()+s.loops.size()+s.uvs.size()+s.faces.size()+s.instances.size();
    owner->allocated.reserve(count+s.layers.size()+s.curves.size());
    std::vector<CLayerPublic*> layers(s.layers.size());
    std::vector<CDibPublic*> images(s.images.size());std::vector<CTexturePublic*> textures(s.textures.size());
    std::vector<CMaterialPublic*> materials(s.materials.size());std::vector<CComponentDefinitionPublic*> defs(s.definitions.size());
    std::vector<CVertexPublic*> vertices(s.vertices.size());std::vector<CEdgePublic*> edges(s.edges.size());
    std::vector<CEdgeUsePublic*> uses(s.edge_uses.size());std::vector<CLoopPublic*> loops(s.loops.size());
    std::vector<CFaceTextureCoordsPublic*> uvs(s.uvs.size());std::vector<CFacePublic*> faces(s.faces.size());
    std::vector<CComponentInstancePublic*> instances(s.instances.size());
    for(std::size_t i=0;i<images.size();++i)images[i]=owner->own(CDibPublic::Load(s.images[i].data(),s.images[i].size()));
    for(std::size_t i=0;i<textures.size();++i){auto& v=s.textures[i];textures[i]=owner->own(CTexturePublic::Load(v.name,v.size_u,v.size_v,nullable(images,v.image)));}
    for(std::size_t i=0;i<materials.size();++i){auto& v=s.materials[i];materials[i]=owner->own(CMaterialPublic::Load(v.name,{v.color[0],v.color[1],v.color[2]},v.use_opacity!=0,v.opacity,nullable(textures,v.texture)));}
    for(std::size_t i=0;i<layers.size();++i){auto& v=s.layers[i];layers[i]=owner->own(CLayerPublic::Load(v.name,v.hidden!=0,nullable(materials,v.material)));}
    // Empty definitions first permit forward references and arbitrary registry order.
    for(std::size_t i=0;i<defs.size();++i){auto& v=s.definitions[i];defs[i]=owner->own(CComponentDefinitionPublic::Load(v.name,v.description,v.agent_hint,v.file_path,{},{},v.dynamic!=0,v.dynamic_comp),true);}
    const auto vertices_base=owner->allocated.size();
    for(std::size_t i=0;i<vertices.size();++i){auto& v=s.vertices[i];vertices[i]=owner->own(CVertexPublic::Load({v[0],v[1],v[2]}));}
    const auto edges_base=owner->allocated.size();
    for(std::size_t i=0;i<edges.size();++i){auto& v=s.edges[i];edges[i]=owner->own(CEdgePublic::Load(v.hidden!=0,nullable(layers,v.layer),vertices[v.start],vertices[v.end],v.soft!=0,v.smooth!=0));}
    const auto uses_base=owner->allocated.size();
    for(std::size_t i=0;i<uses.size();++i){auto& v=s.edge_uses[i];uses[i]=owner->own(CEdgeUsePublic::Load(edges[v.edge],v.reversed!=0));}
    const auto loops_base=owner->allocated.size();
    for(std::size_t i=0;i<loops.size();++i){auto& v=s.loops[i];std::vector<CEdgeUsePublic*> members;members.reserve(v.uses.size());for(Id id:v.uses)members.push_back(uses[id]);loops[i]=owner->own(CLoopPublic::Load(v.outer!=0,v.convex!=0,members));}
    const auto uvs_base=owner->allocated.size();
    for(std::size_t i=0;i<uvs.size();++i){SMatrix33 m;for(int a=0;a<3;++a)for(int b=0;b<3;++b)m.m[a][b]=s.uvs[i][a*3+b];uvs[i]=owner->own(CFaceTextureCoordsPublic::Load(m));}
    const auto faces_base=owner->allocated.size();
    for(std::size_t i=0;i<faces.size();++i){auto& v=s.faces[i];std::vector<CLoopPublic*> members;members.reserve(v.loops.size());for(Id id:v.loops)members.push_back(loops[id]);
        faces[i]=owner->own(CFacePublic::Load(v.hidden!=0,nullable(layers,v.layer),{v.plane[0],v.plane[1],v.plane[2],v.plane[3]},members,nullable(materials,v.material),nullable(uvs,v.uv)));}
    const auto instances_base=owner->allocated.size();
    for(std::size_t i=0;i<instances.size();++i){auto& v=s.instances[i];SMatrix2 m;m.scale=v.transform.scale;m.is_identity=v.transform.identity!=0;m.is_orthogonal=v.transform.orthogonal!=0;
        for(int a=0;a<4;++a)for(int b=0;b<3;++b)m.m[a][b]=v.transform.values[a*3+b];
        instances[i]=owner->own(CComponentInstancePublic::Load(v.hidden!=0,nullable(layers,v.layer),v.name,m,nullable(materials,v.material),defs[v.definition],v.group!=0,v.image!=0));}
    auto resolve=[&](Ref r)->CEntityPublic*{switch(r.kind){
        case Kind::Vertex:return vertices[r.id];case Kind::Edge:return edges[r.id];case Kind::EdgeUse:return uses[r.id];case Kind::Loop:return loops[r.id];
        case Kind::Face:return faces[r.id];case Kind::Instance:return instances[r.id];case Kind::Definition:return defs[r.id];default:throw std::runtime_error("Invalid entity reference");}};
    auto attach_edge=[&](Id e){owner->attach(edges_base+e);owner->attach(vertices_base+s.edges[e].start);owner->attach(vertices_base+s.edges[e].end);};
    for(std::size_t d=0;d<defs.size();++d){
        for(auto r:s.definitions[d].entities){auto* e=resolve(r);defs[d]->AddLoadedEntity(e);
            if(r.kind==Kind::Instance)owner->attach(instances_base+r.id);
            if(r.kind==Kind::Edge)attach_edge(r.id);
            if(r.kind==Kind::Face){auto& f=s.faces[r.id];owner->attach(faces_base+r.id);if(f.uv!=null_id)owner->attach(uvs_base+f.uv);for(Id l:f.loops){owner->attach(loops_base+l);for(Id u:s.loops[l].uses){owner->attach(uses_base+u);attach_edge(s.edge_uses[u].edge);}}}
        }
        for(auto& set:s.definitions[d].named_sets){std::vector<CEntityPublic*> members;members.reserve(set.members.size());for(auto r:set.members)members.push_back(resolve(r));defs[d]->SetLoadedNamedSet(set.name,members);}
    }
    for(auto& c:s.curves){
        auto& a=c.arc;SArcData data{{a.center[0],a.center[1],a.center[2]},{a.xaxis[0],a.xaxis[1],a.xaxis[2]},
            {a.yaxis[0],a.yaxis[1],a.yaxis[2]},{a.plane[0],a.plane[1],a.plane[2],a.plane[3]},a.radius,a.start,a.end};
        auto index=owner->allocated.size();
        auto* curve=owner->own(CCurvePublic::Load(c.is_arc?&data:nullptr,edges[c.first],edges[c.last],int(c.edges.size()),c.polygon!=0));
        curve->SetLoadedParent(defs[c.definition]);
        for(Id id:c.edges)edges[id]->SetLoadedCurve(curve);
        owner->attach(index);
    }
    for(auto* def:defs)def->FinishNativeLoad();
    std::vector<CMaterialPublic*> registry_materials;registry_materials.reserve(s.model_materials.size());for(Id id:s.model_materials)registry_materials.push_back(materials[id]);
    std::vector<CComponentDefinitionPublic*> registry_defs;registry_defs.reserve(s.model_definitions.size());for(Id id:s.model_definitions)registry_defs.push_back(defs[id]);
    auto& registry_layers=layers;
    owner->data=CModelDataPublic::Load(registry_materials, registry_layers, registry_defs,defs[s.top]);
    if(!owner->data)throw std::runtime_error("Native model Load returned null");
    return std::make_unique<NativeLoadedData>(std::move(owner));
}
}
Status ReadNative(const wchar_t* path,std::unique_ptr<NativeLoadedData>& out,Error* error,const ReadLimits* limits)noexcept{
    if(DDFileApiVersion()!=api_version){out.reset();if(error)wcscpy_s(error->message,L"Native file DLL ABI mismatch; update engine and file DLL together");return Status::UnsupportedVersion;}
    out.reset();Scene* records=nullptr;Status status=DDFileRead(path,&records,limits,error);if(status!=Status::Ok)return status;
    std::unique_ptr<Scene,decltype(&DDFileRelease)> scene(records,DDFileRelease);
    try{out=build(*scene);return Status::Ok;}
    catch(const std::bad_alloc&){if(error)wcscpy_s(error->message,L"Cannot allocate native model");return Status::OutOfMemory;}
    catch(const std::exception& e){if(error){std::size_t i=0;for(;e.what()[i]&&i<511;++i)error->message[i]=static_cast<unsigned char>(e.what()[i]);error->message[i]=0;}return Status::InvalidData;}
    catch(...){if(error)wcscpy_s(error->message,L"Native model construction failed");return Status::InternalError;}
}
}
