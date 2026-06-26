from __future__ import annotations

from pathlib import Path

import cadquery as cq
import trimesh

STEP_DIR = Path("output/cad")
MODELS_DIR = Path("docs/assets/models")


def step_to_glb(step_path: Path, glb_path: Path, quality: float = 0.5):
    print(f"  Loading STEP: {step_path}")
    shape = cq.importers.importStep(str(step_path))

    print("  Tessellating...")
    mesh = shape.val().tessellate(quality)

    vertices = [(v.x, v.y, v.z) for v in mesh[0]]
    faces = [f for f in mesh[1]]

    trimesh_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    trimesh_mesh.fix_normals()

    print(f"  Vertices: {len(vertices)}, Faces: {len(faces)}")
    print(f"  Exporting GLB: {glb_path}")

    glb_path.parent.mkdir(parents=True, exist_ok=True)
    trimesh_mesh.export(str(glb_path), file_type="glb")
    print("  Done.")


def main():
    step_files = list(STEP_DIR.glob("*.step"))
    if not step_files:
        print(f"No .step files found in {STEP_DIR}")
        return

    for sp in step_files:
        glb_name = sp.stem + ".glb"
        glb_path = MODELS_DIR / glb_name
        print(f"\nConverting {sp.name} -> {glb_path.name}")
        step_to_glb(sp, glb_path)

    print("\nAll conversions complete.")


if __name__ == "__main__":
    main()
