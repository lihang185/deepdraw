// Numeric transform hierarchy. No retained engine pointers or Python objects.
class TransformTree {
public:
    using Bounds = std::array<double, 6>;
    struct Node {
        int parent;
        size_t end;
        long long instance, definition;
        Matrix local, world;
        Bounds local_bounds, own_bounds, bounds;
        std::vector<size_t> children;
        size_t dirty_epoch = 0;
    };
    std::vector<Node> nodes;
    size_t revision = 0, matrix_updates = 0, bounds_refits = 0, batches = 0;
private:
    Matrix root;
    std::map<long long, std::vector<size_t>> instances, definitions;
    static bool empty(const Bounds& b) { return b[0]>b[1] || b[2]>b[3] || b[4]>b[5]; }
    static void validate(const Bounds& b) {
        for (double v:b) if (!std::isfinite(v)) throw py::value_error("Invalid local bounds");
    }
    static void unite(Bounds& target, const Bounds& value) {
        if(empty(value)) return;
        if(empty(target)) {target=value;return;}
        for(int c=0;c<3;++c) {
            target[c*2]=(std::min)(target[c*2],value[c*2]);
            target[c*2+1]=(std::max)(target[c*2+1],value[c*2+1]);
        }
    }
    static Matrix multiply(const Matrix& a, const Matrix& b) {
        Matrix result{};
        for(int r=0;r<3;++r) {
            for(int c=0;c<3;++c) for(int k=0;k<3;++k)
                result[r*3+c]+=a[r*3+k]*b[k*3+c];
            result[9+r]=a[9+r];
            for(int k=0;k<3;++k) result[9+r]+=a[r*3+k]*b[9+k];
        }
        return result;
    }
    static Bounds transform(const Bounds& b, const Matrix& m) {
        Bounds result={1,-1,1,-1,1,-1};
        if(empty(b)) return result;
        for(int r=0;r<3;++r) {
            double lo=m[9+r],hi=lo;
            for(int c=0;c<3;++c) {
                double a=m[r*3+c]*b[c*2],z=m[r*3+c]*b[c*2+1];
                lo+=(std::min)(a,z);hi+=(std::max)(a,z);
            }
            result[r*2]=lo;result[r*2+1]=hi;
        }
        return result;
    }
    void dirty(size_t index, std::vector<size_t>& indices) {
        for(int i=static_cast<int>(index);i>=0;i=nodes[i].parent) {
            auto& n=nodes[i];
            if(n.dirty_epoch==revision) break;
            n.dirty_epoch=revision;indices.push_back(i);
        }
    }
public:
    void set(py::list source, const Matrix& root_matrix) {
        matrix_from_values(root_matrix);
        TransformTree next;
        next.root=root_matrix;
        for(auto value:source) {
            auto row=py::cast<py::tuple>(value);
            if(row.size()!=5) throw py::value_error("Hierarchy row requires parent, instance, definition, local matrix, local bounds");
            Node n;
            n.parent=py::cast<int>(row[0]);
            if(n.parent < -1 || n.parent >= static_cast<int>(next.nodes.size()))
                throw py::value_error("Hierarchy parent must precede child");
            if(n.parent>=0) {
                int ancestor=static_cast<int>(next.nodes.size())-1;
                while(ancestor>n.parent) ancestor=next.nodes[ancestor].parent;
                if(ancestor!=n.parent) throw py::value_error("Hierarchy must be in subtree preorder");
            }
            n.instance=py::cast<long long>(row[1]);n.definition=py::cast<long long>(row[2]);
            n.local=py::cast<Matrix>(row[3]);matrix_from_values(n.local);
            n.local_bounds=py::cast<Bounds>(row[4]);validate(n.local_bounds);
            n.world=multiply(n.parent>=0 ? next.nodes[n.parent].world:root_matrix,n.local);
            n.own_bounds=transform(n.local_bounds,n.world);n.bounds=n.own_bounds;
            size_t index=next.nodes.size();n.end=index+1;
            if(n.instance>=0) next.instances[n.instance].push_back(index);
            next.definitions[n.definition].push_back(index);
            next.nodes.push_back(std::move(n));
            if(next.nodes[index].parent>=0) next.nodes[next.nodes[index].parent].children.push_back(index);
        }
        for(size_t i=next.nodes.size();i-->0;) {
            auto& n=next.nodes[i];
            if(n.parent>=0) {
                auto& p=next.nodes[n.parent];p.end=(std::max)(p.end,n.end);unite(p.bounds,n.bounds);
            }
        }
        next.revision=revision+1;
        *this=std::move(next);
    }
    std::vector<size_t> update(py::list local_changes, py::list bound_changes) {
        // Validate the complete transaction before modifying any persistent state.
        std::map<long long,Matrix> locals;
        std::map<long long,Bounds> boxes;
        for(auto value:local_changes) {
            auto row=py::cast<py::tuple>(value);
            if(row.size()!=2) throw py::value_error("Local update requires instance ID and matrix");
            auto matrix=py::cast<Matrix>(row[1]);matrix_from_values(matrix);
            locals[py::cast<long long>(row[0])]=matrix;
        }
        for(auto value:bound_changes) {
            auto row=py::cast<py::tuple>(value);
            if(row.size()!=2) throw py::value_error("Bounds update requires definition ID and bounds");
            auto box=py::cast<Bounds>(row[1]);validate(box);
            boxes[py::cast<long long>(row[0])]=box;
        }
        std::set<size_t> roots, changed_boxes;
        for(const auto& value:locals) {
            auto found=instances.find(value.first);if(found==instances.end()) continue;
            for(auto index:found->second) {nodes[index].local=value.second;roots.insert(index);}
        }
        for(const auto& value:boxes) {
            auto found=definitions.find(value.first);if(found==definitions.end()) continue;
            for(auto index:found->second) {nodes[index].local_bounds=value.second;changed_boxes.insert(index);}
        }
        if(roots.empty() && changed_boxes.empty()) return {};
        ++revision;++batches;
        std::vector<size_t> changed;
        size_t end=0;
        // Preorder subtree ranges deduplicate simultaneous parent and child edits.
        for(auto start:roots) {
            if(start<end) continue;
            end=nodes[start].end;
            for(size_t i=start;i<end;++i) {
                auto& n=nodes[i];
                n.world=multiply(n.parent>=0 ? nodes[n.parent].world:root,n.local);
                n.own_bounds=transform(n.local_bounds,n.world);++matrix_updates;
                dirty(i,changed);
            }
        }
        for(auto index:changed_boxes) {
            auto& n=nodes[index];n.own_bounds=transform(n.local_bounds,n.world);
            dirty(index,changed);
        }
        std::sort(changed.begin(),changed.end(),std::greater<size_t>());
        for(auto index:changed) {
            auto& n=nodes[index];n.bounds=n.own_bounds;
            for(auto child:n.children) unite(n.bounds,nodes[child].bounds);
        }
        bounds_refits+=changed.size();
        return changed;
    }
};
