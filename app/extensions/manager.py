class Extension:
    def __init__(self, name):
        self.name = name
    

class SimpleExtensionManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.ext_ls = []
    
    @classmethod
    def create(cls, main_window):
        cls._instance = SimpleExtensionManager(main_window)
        return cls._instance
    
    @classmethod
    def instance(cls):
        return cls._instance
    
    def start_all(self):
        
        for ex in self.ext_ls:
            factory_func = ex.factory
            try:
                factory_func(ex)
            except Exception as error:
                self.main_window.plugin_compatibility[ex.name] = '启动失败：' + str(error)
    
    def register_extension(self, name, creator):
        ex = Extension(name)
        ex.factory = creator
        
        self.ext_ls.append(ex)
        
        return ex
