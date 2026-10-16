# DeepDraw 教育版

独立的人工建模教学客户端。使用 Python 3.8 x64、PySide2 和本地几何/渲染引擎，不依赖 AI 版目录、AI 建模或 AI 渲染服务。

## 启动

双击 `start_education.cmd`，或使用配置好的 Python 3.8 运行：

```console
C:\python\Python38\python.exe editor.py
```

`editor.py` 是唯一启动入口；也保留为 Eric IDE 的启动文件。`DEEPDRAW_EDUCATION_PYTHON` 可以指定解释器。依赖见 `requirements-education.txt`。

## 目录

| 目录 | 职责 |
| --- | --- |
| `app/` | 程序启动、主窗口、Qt 界面及插件管理 |
| `app/ui/` | Designer `.ui`、对应控制器、生成的 `Ui_*.py` 和 Qt 资源模块 |
| `editing/` | 人工编辑事务、撤销、分组、剪贴板、文字与材质操作 |
| `engine/` | 原生绑定、DAI 编解码、几何工具及渲染 |
| `engine/tools/` | 当前使用的人工交互工具，每种工具仅保留一份实现 |
| `engine/viewer/` | 视图区、相机、剖切、标注显示和阴影 |
| `engine/native/cp38/` | 配套的原生几何和渲染二进制 |
| `assets/` | 教育版图标与 Qt 资源清单 |
| `data/` | 现有模型、材质及素材数据；整理过程不修改这些文件 |
| `importers/sketchup/` | 使用当前引擎的独立 SKP 导入进程、pybind11 模块及 SDK DLL |
| `native/sketchup/` | suapi、suapi_extra、skp_exporter 的 pybind11/CMake 源码、SDK 与回归检查 |
| `plugins/` | 兼容当前教育版的扩展入口；废弃旧插件已删除 |
| `scripts/` | 开发工具 |
| `tests/` | 文件格式和真实 Qt/OpenGL 回归检查 |
| `packaging/` | 独立 PyInstaller 打包配置 |
| `runtime/` | 测试截图、报告和构建产物，不存放源代码 |
| `docs/` | 架构、迁移来源、整理记录及素材校验记录 |

## 修改界面和图标

修改 `app/ui/*.ui` 或 `assets/icons/*` / `assets/resources.qrc` 后，统一运行：

```console
python scripts/build_ui.py
python scripts/build_ui.py --check
```

脚本同时生成 UI 和 Qt 资源。不要手改 `Ui_*.py`、`resources_rc.py`。具名 Qt 槽保留在对应控制器；主窗口槽仍定义在具体 `EditorMainWindow` 类中。

## 验证和打包

```console
python tests/run_checks.py
build_education.cmd
python scripts/check_package.py dist/DeepDrawEducation/DeepDrawEducation.exe
```

测试报告及截图写入 `runtime/test-results/`。打包配置是 `packaging/education.spec`；构建需要 PyInstaller。`scripts/check_package.py` 检查打包后的窗口启动、关闭及独立 SKP 转换。`editor_dist_old` 是外部备份，不属于运行时或构建依赖。

## DAI 格式

批量转换素材库中的 SKP：双击 `convert_data_skp.cmd`，或执行 `C:\python\Python38\python.exe data/convert_data_skp.py`。脚本递归处理 `data/` 下的 `.skp`，写入同目录同名 `.dim`；已有 DIM 在覆盖前备份到 `runtime/skp-batch/<本次运行>/backup/`。每个文件独立转换、验证版本和校验后原子替换，失败保留原输出并继续；日志与汇总在同次运行目录。可用 `--directory 路径` 指定其他输入目录。

SKP 原生模块可单独用 `scripts/build_sketchup.ps1 -Install` 重建，执行 `python native/sketchup/tests/check_bindings.py` 验证。SKP 导入和导出均使用当前引擎，不再使用旧 Shiboken 几何绑定或 DIM 写入桥接。详见 [原生模块说明](native/sketchup/README.md)。

教育版仅支持 `.dim`：普通模型用 pickle，大场景可用原生 v2。旧 DIM 不再读取。

`engine.serialization` 保持 v3 记录的模块身份。旧版读取器和兼容映射已经删除。详见 `docs/architecture.md`。

严格版本与损坏文件检查：`python scripts/check_dim_v3.py`。


## DAI 与大场景（2026-10-13）

新模型默认保存为 pickle `.dim`，不再支持 `.dim`；模型从 `.skp` 重新生成。
保存对话框可选择“大场景原生模型”；打开原生 v2 DAI 后直接保存维持原生格式。
原生格式只用于整模型，不支持作为组件插入。文件 DLL 与 editor2 必须配套部署。
模型库同名文件优先 DAI。SKP 导入输出 DAI。

超过 30 MiB 的文件读取完成后询问是否初始化显示缓存，可选择跳过；初始化显示
几何和合批进度。刷新进度后会恢复视图 GL 上下文，加载中暂停绘制及编辑回调。
渲染采用空间合批、远处小物体裁剪（small_object_percent 默认 2.5）、缓存复用和
受影响分支包围盒刷新，算法开关保留在 view 上。所有运行依赖均在教育版项目内。

验证：Python 3.8 运行 `tests/run_checks.py`；可额外将大型 DAI 路径作为
`tests/check_migration.py` 的参数，检查实际窗口的载入、初始化和绘制。

“视图 → 渲染统计”提供分阶段耗时、提交数量、合批分析及小物体过滤参数。
关闭面板会停止统计；默认不会增加统计开销。
本次源码移植未重建 `dist/` 安装包，运行 `editor.py` 或 `start_education.cmd` 使用。
