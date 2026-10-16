"""Embedded planar image references. Pixels have a top-left origin; geometry does not."""
import hashlib
import json
import math
import uuid
from pathlib import Path
from engine import core
from engine.qt import QtCore, QtGui
from .edit import vector

PREFIX = 'DeepDraw reference v1\n'
TRACE_PREFIX = 'DeepDraw trace v1\n'


def xyz(v):
    return [v.x, v.y, v.z]


def metadata(definition, prefix=PREFIX):
    text = getattr(definition, 'description', '')
    return json.loads(text[len(prefix):]) if text.startswith(prefix) else None


def locked(entity):
    if isinstance(entity, core.CComponentInstance):
        comp = entity.GetDefinition()
    elif isinstance(entity, core.CComponent):
        comp = entity
    else:
        comp = entity.GetParentComponent()
    return comp is not None and metadata(comp) is not None


