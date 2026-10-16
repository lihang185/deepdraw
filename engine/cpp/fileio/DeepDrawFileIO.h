#pragma once
// Native logical records, independent of Python, engine internals and cereal.
// Both sides use MSVC x64 /MD and the same STL ABI. Never delete DLL-owned Scene.
#include <array>
#include <cstdint>
#include <string>
#include <vector>

#ifdef DEEPDRAW_FILEIO_EXPORTS
#define DD_FILE_API __declspec(dllexport)
#else
#define DD_FILE_API __declspec(dllimport)
#endif

namespace ddfile {
using Id = std::uint64_t;
constexpr Id null_id = UINT64_MAX;
constexpr std::uint32_t api_version = 2;
using Vec3 = std::array<double,3>;
using Plane = std::array<double,4>;
using UV = std::array<double,9>;
struct Transform {
    std::array<double,12> values{{1,0,0,0,1,0,0,0,1,0,0,0}};
    double scale=1;
    std::uint8_t identity=1, orthogonal=1;
};
enum class Kind : std::uint8_t { Vertex=1, Edge, EdgeUse, Loop, Face, Instance, Definition };
struct Ref { Kind kind=Kind::Vertex; Id id=null_id; };
struct Edge { Id start=null_id,end=null_id; std::uint8_t hidden=0,soft=0,smooth=0; Id layer=null_id; };
struct EdgeUse { Id edge=null_id; std::uint8_t reversed=0; };
struct Loop { std::uint8_t outer=0,convex=0; std::vector<Id> uses; };
struct Face {
    std::uint8_t hidden=0;
    Plane plane{};
    std::vector<Id> loops;
    Id material=null_id,uv=null_id,layer=null_id;
};
struct Texture { std::wstring name; double size_u=1,size_v=1; Id image=null_id; };
struct Material {
    std::wstring name; Vec3 color{};
    std::uint8_t use_opacity=0; double opacity=1; Id texture=null_id;
};
struct Instance {
    std::wstring name; Transform transform;
    Id material=null_id,definition=null_id,layer=null_id;
    std::uint8_t hidden=0,group=0,image=0;
};
struct NamedSet { std::wstring name; std::vector<Ref> members; };
struct Layer { std::wstring name; std::uint8_t hidden=0; Id material=null_id; };
struct Arc { Vec3 center{},xaxis{},yaxis{}; Plane plane{}; double radius=0,start=0,end=0; };
struct Curve {
    Id definition=null_id,first=null_id,last=null_id;
    std::uint8_t is_arc=0,polygon=0;
    std::vector<Id> edges;
    Arc arc;
};
struct Definition {
    std::wstring name,description,agent_hint,file_path,dynamic_comp;
    std::uint8_t dynamic=0;
    std::vector<Ref> entities;
    std::vector<NamedSet> named_sets;
};
struct Scene {
    std::vector<Vec3> vertices;
    std::vector<Edge> edges;
    std::vector<EdgeUse> edge_uses;
    std::vector<Loop> loops;
    std::vector<UV> uvs;
    std::vector<Face> faces;
    std::vector<std::vector<std::uint8_t>> images; // Original PNG/JPEG/etc bytes.
    std::vector<Texture> textures;
    std::vector<Material> materials;
    std::vector<Instance> instances;
    std::vector<Definition> definitions; // Includes the top definition.
    std::vector<Id> model_materials,model_definitions;
    Id top=null_id;
    std::vector<Layer> layers;
    std::vector<Curve> curves;
};
struct ReadLimits {
    std::uint64_t max_file_bytes=16ull*1024*1024*1024;
    std::uint64_t max_allocation_bytes=16ull*1024*1024*1024;
    std::uint64_t max_elements=100000000;
};
enum class Status : int { Ok=0, InvalidArgument, IO, InvalidData, UnsupportedVersion, OutOfMemory, InternalError };
struct Error { wchar_t message[512]{}; };
}

extern "C" {
DD_FILE_API std::uint32_t DDFileApiVersion() noexcept;
// Validates before writing; writes a sibling temp file and replaces only on success.
DD_FILE_API ddfile::Status DDFileSave(const wchar_t* path,const ddfile::Scene* scene,ddfile::Error* error) noexcept;
// Creates records only, never modifies an engine model. *out is null on failure.
DD_FILE_API ddfile::Status DDFileRead(const wchar_t* path,ddfile::Scene** out,const ddfile::ReadLimits* limits,ddfile::Error* error) noexcept;
DD_FILE_API void DDFileRelease(ddfile::Scene* scene) noexcept;
DD_FILE_API ddfile::Status DDFileValidate(const ddfile::Scene* scene,ddfile::Error* error) noexcept;
}
