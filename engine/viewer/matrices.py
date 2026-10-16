"""Native affine transform to an OpenGL column-major matrix."""
from .render_backend import affine12


def gl_matrix(matrix):
    values = affine12(matrix)
    return [values[r*3+c] if r < 3 else 0.0 for c in range(3) for r in range(4)] + values[9:] + [1.0]
