# 大场景静态子树合批

教育版 engine/viewer/subtree_batches.py 为展开超过 1024 节点的场景启用静态子树合批。
候选子树为 4–512 节点，展开图元计数不超过 30000。相同定义复用合批 VBO；透明、
图片及动画分支保持独立绘制。超过上限的子树继续向下寻找小批次，不整场景展开复制。

当前编辑组件不合批；内部实例变换首次发生时展开受影响分支，后续变换仅更新矩阵。
根实例移动、选择不会重建 VBO。几何、图层及历史操作按依赖失效。辅助线与剖切面
列表按资源版本缓存，无辅助线场景不再每帧扫描全部实例。保持 show_guides 开关。

诊断开关 view.subtree_batching，统计 view.pipeline.scene_statistics()['batches']。
新增脚本 scripts/check_subtree_batches.py 验证实际像素、选择、移动、镜像、材质、
组件导航、几何修改、Undo/Redo 和阴影。scripts/check_world_coordinates.py 验证
世界坐标渲染、拾取和数值输入。没有引入 AI/MCP 依赖，不需要重编译引擎 DLL。


### 原生图元计数优先

CComponent 的 GetNumEdges、GetNumFaces、HasGuideLine、GetNumChildren 是当前组件
直属计数，由引擎 AddEntity/RemoveEntity 和 Undo/Redo 自动维护。Python 不重复统计，
也不扫描验证计数。需要枚举指定类型图元时，优先以零计数直接跳过；非零时仍过滤
隐藏对象和关闭的图层。直属计数为零不代表后代为空，不能因此跳过子组件递归。
面分类、边线收集、合批透明材质检查、剖切截交计算已使用这些快速判断。

## 原生变换树（2026-10-07）

世界矩阵传播、变换后的包围盒和祖先范围回填已迁入 deepdraw_render 的数值树。
Python 首次建立层级和合批映射；变换时仅提交变更实例及变化的唯一组件定义范围。
结构变化仍重建列表。辅助线按需读取原生世界矩阵，保留 show_guides 开关。
C++ 负责视锥裁剪和可见待构建节点过滤；相机移动不重算模型矩阵或包围盒。

已部署 Release|x64 的 engine/native/cp38/deepdraw_render.pyd，需重启客户端加载。
规范源码位于 step3/engine/cpp/render，不依赖 AI/MCP 服务，未替换 editor2 引擎。
step3 的 39,205 节点组件测试中，节点更新中位数由 124.89 ms 降至 3.89 ms；
这是变换传播耗时，不是整体帧率。教育版 scripts/check_subtree_batches.py 已通过。

## 打开组件复用显示树（2026-10-07）

新增常驻 WorldScene，打开/关闭组件只更新 C++ 树的编辑路径、内外分类、选择组和
材质继承，不再重新枚举外部场景。路径上的合批展开，外部批次保持复用；首次展开
按需补建直属几何，再次进入不重复构建。几何/结构/图层变化仍按资源版本失效。
辅助线通过缓存节点列表按当前路径分区，保留 show_guides 开关。

scene_statistics()['timings'] 提供枚举、建树、切换上下文、裁剪和几何构建的独立
毫秒计时。两显示分区共享一棵原生树，累计计数不能相加；visible_indices 是世界树
索引。教育版合批和世界坐标真实 GL 回归已通过。需重启客户端加载新渲染 DLL。
