"""Education editing stays on the Qt main thread; there is no AI owner."""
from functools import wraps
from contextlib import contextmanager

_suspended = False

@contextmanager
def suspend_mutations():
    global _suspended
    old = _suspended
    _suspended = True
    try:yield
    finally:_suspended = old

from .qt import QtCore


def check_mutation():
    if _suspended:raise RuntimeError("正在刷新载入界面，请稍候")
    app = QtCore.QCoreApplication.instance()
    if app is not None and QtCore.QThread.currentThread() != app.thread():
        raise RuntimeError('模型只能在界面主线程编辑')


def human_callback(function):
    @wraps(function)
    def call(*args, **kwargs):
        if _suspended:return
        check_mutation()
        return function(*args, **kwargs)
    return call
