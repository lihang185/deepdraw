"""Explicit invalidation contract shared by display, observation and shadows.

Changes are applied immediately. Pending instance references belong to the
pipeline/shadow pass and are discarded on model release.
Geometry changes also rebuild scene membership/bounds; transform-only changes
refit existing scene lists. View overlays do not invalidate shared geometry.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RenderChange:
    components: tuple = ()
    instances: tuple = ()
    all_geometry: bool = False
    scene: bool = False
    overlays: bool = False
    local_geometry: bool = False
    material_only: bool = False
