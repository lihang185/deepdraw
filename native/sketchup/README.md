# 教育版 SketchUp 原生模块

维护源位于本目录，运行文件位于 `importers/sketchup/`。Windows x64、CPython 3.8；三个模块均使用 pybind11，不再使用 Shiboken 生成器或手写 Python C API 模块入口。

| 项目 | 职责 |
| --- | --- |
| `suapi/` | SDK 模型、组件、几何、材质、纹理读取与构建；真实 C++ 句柄包装、生命周期检查 |
| `suapi_extra/` | 模型名称、描述、内嵌缩略图 |
| `skp_exporter/` | 当前 editor2 模型 → SKP，支持整场景和选择导出 |
| `vendor/sketchup/` | 随项目固定的 SketchUp SDK 头文件与导入库 |
| `tests/check_bindings.py` | 分进程执行的真实 SDK、导入导出与当前引擎兼容检查 |

## 构建

安装 Visual Studio 2019 C++ x64 工具、CMake 3.19+，并在 CPython 3.8 中安装 `pybind11==3.0.4`。从教育版根目录执行：

```powershell
.\scripts\build_sketchup.ps1 -Install
C:\python\Python38\python.exe native\sketchup\tests\check_bindings.py
```

省略 `-Install` 只编译。输出在 `build/sketchup/Release/`；安装生成带 `cp38-win_amd64` 后缀的三个 `.pyd`。不需要访问 `editor_cpp`、AI 客户端或备份目录；不自动重建 GUI 发布包。SDK DLL 已放在运行目录，构建过程不会替换它们。

## 生命周期和接口

`SUModel.Create/LoadFromFile/LoadFromBuffer` 创建拥有 SDK 模型的句柄；子对象持有模型生命周期。`Release()` 可重复调用，之后访问子对象会抛异常。几何输入的 loop 被 AddFace/FaceAddInnerLoop 消耗后不可复用。模块析构不会先于仍存活的 SDK 资源终止 SDK。

Python 包装对象不再依靠 Shiboken 的指针缓存。转换器用 `_handle_id` 识别同一个 SDK 对象，并在整个模型转换期间保留几何包装引用。保留现用的大写方法接口以及几何构建接口；废弃的 SDK OpenGL 绘制、调试和重复导出算法不再移植。

`suapi_extra.sumodel_get_*` 接受 SUModel，或由仍存活的模型返回的 GetPtr；任意地址、已释放地址会被拒绝。名称和描述使用公开 SDK API。

导出器使用教育版唯一的 `engine/native/cp38/DeepDrawAPI.h` 与 `editor2.cp38-win_amd64.lib`，运行时直接依赖 `editor2.cp38-win_amd64.pyd`，不依赖旧 DeepDrawAPI.dll。

`skp_exporter.export_scene_to_file(model, path)` 和 `export_selection_to_file(model, path)` 接受 **当前 editor2.CModel 对象**，拒绝旧 Shiboken 模型和裸整数地址。选择导出保留原来的水平居中规则；场景导出保留原坐标。

客户端代码应通过下面的入口调用，自动配置 DLL 路径、加载配套 pybind11 模块，并清理纹理临时文件：

```python
from engine.sketchup_export import export_scene_to_file, export_selection_to_file
export_scene_to_file(model, output_path)
```

回归检查使用当前引擎读取导入后的 DIM 并直接导出，检查孔洞、共享定义、透明度、纹理像素/比例，以及导出进程未加载 sbksueditor 或旧 DeepDrawAPI.dll。

SKP 导入也使用当前引擎：`convert.py` 启动独立工作进程，`import_model.py` 用 editor2.CEntityFactory 构建共享顶点、边、孔洞、组件和实例，再用 `engine.model_files` 写入带版本和校验的 payload 3 DIM。读取失败不会覆盖已有输出；纹理临时文件在成功或异常退出时清理。原始 SKP 保持不变。

旧 `suapi_to_binfile.py`、`sbksueditor.pyd`、`libshiboken.dll`、`DeepDrawAPI.dll`、`binary_file_v2.cp38-win_amd64.pyd` 已删除。导入/导出均只加载当前引擎与 pybind11 SDK 模块。PySide2 自身的 shiboken2 仍是 Qt 的依赖，与已移除的旧几何绑定不同。DIM 仅读写数据版本 3；旧 DIM 读取器和记录名映射已删除，其他版本及无版本文件明确报错。

除基础回归外，可运行 `python native/sketchup/tests/check_library.py`，逐一导入 data 中的 SKP，再由当前引擎读取，对照原 SDK 中的边、面、实例、环数量。所有测试输出放在临时目录。

实例矩阵：SketchUp 的前三列是局部坐标轴，必须用 editor2 的 `SetAxis` 写入，不能用 `SetRow`。齐次值 data[15] 在 SDK 中是除数，导入时归一化线性部分和位移，再令 editor2.scale 为 1；只有位移作英寸到厘米换算。`tests/matrix_oracle.py` 直接调用 SDK 的 SUPoint3DTransform，校验旋转、非均匀缩放、镜像、切变、齐次缩放和嵌套变换。素材库检查同时比较每条实例路径在保存/重读后的世界坐标。

## 固定 SDK 与兼容范围

SDK DLL 来自 `D:/deepdraw_main/editor_cpp/suapi/`，与教育版现有副本一致：

| 文件 | SHA-256 |
| --- | --- |
| SketchUpAPI.dll | `9677758b87a2b0be90580d5ea75401e69cc8fc021deca23eeae638838b0b797f` |
| SketchUpCommonPreferences.dll | `d2d02d1ee1d557c9a08ef55c4cfae69e2820480506d7c286abd90fe6738ce188` |

绑定迁移不会提升这个 SDK 能读取的 SKP 文件版本。旧 SDK 未提供模型缩略图和原转换器 UV 矩阵所需的全部公开接口，因此保留这两处固定版本布局兼容；加载时验证实际载入 DLL 的 SHA-256，版本不符直接拒绝，不能单独替换新版 DLL。其余模块依赖公开 SDK API。以后升级 SDK 应同时替换这两处实现并更新测试。

纹理转换使用无损 PNG，导出器在厘米与 SDK 英寸之间转换纹理尺寸。检查包含真实 ren.skp 的像素/比例往返、中文路径、孔洞、共享组件、透明度、软/平滑边、空选择、失效句柄、无效文件、当前引擎读取及 payload 3 保存。SDK 不支持或原兼容转换器未表达的其他 SketchUp 特性不因换绑定而新增支持。
