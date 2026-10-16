#pragma once
// Include only in the engine's Python binding translation unit.
#include "DeepDrawFileIO.h"
#include <pybind11/pybind11.h>

namespace ddfile {
template<class Model,class... Options>
void BindNativeFileIO(pybind11::class_<Model,Options...>& cls)
{
    cls.def("SaveNativeFile", [](Model& self,const std::wstring& path) {
        Error error;
        const auto status=self.SaveNativeFile(path.c_str(),&error);
        return pybind11::make_tuple(static_cast<int>(status),std::wstring(error.message));
    },pybind11::arg("path"));
    cls.def("ReadNativeFile", [](Model& self,const std::wstring& path) {
        Error error;
        const auto status=self.ReadNativeFile(path.c_str(),&error);
        return pybind11::make_tuple(static_cast<int>(status),std::wstring(error.message));
    },pybind11::arg("path"));
}
}
