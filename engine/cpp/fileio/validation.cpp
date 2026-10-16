#include "codec.h"
#include <cmath>
#include <set>
#include <map>
#include <algorithm>

namespace ddfile {
namespace {
void check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
void ref(Id id,std::size_t n,bool nullable=false){check((nullable&&id==null_id)||id<n,"Invalid reference index");}
void flag(std::uint8_t v){check(v<=1,"Invalid boolean flag");}
template<std::size_t N> void finite(const std::array<double,N>& v){for(double x:v)check(std::isfinite(x),"Nonfinite geometry");}
void unique_ids(const std::vector<Id>& ids,std::size_t n){std::set<Id> seen;for(Id id:ids){ref(id,n);check(seen.insert(id).second,"Duplicate model resource");}}
}
void validate(const Scene& s) {
    ref(s.top,s.definitions.size());
    unique_ids(s.model_materials,s.materials.size());unique_ids(s.model_definitions,s.definitions.size());
    check(std::find(s.model_definitions.begin(),s.model_definitions.end(),s.top)==s.model_definitions.end(),"Top is in definition registry");
    check(s.model_definitions.size()+1==s.definitions.size(),"Unregistered definition");
    check(s.model_materials.size()==s.materials.size(),"Unregistered material");
    for(auto& v:s.vertices)finite(v);
    for(auto& l:s.layers){flag(l.hidden);ref(l.material,s.materials.size(),true);}
    for(auto& e:s.edges)ref(e.layer,s.layers.size(),true);
    for(auto& f:s.faces)ref(f.layer,s.layers.size(),true);
    for(auto& i:s.instances)ref(i.layer,s.layers.size(),true);
    for(auto& e:s.edges){ref(e.start,s.vertices.size());ref(e.end,s.vertices.size());check(e.start!=e.end,"Edge repeats a vertex");flag(e.hidden);flag(e.soft);flag(e.smooth);}
    for(auto& e:s.edge_uses){ref(e.edge,s.edges.size());flag(e.reversed);}
    std::vector<int> use_owner(s.edge_uses.size(),-1),loop_owner(s.loops.size(),-1);
    for(std::size_t i=0;i<s.loops.size();++i){auto& l=s.loops[i];flag(l.outer);flag(l.convex);check(l.uses.size()>=3,"Loop has fewer than three edges");
        Id last=null_id,first=null_id;
        for(Id id:l.uses){ref(id,s.edge_uses.size());check(use_owner[id]<0,"Edge use has multiple owners");use_owner[id]=int(i);
            auto& u=s.edge_uses[id];auto& e=s.edges[u.edge];Id a=u.reversed?e.end:e.start,b=u.reversed?e.start:e.end;
            if(first==null_id)first=a;else check(last==a,"Loop is not connected");last=b;
        }check(last==first,"Loop is not closed");
    }
    for(auto& uv:s.uvs)finite(uv);
    for(auto& image:s.images)check(image.size()<=INT_MAX,"Image exceeds engine CDib capacity");
    for(std::size_t i=0;i<s.faces.size();++i){auto& f=s.faces[i];flag(f.hidden);finite(f.plane);
        check(f.plane[0]!=0||f.plane[1]!=0||f.plane[2]!=0,"Zero plane normal");
        ref(f.material,s.materials.size(),true);ref(f.uv,s.uvs.size(),true);check(!f.loops.empty(),"Face has no loops");unsigned outer=0;
        for(Id id:f.loops){ref(id,s.loops.size());check(loop_owner[id]<0,"Loop has multiple owners");loop_owner[id]=int(i);outer+=s.loops[id].outer;}
        check(outer==1,"Face requires one outer loop");
    }
    for(auto& t:s.textures){ref(t.image,s.images.size(),true);check(std::isfinite(t.size_u)&&std::isfinite(t.size_v),"Nonfinite texture size");}
    for(auto& m:s.materials){finite(m.color);flag(m.use_opacity);check(std::isfinite(m.opacity)&&m.opacity>=0&&m.opacity<=1,"Invalid opacity");ref(m.texture,s.textures.size(),true);}
    for(auto& i:s.instances){finite(i.transform.values);check(std::isfinite(i.transform.scale),"Nonfinite transform scale");flag(i.transform.identity);flag(i.transform.orthogonal);
        flag(i.hidden);flag(i.group);flag(i.image);ref(i.material,s.materials.size(),true);ref(i.definition,s.definitions.size());check(i.definition!=s.top,"Instance refers to top");}
    auto validate_ref=[&](const Ref& r){switch(r.kind){
        case Kind::Vertex:ref(r.id,s.vertices.size());break;case Kind::Edge:ref(r.id,s.edges.size());break;
        case Kind::EdgeUse:ref(r.id,s.edge_uses.size());break;case Kind::Loop:ref(r.id,s.loops.size());break;
        case Kind::Face:ref(r.id,s.faces.size());break;case Kind::Instance:ref(r.id,s.instances.size());break;
        case Kind::Definition:ref(r.id,s.definitions.size());break;default:check(false,"Unknown entity kind");}};
    std::vector<Id> edge_owner(s.edges.size(),null_id),face_owner(s.faces.size(),null_id),inst_owner(s.instances.size(),null_id);
    std::vector<std::vector<Id>> children(s.definitions.size());std::vector<std::size_t> indegree(s.definitions.size());
    for(std::size_t d=0;d<s.definitions.size();++d){auto& def=s.definitions[d];flag(def.dynamic);
        for(auto r:def.entities){validate_ref(r);std::vector<Id>* owner=nullptr;
            if(r.kind==Kind::Edge)owner=&edge_owner;else if(r.kind==Kind::Face)owner=&face_owner;
            else if(r.kind==Kind::Instance){owner=&inst_owner;Id child=s.instances[r.id].definition;children[d].push_back(child);++indegree[child];}
            else check(false,"Unsupported component member in v1");
            check((*owner)[r.id]==null_id,"Entity has multiple component owners");(*owner)[r.id]=d;
        }
        std::set<std::wstring> names;for(auto& set:def.named_sets){check(names.insert(set.name).second,"Duplicate named set");for(auto r:set.members)validate_ref(r);}
    }
    for(auto id:edge_owner)check(id!=null_id,"Unowned edge");for(auto id:face_owner)check(id!=null_id,"Unowned face");for(auto id:inst_owner)check(id!=null_id,"Unowned instance");
    std::vector<bool> curved(s.edges.size());
    for(auto& c:s.curves){
        flag(c.is_arc);flag(c.polygon);ref(c.definition,s.definitions.size());
        check(!c.edges.empty()&&c.edges.size()<=INT_MAX,"Invalid curve edge count");
        ref(c.first,s.edges.size());ref(c.last,s.edges.size());
        std::set<Id> members;std::map<Id,std::vector<Id>> links;
        for(Id id:c.edges){ref(id,s.edges.size());check(!curved[id],"Edge belongs to multiple curves");curved[id]=true;
            check(edge_owner[id]==c.definition,"Curve crosses component topology");members.insert(id);
            auto& e=s.edges[id];links[e.start].push_back(e.end);links[e.end].push_back(e.start);}
        check(members.count(c.first)&&members.count(c.last),"Curve endpoints are not members");
        std::set<Id> reached;std::vector<Id> pending{links.begin()->first};
        while(!pending.empty()){Id v=pending.back();pending.pop_back();if(!reached.insert(v).second)continue;
            check(links[v].size()<=2,"Branched curve");for(Id n:links[v])pending.push_back(n);}
        check(reached.size()==links.size(),"Disconnected curve");
        if(c.is_arc){auto& a=c.arc;finite(a.center);finite(a.xaxis);finite(a.yaxis);finite(a.plane);
            check(std::isfinite(a.radius)&&a.radius>0&&std::isfinite(a.start)&&std::isfinite(a.end),"Invalid arc parameters");
            check(a.plane[0]!=0||a.plane[1]!=0||a.plane[2]!=0,"Zero arc normal");}
    }
    for(auto id:use_owner)check(id>=0,"Unowned edge use");for(auto id:loop_owner)check(id>=0,"Unowned loop");
    for(std::size_t f=0;f<s.faces.size();++f)for(Id l:s.faces[f].loops)for(Id u:s.loops[l].uses)
        check(edge_owner[s.edge_uses[u].edge]==face_owner[f],"Face crosses component topology");
    std::vector<Id> vertex_owner(s.vertices.size(),null_id),uv_owner(s.uvs.size(),null_id);
    for(std::size_t i=0;i<s.edges.size();++i)for(Id id:{s.edges[i].start,s.edges[i].end}){
        check(vertex_owner[id]==null_id||vertex_owner[id]==edge_owner[i],"Vertex crosses component topology");vertex_owner[id]=edge_owner[i];}
    for(std::size_t i=0;i<s.faces.size();++i)if(s.faces[i].uv!=null_id){auto id=s.faces[i].uv;
        check(uv_owner[id]==null_id||uv_owner[id]==face_owner[i],"UV object crosses component ownership");uv_owner[id]=face_owner[i];}
    for(Id id:vertex_owner)check(id!=null_id,"Unowned vertex");for(Id id:uv_owner)check(id!=null_id,"Unowned UV object");
    std::vector<bool> texture_used(s.textures.size()),image_used(s.images.size());
    for(auto& m:s.materials)if(m.texture!=null_id)texture_used[m.texture]=true;
    for(auto& t:s.textures)if(t.image!=null_id)image_used[t.image]=true;
    for(bool used:texture_used)check(used,"Unowned texture");for(bool used:image_used)check(used,"Unowned image");
    // Iterative cycle detection, including unused definitions; no input-controlled recursion.
    std::vector<Id> ready;for(Id i=0;i<indegree.size();++i)if(!indegree[i])ready.push_back(i);
    for(std::size_t n=0;n<ready.size();++n)for(Id c:children[ready[n]])if(!--indegree[c])ready.push_back(c);
    check(ready.size()==s.definitions.size(),"Cyclic component definitions");
}
}
