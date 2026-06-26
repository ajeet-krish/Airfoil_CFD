from pathlib import Path
from physics.fea import FeaWingAnalysis
import numpy as np

# Use the existing setup from the optimized wing
dat_path = Path("output/cfd/optimized/optimized_airfoil.dat")
output_dir = Path("output/fea/diagnostic_uniform")

# Initialize FEA
fea = FeaWingAnalysis(
    vtu_path="",
    dat_path=str(dat_path),
    output_dir=str(output_dir),
)

# Run with uniform load
results = fea.run_uniform_load(pressure=1000.0)
print(f"Results: {results}")
