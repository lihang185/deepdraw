#pragma once
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <functional>
#include <unordered_map>
#include <tuple>
#include "model.h"
#include <SketchUpAPI/sketchup.h>
namespace py = pybind11;

struct SDKSession {
    SDKSession() { SUInitialize(); }
    ~SDKSession() { SUTerminate(); }
};
inline std::weak_ptr<SDKSession> sdk_session;

// Real C++ wrappers: never expose the SDK's opaque allocation as a pybind object.
// All descendants share a lifetime token. Explicit Release invalidates them too.
struct Lifetime {
    std::shared_ptr<SDKSession> sdk = sdk_session.lock();
    void* ptr;
    std::function<void()> dispose;
    std::shared_ptr<Lifetime> parent;
    bool valid = true;
    ~Lifetime() { release(); }
    void check() const {
        if (!valid) throw std::runtime_error("SketchUp handle has been released");
        if (parent) parent->check();
    }
    void release() {
        if (valid) { valid = false; if (dispose) dispose(); }
    }
};
template<class T> struct Handle {
    T* ptr;
    std::shared_ptr<Lifetime> life;
    T* get() const { life->check(); return ptr; }
};
inline std::unordered_map<uintptr_t, std::weak_ptr<Lifetime>> models;
template<class T> py::object wrap(T* ptr, std::shared_ptr<Lifetime> life) {
    if (!ptr) return py::none();
    if constexpr (std::is_same_v<T, SUUVHelper>) {
        auto uv = std::make_shared<Lifetime>();
        uv->ptr = ptr; uv->dispose = [ptr] { ptr->Release(); }; uv->parent = life;
        life = uv;
    }
    return py::cast(Handle<T>{ptr, life});
}
template<class T> py::object wrap(const std::vector<T*>& values, std::shared_ptr<Lifetime> life) {
    py::list result;
    for (auto* value : values) result.append(wrap(value, life));
    return result;
}
template<class T> py::object wrap(const T& value, std::shared_ptr<Lifetime>) { return py::cast(value); }
template<class T> auto argument(py::handle value) {
    using V = std::remove_cv_t<std::remove_reference_t<T>>;
    if constexpr (std::is_pointer_v<V>) {
        using P = std::remove_pointer_t<V>;
        if (value.is_none()) return static_cast<P*>(nullptr);
        return py::cast<Handle<P>&>(value).get();
    } else return py::cast<V>(value);
}
template<class Bound, class C, class R, class... A, size_t... I>
py::object invoke(Handle<Bound>& self, R(C::*method)(A...), py::args args, std::index_sequence<I...>) {
    if (args.size() != sizeof...(A)) throw py::type_error("Incorrect argument count");
    auto values = std::make_tuple(argument<A>(args[I])...);
    auto* ptr = reinterpret_cast<C*>(self.get());
    if constexpr (std::is_void_v<R>) {
        std::apply([&](auto&... v) { (ptr->*method)(v...); }, values);
        return py::none();
    } else {
        auto result = std::apply([&](auto&... v) { return (ptr->*method)(v...); }, values);
        return wrap(result, self.life);
    }
}
template<class Bound, class C, class R, class... A>
void bind(py::class_<Handle<Bound>>& cls, const char* name, R(C::*method)(A...)) {
    cls.def(name, [method](Handle<Bound>& self, py::args args) {
        return invoke(self, method, args, std::index_sequence_for<A...>{});
    });
}
template<class T> py::class_<Handle<T>> handle_class(py::module_& m, const char* name) {
    return py::class_<Handle<T>>(m, name)
        .def_property_readonly("_handle_id", [](Handle<T>& self) { return reinterpret_cast<uintptr_t>(self.get()); });
}
inline py::object model_object(SUModel* ptr) {
    if (!ptr) throw std::runtime_error("SketchUp SDK could not create/load model");
    auto life = std::make_shared<Lifetime>();
    life->ptr = ptr; life->dispose = [ptr] { ptr->Release(); };
    models[reinterpret_cast<uintptr_t>(ptr)] = life;
    return wrap(ptr, life);
}
