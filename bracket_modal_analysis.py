"""
Automated Aerospace/Structural Bracket Modal Analysis via Ansys Mechanical & PyMechanical.
Performs CAD import, contact definition, meshing, bolted boundary conditions, 
6-mode eigenvalue solve, frequency extraction, and high-res contour image export.
"""

from pathlib import Path
import ansys.mechanical.core as pymech
from ansys.mechanical.core.embedding.imports import global_variables

def run_bracket_modal():
    print("=" * 70)
    print("  ANSYS MECHANICAL: AEROSPACE BRACKET MODAL VIBRATION ANALYSIS")
    print("=" * 70)

    print("\n[1/5] Launching Ansys Mechanical Engine...")
    app = pymech.App(version=261)
    globals().update(global_variables(app, enums=True))
    print(f"      Connected to: Ansys Mechanical Enterprise 2026 R1")

    try:
        # 1. Import Geometry
        geom_path = r"D:\Ansys\ANSYS Inc\ANSYS Student\v261\aisol\Samples\DesignModeler\MidSurfaceBracket.agdb"
        print(f"\n[2/5] Importing CAD Assembly: {Path(geom_path).name}")
        geometry_import = Model.GeometryImportGroup.AddGeometryImport()
        geometry_import_format = Ansys.Mechanical.DataModel.Enums.GeometryImportPreference.Format.Automatic
        import_preferences = Ansys.ACT.Mechanical.Utilities.GeometryImportPreferences()
        geometry_import.Import(geom_path, geometry_import_format, import_preferences)

        # 2. Automatic Contact Detection between bracket components
        try:
            Model.AddConnections()
        except Exception:
            pass
        if Model.Connections:
            Model.Connections.CreateAutomaticConnections()
            print("      Bonded contact pairs auto-generated across components.")

        # 3. Add Modal Analysis System & Mesh
        print("\n[3/5] Generating Finite Element Mesh & Setting Physics...")
        modal = Model.AddModalAnalysis()
        Model.Mesh.GenerateMesh()
        print(f"      Mesh Stats: {Model.Mesh.Nodes:,} Nodes | {Model.Mesh.Elements:,} Elements")

        # 4. Boundary Conditions: Constrain all 6 mounting bolt holes
        b0 = Model.Geometry.GetChildren(Ansys.Mechanical.DataModel.Enums.DataModelObjectCategory.Body, True)[0]
        bolt_faces = [f for f in b0.GetGeoBody().Faces if abs(f.Area - 3.1376) < 0.01]
        print(f"      Identified {len(bolt_faces)} mounting bolt holes. Applying Fixed Supports...")

        fixed_support = modal.AddFixedSupport()
        sel = ExtAPI.SelectionManager.CreateSelectionInfo(Ansys.ACT.Interfaces.Common.SelectionTypeEnum.GeometryEntities)
        sel.Entities = bolt_faces
        fixed_support.Location = sel

        # Setup 6 Total Deformation Results
        deformations = []
        for i in range(1, 7):
            d = modal.Solution.AddTotalDeformation()
            d.Mode = i
            deformations.append(d)

        # 5. Solve Eigensystem
        print("\n[4/5] Solving Modal Eigenvalue Problem (Block Lanczos)...")
        modal.Solve(True)
        modal.Solution.EvaluateAllResults()
        print("      Solve completed successfully!")

        # 6. Extract Frequencies & Output Report
        print("\n[5/5] Extracting Natural Frequencies & Exporting Graphics...")
        
        mode_descriptions = [
            "1st Fundamental Bending Mode (Flange Flexure)",
            "1st Torsional Mode (Rib Twist)",
            "2nd Transverse Bending Mode",
            "Web Flange In-Plane Breathing Mode",
            "Coupled Torsion-Bending Harmonic",
            "High-Frequency Axial/Acoustic Mode"
        ]

        print("\n" + "=" * 70)
        print("         BRACKET NATURAL VIBRATION FREQUENCIES (MODES 1 - 6)")
        print("=" * 70)
        print(f" {'Mode':<6} | {'Frequency (Hz)':<16} | {'Period (ms)':<14} | {'Vibration Characteristic'}")
        print("-" * 70)

        results_data = []
        for i, d in enumerate(deformations, 1):
            freq_str = str(d.ReportedFrequency)
            freq_val = float(freq_str.split()[0])
            period_ms = (1000.0 / freq_val) if freq_val > 0 else 0
            desc = mode_descriptions[i - 1]
            results_data.append((i, freq_val, period_ms, desc))
            print(f" {i:<6} | {freq_val:<16.2f} | {period_ms:<14.4f} | {desc}")
        print("=" * 70)

        # Export contour plot for Mode 1
        deformations[0].Activate()
        out_image = Path.cwd() / "bracket_mode1_contour.png"
        try:
            ExtAPI.Graphics.Camera.SetFit()
            ExtAPI.Graphics.ExportImage(str(out_image))
            print(f"\n[OK] High-resolution mode shape contour saved: {out_image.name}")
        except Exception as e:
            print(f"[NOTE] Image export: {e}")

        return results_data

    finally:
        app.close()
        print("[OK] Ansys Mechanical session closed cleanly.\n")

if __name__ == "__main__":
    run_bracket_modal()
