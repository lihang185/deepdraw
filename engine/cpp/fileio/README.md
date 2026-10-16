# DeepDraw native file IO, version 2

`deepdraw_fileio.dll` is an x64 C++17 DLL using cereal 1.3.2 BinaryArchive. It has
no Python or engine dependency. Its only model representation is the native logical
record API in `DeepDrawFileIO.h`. File-format encoding lives in this DLL; neither
Python nor the engine needs cereal headers. This is obfuscation by distribution
of compiled code, not file encryption.

## Engine integration

Build `fileio.vcxproj` with VS2019, Release/x64 (/MD). Output:
`build/x64/Release/deepdraw_fileio.dll` and `.lib`.

Compile `NativeSceneBridge.cpp` and `NativeSceneLoad.cpp` into the ENGINE project, alongside the updated
`../DeepDrawAPI.cpp`. Include `NativeSceneBridge.h` and link the file IO import
library. The bridge uses public getters/Load functions; private engine sources
remain in the offline engine project. The engine must use compatible MSVC STL/CRT
settings. The DLL does not import the engine, so there is no circular DLL import.

`CModelNativeFile.cpp` already contains the two CModel method bodies below. Add
it to the engine project after adding their declarations; do not also paste the
same bodies into another source file. This file needs the private `model.h` and
is deliberately not compiled by the independent DLL project.

Example saving entry in CModel (adjust the method declaration to your conventions):

```cpp
ddfile::Status CModel::SaveNativeFile(const wchar_t* path, ddfile::Error* error)
{
    return ddfile::SaveNative(reinterpret_cast<CModelPublic*>(this), path, error);
}
```

Add these declarations to CModel (include NativeSceneBridge.h or forward-declare
the ddfile status/error types):

```cpp
ddfile::Status SaveNativeFile(const wchar_t* path, ddfile::Error* error);
ddfile::Status ReadNativeFile(const wchar_t* path, ddfile::Error* error);
```

Corresponding read entry:

```cpp
ddfile::Status CModel::ReadNativeFile(const wchar_t* path, ddfile::Error* error)
{
    std::unique_ptr<ddfile::NativeLoadedData> loaded;
    auto status = ddfile::ReadNative(path, loaded, error);
    if (status != ddfile::Status::Ok) return status;
    LoadData(reinterpret_cast<CModelData*>(loaded->GetData()));
    loaded->TransferOwnership();
    return ddfile::Status::Ok;
}
```

Prefer reading into a NEW temporary CModel, then publishing it through the
client's existing model-replacement lifecycle. Parsing/construction failures never
touch the current model. The final engine LoadData must finish ownership adoption
without throwing after a partial transfer; this private engine behavior cannot be
verified here. If LoadData can partially adopt and throw, its engine-side exception
contract must be fixed before using this entry in production.

The materializer first loads empty definition shells, then geometry and instances,
then AddEntity, named sets and CModel::Load -> CModelData. Forward references work
without recursion or dependence on registry ordering. Bounds are invalidated once
per loaded definition. All creation goes through the existing native Load methods.

The NativeLoadedData holder follows the supplied engine ownership contract:
unattached entities use DeleteThis; components use Release; CModelData is a
caller-owned container. On successful LoadData, TransferOwnership disarms entity
cleanup but still deletes the container. This replaces Python wrapper cleanup in
the fully native path. Confirm that CModelData's destructor does not separately
delete the entity graph before adoption; entity cleanup is the holder's job.

The lower-level DDFileRead/Release record API is also available. Do not delete a
DLL-owned Scene in caller code. No Python interpreter is initialized anywhere.

Do not call these entry points concurrently with editing, undo, model replacement
or animation mutation. UI/CLI ownership remains the caller's responsibility.
No client save/open routing was switched by this change. Existing pickle loading
continues to work. Route by magic/version, never try to unpickle this payload.

## Supported first-version content

- Vertices, shared edges, edge uses, outer/inner loops and plane-based faces.
- Hidden/soft/smooth flags and face UV matrices; concavity flags are preserved.
- Shared definitions, instances, full transforms, groups/images, material inheritance.
- Definition metadata/dynamic recipe text and named sets of saved topology.
- Materials and raw encoded image bytes (PNG/JPEG/etc), without image conversion.
- Unused registered definitions/materials are retained.

Version 2 adds registered layers (including empty layers), edge/face/instance layer
references, CCurve and CArcCurve with shared edge references and complete arc data.
Guides and section planes still fail saving before touching the destination.
Python scene metadata handling now converts visibility IDs to layer indices under
saved_scenes_file_v1 and restores runtime IDs after loading. Save through
engine.model_files.save_sketchup_model(model, path, native=True) and read through
engine.model_files.load_sketchup_model; direct native calls bypass this conversion.
The existing native guard rejects unconverted saved_scenes_v1 metadata. Hidden
definition state also fails rather than silently dropping it. Runtime animation
transforms are not persisted; the base instance transform is saved.

## File format and validation

`.dim` extension, distinct 16-byte `DeepDrawNative\r\n` magic, little-endian uint32
file version (2 only), uint32 reserved flags (0), then explicitly ordered cereal binary
fields. This is a Windows x64 little-endian format. No compiler struct padding or
raw pointer is persisted. Strings are UTF-8 on disk; lengths/IDs are uint64;
`UINT64_MAX` is the optional-reference sentinel. Vector/UV/index arrays use bulk IO.

Logical arrays use indices for sharing, independent of runtime entity IDs. The
parser validates sizes, booleans, finite geometry, references, closed loops,
component ownership, registration and definition cycles before returning data.
This does not replace the engine's complete geometric/topological validity checks.
Configurable file/element/allocation limits protect against corrupt lengths.
The format is not cryptographically authenticated and has no compression in v1.

Save validates first, writes a sibling temporary file, closes it and replaces the
destination. Failure before replacement preserves the old file. Read never edits
an existing engine model. Exceptions are translated to status + caller-owned
error buffer at the DLL boundary.

## Tests

`tests/native_fileio_test.cpp` runs as a standalone C++ executable linked only to
the file DLL. It checks deterministic round trips, shared definitions, transforms,
Unicode, raw images, invalid references, duplicate ownership, truncated payloads,
unknown versions, allocation limits, extension enforcement and destination safety.
`NativeSceneBridge.cpp` and `NativeSceneLoad.cpp` have also been compiled as
translation units; linking their new APIs needs the next offline engine build.
`tests/native_scene_load_test.cpp` tests graph cleanup/adoption with a mock public
API and injected failure at every native construction/assembly step. This tests
the adapter's bookkeeping, not the private engine's destruction implementation.
A full engine scene round trip
and the large-scene timing remain to be run after integration.

## Third-party dependency

Vendored cereal v1.3.2 headers: https://github.com/USCiLab/cereal/tree/v1.3.2
License: `vendor/cereal/LICENSE` (BSD 3-Clause).
Downloaded release ZIP SHA256:
`e72c3fa8fe3d531247773e346e6824a4744cc6472a25cf9b30599cd52146e2ae`.
Build is entirely offline after this checkout is copied. No source/model uploads
were needed to obtain the public dependency.

## Version 2 coordinated deployment (2026-10-08)

The logical-record ABI is now 2. Rebuild the engine with DeepDrawAPI.h/.cpp,
DeepDrawFileIO.h, NativeSceneBridge.cpp and NativeSceneLoad.cpp together, then
ship the new deepdraw_fileio.dll beside that engine. Do NOT replace the file DLL
beside an older engine: its STL record layout is incompatible. New bridge code
checks DDFileApiVersion before exchanging records. Existing Python bindings for
SaveNativeFile / ReadNativeFile do not change. Model assembly calls
CModelData::Load(materials, layers, definitions, top).

The reader accepts only native v2. Native v1 is rejected; reconvert old models.
Python pickle save routing remains unchanged. Native component insertion is
still unsupported. Main engine sources are not compiled or uploaded here.

Verified locally: independent DLL build; bridge translation-unit compilation;
v2 codec round trips and v1 rejection and malformed input; materializer mock ownership and
32 injected failure points. The mock cannot verify actual engine destruction.
After offline engine compilation, run with engine Python 3.8:

    python tests/check_native_v2_curves_layers.py
    python tests/check_native_file_roundtrip.py

The first checks native/pickle parity, plain curves, polygons, open arcs, circles,
empty/shared/default layers, lifetime after gc, and deterministic resaving.
The second checks faces, materials, shared definitions and rendered output.
These engine integration tests remain pending the rebuilt engine.
