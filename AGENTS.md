# DeepDraw education client

This is the independently maintained education client. Do not modify the external
backup ../editor_dist_old. No runtime or build dependency may refer to the AI client.

- editor.py is the sole launcher. app/bootstrap.py creates the Qt application;
  app/main_window.py owns the native model and EditingContext.
- Preserve the education QMainWindow and plugin architecture. Do not introduce
  AI modeling, rendering services, MCP, command queues, observers or takeover code.
- All UI controllers and Designer forms live in app/ui/. Edit .ui then run
  scripts/build_ui.py (also generates assets/resources.qrc). Never hand-edit
  Ui_*.py or resources_rc.py. Named Qt slots stay on the concrete QObject class.
- editing/ contains the human transaction/geometry/material APIs. engine/tools/
  contains one implementation per human tool; engine/viewer/ owns rendering.
- Use CPython 3.8 x64 and the matching engine/native/cp38 binaries.
- Geometry units are centimetres; display conversion is only at I/O boundaries.
- Models save as .dim (pickle by default; native v2 for large scenes). Both codecs
  are local to this project. Legacy DIM payloads are unsupported. Route by
  extension and DAI magic; preserve atomic replacement on save. Native v1 is rejected.
- Keep engine.serialization's serialized module identity stable for existing DAI
  records. Increment payload version for record changes and retain explicit readers.
- Model replacement invalidates old bindings/context before releasing native data.
  Preserve undo, preview rollback, layer/section references and selection checks.
- SKP import runs in an isolated worker using current editor2/CEntityFactory and
  writes pickle DAI through engine.model_files. Do not restore sbksueditor,
  binary_file_v2 native modules or the old DeepDrawAPI.dll.
- Maintain suapi/suapi_extra/skp_exporter in native/sketchup using pybind11/CMake.
  Build with scripts/build_sketchup.ps1; run native/sketchup/tests/check_bindings.py.
  Keep the pinned SDK DLL pair together. skp_exporter links the current header/lib
  in engine/native/cp38 and accepts editor2.CModel, never legacy/raw pointers.
  Use importers.sketchup.native for shared module loading and engine.sketchup_export
  for exports. Legacy DIM readers and old pickle-name mappings have been removed.
- plugins/ accepts only entry files declaring DEEPDRAW_ENGINE_API = 2. Supported
  extension helpers live in app/extensions/. Do not restore obsolete root aliases.
- data/ is user/model library data. runtime/ contains generated diagnostics only.
- Run python tests/run_checks.py for structural, format and real Qt/OpenGL checks.
  Keep build_education.cmd, packaging/education.spec and SuEditor.epj in sync.
