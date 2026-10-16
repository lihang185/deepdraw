"""Qt bridge for the supported CPython 3.8 engine."""
import sys

if sys.version_info[:2] != (3, 8):
    raise ImportError('DeepDraw engine requires CPython 3.8 x64')
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtWidgets import QOpenGLWidget
from PySide2.QtGui import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat, QOpenGLTexture
