#include <pybind11/pybind11.h>
#include <SketchUpAPI/sketchup.h>
#include "sdk_layout.h"
namespace py = pybind11;

static SUModelRef checked_model(py::object model) {
    if (!py::isinstance<py::int_>(model)) model = model.attr("GetPtr")();
    py::capsule value = py::module_::import("suapi").attr("_validate_model_ptr")(model);
    return SUModelRef{value.get_pointer()};
}
static std::string model_text(py::object model, bool description) {
    auto ref = checked_model(model);
    SUStringRef text = SU_INVALID;
    SUStringCreate(&text);
    auto result = description ? SUModelGetDescription(ref, &text) : SUModelGetName(ref, &text);
    std::string value;
    if (result == SU_ERROR_NONE) {
        size_t length=0, copied=0;
        SUStringGetUTF8Length(text,&length);
        value.resize(length+1);
        SUStringGetUTF8(text,value.size(),value.data(),&copied);
        value.resize(length);
    }
    SUStringRelease(&text);
    if (result != SU_ERROR_NONE) throw std::runtime_error("Cannot read SketchUp model metadata");
    return value;
}
// The bundled SDK exposes no public model-thumbnail API. This compatibility
// layout is pinned to the two DLL hashes recorded in README.md, worker-only.
static py::bytearray thumbnail(py::object model, bool secondary) {
    auto* ptr = static_cast<CSketchupModel*>(checked_model(model).ptr);
    auto* dib = secondary ? ptr->cdib_2 : ptr->cdib;
    if (!dib || !dib->data_buffer) return py::bytearray();
    auto* data = dib->data_buffer;
    if (!data->file_buf || data->buf_len <= 0) return py::bytearray();
    if (data->buf_len > 64*1024*1024) throw std::runtime_error("Invalid SketchUp thumbnail size");
    return py::bytearray(static_cast<char*>(data->file_buf),data->buf_len);
}
PYBIND11_MODULE(suapi_extra,m) {
    m.attr("__binding__") = "pybind11";
    m.def("sumodel_get_name",[](py::object model) {return model_text(model,false);});
    m.def("sumodel_get_description",[](py::object model) {return model_text(model,true);});
    m.def("sumodel_get_dib",[](py::object model) {return thumbnail(model,false);});
    m.def("sumodel_get_dib2",[](py::object model) {return thumbnail(model,true);});
}
