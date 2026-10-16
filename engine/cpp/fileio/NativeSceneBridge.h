#pragma once
#include "DeepDrawFileIO.h"
#include "DeepDrawAPI.h"
#include <memory>

namespace ddfile {
// Compile NativeSceneBridge.cpp into the ENGINE project (not the file DLL).
// Caller holds document ownership; no concurrent edits/undo while snapshotting.
Scene CaptureNative(CModelPublic* model);
Status SaveNative(CModelPublic* model,const wchar_t* path,Error* error) noexcept;

// Until CModel::LoadData succeeds, this object owns the complete loaded graph.
// After success call TransferOwnership(); the CModelData wrapper is still freed
// by this holder, just as a Python wrapper would release it after LoadData.
class NativeLoadedData {
public:
    struct Impl;
    explicit NativeLoadedData(std::unique_ptr<Impl> impl);
    ~NativeLoadedData();
    NativeLoadedData(const NativeLoadedData&)=delete;
    NativeLoadedData& operator=(const NativeLoadedData&)=delete;
    CModelDataPublic* GetData() const noexcept;
    void TransferOwnership() noexcept;
private:
    std::unique_ptr<Impl> impl_;
};
Status ReadNative(const wchar_t* path,std::unique_ptr<NativeLoadedData>& out,Error* error,
                  const ReadLimits* limits=nullptr) noexcept;
}
