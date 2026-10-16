#include <pybind11/pybind11.h>
#include <filesystem>
#include "SkpExporter.h"
namespace py = pybind11;
static std::wstring temp_directory;

// Link to the same editor2 binary which owns this Python model. Never accept
// a legacy Shiboken allocation or a caller-supplied integer address.
static CModelPublic* current_model(py::object model) {
    auto cls = py::module_::import("editor2").attr("CModel");
    if (!py::isinstance(model,cls)) throw py::type_error("Expected current editor2.CModel; legacy models and integer pointers are not supported");
    auto address = model.attr("GetPtr")().cast<uintptr_t>();
    if (!address) throw py::value_error("Null model handle");
    return reinterpret_cast<CModelPublic*>(address);
}
static bool export_file(py::object model, std::string filename, bool selection) {
    auto* ptr = current_model(model);
    // suapi owns one balanced SDK initialization for the worker process.
    py::module_::import("suapi");
    SkpExporter exporter;
    exporter.temp_dir = temp_directory.empty() ? std::filesystem::temp_directory_path().wstring() : temp_directory;
    std::filesystem::create_directories(exporter.temp_dir);
    return selection ? exporter.ExportSelectionToFile(ptr,filename.c_str()) : exporter.ExportSceneToFile(ptr,filename.c_str());
}
PYBIND11_MODULE(skp_exporter,m) {
    m.attr("__binding__") = "pybind11";
    m.def("set_temp_dir",[](std::wstring path) {temp_directory=std::move(path);});
    m.def("export_scene_to_file",[](py::object model,std::string path) {return export_file(model,path,false);});
    m.def("export_selection_to_file",[](py::object model,std::string path) {return export_file(model,path,true);});
}
