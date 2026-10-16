# 教育版扩展入口

此目录仅放适配当前引擎的插件。旧插件不再保留。

在顶层 Python 入口中声明 `DEEPDRAW_ENGINE_API = 2`；启动时通过 `app.extensions.api.ExtensionManager.register_extension(name, factory)` 注册扩展。`UI` 提供当前主窗口、工具栏和命令接口。工厂接受扩展对象，插件命令通过主窗口 `run_action` 执行；模型修改必须使用 `window.editing.edit.operation(...)`。

不要导入旧 `su`、`su_algo` 或旧原生 DLL，不要保存跨模型生命周期的原生对象。
