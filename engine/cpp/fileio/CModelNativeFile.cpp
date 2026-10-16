// Compile in the offline ENGINE project after adding the two declarations from
// README.md to CModel. Not part of deepdraw_fileio.dll's project.
#include "model.h"
#include "NativeSceneBridge.h"

ddfile::Status CModel::SaveNativeFile(const wchar_t* path, ddfile::Error* error)
{
    return ddfile::SaveNative(reinterpret_cast<CModelPublic*>(this), path, error);
}

ddfile::Status CModel::ReadNativeFile(const wchar_t* path, ddfile::Error* error)
{
    std::unique_ptr<ddfile::NativeLoadedData> loaded;
    auto status = ddfile::ReadNative(path, loaded, error);
    if (status != ddfile::Status::Ok) return status;
    LoadData(reinterpret_cast<CModelData*>(loaded->GetData()));
    loaded->TransferOwnership();
    return ddfile::Status::Ok;
}
