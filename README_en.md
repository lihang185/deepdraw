# DeepDraw Engine

[中文](README.md) | [English](README_en.md)

Official website: [www.archieast.com](https://www.archieast.com)

DeepDraw is an alternative to SketchUp and a lightweight, general-purpose 3D graphics engine developed in China.

It follows a technical approach as close to SketchUp as possible, keeping its core algorithms and data structures aligned with SketchUp to enable seamless migration of existing projects without changing users' workflows.

![DeepDraw interface screenshot](screenshot/screenshot01.png)

## National Strategy

China has a vast number of architectural design, urban renewal, interior design, and engineering projects, with design exploration and 3D visualization forming part of everyday work. The National Bureau of Statistics' Fifth National Economic Census bulletin documents the enormous scale of the construction industry. The *Guiding Opinions on Promoting the Coordinated Development of Intelligent Construction and Building Industrialization*, issued by the Ministry of Housing and Urban-Rural Development and other departments, calls for breakthroughs in key technologies such as specialized software, the active adoption of independently controlled BIM technologies, and the development of digital design platforms and integrated systems.

## Cornerstone Initiative

As the world's largest industrial nation, China has long lacked its own industrial design software products, relying on foreign vendors and remaining dependent on Europe and the United States. This is like a towering skyscraper whose foundations still need strengthening. We have launched the "Cornerstone Initiative" with the goal of developing affordable alternatives to all industrial design software sold in China over the next ten years. A decade of foundation-building will support an independent future for Chinese industry. The scope includes Rhino, AutoCAD, SolidWorks, UG, and MATLAB.

## Product Comparison

This project shares much of its product positioning with [IngeTrazo](https://github.com/ingelibre/ingetrazo), but takes a different technical approach.

| Product | Origin | Price | Technology Stack | Features |
| --- | --- | --- | --- | --- |
| DeepDraw | China · Shendu Zhihui (Shanghai) | Free | Python + Qt5, with core components in C++ | Low-level algorithms implemented in C++ with a focus on performance; technical implementation kept as close to SketchUp as possible |
| IngeTrazo | Peru | Free | Python + Qt6 | Written entirely in Python |

## Running the Application

Double-click `start_education.cmd`, or run the application with a configured Python 3.8 interpreter:

```console
C:\python\Python38\python.exe editor.py
```

`editor.py` is the sole entry point and is also retained as the startup file for Eric IDE. Set `DEEPDRAW_EDUCATION_PYTHON` to specify the interpreter. See `requirements-education.txt` for dependencies.

## Directory Structure

| Directory | Purpose |
| --- | --- |
| `app/` | Application startup, main window, Qt interface, and plugin management |
| `app/ui/` | Designer `.ui` files, corresponding controllers, generated `Ui_*.py` files, and Qt resource modules |
| `editing/` | User editing transactions, undo, grouping, clipboard, text, and material operations |
| `engine/` | Native bindings, DAI encoding and decoding, geometry tools, and rendering |
| `engine/tools/` | Active interactive modeling tools, with one implementation per tool |
| `engine/viewer/` | Viewport, camera, section cuts, annotation display, and shadows |
| `engine/native/cp38/` | Matching native geometry and rendering binaries |
| `assets/` | Education edition icons and Qt resource manifest |
| `data/` | Existing models, materials, and asset data; these files are not modified during reorganization |
| `importers/sketchup/` | Isolated SKP import process using the current engine, pybind11 modules, and SDK DLLs |
| `native/sketchup/` | pybind11/CMake source code, SDK, and regression checks for suapi, suapi_extra, and skp_exporter |
| `plugins/` | Extension entry points compatible with the current education edition; obsolete plugins have been removed |
| `scripts/` | Development tools |
| `tests/` | File format checks and regression checks using real Qt/OpenGL |
| `packaging/` | Standalone PyInstaller packaging configuration |
| `runtime/` | Test screenshots, reports, and build artifacts; no source code |
| `docs/` | Architecture, migration sources, reorganization records, and asset verification records |

## Environment Setup

Currently, only **64-bit CPython 3.8 (x64) on Windows** is supported. The bundled native extensions are built for Python 3.8 x64; other Python versions and 32-bit interpreters are not supported.

1. Install 64-bit Python 3.8, preferably at `C:\python\Python38`.
2. Run the following command from the project root to install the runtime dependencies:

   ```console
   C:\python\Python38\python.exe -m pip install -r requirements-education.txt
   ```

   Runtime dependencies include PySide2, PyOpenGL, NumPy, and Pillow. See `requirements-education.txt` for version requirements.

3. Keep the bundled native extensions and matching DLLs in `engine/native/cp38/` and `importers/sketchup/`.
4. Double-click `start_education.cmd` to launch the application. If Python is installed elsewhere, set the `DEEPDRAW_EDUCATION_PYTHON` environment variable to the full path of your 64-bit Python 3.8 interpreter.
