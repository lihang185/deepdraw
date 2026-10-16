# Independent render binding (API version 1)

`deepdraw_render.pyd` is a separate Windows CPython 3.8 x64 DLL. It owns VBOs
and numeric material snapshots. Python owns model-change synchronization, editing
context and pass order. The DLL retains numeric draw hierarchies and performs
view-frustum traversal and batched submission. Definition geometry is shared;
an optional single directional shadow map uses a separate light list.

## Python API

```python
import deepdraw_render as renderer

# A compatible OpenGL context must already be current.
renderer.init_opengl()
material = renderer.Material(
    type=1, color=(0.7, 0.6, 0.5), transparent=False,
    opacity=1.0, texture=0, texture_size=(1.0, 1.0))
cache = renderer.MeshCache()
cache.build(
    faces=[([editor2.borrow_entity(face)], affine12, material)],
    edges=[([editor2.borrow_entity(edge)], affine12)])
cache.draw(1)
cache.close()
```

`MeshBuildSession(limit=128*1024*1024)` optionally shares definition-local
`TriangleMeshPublic` results across `cache.build(faces, edges, session)` calls.
Use one session only during immutable batch initialization, and destroy it before
allowing model edits, undo, replacement or native release. VBO caches do not retain
the session. The budget bounds estimated mesh payload (including an overhead
allowance), not exact process RSS; a full budget simply stops admitting new faces.
`hits`, `misses`, and `estimated_bytes` provide startup diagnostics. Each instance
still applies its own transform, mirrored winding and material grouping.

`ComponentBuildSession([(material_capsule, material_snapshot), ...])` snapshots
the material lookup for direct definition warmup. `MeshCache.build_component`
accepts a component/definition capsule and this session, enumerates and groups
native faces/edges, and returns used material IDs. `None` requests the existing
Python fallback (layered geometry or an unknown material) before replacing the
cache. Public API exposes HasLayer but not layer visibility, so layered geometry
must not use this fast path. The Python wrapper retains the corresponding Qt
texture owners. Sessions end before interactive editing resumes.

`build` accepts positional or keyword arguments. Batch tuples contain:

- Faces: `(list_of_entity_capsules, affine12, Material_or_None)`.
- Edges: `(list_of_entity_capsules, affine12)`.
- `affine12`: twelve finite doubles, three rows of the linear transform followed
  by translation: `r00,r01,r02,r10,r11,r12,r20,r21,r22,tx,ty,tz`.
  There is no hidden scale field; values include the full evaluated transform.
- `None` means inherited material (pass 0), not a newly allocated default material.

Passes retain the current behavior: 0 inherited faces, 1 opaque material faces,
2 edges, 3 transparent material faces. Values outside 0..3 are rejected.
`has_geometry(pass)` reports whether a cache contains that partition.
`Material.bind()` establishes fixed-function material state; `update(other)`
copies numeric state into the existing snapshot so cached batches remain valid.
Changing opacity classification requires rebuilding the affected batches.

The public Python adapter is `engine/viewer/render_backend.py`. It evaluates
native transforms, converts entity references to capsules, retains Qt texture
owners, and requires the independent backend. Python pipelines no longer
construct exported native face/material/edge group objects.

## Engine-side capsule bridge

`entity_capsule.h` is shared with the engine binding. In editor2, after registering
the entity hierarchy, add:

```cpp
#include "entity_capsule.h"
m.def("borrow_entity", &deepdraw_bridge::borrow_entity<CEntity>,
      pybind11::arg("entity"));
```

It must receive a real `CEntity*` from the existing pybind11 caster. Capsules are
named `deepdraw.CEntity.borrowed.v1` and do not own entities. Face/edge types are
checked after unwrapping. No Python object addresses or pointer integers are used.
No GIL release, event processing, or concurrent model mutation is allowed while
`build` consumes borrowed entities. A capsule is not a lifetime guarantee: never
reuse one after delete, undo/redo, or model replacement.

Build consumes engine pointers synchronously. Persistent caches hold only GPU
buffers and shared render-material snapshots. Internal group objects exist only
for the call. Qt textures remain borrowed GPU IDs; the Python adapter keeps their
owners alive until cache replacement or close. Material and texture creation stay
on the Qt/context thread. DLL Material.bind does not invoke engine model methods.

## Build and deployment

Open `render.sln` and use **RelDbg | x64** or **Release | x64**. Override MSBuild
properties `EnginePythonDir` and `DeepDrawApiDir` for another development machine.
The latter defaults to `engine/native/cp38` and contains
`editor2.cp38-win_amd64.lib`. The module links Public API exports directly from
`editor2.cp38-win_amd64.pyd`, the same binary that owns the entities.
Do not pair a historical API DLL with current model pointers merely because it
has compatible export names. Capsule protocol version 1 is not engine ABI proof.

```powershell
MSBuild.exe render.vcxproj /p:Configuration=RelDbg /p:Platform=x64
```

Output: `build/x64/RelDbg/deepdraw_render.pyd`. No post-build copying into the
application or distribution occurs. The DLL uses the dynamic CRT and has no
Shiboken dependency. `editor2.cp38-win_amd64.pyd`, Python and the VC runtime are
dependencies; a separate historical `DeepDrawAPI.dll` is not used.

After validating matching engine binaries, install the render module into
`engine/native/cp38`, alongside the updated editor2 binding. The existing native loader
adds this directory to both Python and DLL search paths.

The independent module is required. There is no legacy/auto selection and the
old `DEEPDRAW_RENDER_BACKEND` switch is no longer read. Missing or incompatible
render binaries fail at import time with an installation diagnostic.

`filter_bounds(planes, bounds, transforms)` performs batch view-frustum culling
inside the render DLL and returns indices into the input lists. Bounds contain
`min_x,max_x,min_y,max_y,min_z,max_z`; transforms use `affine12`. Inward plane
normals use `nx*x + ny*y + nz*z + w >= 0`. No model pointers are needed. Python
filters hidden/deleted instances before submission and includes `inst.GetAnimationTransform()` in
transforms, matching drawing and animation. Engine CGeomFilterVolume,
CFilteredInstance and InstanceInfo bindings are no longer needed by the viewer.

## Resources and validation

`build`, `draw`, `close`, material binding and collection require a current
compatible GL context. Cache use under a different context is rejected, including
shared contexts. Build validates inputs and builds replacement buffers before
discarding the previous cache. Close is idempotent. Destructor cleanup is deferred
to the owning context and never invokes GL on an arbitrary Python GC thread.

Call `release_context()` while the owning context is current before destroying
it. This closes every live cache for that context and drains deferred deletions.
View3D connects this to Qt's context-destruction signal and invalidates its CPU
render records/materials so they can be rebuilt. Normal model replacement already
releases observation and human pipelines while the context and model are alive.

```powershell
python tests/check_independent_renderer.py --module-dir engine/cpp/render/build/x64/RelDbg --api-dir engine/native/cp38
python tests/check_camera_isolation.py
python tests/check_layer_render.py
python -m unittest tests.test_render_material_opacity tests.test_observation_geometry
```

The standalone GL check covers empty cache creation, validation failures, material
snapshots, context ownership and resource lifecycle. It intentionally does not
claim nonempty model/capsule integration. Real-scene acceptance requires the
updated editor2 bridge and ABI-matched API DLL, then running the scene checks with the installed module (including image inspection).

## Integration verification (2026-10-05)

The updated engine exports `CModel`, `borrow_entity`, `license.start` and the
Public API. RelDbg x64 was relinked against its import library. Dependency
inspection confirms the renderer imports editor2 directly.

With the installed renderer and no backend-selection environment variables,
camera/capture/picking isolation and layer visibility scene checks passed.
All 14 material, affine, navigation and culling unit tests passed. The standalone
GL contract check passed against the installed module. Both the human side view
and AI textured door capture were visually inspected.

## Legacy removal

The renderer is installed into `engine/native/cp38/deepdraw_render.pyd` and is the
only backend. All legacy render aliases and adapter fallback branches have been
removed. The obsolete `engine/cpp/CModelCache.{h,cpp}` copies were removed; active
cache implementations live under this render project. Native picking/inference
remain geometry services. Python viewer/tools no longer call CSimpleDraw, engine
init_opengl, or CInputPointFinder.Draw; editor overlays live in
`engine/viewer/overlays.py`. See `docs/render-architecture.md` for the staged
component-cache, batching and shadow design.

Python now submits definition-local geometry only for shared component caches.
Occurrence matrices, inherited materials and front-face orientation are applied
at draw time. Human and observation pipelines share those caches within the same
View3D context; observation entity subsets have request-owned local caches.
No ABI change is needed. See `tests/check_component_render_cache.py` for the
repeated-instance, navigation, material-inheritance and invalidation regression.

## Persistent draw lists

The viewer now requires `DrawList` in addition to the original mesh API. Rebuild
and replace the renderer alongside the Python changes; old binaries fail with a
specific installation diagnostic. The engine capsule/mesh API remains version 1.

- `set(rows)`: each row is `(MeshCache, Material, affine12, bounds6, parent_index,
  selection_group, is_image)`. Parents precede children in subtree preorder;
  `-1` denotes a root. Matrices map local geometry into the list's coordinate frame.
- `update(rows)`: `(index, affine12, bounds6)` updates occurrence transforms and
  refits affected ancestor bounds. Invalid input preserves the existing list.
- `cull(planes)`: at most six inward planes; three-state hierarchical culling
  carries a remaining-plane mask. Identical planes reuse the visibility result.
- `visible_indices()`: used for lazy geometry uploads; no engine pointers returned.
- `set_selection(groups)`: updates edge highlighting without replacing the list.
- `update_materials(rows)`: validates all `(node_index, material_snapshot)` rows
  before replacing shared material references. Python owns inheritance and batch
  policy; this method neither traverses engine entities nor rebuilds transforms.
- `draw(pass, parent_mirror, outer, xray)`: validates current GL ownership, then
  submits visible nodes internally. Matrix/polygon state is restored afterward.
- `statistics()`: numeric counters, not GPU timing. Counters belong to this list.

The list holds shared references to mesh/material wrappers, so mesh rebuilds and
explicit context release remain safe. Qt texture owners remain on the Python side.
Animation updates use the same meshes; no VBO uploads are required.

## Directional shadow prototype

`ShadowMap.configure(size)` creates depth texture/FBO and compatibility shaders;
sizes 512/1024/2048/4096 are accepted (UI exposes 1024/2048/4096).
`render(draw_list, light_clip16)` updates depth from an independently culled world
list. The matrix is column-major, world to light clip space.
`begin_receive(shadow_from_eye16, strength, bias)` / `end_receive()` bracket an
opaque receiver pass; callers must use try/finally. The receiver matrix includes
the clip-to-texture bias transform. Neither method changes mesh geometry.
`DrawList.draw_opaque(parent_mirror)` and `MeshCache.draw_opaque(inherited)` draw
opaque partitions without binding materials. Image occurrence nodes are skipped.
`DrawList.bounds()` returns its conservative aggregate bounds in list coordinates.

`close()` is idempotent; `release_context()` also releases maps belonging to the
current context. Destructor work is deferred when needed. Framebuffer entry points
are loaded per context because the bundled GLAD generator targets GL 2.0.
The receiver uses 3x3 PCF with receiver-plane correction; it preserves destination
alpha and restores prior GL state. Transparency, edges and overlays do not cast.
The Python UI checks feature availability at enable time; an old renderer can
still draw normally but cannot enable the new shadow option.
