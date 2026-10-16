#include "handles.h"
#include <SketchUpAPI/sketchup.h>

template<class T, class F> static py::object owned(T* ptr, F release) {
    if (!ptr) throw std::runtime_error("SketchUp SDK allocation failed");
    auto life = std::make_shared<Lifetime>();
    life->ptr=ptr; life->dispose=[ptr,release] {release(ptr);};
    return wrap(ptr,life);
}
template<class T> static auto existing(py::module_& m,const char* name) {
    return py::reinterpret_borrow<py::class_<Handle<T>>>(m.attr(name));
}
static void transfer(std::shared_ptr<Lifetime> child,std::shared_ptr<Lifetime> parent) {
    child->dispose=nullptr;
    child->parent=parent;
}
static void transferable(std::shared_ptr<Lifetime> child) {
    child->check();
    if (!child->dispose || child->parent) throw py::value_error("Resource already belongs to a model");
}
static void consumed(std::shared_ptr<Lifetime> life) {life->dispose=nullptr;life->valid=false;}
void bind_builders(py::module_& m) {
    auto model=existing<SUModel>(m,"SUModel");
    auto material=existing<SUMaterial>(m,"SUMaterial");
    auto texture=existing<SUTexture>(m,"SUTexture");
    auto definition=existing<SUComponentDefinition>(m,"SUComponentDefinition");
    auto entities=existing<SUEntities>(m,"SUEntities");
    material.def_static("Create",[] {return owned(SUMaterial::Create(),[](SUMaterial* p) {SUMaterialRef r{p};SUMaterialRelease(&r);});});
    texture.def_static("CreateFromFile",[](std::string path,double u,double v) {
        return owned(SUTexture::CreateFromFile(path,u,v),[](SUTexture* p) {SUTextureRef r{p};SUTextureRelease(&r);});
    });
    // Replace the generic setter: SU material consumes the texture allocation.
    material.attr("SetTexture") = py::cpp_function([](Handle<SUMaterial>& a,Handle<SUTexture>& b) {
        transferable(b.life);a.get()->SetTexture(b.get());transfer(b.life,a.life);
    },py::is_method(material));
    definition.def_static("Create",[] {return owned(SUComponentDefinition::Create(),[](SUComponentDefinition* p) {SUComponentDefinitionRef r{p};SUComponentDefinitionRelease(&r);});});
    definition.def("CreateInstance",[](Handle<SUComponentDefinition>& h) {
        return owned(h.get()->CreateInstance(),[](SUComponentInstance* p) {SUComponentInstanceRef r{p};SUComponentInstanceRelease(&r);});
    },py::keep_alive<0,1>());
    model.def("AddMaterial",[](Handle<SUModel>& a,Handle<SUMaterial>& b) {
        transferable(b.life);a.get()->AddMaterial(b.get());transfer(b.life,a.life);
    });
    model.def("AddComponentDefinition",[](Handle<SUModel>& a,Handle<SUComponentDefinition>& b) {
        transferable(b.life);a.get()->AddComponentDefinition(b.get());transfer(b.life,a.life);
    });
    entities.def("AddInstance",[](Handle<SUEntities>& a,Handle<SUComponentInstance>& b) {
        transferable(b.life);a.get()->AddInstance(b.get());transfer(b.life,a.life);
    });
    auto loop=handle_class<SULoopInput>(m,"SULoopInput");
    loop.def_static("Create",[] {return owned(SULoopInput::Create(),[](SULoopInput* p) {p->Release();});});
    loop.def("Release",[](Handle<SULoopInput>& h) {h.life->release();});
    bind(loop,"AddVertexIndex",&SULoopInput::AddVertexIndex);
    bind(loop,"EdgeSetHidden",&SULoopInput::EdgeSetHidden);
    bind(loop,"EdgeSetSoft",&SULoopInput::EdgeSetSoft);
    bind(loop,"EdgeSetSmooth",&SULoopInput::EdgeSetSmooth);
    py::class_<SUTextureCoordInput>(m,"SUTextureCoordInput").def(py::init<>()).def("AddTexCoord",&SUTextureCoordInput::AddTexCoord);
    auto geometry=handle_class<SUGeometryInput>(m,"SUGeometryInput");
    geometry.def_static("Create",[] {return owned(SUGeometryInput::Create(),[](SUGeometryInput* p) {p->Release();});});
    geometry.def("Release",[](Handle<SUGeometryInput>& h) {h.life->release();});
    bind(geometry,"AddVertex",&SUGeometryInput::AddVertex);
    bind(geometry,"AddEdge",&SUGeometryInput::AddEdge);
    bind(geometry,"EdgeSetSoft",&SUGeometryInput::EdgeSetSoft);
    bind(geometry,"EdgeSetSmooth",&SUGeometryInput::EdgeSetSmooth);
    geometry.def("AddFace",[](Handle<SUGeometryInput>& g,Handle<SULoopInput>& l) {
        auto index=g.get()->AddFace(l.get()); consumed(l.life);return index;
    });
    geometry.def("FaceAddInnerLoop",[](Handle<SUGeometryInput>& g,int index,Handle<SULoopInput>& l) {
        g.get()->FaceAddInnerLoop(index,l.get());consumed(l.life);
    });
    geometry.def("FaceSetFrontMaterial",[](Handle<SUGeometryInput>& g,int index,Handle<SUMaterial>& mat,SUTextureCoordInput* tc) {
        g.get()->FaceSetFrontMaterial(index,mat.get(),tc);
    },py::keep_alive<1,3>());
    geometry.def("FaceSetBackMaterial",[](Handle<SUGeometryInput>& g,int index,Handle<SUMaterial>& mat,SUTextureCoordInput* tc) {
        g.get()->FaceSetBackMaterial(index,mat.get(),tc);
    },py::keep_alive<1,3>());
    entities.def("Fill",[](Handle<SUEntities>& e,Handle<SUGeometryInput>& g,bool weld) {e.get()->Fill(g.get(),weld);});
}
