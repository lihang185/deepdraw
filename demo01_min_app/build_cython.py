#python build_cython.py build_ext --inplace
#https://blog.csdn.net/weixin_36078669/article/details/151687672

from setuptools import setup
from Cython.Build import cythonize

mod_list = [
#"render_pipeline.py", 
"push_pull_controller.py", 
]
 
setup(
    ext_modules=cythonize(mod_list)
)
