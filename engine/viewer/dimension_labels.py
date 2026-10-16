"""Screen-space labels for persistent dimension components."""
import json
from engine import core
from engine.qt import QtCore, QtGui
from engine.units import format_length
import numpy as np


def label_layout(view, projection, point, text, align, metrics):
    vector=QtGui.QVector4D(point.x,point.y,point.z,1)
    q=QtGui.QVector4D(*[QtGui.QVector4D.dotProduct(projection.row(i),vector) for i in range(4)])
    if q.w()<=0 or not -q.w()<=q.z()<=q.w():return None
    width=metrics.horizontalAdvance(text)
    offset=5 if align=='left' else (-width-5 if align=='right' else -width/2)
    baseline=QtCore.QPointF((q.x()/q.w()+1)*view.width()/2+offset,
        (1-q.y()/q.w())*view.height()/2+(metrics.ascent()-metrics.descent())/2)
    center=metrics.boundingRect(text).center()+baseline
    return baseline,center,(q.z()/q.w()+1)/2


def prepare_label_depth(view):
    """Read only label-center pixels, before QPainter can change GL state."""
    view._label_visibility={}
    if not has_labels(view):return
    gl=view.gl
    viewport=gl.glGetIntegerv(gl.GL_VIEWPORT)
    font=QtGui.QFont(view.font());font.setPixelSize(14)
    metrics=QtGui.QFontMetricsF(font)
    for projection,point,text,align in labels(view):
        layout=label_layout(view,projection,point,text,align,metrics)
        if layout is None:continue
        _,center,depth=layout
        key=(text,align,tuple(point.ToTuple()))
        x,y=center.x(),center.y()
        if not (0<=x<view.width() and 0<=y<view.height()):
            view._label_visibility[key]=False
            continue
        px=int(viewport[0])+min(int(viewport[2])-1,int(x*int(viewport[2])/view.width()))
        py=int(viewport[1])+min(int(viewport[3])-1,int((view.height()-y)*int(viewport[3])/view.height()))
        sample=gl.glReadPixels(px,py,1,1,gl.GL_DEPTH_COMPONENT,gl.GL_FLOAT)
        nearest=float(np.frombuffer(sample,dtype=np.float32)[0] if isinstance(sample,bytes) else np.asarray(sample).flat[0])
        view._label_visibility[key]=depth<=nearest+1e-5


def paint_label(view,painter,projection,point,text,align='center'):
    if not getattr(view,'_label_visibility',{}).get((text,align,tuple(point.ToTuple())),True):return
    painter.save()
    try:
        font=painter.font();font.setPixelSize(14);painter.setFont(font)
        painter.setPen(QtGui.QColor(35,45,65))
        layout=label_layout(view,projection,point,text,align,QtGui.QFontMetricsF(font))
        if layout is not None:painter.drawText(layout[0],text)
    finally:painter.restore()


class LabelCache:
    """World-space label values; never retain native entity handles across undo."""
    def __init__(self):
        self.key = None
        self.items = ()

    def get(self, pipeline):
        owner = pipeline.resource_owner
        key = (getattr(owner, 'label_revision', 0), owner.transform_revision)
        if self.key != key:
            items = []
            for node in pipeline.RecursiveRnumInstance(None, pipeline.model.GetTopComponent(), core.CMatrix(), None):
                description = node.comp.description
                if 'linear_dimension' not in description and 'text_annotation' not in description:
                    continue
                try:
                    data = json.loads(description)
                    if not isinstance(data, dict) or (data.get('kind'), data.get('version')) not in (
                            ('linear_dimension', 2), ('text_annotation', 1)):
                        continue
                    point = node.matrix.Transform(core.CVector3D(*data['label_position']))
                    annotation = data['kind'] == 'text_annotation'
                    value = data['text'] if annotation else data['distance_cm']
                    items.append((tuple(point.ToTuple()), annotation, value,
                                  data.get('align', 'left') if annotation else 'center'))
                except (ValueError, TypeError, KeyError):
                    continue
            self.items = tuple(items)
            self.key = key
        return self.items


def has_labels(view):
    return (view.model is not None and view.pipeline is not None
            and bool(view.pipeline.label_cache.get(view.pipeline)))


def labels(view):
    if not has_labels(view):
        return
    projection = view.ComputeProjectMatrix()*view.ComputeCameraMatrix()[0]
    for coords, annotation, value, align in view.pipeline.label_cache.get(view.pipeline):
        try:
            text = value if annotation else format_length(value, getattr(view, 'display_unit', 'cm'))
            yield projection, core.CVector3D(*coords), text, align
        except (ValueError, TypeError, KeyError):
            continue


def draw_labels(view,painter):
    for projection,point,text,align in labels(view):
        paint_label(view,painter,projection,point,text,align)
