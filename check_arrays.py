import pyvista as pv
mesh = pv.read("output/aoa_0/flow_results.vtu")
print(mesh.array_names)
