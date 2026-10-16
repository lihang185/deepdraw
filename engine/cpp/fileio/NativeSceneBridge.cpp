#include "NativeSceneBridge.h"
#include <unordered_map>
#include <memory>
#include <stdexcept>
#include <algorithm>

namespace ddfile {
namespace {
struct IteratorDelete {void operator()(IEntityIteratorPublic* p)const{if(p)p->Release();}};
using Iterator=std::unique_ptr<IEntityIteratorPublic,IteratorDelete>;
struct Capture {
    Scene s;
    std::unordered_map<const void*,Id> vertex,edge,use,loop,uv,face,dib,texture,material,instance,definition;
    std::unordered_map<const void*,Ref> entities;
    std::vector<CComponentDefinitionPublic*> comps;
    std::unordered_map<const void*,Id> layer;
    void live(CEntityPublic* p){if(!p||p->IsMarkedDeleted())throw std::runtime_error("Invalid/deleted entity reference");}
    void drawing(CDrawingElementPublic* p){live(p);}
    Id layer_id(CDrawingElementPublic* p){auto* l=p->GetLayer();if(!l)return null_id;
        auto it=layer.find(l);if(it==layer.end())throw std::runtime_error("Unregistered layer");return it->second;}
    Id add_vertex(CVertexPublic* p){live(p);auto found=vertex.find(p);if(found!=vertex.end())return found->second;
        Id id=s.vertices.size();vertex[p]=id;entities[p]={Kind::Vertex,id};auto v=p->Pos();s.vertices.push_back({v.x,v.y,v.z});return id;}
    Id add_edge(CEdgePublic* p){drawing(p);auto found=edge.find(p);if(found!=edge.end())return found->second;
        Edge r;r.start=add_vertex(p->GetStartVertex());r.end=add_vertex(p->GetEndVertex());r.hidden=p->IsHide();r.soft=p->IsSoft();r.smooth=p->IsSmooth();
        r.layer=layer_id(p);Id id=s.edges.size();edge[p]=id;entities[p]={Kind::Edge,id};s.edges.push_back(r);return id;}
    Id add_use(CEdgeUsePublic* p){live(p);auto found=use.find(p);if(found!=use.end())return found->second;
        EdgeUse r;r.edge=add_edge(p->GetEdge());r.reversed=p->IsEdgeReversed();Id id=s.edge_uses.size();use[p]=id;entities[p]={Kind::EdgeUse,id};s.edge_uses.push_back(r);return id;}
    Id add_loop(CLoopPublic* p){live(p);auto found=loop.find(p);if(found!=loop.end())return found->second;
        Loop r;r.outer=p->IsOuterLoop();r.convex=p->IsConvex();Iterator it(p->EnumEdgeUse());CEdgeUsePublic* child=nullptr;
        while(it->Next(&child))r.uses.push_back(add_use(child));Id id=s.loops.size();loop[p]=id;entities[p]={Kind::Loop,id};s.loops.push_back(std::move(r));return id;}
    Id add_uv(CFaceTextureCoordsPublic* p){if(!p)return null_id;live(p);auto found=uv.find(p);if(found!=uv.end())return found->second;
        auto m=p->GetFrontTextureCoords();UV r;for(int i=0;i<3;++i)for(int j=0;j<3;++j)r[i*3+j]=m.m[i][j];Id id=s.uvs.size();uv[p]=id;s.uvs.push_back(r);return id;}
    Id add_dib(CDibPublic* p){if(!p)return null_id;live(p);auto found=dib.find(p);if(found!=dib.end())return found->second;
        int length=p->GetLength();if(length<0)throw std::runtime_error("Invalid image length");std::vector<std::uint8_t> bytes(length);if(length)p->GetData(bytes.data(),length);
        Id id=s.images.size();dib[p]=id;s.images.push_back(std::move(bytes));return id;}
    Id add_texture(CTexturePublic* p){if(!p)return null_id;live(p);auto found=texture.find(p);if(found!=texture.end())return found->second;
        Texture r;r.name=p->GetName();r.size_u=p->GetSizeU();r.size_v=p->GetSizeV();r.image=add_dib(p->GetDib());Id id=s.textures.size();texture[p]=id;s.textures.push_back(std::move(r));return id;}
    Id add_material(CMaterialPublic* p){if(!p)return null_id;live(p);auto found=material.find(p);if(found!=material.end())return found->second;
        Material r;r.name=p->GetName();auto c=p->GetColor();r.color={c.x,c.y,c.z};r.use_opacity=p->IsOpacity();r.opacity=p->GetOpacity();r.texture=add_texture(p->GetTexture());
        Id id=s.materials.size();material[p]=id;s.materials.push_back(std::move(r));return id;}
    Id add_face(CFacePublic* p){drawing(p);auto found=face.find(p);if(found!=face.end())return found->second;
        Face r;r.layer=layer_id(p);r.hidden=p->IsHide();auto plane=p->GetPlane();r.plane={plane.x,plane.y,plane.z,plane.w};
        for(int i=0;i<p->GetNumLoops();++i)r.loops.push_back(add_loop(p->GetLoop(i)));r.material=add_material(p->GetMaterial());r.uv=add_uv(p->GetTextureCoords());
        Id id=s.faces.size();face[p]=id;entities[p]={Kind::Face,id};s.faces.push_back(std::move(r));return id;}
    Id register_definition(CComponentDefinitionPublic* p){drawing(p);auto found=definition.find(p);if(found!=definition.end())return found->second;
        if(p->IsHide()||p->HasLayer())throw std::runtime_error("Native format does not support hidden/layered definitions");
        Id id=s.definitions.size();definition[p]=id;entities[p]={Kind::Definition,id};s.definitions.emplace_back();comps.push_back(p);return id;}
    Id add_instance(CComponentInstancePublic* p){drawing(p);auto found=instance.find(p);if(found!=instance.end())return found->second;
        Instance r;r.layer=layer_id(p);r.name=p->GetName();r.hidden=p->IsHide();r.group=p->IsGroup();r.image=p->IsImage();r.material=add_material(p->GetMaterial());
        auto def=definition.find(p->GetDefinition());if(def==definition.end())throw std::runtime_error("Unregistered component definition");r.definition=def->second;
        auto m=p->GetTransform2();r.transform.scale=m.scale;r.transform.identity=m.is_identity;r.transform.orthogonal=m.is_orthogonal;
        for(int i=0;i<4;++i)for(int j=0;j<3;++j)r.transform.values[i*3+j]=m.m[i][j];
        Id id=s.instances.size();instance[p]=id;entities[p]={Kind::Instance,id};s.instances.push_back(std::move(r));return id;}
    Scene run(CModelPublic* model){
        if(!model)throw std::invalid_argument("Null model");
        for(auto* m:model->GetMaterials())s.model_materials.push_back(add_material(m));
        for(auto* l:model->GetLayers()){live(l);Layer r;r.name=l->GetName();r.hidden=l->IsHide();r.material=add_material(l->GetMaterial());
            layer[l]=s.layers.size();s.layers.push_back(std::move(r));}
        for(auto* d:model->GetDefinitions())s.model_definitions.push_back(register_definition(d));
        auto* top=model->GetTopComponent();if(!top||top->GetType()!=DEEPDRAW_CComponentDefinition)throw std::runtime_error("Top component must be a definition");
        s.top=register_definition(static_cast<CComponentDefinitionPublic*>(top));
        // Saved-view metadata contains session layer IDs, which require remapping.
        // Until that schema is supported, reject instead of silently losing visibility.
        if(!s.layers.empty()&&comps[s.top]->GetAgentHint().find(L"saved_scenes_v1")!=std::wstring::npos)
            throw std::runtime_error("Native v2 does not yet support saved-view layer visibility; use pickle DAI");
        for(Id i=0;i<comps.size();++i){auto* p=comps[i];Definition d;d.name=p->GetName();d.description=p->GetDescription();d.agent_hint=p->GetAgentHint();d.file_path=p->GetFilePath();d.dynamic=p->IsDynamicComponent();d.dynamic_comp=p->GetDynamicComponent();
            Iterator it(p->EnumEntities());CEntityPublic* e=nullptr;while(it->Next(&e)){
                if(!e||e->IsMarkedDeleted())continue;
                switch(e->GetType()){
                    case DEEPDRAW_CEdge:d.entities.push_back({Kind::Edge,add_edge(static_cast<CEdgePublic*>(e))});break;
                    case DEEPDRAW_CFace:d.entities.push_back({Kind::Face,add_face(static_cast<CFacePublic*>(e))});break;
                    case DEEPDRAW_CComponentInstance:d.entities.push_back({Kind::Instance,add_instance(static_cast<CComponentInstancePublic*>(e))});break;
                    default:throw std::runtime_error("Native format does not support this component entity (guide/section/etc)");
                }
            }s.definitions[i]=std::move(d);
        }
        for(Id i=0;i<comps.size();++i)for(auto& entry:comps[i]->GetNamedSets()){
            NamedSet r;r.name=entry.first;for(auto* e:entry.second){if(!e||e->IsMarkedDeleted())continue;auto found=entities.find(e);
                if(found==entities.end())throw std::runtime_error("Named set references an entity outside saved topology");r.members.push_back(found->second);}
            s.definitions[i].named_sets.push_back(std::move(r));
        }
        std::unordered_map<const void*,Id> seen_curves;
        std::vector<Id> edge_owner(s.edges.size(),null_id);
        for(Id d=0;d<s.definitions.size();++d)for(auto r:s.definitions[d].entities)
            if(r.kind==Kind::Edge)edge_owner[r.id]=d;
        std::vector<CEdgePublic*> ordered_edges(s.edges.size());
        for(auto& entry:edge)ordered_edges[entry.second]=(CEdgePublic*)entry.first;
        for(Id edge_id=0;edge_id<ordered_edges.size();++edge_id){auto* c=ordered_edges[edge_id]->GetCurve();if(!c||seen_curves.count(c))continue;
            live(c);Curve r;r.definition=edge_owner[edge_id];r.is_arc=c->IsArc();r.polygon=c->IsPolygon();
            auto lookup=[&](CEdgePublic* e){auto it=edge.find(e);if(it==edge.end())throw std::runtime_error("Curve references unsaved edge");return it->second;};
            r.first=lookup(c->GetFirstEdge());r.last=lookup(c->GetLastEdge());for(auto* e:c->GetEdges())r.edges.push_back(lookup(e));
            if(r.is_arc){auto a=c->GetArc();r.arc={{a.center.x,a.center.y,a.center.z},{a.xaxis.x,a.xaxis.y,a.xaxis.z},
                {a.yaxis.x,a.yaxis.y,a.yaxis.z},{a.plane.x,a.plane.y,a.plane.z,a.plane.w},a.radius,a.start_angle,a.end_angle};}
            seen_curves[c]=s.curves.size();s.curves.push_back(std::move(r));
        }
        return std::move(s);
    }
};
}
Scene CaptureNative(CModelPublic* model){return Capture().run(model);}
Status SaveNative(CModelPublic* model,const wchar_t* path,Error* error) noexcept {
    if(DDFileApiVersion()!=api_version){if(error)wcscpy_s(error->message,L"Native file DLL ABI mismatch; update engine and file DLL together");return Status::UnsupportedVersion;}
    try{auto scene=CaptureNative(model);return DDFileSave(path,&scene,error);}
    catch(const std::bad_alloc&){if(error)wcscpy_s(error->message,L"Cannot allocate native scene snapshot");return Status::OutOfMemory;}
    catch(const std::exception& e){if(error){std::size_t i=0;for(;e.what()[i]&&i<511;++i)error->message[i]=static_cast<unsigned char>(e.what()[i]);error->message[i]=0;}return Status::InvalidData;}
    catch(...){if(error)wcscpy_s(error->message,L"Native scene capture failed");return Status::InternalError;}
}
}
