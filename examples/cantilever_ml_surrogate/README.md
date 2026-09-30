# Cantilever Beam ML Surrogate Benchmark

This directory contains the legacy benchmark comparing traditional FEA exports against a Random Forest Regressor surrogate model for rapid mode shape deformation inference.

## Contents
- `Beam.py`: ML training and inference script mapping nodal coordinates + mode index to total deformation.
- `Beam_Mesh.stl`: 3D cantilever beam mesh geometry.
- `Mode1.txt` – `Mode6.txt`: Tabulated nodal deformation field data exported from Ansys.
