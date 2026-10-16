#include "codec.h"
#include <filesystem>
#include <fstream>
#include <memory>
#include <cstring>

namespace {
constexpr char magic[16]={'D','e','e','p','D','r','a','w','N','a','t','i','v','e','\r','\n'};
struct Failure:std::runtime_error {ddfile::Status status;Failure(ddfile::Status s,const char* m):runtime_error(m),status(s){}};
void message(ddfile::Error* error,const char* text) noexcept {
    if(!error)return;error->message[0]=0;
    try {auto s=ddfile::wide(text);wcsncpy_s(error->message,s.c_str(),_TRUNCATE);}catch(...){wcscpy_s(error->message,L"Native file operation failed");}
}
template<class F> ddfile::Status boundary(ddfile::Error* error,F f) noexcept {
    if(error)error->message[0]=0;
    try{f();return ddfile::Status::Ok;}
    catch(const Failure& e){message(error,e.what());return e.status;}
    catch(const std::bad_alloc& e){message(error,e.what());return ddfile::Status::OutOfMemory;}
    catch(const std::exception& e){message(error,e.what());return ddfile::Status::InvalidData;}
    catch(...){message(error,"Unexpected native exception");return ddfile::Status::InternalError;}
}
void path_ok(const wchar_t* p){if(!p||!*p)throw Failure(ddfile::Status::InvalidArgument,"Empty path");
    auto ext=std::filesystem::path(p).extension().wstring();for(auto& c:ext)c=static_cast<wchar_t>(towlower(c));
    if(ext!=L".dim")throw Failure(ddfile::Status::InvalidArgument,"Native format requires .dim extension");}
struct TempFile {std::filesystem::path path;~TempFile(){if(!path.empty())DeleteFileW(path.c_str());}};
}
extern "C" {
std::uint32_t DDFileApiVersion() noexcept{return ddfile::api_version;}
void DDFileRelease(ddfile::Scene* s) noexcept{delete s;}
ddfile::Status DDFileValidate(const ddfile::Scene* s,ddfile::Error* e) noexcept {
    return boundary(e,[&]{if(!s)throw Failure(ddfile::Status::InvalidArgument,"Null scene");ddfile::validate(*s);});
}
ddfile::Status DDFileSave(const wchar_t* path,const ddfile::Scene* scene,ddfile::Error* error) noexcept {
    return boundary(error,[&]{
        path_ok(path);if(!scene)throw Failure(ddfile::Status::InvalidArgument,"Null scene");ddfile::validate(*scene);
        TempFile temp;auto target=std::filesystem::absolute(path);
        for(unsigned i=0;i<100;++i){auto p=target;p+=L".tmp-"+std::to_wstring(GetCurrentProcessId())+L"-"+std::to_wstring(GetTickCount64())+L"-"+std::to_wstring(i);
            HANDLE h=CreateFileW(p.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
            if(h!=INVALID_HANDLE_VALUE){CloseHandle(h);temp.path=p;break;}
            if(GetLastError()!=ERROR_FILE_EXISTS)throw Failure(ddfile::Status::IO,"Cannot create temporary scene file");}
        if(temp.path.empty())throw Failure(ddfile::Status::IO,"Cannot allocate temporary filename");
        {
            std::ofstream out(temp.path,std::ios::binary|std::ios::trunc);
            if(!out)throw Failure(ddfile::Status::IO,"Cannot open output file");
            out.write(magic,sizeof(magic));
            cereal::BinaryOutputArchive ar(out);
            std::uint32_t version=2,flags=0;ar(version,flags);
            ddfile::Codec<cereal::BinaryOutputArchive> codec(ar);
            // Output codec does not modify records; cereal's binary_data needs mutable pointer types.
            codec.value(const_cast<ddfile::Scene&>(*scene));
            out.flush();if(!out)throw Failure(ddfile::Status::IO,"Writing scene failed");
            out.close();if(out.fail())throw Failure(ddfile::Status::IO,"Closing scene failed");
        }
        if(!MoveFileExW(temp.path.c_str(),target.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH))
            throw Failure(ddfile::Status::IO,"Cannot replace scene destination");
        temp.path.clear();
    });
}
ddfile::Status DDFileRead(const wchar_t* path,ddfile::Scene** out,const ddfile::ReadLimits* limits,ddfile::Error* error) noexcept {
    if(out)*out=nullptr;
    return boundary(error,[&]{
        path_ok(path);if(!out)throw Failure(ddfile::Status::InvalidArgument,"Null output pointer");
        ddfile::ReadLimits bounds=limits?*limits:ddfile::ReadLimits{};
        std::ifstream in(std::filesystem::path(path),std::ios::binary|std::ios::ate);
        if(!in)throw Failure(ddfile::Status::IO,"Cannot open scene file");
        auto end=in.tellg();if(end<0||std::uint64_t(end)>bounds.max_file_bytes)throw Failure(ddfile::Status::InvalidData,"Scene exceeds file size limit");
        in.seekg(0);char header[16]{};in.read(header,sizeof(header));
        if(!in||std::memcmp(header,magic,sizeof(magic)))throw Failure(ddfile::Status::UnsupportedVersion,"Not a native DAI file (legacy pickle is not supported by this DLL)");
        cereal::BinaryInputArchive ar(in);std::uint32_t version=0,flags=0;ar(version,flags);
        if(version!=2||flags)throw Failure(ddfile::Status::UnsupportedVersion,"Unsupported native DAI version or flags");
        auto scene=std::make_unique<ddfile::Scene>();
        ddfile::Codec<cereal::BinaryInputArchive> codec(ar,bounds,std::uint64_t(end));codec.value(*scene);
        if(in.peek()!=std::char_traits<char>::eof())throw Failure(ddfile::Status::InvalidData,"Trailing scene data");
        ddfile::validate(*scene);*out=scene.release();
    });
}
}
