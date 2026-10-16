"""Independent transform oracle: call SketchUp's public point-transform API."""
import ctypes
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Point(ctypes.Structure):
    _fields_ = [('x',ctypes.c_double),('y',ctypes.c_double),('z',ctypes.c_double)]


class Matrix(ctypes.Structure):
    _fields_ = [('values',ctypes.c_double*16)]


def sdk_point(data, point):
    dll=ctypes.CDLL(str(ROOT/'importers/sketchup/SketchUpAPI.dll'))
    function=dll.SUPoint3DTransform
    function.argtypes=[ctypes.POINTER(Matrix),ctypes.POINTER(Point)]
    matrix=Matrix((ctypes.c_double*16)(*data))
    result=Point(*point)
    assert function(ctypes.byref(matrix),ctypes.byref(result))==0
    return result.x,result.y,result.z


def assert_point(actual, expected, context):
    assert all(math.isclose(a,b,abs_tol=1e-6,rel_tol=1e-9) for a,b in zip(actual,expected)), (context,actual,expected)


def check_import_math():
    from engine import core
    from importers.sketchup.native import load
    from importers.sketchup.import_model import ModelImporter
    sdk=load('suapi')
    transforms=[
        [1,0,0,0,0,1,0,0,0,0,1,0,10,-20,30,1],
        [0,1,0,0,-1,0,0,0,0,0,1,0,3,7,9,1],
        [0,2,0,0,-3,0,0,0,0,0,4,0,10,20,30,1],
        [-2,0,0,0,0,0.5,0,0,0,0,3,0,7,8,9,1],
        [1,0.25,0,0,0.4,1,0.2,0,0,0.3,1,0,-3,8,2,1],
        [0,2,0,0,-3,0,0,0,0,0,4,0,10,20,30,2],
    ]
    point=(1.25,-2.5,3.75)
    native_point=core.CVector3D(*(v*2.54 for v in point))
    nested_sdk=point
    nested_native=native_point
    for data in transforms:
        matrix=ModelImporter.transform(sdk.CMatrix.NewFromData(data))
        assert_point(matrix.Transform(native_point).ToTuple(),tuple(v*2.54 for v in sdk_point(data,point)),data)
        nested_sdk=sdk_point(data,nested_sdk)
        nested_native=matrix.Transform(nested_native)
        assert_point(nested_native.ToTuple(),tuple(v*2.54 for v in nested_sdk),'nested transforms')


def check_instances(source, model):
    """Compare saved/reloaded DIM transforms against SDK for every instance path."""
    from engine import core
    count=0
    def visit(sdk_component, native_component, parents, ancestors):
        nonlocal count
        originals=sdk_component.GetInstances()+sdk_component.GetGroups()+sdk_component.GetImages()
        converted=[e for e in native_component.EnumEntities() if isinstance(e,core.CComponentInstance)]
        assert len(originals)==len(converted)
        for original,converted in zip(originals,converted):
            definition=original.GetDefinition()
            native_definition=converted.GetDefinition()
            assert definition.GetName()==native_definition.name
            chain=[(original.GetTransform().GetData(),converted.GetTransform())]+parents
            for point in ((0,0,0),(1,0,0),(0,1,0),(0,0,1),(1.25,-2.5,3.75)):
                expected=point
                actual=core.CVector3D(*(v*2.54 for v in point))
                for sdk_matrix,native_matrix in chain:
                    expected=sdk_point(sdk_matrix,expected)
                    actual=native_matrix.Transform(actual)
                assert_point(actual.ToTuple(),tuple(v*2.54 for v in expected),definition.GetName())
            count+=1
            key=definition._handle_id
            assert key not in ancestors,'Cyclic component definitions'
            visit(definition.GetEntities(),native_definition,chain,ancestors|{key})
    visit(source.GetEntities(),model.GetTopComponent(),[],set())
    return count
