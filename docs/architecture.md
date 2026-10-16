# 教育版架构与维护边界

## 程序和文档所有权

`editor.py` 调用 `app.bootstrap.main()`。启动代码负责 QApplication 和唯一主窗口；`app.main_window.EditorMainWindow` 继续拥有模型、EditingContext、场景管理器和面板。保留原教育版 QMainWindow 架构，不引入 AI 版 EngineDocument、命令服务、任务队列或接管机制。

主窗口按生命周期、面板/工具调度、文件操作、编辑操作、视图设置、扩展和具名 Qt 槽编排。Qt 自动连接槽必须留在具体 QObject 类上，避免混入普通 Python mixin 导致旧 PySide2 原生崩溃。

模型替换必须先结束当前工具，再通知面板清理引用、使旧 EditingContext 失效，最后释放原生模型。面板跨事件循环只保存 ID/token，不保留失效的原生对象。

## 界面与编辑

所有 Designer 源和控制器归入 `app/ui/`。三个侧栏为模型库、材质库和图层/场景；图层下拉框位于现有工具栏。模型库单击预览、双击放置。材质库只使用新版面板实现，创建与更新材质统一经过 `editing.material_assets`。

`editing/` 提供 Qt 人工操作所需的事务、撤销、预览回滚、对象封装及几何辅助。工具位于 `engine/tools/`；显示和拾取位于 `engine/viewer/`。菜单、面板和工具修改模型时复用同一编辑事务。

`engine.mutation_guard` 只处理主线程人工回调边界，不包含 AI 所有权。

## 数据与资源

- 几何内部长度单位始终为厘米，显示单位转换仅发生于输入/输出。
- `engine.dim_format` 验证 DIM 容器；`engine.model_files` 统一使用 v3 编解码器。
- `engine.legacy_dim` 和旧 pickle 名称映射已删除；无版本及非 v3 数据明确报错。
- `engine.serialization` 仅读写版本 3，保存材质边线参数并恢复原生 LoadData 遗漏的剖切附着。
- 已保存的 pickle 记录引用 `engine.serialization`，不应随意改名或移动；若改变数据结构，先设计版本兼容。
- `assets/resources.qrc` 是唯一图标清单；生成资源模块为 `app/ui/resources_rc.py`。资源不依赖工作目录。
- `data/` 保留模型与材质素材，`runtime/` 仅保存可再生输出。

## SketchUp 导入

`importers/sketchup/convert.py` 在独立进程运行，调用 `import_model.py`，由当前 editor2 的 CEntityFactory 创建几何、组件和模型，用 `engine.model_files` 原子写入 payload 3 的临时 DIM。主进程沿用已有异步导入和组件插入流程。`native.py` 统一加载固定目录内的 pybind11 模块，不向主进程的 sys.path 添加旧绑定目录。

`suapi`、`suapi_extra`、`skp_exporter` 的维护源码位于 `native/sketchup/`，统一以 pybind11/CMake 构建。前两者封装 SketchUp SDK；导出器链接 `engine/native/cp38/DeepDrawAPI.h` 与 `editor2.cp38-win_amd64.lib`，直接接收当前 editor2.CModel。通过 `engine.sketchup_export` 导出。导入和导出均不再依赖旧 DeepDrawAPI.dll、sbksueditor、libshiboken.dll 或 binary_file_v2.pyd，这些旧文件已删除。旧 DIM 读取器和 binary_file_v2 记录映射也已删除。原生构建与回归命令见 `native/sketchup/README.md`。

## 扩展

扩展管理集中于 `app/extensions/`，插件入口仍从项目 `plugins/` 加载。入口必须声明 `DEEPDRAW_ENGINE_API = 2`。旧的根目录 su/工具兼容别名、AI 渲染、云模型及旧引擎插件均已删除；新插件使用 `app.extensions.api` 和当前 engine/editing API。

## 验证

`tests/run_checks.py` 串行执行真实窗口检查，覆盖图元、推拉、变换、撤销、剖切、图层/场景、材质、文字、右键菜单、SKP 导入和 DIM 保存/读取。素材 SHA-256 基线在 `docs/data_integrity.json`。对比基线能证明整理没有改写原始素材。

启动入口测试使用真实 QApplication 的事件循环，不继承 QApplication 替代生产对象（当前 PySide2 在这种测试替身退出时可能触发原生析构异常）。
