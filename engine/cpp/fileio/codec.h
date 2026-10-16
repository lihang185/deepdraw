#pragma once
#include "DeepDrawFileIO.h"
#include <cereal/archives/binary.hpp>
#include <Windows.h>
#include <limits>
#include <stdexcept>
#include <type_traits>

namespace ddfile {
inline std::string utf8(const std::wstring& s) {
    if(s.empty())return {};
    if(s.size()>INT_MAX)throw std::length_error("String too large");
    int n=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,s.data(),int(s.size()),nullptr,0,nullptr,nullptr);
    if(!n)throw std::runtime_error("Invalid UTF-16 text");
    std::string out(n,0);WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,s.data(),int(s.size()),&out[0],n,nullptr,nullptr);return out;
}
inline std::wstring wide(const std::string& s) {
    if(s.empty())return {};
    if(s.size()>INT_MAX)throw std::length_error("String too large");
    int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),int(s.size()),nullptr,0);
    if(!n)throw std::runtime_error("Invalid UTF-8 text");
    std::wstring out(n,0);MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),int(s.size()),&out[0],n);return out;
}

template<class Archive> class Codec {
    Archive& ar;
    ReadLimits limits;
    std::uint64_t allocated=0,file_size=0;
    void budget(std::uint64_t n,std::size_t width,bool bytes=false) {
        if(n>(bytes?limits.max_file_bytes:limits.max_elements) || n>file_size ||
           n>(limits.max_allocation_bytes-allocated)/width)
            throw std::runtime_error("File exceeds configured allocation/element limits");
        allocated+=n*width;
    }
public:
    Codec(Archive& a,const ReadLimits& l={},std::uint64_t size=UINT64_MAX):ar(a),limits(l),file_size(size){}
    template<class T> typename std::enable_if<std::is_arithmetic<T>::value>::type value(T& v){ar(v);}
    void value(Kind& v){auto n=static_cast<std::uint8_t>(v);ar(n);if(Archive::is_loading::value)v=static_cast<Kind>(n);}
    template<class T,std::size_t N> void value(std::array<T,N>& v){ar(cereal::binary_data(v.data(),sizeof(T)*N));}
    template<class T> void value(std::vector<T>& v) {
        std::uint64_t n=v.size();ar(n);
        if(Archive::is_loading::value){budget(n,sizeof(T));v.resize(static_cast<std::size_t>(n));}
        if constexpr(std::is_arithmetic<T>::value || std::is_same<T,Vec3>::value || std::is_same<T,UV>::value) {
            if(n)ar(cereal::binary_data(v.data(),static_cast<std::size_t>(n)*sizeof(T)));
        } else for(auto& x:v)value(x);
    }
    void value(std::vector<std::uint8_t>& v) {
        std::uint64_t n=v.size();ar(n);
        if(Archive::is_loading::value){budget(n,1,true);v.resize(static_cast<std::size_t>(n));}
        if(n)ar(cereal::binary_data(v.data(),static_cast<std::size_t>(n)));
    }
    void value(std::wstring& v) {
        std::string s=Archive::is_loading::value?std::string():utf8(v);
        std::uint64_t n=s.size();ar(n);
        if(Archive::is_loading::value){budget(n,3);s.resize(static_cast<std::size_t>(n));}
        if(n)ar(cereal::binary_data(&s[0],static_cast<std::size_t>(n)));
        if(Archive::is_loading::value)v=wide(s);
    }
    template<class... T> void fields(T&... v){int unused[]={0,(value(v),0)...};(void)unused;}
    void value(Transform& v){fields(v.values,v.scale,v.identity,v.orthogonal);}
    void value(Ref& v){fields(v.kind,v.id);}
    void value(Edge& v){fields(v.start,v.end,v.hidden,v.soft,v.smooth);value(v.layer);}
    void value(EdgeUse& v){fields(v.edge,v.reversed);}
    void value(Loop& v){fields(v.outer,v.convex,v.uses);}
    void value(Face& v){fields(v.hidden,v.plane,v.loops,v.material,v.uv);value(v.layer);}
    void value(Texture& v){fields(v.name,v.size_u,v.size_v,v.image);}
    void value(Material& v){fields(v.name,v.color,v.use_opacity,v.opacity,v.texture);}
    void value(Instance& v){fields(v.name,v.transform,v.material,v.definition,v.hidden,v.group,v.image);value(v.layer);}
    void value(Layer& v){fields(v.name,v.hidden,v.material);}
    void value(Arc& v){fields(v.center,v.xaxis,v.yaxis,v.plane,v.radius,v.start,v.end);}
    void value(Curve& v){fields(v.definition,v.first,v.last,v.is_arc,v.polygon,v.edges);if(v.is_arc)value(v.arc);}
    void value(NamedSet& v){fields(v.name,v.members);}
    void value(Definition& v){fields(v.name,v.description,v.agent_hint,v.file_path,v.dynamic_comp,v.dynamic,v.entities,v.named_sets);}
    void value(Scene& v){fields(v.vertices,v.edges,v.edge_uses,v.loops,v.uvs,v.faces,v.images,v.textures,v.materials,v.instances,v.definitions,v.model_materials,v.model_definitions,v.top);fields(v.layers,v.curves);}
};
void validate(const Scene& scene);
}
