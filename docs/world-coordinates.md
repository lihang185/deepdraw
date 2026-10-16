# 教育版世界坐标与工具长度约定

相机、渲染、CPickHelper 和 CInputPointFinder 使用世界坐标。进入和退出组件不转换相机。
组件内部几何与工具工作点仍为局部坐标；engine/coordinates.py 提供统一的点、向量、平面、射线和预览转换。
原生接口的 Inference origin、AddRefPoint、Position 均约定为世界坐标。

用户输入的长度与工具显示的长度使用世界厘米；沿当前局部操作方向计算实际缩放比例后换算。
例：局部 X 放大两倍，输入 10 cm 写入局部长度 5；锁定 X 仍沿组件局部 X。
线段、矩形、圆/多边形、圆弧、移动、推拉、辅助线、偏移和尺寸标注已适配。
圆/圆弧及偏移的度量在世界空间计算，结果再存回局部坐标，避免非均匀缩放改变输入半径或偏移距离。
旋转的角度、缩放比例、复制数量仍是各自原有语义，不作为长度换算。

保留教育版 EditingContext、插件、辅助线显示开关、相机适配和 DIM v3 格式，不依赖 AI 客户端。
新增模块随现有 Python 导入和打包规则收集，未重新打包 exe。
原生 editor2.pyd 与导入库已更新到验证过的世界拾取版本；原文件备份在 runtime/native-before-world-coordinates。

验证命令（C:/python/Python38/python.exe）：
- scripts/check_world_coordinates.py：真实原生外部面捕获、嵌套旋转/缩放、相机不变、局部编辑、世界长度和局部锁轴、GL 非空截图。
- scripts/check_rotation.py：90 度和多选共用中心旋转。
- scripts/check_fit_camera.py：27 组透视适配。
- scripts/check_dim_v3.py：格式、往返、原子保存和损坏文件拒绝。
- scripts/check_group_undo_pick.py：成组、撤销、重做、回滚后的选取。

AGENTS.md 指定的 tests/run_checks.py 当前不存在；已运行上述现有检查和新增联调。
