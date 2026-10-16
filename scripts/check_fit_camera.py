"""Regression checks for perspective fitting and orthonormal camera axes."""
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide2.QtWidgets import QApplication
from PySide2.QtGui import QVector3D, QVector4D
from engine.viewer.view3d import View3D, SuCamera


def main():
    app = QApplication([])
    view = View3D(None)
    cases = 0
    for width, height in ((1200, 700), (500, 1000), (800, 800)):
        view.resize(width, height)
        for direction in ((1, -2, 1), (0, 0, 1), (0, 0, -1)):
            for extents in ((100, 200, 300), (1000, 2, 10), (.1, .1, .1)):
                camera = view.camera = SuCamera()
                camera.target = QVector3D(0, 0, 0)
                camera.position = QVector3D(*direction) * 100
                camera.up = QVector3D(0, 0, 1)
                camera.compute()
                forward = QVector3D(camera.forward)
                box = SimpleNamespace(**dict(zip(
                    ('min_x', 'max_x', 'min_y', 'max_y', 'min_z', 'max_z'),
                    (-extents[0], extents[0], -extents[1], extents[1], 0, extents[2]))))
                _, fov, aspect = view.ComputeFOV()
                camera.fit_bounds(box, fov, aspect)
                assert (camera.forward-forward).length() < 1e-5
                axes = (camera.forward, camera.up, camera.right)
                for i, axis in enumerate(axes):
                    assert abs(axis.length()-1) < 1e-5
                    for other in axes[i+1:]:
                        assert abs(QVector3D.dotProduct(axis, other)) < 1e-5
                matrix = view.ComputeProjectMatrix() * view.ComputeCameraMatrix()[0]
                for x in (box.min_x, box.max_x):
                    for y in (box.min_y, box.max_y):
                        for z in (box.min_z, box.max_z):
                            clip = matrix.map(QVector4D(x, y, z, 1))
                            assert clip.w() > 10
                            assert abs(clip.x()/clip.w()) < .910
                            assert abs(clip.y()/clip.w()) < .910
                            assert -1 < clip.z()/clip.w() < 1
                # Perspective must shrink the same transverse offset with depth.
                def project(depth):
                    p = camera.position + camera.forward*depth + camera.right*5
                    clip = matrix.map(QVector4D(p, 1))
                    return clip.x()/clip.w()
                assert abs(project(100)/project(200)-2) < .001
                position = QVector3D(camera.position)
                camera.fit_bounds(box, fov, aspect)
                assert (camera.position-position).length() < .002
                cases += 1
    view.close()
    print('PASS: {} perspective fits; axes, framing, depth and repeat fitting'.format(cases))


if __name__ == '__main__':
    main()

