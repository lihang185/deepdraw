#pragma once
#include <pybind11/pybind11.h>

// Shared protocol, not a registration of engine classes in the render module.
namespace deepdraw_bridge {
static constexpr char entity_name[] = "deepdraw.CEntity.borrowed.v1";

// Call from editor2's bindings with a real CEntity*, never a Python address.
template<class Entity>
pybind11::capsule borrow_entity(Entity* entity) {
    if (!entity) throw pybind11::value_error("Entity pointer is null");
    PyObject* result = PyCapsule_New(static_cast<void*>(entity), entity_name, nullptr);
    if (!result) throw pybind11::error_already_set();
    return pybind11::reinterpret_steal<pybind11::capsule>(result);
}
}
