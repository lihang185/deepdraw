// Included in main.cpp's private namespace after MeshCache. No engine pointers.
class DrawList {
    using Bounds = std::array<double, 6>;
    using Plane = std::array<double, 4>;
    struct Node {
        std::shared_ptr<MeshCache> mesh;
        std::shared_ptr<RBaseMaterial> material;
        std::array<double, 16> matrix;
        Bounds bounds, own_bounds;
        int parent;
        size_t end;
        long long group;
        bool mirror, image, selected = false;
        unsigned clip_mask = 0;
        bool pending = false;
        std::shared_ptr<MeshCache> batch;
        std::shared_ptr<RBaseMaterial> local_material, edit_material;
        bool batch_pending = false, use_batch = false, inside = false;
        bool partial_batch = false;
        bool size_protected = false;
        int covered = -1;
        long long instance_id = -1;
    };
    std::vector<Node> nodes;
    std::unique_ptr<TransformTree> hierarchy;
    std::vector<int> source_to_draw;
    void sync_transform(size_t source) {
        int index=source_to_draw[source];
        if(index<0) return;
        const auto& input=hierarchy->nodes[source];
        auto& n=nodes[index];const auto& m=input.world;
        n.matrix={m[0],m[3],m[6],0,m[1],m[4],m[7],0,m[2],m[5],m[8],0,m[9],m[10],m[11],1};
        n.mirror=m[0]*(m[4]*m[8]-m[5]*m[7])-m[1]*(m[3]*m[8]-m[5]*m[6])+m[2]*(m[3]*m[7]-m[4]*m[6])<0;
        n.own_bounds=input.own_bounds;n.bounds=input.bounds;
    }
    std::vector<std::vector<size_t>> children;
    std::vector<size_t> visible;
    std::vector<size_t> transparent_visible, transparent_enabled;
    std::vector<Plane> previous_planes;
    bool culled = false;
    std::array<double,3> size_camera = {0,0,0};
    double size_ratio = 0;
    size_t size_rejected = 0;
    int active = -1;
    size_t context_changes = 0;
    std::vector<size_t> enabled;
    MeshCache* mesh(const Node& n) const {return (n.use_batch ? n.batch : n.mesh).get();}
    bool partial(const Node& n) const {return n.covered>=0 && nodes[n.covered].partial_batch;}
    MeshCache* pass_mesh(const Node& n, int pass) const {return pass==3 && partial(n) ? n.mesh.get():mesh(n);}
    void append_visible(size_t i) {
        if(static_cast<int>(i)==active) return;
        if(nodes[i].covered<0 || nodes[i].covered==static_cast<int>(i)) visible.push_back(i);
        transparent_visible.push_back(i);
    }
    bool scope(const Node& n, int part) const {return part<0 || active<0 || n.inside==(part==0);}
    size_t uploads = 0, culls = 0, plane_tests = 0, draws = 0, submissions = 0, updates = 0;
    static bool empty(const Bounds& b) { return b[0]>b[1] || b[2]>b[3] || b[4]>b[5]; }
public:
    void set(py::list source) {
        std::vector<Node> replacement;
        for (auto value : source) {
            auto t = py::cast<py::tuple>(value);
            if (t.size()!=7) throw py::value_error("Draw node requires mesh, material, affine, bounds, parent, group, image");
            Node n;
            n.mesh = py::cast<std::shared_ptr<MeshCache>>(t[0]);
            n.material = py::cast<std::shared_ptr<RBaseMaterial>>(t[1]);
            if (!n.mesh || !n.material) throw py::value_error("Draw node resources cannot be null");
            auto m = py::cast<Matrix>(t[2]);
            matrix_from_values(m); // Validate finite coefficients.
            auto b = py::cast<Bounds>(t[3]);
            for (double v : b) if (!std::isfinite(v)) throw py::value_error("Invalid bounds");
            n.parent = py::cast<int>(t[4]);
            if (n.parent < -1 || n.parent >= static_cast<int>(replacement.size()))
                throw py::value_error("Parents must precede children");
            // Ensure preorder: a new node cannot return to a closed subtree.
            if (n.parent >= 0) {
                int ancestor = static_cast<int>(replacement.size())-1;
                while (ancestor > n.parent) ancestor = replacement[ancestor].parent;
                if (ancestor != n.parent) throw py::value_error("Nodes must be in subtree preorder");
            }
            n.group = py::cast<long long>(t[5]); n.image = py::cast<bool>(t[6]);
            n.end = replacement.size()+1;
            n.matrix = {m[0],m[3],m[6],0,m[1],m[4],m[7],0,m[2],m[5],m[8],0,m[9],m[10],m[11],1};
            n.mirror = m[0]*(m[4]*m[8]-m[5]*m[7])-m[1]*(m[3]*m[8]-m[5]*m[6])+m[2]*(m[3]*m[7]-m[4]*m[6]) < 0;
            n.bounds = {1,-1,1,-1,1,-1};
            if (!empty(b)) for (int r=0;r<3;++r) {
                double lo=m[9+r], hi=lo;
                for (int c=0;c<3;++c) {
                    double a=m[r*3+c]*b[2*c], z=m[r*3+c]*b[2*c+1];
                    lo+=(std::min)(a,z); hi+=(std::max)(a,z);
                }
                n.bounds[2*r]=lo; n.bounds[2*r+1]=hi;
            }
            n.own_bounds=n.bounds;
            replacement.push_back(std::move(n));
        }
        // Union current child bounds: engine ancestor bounds may lag animation transforms.
        for (size_t i=replacement.size();i-->0;) {
            auto& n=replacement[i];
            if (n.parent<0) continue;
            auto& p=replacement[n.parent];
            p.end=(std::max)(p.end,n.end);
            if (empty(n.bounds)) continue;
            if (empty(p.bounds)) p.bounds=n.bounds;
            else for (int c=0;c<3;++c) {
                p.bounds[2*c]=(std::min)(p.bounds[2*c],n.bounds[2*c]);
                p.bounds[2*c+1]=(std::max)(p.bounds[2*c+1],n.bounds[2*c+1]);
            }
        }
        nodes.swap(replacement); visible.clear(); culled=false; ++uploads;
        transparent_visible.clear();transparent_enabled.clear();
        active=-1;enabled.clear();
        hierarchy.reset();source_to_draw.clear();
        children.assign(nodes.size(), {});
        for(size_t i=0;i<nodes.size();++i) if(nodes[i].parent>=0) children[nodes[i].parent].push_back(i);
    }
    void set_hierarchy(py::list source, const std::vector<size_t>& mapping, const Matrix& root) {
        if(mapping.size()!=nodes.size()) throw py::value_error("Hierarchy mapping must cover every draw node");
        auto next=std::make_unique<TransformTree>();next->set(source,root);
        std::vector<int> indices(next->nodes.size(),-1);
        for(size_t i=0;i<mapping.size();++i) {
            if(mapping[i]>=indices.size() || indices[mapping[i]]>=0)
                throw py::value_error("Invalid or duplicate hierarchy source index");
            indices[mapping[i]]=static_cast<int>(i);
        }
        next->revision=hierarchy ? hierarchy->revision+1:1;
        hierarchy=std::move(next);source_to_draw=std::move(indices);
        for(auto index:mapping) sync_transform(index);
        culled=false;
    }
    void update_instances(py::list locals, py::list bounds) {
        if(!hierarchy) throw py::value_error("No transform hierarchy installed");
        auto changed=hierarchy->update(locals,bounds);
        for(auto index:changed) if(source_to_draw[index]>=0) {sync_transform(index);++updates;}
        if(!changed.empty()) culled=false;
    }
    Matrix world_matrix(size_t index) const {
        if(!hierarchy || index>=hierarchy->nodes.size()) throw py::value_error("Invalid hierarchy index");
        return hierarchy->nodes[index].world;
    }
    size_t transform_revision() const {return hierarchy ? hierarchy->revision:0;}
    void update_materials(py::list source) {
        std::vector<std::pair<size_t,std::shared_ptr<RBaseMaterial>>> changes;
        for (auto item:source) {
            auto row=py::cast<py::tuple>(item);
            if(row.size()!=2) throw py::value_error("Material update requires index and material");
            auto index=py::cast<size_t>(row[0]);
            auto material=py::cast<std::shared_ptr<RBaseMaterial>>(row[1]);
            if(index>=nodes.size() || !material) throw py::value_error("Invalid material update");
            changes.emplace_back(index,std::move(material));
        }
        for(auto& change:changes) nodes[change.first].material=std::move(change.second);
        active=-1;culled=false;
    }
    void editing_data(py::list source) {
        if(source.size()!=nodes.size()) throw py::value_error("Editing data must cover all nodes");
        struct Data {long long id;std::shared_ptr<RBaseMaterial> local;std::shared_ptr<MeshCache> batch;bool pending,partial;};
        std::vector<Data> rows;
        for(auto item:source) {
            auto t=py::cast<py::tuple>(item);
            if(t.size()!=4 && t.size()!=5) throw py::value_error("Editing data requires instance, local material, batch, pending, optional partial flag");
            rows.push_back({py::cast<long long>(t[0]), t[1].is_none()?nullptr:py::cast<std::shared_ptr<RBaseMaterial>>(t[1]),
                t[2].is_none()?nullptr:py::cast<std::shared_ptr<MeshCache>>(t[2]),py::cast<bool>(t[3]),t.size()==5 && py::cast<bool>(t[4])});
        }
        for(size_t i=0;i<nodes.size();++i) {
            nodes[i].instance_id=rows[i].id;nodes[i].local_material=rows[i].local;
            nodes[i].batch=rows[i].batch;nodes[i].batch_pending=rows[i].pending;
            nodes[i].partial_batch=rows[i].partial;
        }
        active=-1;culled=false;
    }
    void edit_context(size_t index, std::shared_ptr<RBaseMaterial> default_material) {
        if(index>=nodes.size() || !default_material) throw py::value_error("Invalid editing context");
        if(active==static_cast<int>(index)) return;
        active=static_cast<int>(index);++context_changes;enabled.clear();transparent_enabled.clear();
        const auto end=nodes[index].end;
        for(size_t i=0;i<nodes.size();++i) {
            auto& n=nodes[i];n.inside=i>index && i<end;
            n.covered=n.parent>=0 ? nodes[n.parent].covered:-1;
            n.use_batch=n.covered<0 && bool(n.batch) && !(i<=index && index<n.end);
            if(n.use_batch)n.covered=static_cast<int>(i);
            n.edit_material=n.material;
            if(n.inside) {
                n.edit_material=n.local_material ? n.local_material :
                    (n.parent==active ? default_material : nodes[n.parent].edit_material);
                n.group=n.parent==active ? n.instance_id : nodes[n.parent].group;
            } else n.group=-1;
            n.selected=false;n.size_protected=false;
        }
        for(size_t i=0;i<nodes.size();) {
            if(i!=index) {
                if(nodes[i].covered<0 || nodes[i].covered==static_cast<int>(i)) enabled.push_back(i);
                transparent_enabled.push_back(i);
            }
            i=nodes[i].use_batch && !nodes[i].partial_batch ? nodes[i].end : i+1;
        }
        culled=false;
    }
    std::vector<size_t> enabled_indices(int part) const {
        std::vector<size_t> result;
        for(auto i:enabled) if(scope(nodes[i],part)) result.push_back(i);
        return result;
    }
    void update(py::list source) {
        // Validate and prepare all changes before replacing any live node.
        std::vector<std::pair<size_t,Node>> changes;
        for(auto value:source) {
            auto t=py::cast<py::tuple>(value);
            if(t.size()!=3) throw py::value_error("Update requires index, affine, bounds");
            auto i=py::cast<size_t>(t[0]);
            if(i>=nodes.size()) throw py::value_error("Invalid node index");
            auto m=py::cast<Matrix>(t[1]);matrix_from_values(m);
            auto b=py::cast<Bounds>(t[2]);
            for(double v:b) if(!std::isfinite(v)) throw py::value_error("Invalid bounds");
            Node n=nodes[i];
            n.matrix={m[0],m[3],m[6],0,m[1],m[4],m[7],0,m[2],m[5],m[8],0,m[9],m[10],m[11],1};
            n.mirror=m[0]*(m[4]*m[8]-m[5]*m[7])-m[1]*(m[3]*m[8]-m[5]*m[6])+m[2]*(m[3]*m[7]-m[4]*m[6])<0;
            n.own_bounds={1,-1,1,-1,1,-1};
            if(!empty(b)) for(int r=0;r<3;++r) {
                double lo=m[9+r],hi=lo;
                for(int c=0;c<3;++c) {
                    double a=m[r*3+c]*b[2*c],z=m[r*3+c]*b[2*c+1];
                    lo+=(std::min)(a,z);hi+=(std::max)(a,z);
                }
                n.own_bounds[2*r]=lo;n.own_bounds[2*r+1]=hi;
            }
            changes.emplace_back(i,std::move(n));
        }
        std::set<size_t,std::greater<size_t>> dirty;
        for(auto& change:changes) {
            nodes[change.first]=std::move(change.second);
            for(int i=static_cast<int>(change.first);i>=0;i=nodes[i].parent) {
                if(!dirty.insert(i).second) break;
            }
        }
        for(auto i:dirty) {
            auto& n=nodes[i];n.bounds=n.own_bounds;
            for(auto child:children[i]) {
                const auto& b=nodes[child].bounds;
                if(empty(b)) continue;
                if(empty(n.bounds)) n.bounds=b;
                else for(int c=0;c<3;++c) {
                    n.bounds[2*c]=(std::min)(n.bounds[2*c],b[2*c]);
                    n.bounds[2*c+1]=(std::max)(n.bounds[2*c+1],b[2*c+1]);
                }
            }
        }
        updates+=changes.size();if(!changes.empty()) culled=false;
    }
    void selection(const std::vector<long long>& groups) {
        std::set<long long> selected(groups.begin(),groups.end());
        bool changed=false;
        for (auto& n:nodes) {
            bool value=selected.count(n.group)!=0;
            changed|=value!=n.selected;
            n.selected=value;n.size_protected=value;
        }
        for(size_t i=nodes.size();i-->0;) if(nodes[i].size_protected && nodes[i].parent>=0)
            nodes[nodes[i].parent].size_protected=true;
        if(changed) culled=false;
    }
    void size_filter(const std::array<double,3>& camera, double ratio) {
        if(!std::isfinite(ratio) || ratio<0) throw py::value_error("Invalid size ratio");
        for(double v:camera) if(!std::isfinite(v)) throw py::value_error("Invalid camera position");
        if(ratio!=size_ratio || (ratio>0 && camera!=size_camera)) culled=false;
        size_camera=camera;size_ratio=ratio;
    }
    void cull(const std::vector<Plane>& planes) {
        if (planes.size()>6) throw py::value_error("At most six frustum planes supported");
        for (const auto& p:planes) {
            for(double v:p) if (!std::isfinite(v)) throw py::value_error("Invalid clip plane");
            if (p[0]==0 && p[1]==0 && p[2]==0) throw py::value_error("Zero clip normal");
        }
        if (culled && planes==previous_planes) {plane_tests=0;return;}
        visible.clear();transparent_visible.clear(); plane_tests=0;size_rejected=0; ++culls;
        // Empty plane set is the diagnostic no-culling path. Do not even
        // reject empty bounds: keep exactly the context/batch display nodes.
        if(planes.empty() && size_ratio==0) {
            if(active>=0) {visible=enabled;transparent_visible=transparent_enabled;}
            else for(size_t i=0;i<nodes.size();++i) append_visible(i);
            previous_planes=planes;culled=true;
            return;
        }
        for (size_t i=0;i<nodes.size();) {
            auto& n=nodes[i];
            // The editing path may have deliberately stale/dirty bounds.
            // Never reject it or inherit its plane mask into descendants.
            if(active>=0 && i<=static_cast<size_t>(active) && static_cast<size_t>(active)<n.end) {
                n.clip_mask=(1u<<planes.size())-1;
                append_visible(i);
                ++i;
                continue;
            }
            if (empty(n.bounds)) {i=n.end;continue;}
            // Test the whole subtree before its frustum planes. Covered children
            // already belong to an opaque batch: keep their transparent pass consistent.
            if(size_ratio>0 && !n.size_protected && (n.covered<0 || n.use_batch)) {
                double diameter2=0,distance2=0;
                for(int c=0;c<3;++c) {
                    double lo=n.bounds[2*c],hi=n.bounds[2*c+1];
                    diameter2+=(hi-lo)*(hi-lo);
                    double d=(std::max)(lo-size_camera[c],(std::max)(0.0,size_camera[c]-hi));
                    distance2+=d*d;
                }
                if(diameter2<size_ratio*size_ratio*distance2) {
                    size_rejected+=n.end-i;i=n.end;continue;
                }
            }
            unsigned mask=n.parent<0 ? (1u<<planes.size())-1 : nodes[n.parent].clip_mask;
            bool outside=false;
            for (size_t k=0;k<planes.size();++k) if(mask & (1u<<k)) {
                ++plane_tests;
                const auto& p=planes[k]; double lo=p[3],hi=p[3];
                for (int c=0;c<3;++c) {
                    double a=p[c]*n.bounds[2*c], b=p[c]*n.bounds[2*c+1];
                    lo+=(std::min)(a,b);hi+=(std::max)(a,b);
                }
                double epsilon=1e-7*std::sqrt(p[0]*p[0]+p[1]*p[1]+p[2]*p[2]);
                if(hi < -epsilon) {outside=true;break;}
                if(lo >= epsilon) mask &= ~(1u<<k);
            }
            if(outside) {i=n.end;continue;}
            n.clip_mask=mask;
            append_visible(i);
            i=n.use_batch && !n.partial_batch ? n.end : i+1;
        }
        previous_planes=planes;culled=true;
    }
    std::vector<size_t> indices(int part=-1) const {
        std::vector<size_t> result;for(auto i:visible) if(scope(nodes[i],part)) result.push_back(i);return result;
    }
    void pending_indices(const std::vector<size_t>& indices, bool value) {
        for(auto index:indices) if(index>=nodes.size()) throw py::value_error("Invalid pending draw index");
        for(auto index:indices) nodes[index].pending=value;
    }
    std::vector<size_t> visible_pending() const {
        std::vector<size_t> result;
        for(auto index:transparent_visible) if((!nodes[index].use_batch || partial(nodes[index])) && nodes[index].pending) result.push_back(index);
        return result;
    }
    std::vector<size_t> visible_batch_pending() const {
        std::vector<size_t> result;
        for(auto index:visible) if(nodes[index].use_batch && nodes[index].batch_pending) result.push_back(index);
        return result;
    }
    void clear_batch_pending(const std::vector<size_t>& indices) {
        for(auto i:indices) if(i>=nodes.size()) throw py::value_error("Invalid batch index");
        for(auto i:indices) nodes[i].batch_pending=false;
    }
    Bounds bounds() const {
        Bounds result={1,-1,1,-1,1,-1};
        for(const auto& n:nodes) if(n.parent<0 && !empty(n.bounds)) {
            if(empty(result)) result=n.bounds;
            else for(int c=0;c<3;++c) {
                result[2*c]=(std::min)(result[2*c],n.bounds[2*c]);
                result[2*c+1]=(std::max)(result[2*c+1],n.bounds[2*c+1]);
            }
        }
        return result;
    }
    void draw_opaque(bool parent_mirror, int part=-1) {
        require_context();auto context=current_context();
        for(auto i:visible) if(scope(nodes[i],part) && mesh(nodes[i])->cache && mesh(nodes[i])->owner!=context)
            throw std::runtime_error("DrawList mesh belongs to another GL context");
        glPushAttrib(GL_POLYGON_BIT);
        for(auto i:visible) {
            const auto& n=nodes[i];if(!scope(n,part)) continue;
            auto* cache=mesh(n)->cache.get();
            if(!cache || n.image) continue;
            bool inherited=!(active>=0?n.edit_material:n.material)->IsOpacity();
            if(!cache->HasGeomtry(1) && !(inherited && cache->HasGeomtry(0))) continue;
            glPushMatrix();glMultMatrixd(n.matrix.data());
            glFrontFace(n.mirror!=parent_mirror ? GL_CW:GL_CCW);
            cache->DrawOpaque(inherited);
            glPopMatrix();
        }
        glPopAttrib();
    }
    void draw(int pass, bool parent_mirror, bool outer, bool xray) {
        check_pass(pass);require_context();auto context=current_context();
        const auto& draw_nodes=pass==3 ? transparent_visible:visible;
        // Validate before mutating GL state, including shared resources closed/rebuilt since upload.
        for(auto i:draw_nodes) if(scope(nodes[i],outer?1:0) && pass_mesh(nodes[i],pass)->cache && pass_mesh(nodes[i],pass)->owner!=context)
            throw std::runtime_error("DrawList mesh belongs to another GL context");
        ++submissions;
        glPushAttrib(GL_POLYGON_BIT);
        for(auto i:draw_nodes) {
            const auto& n=nodes[i];if(!scope(n,outer?1:0)) continue;
            auto* cache=pass_mesh(n,pass)->cache.get();
            if(!cache || (pass==2 && n.image)) continue;
            const auto& material=active>=0?n.edit_material:n.material;
            bool transparent=material->IsOpacity();
            bool inherited=(pass==0 && !transparent) || (pass==3 && transparent);
            bool own=pass!=0 && cache->HasGeomtry(pass);
            if(!(inherited && cache->HasGeomtry(0)) && !own) continue;
            glPushMatrix(); glMultMatrixd(n.matrix.data());
            glFrontFace(n.mirror!=parent_mirror ? GL_CW:GL_CCW);
            if(pass==2) {
                if(outer) glColor3f(.5f,.8f,.8f);
                else glColor3f(0,n.selected?1.f:0.f,0);
            }
            if(inherited && cache->HasGeomtry(0)) {
                material->Bind();
                if(pass==0 && xray) {glDisable(GL_TEXTURE_2D);glColor4f(1,1,1,.3f);}
                cache->Draw(0);++draws;
            }
            if(own) {cache->Draw(pass);++draws;}
            glPopMatrix();
        }
        glPopAttrib();
    }
    py::dict statistics(int part=-1) const {
        py::dict d;
        d["uploads"]=uploads;d["culls"]=culls;d["plane_tests"]=plane_tests;
        d["size_rejected"]=size_rejected;
        d["nodes"]=active>=0 ? enabled_indices(part).size():nodes.size();d["visible_nodes"]=indices(part).size();
        d["context_changes"]=context_changes;
        d["draws"]=draws;d["submissions"]=submissions;d["updated_nodes"]=updates;
        d["hierarchy_nodes"]=hierarchy ? hierarchy->nodes.size():0;
        d["matrix_updates"]=hierarchy ? hierarchy->matrix_updates:0;
        d["bounds_refits"]=hierarchy ? hierarchy->bounds_refits:0;
        d["transform_batches"]=hierarchy ? hierarchy->batches:0;
        return d;
    }
};
