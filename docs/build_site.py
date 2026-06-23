#!/usr/bin/env python3
"""Generate static docs/index.html with embedded, escaped source code."""
from __future__ import annotations
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = Path(__file__).resolve().parent

CHART = "\U0001f4c8"
MAP = "\U0001f5c2"
KEY = "\U0001f52e"
CAM = "\U0001f4f7"
BAR = "\U0001f4ca"
ROCK = "\U0001f680"


def read_src(rel: str) -> str:
    return (ROOT / rel).read_text()


def esc(code: str) -> str:
    return html.escape(code, quote=True)


def code_block(rel: str) -> str:
    src = read_src(rel)
    cls = 'class="code-block"'
    summ = f"<code>{rel}</code>"
    return (
        f'<div {cls}><details><summary>{summ}</summary>'
        f'<pre><code class="language-python">{esc(src)}</code></pre>'
        f"</details></div>"
    )


def code_summary(rel: str, summary: str) -> str:
    src = read_src(rel)
    cls = 'class="code-block"'
    return (
        f'<div {cls}><details><summary>{summary}</summary>'
        f'<pre><code class="language-python">{esc(src)}</code></pre>'
        f"</details></div>"
    )


RESULTS_TABLE = """<table>
  <tr><th>AoA</th><th>Regime</th><th>C_l</th><th>C_d</th><th>C_l/C_d</th><th>Status</th></tr>
  <tr><td>0&deg;</td><td>Symmetric Baseline</td><td class="hl-purple">0.0014</td><td class="hl-pink">0.0749</td><td class="hl-green">0.02</td><td>Converged</td></tr>
  <tr><td>4&deg;</td><td>Linear Lift</td><td class="hl-purple">0.4453</td><td class="hl-pink">0.0969</td><td class="hl-green">4.6</td><td>Converged</td></tr>
  <tr><td>8&deg;</td><td>High Lift</td><td class="hl-purple">0.8718</td><td class="hl-pink">0.1644</td><td class="hl-green">5.3</td><td>Converged</td></tr>
  <tr><td>12&deg;</td><td>Onset of Stall</td><td class="hl-purple">1.2647</td><td class="hl-pink">0.2764</td><td class="hl-green">4.6</td><td>Converged</td></tr>
  <tr><td>16&deg;</td><td>Deep Stall</td><td class="hl-purple">1.6082</td><td class="hl-pink">0.4314</td><td class="hl-green">3.7</td><td>Converged</td></tr>
</table>"""

SIMULATION_DETAILS = """<table>
  <tr><th>Parameter</th><th>Value</th></tr>
  <tr><td>Airfoil</td><td>NACA 0012 (symmetric, 12% thickness)</td></tr>
  <tr><td>Flow Solver</td><td>SU2 8.4.0 &mdash; Compressible RANS</td></tr>
  <tr><td>Turbulence Model</td><td>Spalart-Allmaras (SA)</td></tr>
  <tr><td>Convective Scheme</td><td>ROE &mdash; 1st-order (MUSCL=NO)</td></tr>
  <tr><td>Mesh Type</td><td>Hybrid C-grid &mdash; quads (BL) + triangles (farfield)</td></tr>
  <tr><td>Mesh Points</td><td>31,927</td></tr>
  <tr><td>Mesh Cells</td><td>63,141</td></tr>
  <tr><td>Boundary Layers</td><td>20 layers, ratio 1.15, first height 2&times;10<sup>-5</sup></td></tr>
  <tr><td>Y<sup>+</sup> (max / mean)</td><td>1.04 / 0.01</td></tr>
  <tr><td>Farfield Radius</td><td>15 chords (semicircle) + 30 chords downstream</td></tr>
  <tr><td>Mach Number</td><td>0.15</td></tr>
  <tr><td>Reynolds Number</td><td>1 &times; 10<sup>6</sup></td></tr>
  <tr><td>CFL Number</td><td>0.01 &rarr; 5.0 (ramp over 2000 iters)</td></tr>
  <tr><td>Iterations per AoA</td><td>2,000</td></tr>
  <tr><td>Angles of Attack</td><td>0&deg;, 4&deg;, 8&deg;, 12&deg;, 16&deg;</td></tr>
  <tr><td>Convergence Criterion</td><td>RMS Density &lt; 10<sup>-6</sup></td></tr>
</table>"""

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="CFD analysis of NACA 0012 across multiple angles of attack using SU2 RANS with C-grid meshing">
  <title>NACA 0012 &mdash; CFD Wind Tunnel Report</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,600;14..32,700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@xz/fonts@1/serve/meslo-lg.min.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css">
  <link rel="stylesheet" href="css/style.css">
</head>
<body>

<div class="bg-motif" aria-hidden="true"></div>

<!-- NAV -->
<nav class="site-nav" id="top">
  <div class="nav-inner">
    <span class="nav-brand">NACA 0012</span>
    <div class="nav-entries">
      <a href="#theory">Theory</a>
      <a href="#methodology">Methodology</a>
      <a href="#results">Results</a>
      <a href="#code">Code</a>
      <a href="#paraview">ParaView</a>
    </div>
  </div>
</nav>

<!-- HERO -->
<div class="hero">
  <h1>NACA 0012 <span class="highlight">Wind Tunnel</span></h1>
  <p>Automated CFD analysis sweeping five angles of attack using SU2 RANS (Spalart-Allmaras) on a high-quality C-grid mesh with structured boundary layers.</p>
  <div style="margin-top:1rem; display:flex; gap:0.8rem; justify-content:center; flex-wrap:wrap;">
    <span class="hero-badge">SU2 8.4.0</span>
    <span class="hero-badge">Gmsh C-Grid</span>
    <span class="hero-badge">Spalart-Allmaras</span>
    <span class="hero-badge">Dracula Theme</span>
  </div>
</div>

<div class="container main-with-toc">

  <!-- TOC -->
  <aside class="sidebar-toc" id="toc"></aside>

  <main>

    <!-- ============================================================ -->
    <section id="theory">
    <h2>1. Aerodynamic Theory</h2>
    <!-- ============================================================ -->

    <p>The NACA 0012 is a symmetric 4-digit airfoil with 12% thickness-to-chord ratio. The upper and lower surfaces are described by the NACA thickness distribution:</p>

    <p>$$y_t = 5t\\left(0.2969\\sqrt{x} - 0.1260x - 0.3516x^2 + 0.2843x^3 - 0.1015x^4\\right)$$</p>

    <p>where $t = 0.12$ is the maximum thickness. For symmetric airfoils ($m=0, p=0$), the camber line is zero, giving $y_{\\text{upper}} = +y_t$ and $y_{\\text{lower}} = -y_t$.</p>

    <p>The simulation sweep spans five key flight regimes:</p>
    <ul>
      <li><strong class="hl-cyan">0&deg; &mdash; Symmetric Baseline:</strong> Attached flow, zero lift. Verifies solver symmetry and mesh quality.</li>
      <li><strong class="hl-cyan">4&deg; &mdash; Linear Lift:</strong> Attached flow in the linear portion of the lift curve. $C_l \\approx 2\\pi\\alpha$.</li>
      <li><strong class="hl-cyan">8&deg; &mdash; High Lift:</strong> Strong suction peak near the leading edge. Approaching the nonlinear regime.</li>
      <li><strong class="hl-cyan">12&deg; &mdash; Onset of Stall:</strong> Boundary layer separation near the trailing edge. Recirculation develops in the wake.</li>
      <li><strong class="hl-cyan">16&deg; &mdash; Deep Stall:</strong> Massive separation. Large recirculating wake dominates the aerodynamics.</li>
    </ul>

    <p>Flow conditions: $M = 0.15$, $Re = 1 \\times 10^6$, chord = 1 m, standard air at sea level.</p>

    <h3>Lift Curve Slope</h3>
    <p>For a thin symmetric airfoil, potential flow theory predicts $C_l = 2\\pi\\alpha$. With our RANS results, the slope from 0&deg; to 8&deg; is approximately <strong class="hl-purple">0.109 per degree</strong> &mdash; matching the theoretical $2\\pi$ prediction within 1%.</p>
    </section>

    <!-- ============================================================ -->
    <section id="methodology">
    <h2>2. Methodology</h2>
    <!-- ============================================================ -->

    <div class="card-grid">
      <div class="card">
        <span class="tag">Mesh</span>
        <h4>C-Grid with Boundary Layer</h4>
        <p>Hybrid mesh: structured quad boundary layer (20 layers, $y^+ \\approx 1$) around the airfoil, transitioning to unstructured triangles in the farfield. C-shaped outer boundary with semicircular inlet (R=15 chords) and rectangular outlet (30 chords downstream).</p>
      </div>
      <div class="card">
        <span class="tag">Solver</span>
        <h4>SU2 RANS (SA)</h4>
        <p>Steady compressible Reynolds-Averaged Navier-Stokes equations closed by the Spalart-Allmaras one-equation turbulence model. ROE scheme with 1st-order spatial discretization (MUSCL=NO). CFL adaptively ramps from 0.01 to 5.0.</p>
      </div>
      <div class="card">
        <span class="tag">Post-Processing</span>
        <h4>Matplotlib + PyVista</h4>
        <p>Off-screen rendering of velocity contours with streamlines, pressure field, mesh topology, convergence history, and aggregate $C_l$/$C_d$ curves with experimental (Ladson 1988) comparison.</p>
      </div>
    </div>

    <h3>Simulation Details</h3>
    """ + SIMULATION_DETAILS + """

    <h3>Code Implementation</h3>
    <p>Each major pipeline component is implemented as a reusable Python class. Click to expand the source:</p>

    <h4>Geometry Generation</h4>
    <p>The NACA 4-digit thickness distribution uses cosine-spaced points for leading/trailing edge clustering. The <code>t/100</code> bug was fixed to correctly interpret NACA convention (e.g., NACA 0012 = 12% thickness, not 1200%).</p>
    """ + code_summary('physics/geometry.py', f'{CHART} generate_naca_4digit() &mdash; NACA airfoil coordinates with cosine spacing') + """

    <h4>C-Grid Mesh Generation</h4>
    <p>Gmsh builds a hybrid C-grid: structured boundary layer (20 layers, ratio 1.15) via <code>setAsBoundaryLayer()</code>, then Frontal-Delaunay triangulation for the farfield. Physical groups for airfoil (wall), farfield (inlet/outlet), and fluid are tagged for SU2.</p>
    """ + code_summary('physics/mesher.py', f'{MAP} MeshGenerator.generate() &mdash; Hybrid C-grid with boundary layer') + """

    <h4>Solver Configuration &amp; Execution</h4>
    <p>SU2Config is a dataclass that generates a <code>.cfg</code> file programmatically. SU2Solver runs SU2_CFD, parses the history CSV to extract CL/CD, and returns an SU2Results dataclass. Fixed: <code>Path.resolve()</code> needed for correct SU2 working directory.</p>
    """ + code_summary('physics/solver.py', f'{KEY} SU2Config + SU2Solver.run() &mdash; Config generation & solver interface') + """

    <h4>Visualization Pipeline</h4>
    <p>Velocity and pressure contours are computed by interpolating the unstructured VTU data onto a regular 600&times;400 Cartesian grid via <code>scipy.griddata</code> (Soccer CFD pattern). Streamlines use <code>matplotlib.ax.streamplot()</code>, avoiding PyVista's hanging <code>streamlines_evenly_spaced_2D</code> on the 97K-cell mesh.</p>
    """ + code_summary('physics/post.py', f'{CAM} Visualizer &mdash; matplotlib velocity/pressure with griddata + streamplot') + """

    <h4>Analysis &amp; Validation</h4>
    <p>Convergence history, Cl/Cd curves, and drag polar with experimental overlay (Ladson 1988). All plots use the Dracula color scheme.</p>
    """ + code_summary('physics/analysis.py', f'{BAR} Analysis &mdash; Convergence, Cl/Cd, drag polar with experimental overlay') + """

    <h4>Orchestrator</h4>
    <p>The main loop iterates through 5 angles of attack, coordinating geometry &rarr; mesh &rarr; solver &rarr; viz. This file is the entrypoint for the pipeline.</p>
    """ + code_summary('run_tunnel.py', f'{ROCK} run_tunnel.py &mdash; Main pipeline orchestrator') + """

    </section>

    <!-- ============================================================ -->
    <section id="results">
    <h2>3. CFD Results</h2>
    <!-- ============================================================ -->

    <h3>Results Summary</h3>
    """ + RESULTS_TABLE + """

    <!-- Aggregate Plots -->
    <div class="aggregate-section">
      <h3 style="margin-top: 0; border-bottom: 2px solid var(--comment); padding-bottom: 0.5rem;">Aggregate Aerodynamic Coefficients</h3>
      <div class="vis-grid">
        <div class="vis-card wide-row">
          <div class="vis-card-title">Lift Curve &mdash; $C_l$ vs Angle of Attack</div>
          <div class="vis-image-container">
            <img src="assets/images/cl_vs_alpha.png" alt="Lift curve" class="vis-image" loading="lazy">
          </div>
        </div>
        <div class="vis-card">
          <div class="vis-card-title">Drag Polar &mdash; $C_d$ vs $\\alpha$</div>
          <div class="vis-image-container">
            <img src="assets/images/cd_vs_alpha.png" alt="Drag vs alpha" class="vis-image" loading="lazy">
          </div>
        </div>
        <div class="vis-card">
          <div class="vis-card-title">Drag Polar &mdash; $C_l$ vs $C_d$</div>
          <div class="vis-image-container">
            <img src="assets/images/drag_polar.png" alt="Lift vs drag" class="vis-image" loading="lazy">
          </div>
        </div>
      </div>
    </div>

    <!-- AoA Nav -->
    <div class="aoa-nav">
      <a href="#aoa-0">0&deg;</a>
      <a href="#aoa-4">4&deg;</a>
      <a href="#aoa-8">8&deg;</a>
      <a href="#aoa-12">12&deg;</a>
      <a href="#aoa-16">16&deg;</a>
    </div>

    <!-- Per-AoA Sections -->
    <section class="aoa-section fade-in" id="aoa-0">
      <div class="aoa-header">
        <h3 class="aoa-title">AoA = 0&deg;</h3>
        <span class="aoa-badge">Symmetric Baseline</span>
      </div>
      <div class="metrics-grid">
        <div class="metric-card lift"><div class="metric-label">$C_l$</div><div class="metric-value hl-purple">0.0014</div></div>
        <div class="metric-card drag"><div class="metric-label">$C_d$</div><div class="metric-value hl-pink">0.0749</div></div>
        <div class="metric-card ratio"><div class="metric-label">$C_l/C_d$</div><div class="metric-value hl-green">0.02</div></div>
      </div>
      <div class="vis-grid">
        <div class="vis-card mesh-row">
          <div class="vis-card-title">C-Grid Mesh &mdash; Leading Edge Detail</div>
          <div class="vis-image-container"><img src="assets/images/aoa_0/mesh.png" alt="Mesh at 0 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card">
          <div class="vis-card-title">Velocity Contours &amp; Streamlines</div>
          <div class="vis-image-container"><img src="assets/images/aoa_0/velocity.png" alt="Velocity at 0 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card">
          <div class="vis-card-title">Pressure Field (Pa)</div>
          <div class="vis-image-container"><img src="assets/images/aoa_0/pressure.png" alt="Pressure at 0 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card wide-row">
          <div class="vis-card-title">Convergence History &mdash; RMS Residuals &amp; Force Coefficients</div>
          <div class="vis-image-container"><img src="assets/images/aoa_0/convergence.png" alt="Convergence at 0 degrees" class="vis-image" loading="lazy"></div>
        </div>
      </div>
    </section>

    <section class="aoa-section fade-in" id="aoa-4">
      <div class="aoa-header">
        <h3 class="aoa-title">AoA = 4&deg;</h3>
        <span class="aoa-badge">Linear Lift</span>
      </div>
      <div class="metrics-grid">
        <div class="metric-card lift"><div class="metric-label">$C_l$</div><div class="metric-value hl-purple">0.4453</div></div>
        <div class="metric-card drag"><div class="metric-label">$C_d$</div><div class="metric-value hl-pink">0.0969</div></div>
        <div class="metric-card ratio"><div class="metric-label">$C_l/C_d$</div><div class="metric-value hl-green">4.6</div></div>
      </div>
      <div class="vis-grid">
        <div class="vis-card mesh-row">
          <div class="vis-card-title">C-Grid Mesh &mdash; Leading Edge Detail</div>
          <div class="vis-image-container"><img src="assets/images/aoa_4/mesh.png" alt="Mesh at 4 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card">
          <div class="vis-card-title">Velocity Contours &amp; Streamlines</div>
          <div class="vis-image-container"><img src="assets/images/aoa_4/velocity.png" alt="Velocity at 4 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card">
          <div class="vis-card-title">Pressure Field (Pa)</div>
          <div class="vis-image-container"><img src="assets/images/aoa_4/pressure.png" alt="Pressure at 4 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card wide-row">
          <div class="vis-card-title">Convergence History</div>
          <div class="vis-image-container"><img src="assets/images/aoa_4/convergence.png" alt="Convergence at 4 degrees" class="vis-image" loading="lazy"></div>
        </div>
      </div>
    </section>

    <section class="aoa-section fade-in" id="aoa-8">
      <div class="aoa-header">
        <h3 class="aoa-title">AoA = 8&deg;</h3>
        <span class="aoa-badge">High Lift</span>
      </div>
      <div class="metrics-grid">
        <div class="metric-card lift"><div class="metric-label">$C_l$</div><div class="metric-value hl-purple">0.8718</div></div>
        <div class="metric-card drag"><div class="metric-label">$C_d$</div><div class="metric-value hl-pink">0.1644</div></div>
        <div class="metric-card ratio"><div class="metric-label">$C_l/C_d$</div><div class="metric-value hl-green">5.3</div></div>
      </div>
      <div class="vis-grid">
        <div class="vis-card mesh-row">
          <div class="vis-card-title">C-Grid Mesh &mdash; Leading Edge Detail</div>
          <div class="vis-image-container"><img src="assets/images/aoa_8/mesh.png" alt="Mesh at 8 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card">
          <div class="vis-card-title">Velocity Contours &amp; Streamlines</div>
          <div class="vis-image-container"><img src="assets/images/aoa_8/velocity.png" alt="Velocity at 8 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card">
          <div class="vis-card-title">Pressure Field (Pa)</div>
          <div class="vis-image-container"><img src="assets/images/aoa_8/pressure.png" alt="Pressure at 8 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card wide-row">
          <div class="vis-card-title">Convergence History</div>
          <div class="vis-image-container"><img src="assets/images/aoa_8/convergence.png" alt="Convergence at 8 degrees" class="vis-image" loading="lazy"></div>
        </div>
      </div>
    </section>

    <section class="aoa-section fade-in" id="aoa-12">
      <div class="aoa-header">
        <h3 class="aoa-title">AoA = 12&deg;</h3>
        <span class="aoa-badge">Onset of Stall</span>
      </div>
      <div class="metrics-grid">
        <div class="metric-card lift"><div class="metric-label">$C_l$</div><div class="metric-value hl-purple">1.2647</div></div>
        <div class="metric-card drag"><div class="metric-label">$C_d$</div><div class="metric-value hl-pink">0.2764</div></div>
        <div class="metric-card ratio"><div class="metric-label">$C_l/C_d$</div><div class="metric-value hl-green">4.6</div></div>
      </div>
      <div class="vis-grid">
        <div class="vis-card mesh-row">
          <div class="vis-card-title">C-Grid Mesh &mdash; Leading Edge Detail</div>
          <div class="vis-image-container"><img src="assets/images/aoa_12/mesh.png" alt="Mesh at 12 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card">
          <div class="vis-card-title">Velocity Contours &amp; Streamlines</div>
          <div class="vis-image-container"><img src="assets/images/aoa_12/velocity.png" alt="Velocity at 12 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card">
          <div class="vis-card-title">Pressure Field (Pa)</div>
          <div class="vis-image-container"><img src="assets/images/aoa_12/pressure.png" alt="Pressure at 12 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card wide-row">
          <div class="vis-card-title">Convergence History</div>
          <div class="vis-image-container"><img src="assets/images/aoa_12/convergence.png" alt="Convergence at 12 degrees" class="vis-image" loading="lazy"></div>
        </div>
      </div>
    </section>

    <section class="aoa-section fade-in" id="aoa-16">
      <div class="aoa-header">
        <h3 class="aoa-title">AoA = 16&deg;</h3>
        <span class="aoa-badge">Deep Stall</span>
      </div>
      <div class="metrics-grid">
        <div class="metric-card lift"><div class="metric-label">$C_l$</div><div class="metric-value hl-purple">1.6082</div></div>
        <div class="metric-card drag"><div class="metric-label">$C_d$</div><div class="metric-value hl-pink">0.4314</div></div>
        <div class="metric-card ratio"><div class="metric-label">$C_l/C_d$</div><div class="metric-value hl-green">3.7</div></div>
      </div>
      <div class="vis-grid">
        <div class="vis-card mesh-row">
          <div class="vis-card-title">C-Grid Mesh &mdash; Leading Edge Detail</div>
          <div class="vis-image-container"><img src="assets/images/aoa_16/mesh.png" alt="Mesh at 16 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card">
          <div class="vis-card-title">Velocity Contours &amp; Streamlines</div>
          <div class="vis-image-container"><img src="assets/images/aoa_16/velocity.png" alt="Velocity at 16 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card">
          <div class="vis-card-title">Pressure Field (Pa)</div>
          <div class="vis-image-container"><img src="assets/images/aoa_16/pressure.png" alt="Pressure at 16 degrees" class="vis-image" loading="lazy"></div>
        </div>
        <div class="vis-card wide-row">
          <div class="vis-card-title">Convergence History</div>
          <div class="vis-image-container"><img src="assets/images/aoa_16/convergence.png" alt="Convergence at 16 degrees" class="vis-image" loading="lazy"></div>
        </div>
      </div>
    </section>

    </section>

    <!-- ============================================================ -->
    <section id="code">
    <h2>4. Code Architecture</h2>
    <!-- ============================================================ -->

    <p>The pipeline is organized into five modular components under <code>physics/</code>:</p>

    <table>
      <tr><th>Module</th><th>Purpose</th></tr>
      <tr><td><code>geometry.py</code></td><td>NACA 4-digit coordinate generation with cosine spacing</td></tr>
      <tr><td><code>mesher.py</code></td><td>MeshGenerator class &mdash; hybrid C-grid with structured boundary layers via Gmsh</td></tr>
      <tr><td><code>solver.py</code></td><td>SU2Config dataclass + SU2Solver + SU2Results</td></tr>
      <tr><td><code>post.py</code></td><td>Visualizer &mdash; matplotlib velocity/pressure/mesh with griddata-based streamlines</td></tr>
      <tr><td><code>analysis.py</code></td><td>Convergence plots, $C_l$/$C_d$ curves, drag polar with experimental overlay</td></tr>
    </table>

    <p>The orchestrator <code>run_tunnel.py</code> iterates through angles of attack, coordinates the pipeline stages, aggregates results, and syncs output images to <code>docs/assets/images/</code>.</p>

    <h3>Full Source Code</h3>
    <p>Complete source for all pipeline modules:</p>

    """ + code_block('physics/geometry.py') + """
    """ + code_block('physics/mesher.py') + """
    """ + code_block('physics/solver.py') + """
    """ + code_block('physics/post.py') + """
    """ + code_block('physics/analysis.py') + """
    """ + code_block('run_tunnel.py') + """

    </section>

    <!-- ============================================================ -->
    <section id="paraview">
    <h2>5. ParaView Walkthrough</h2>
    <!-- ============================================================ -->

    <p>ParaView provides interactive exploration of the CFD results. Follow these steps to load and analyze the VTU solution files:</p>

    <div class="card-grid">
      <div class="card">
        <span class="tag">Step 1</span>
        <h4>Open the Solution File</h4>
        <p><code>File &rarr; Open</code> &rarr; navigate to <code>output/aoa_0/flow_results.vtu</code> (or any angle). Click <strong>Apply</strong> in the Properties panel.</p>
      </div>
      <div class="card">
        <span class="tag">Step 2</span>
        <h4>2D View</h4>
        <p>Press <kbd>X</kbd> to switch to the X-axis normal view (looking down the span). Use <kbd>Ctrl+Scroll</kbd> to zoom. The mesh appears as an unstructured surface.</p>
      </div>
      <div class="card">
        <span class="tag">Step 3</span>
        <h4>Velocity Contours</h4>
        <p>In the dropdown next to the color bar, change from <code>Solid Color</code> to <code>Velocity</code> or <code>Pressure</code>. Use the rainbow preset or edit the color map.</p>
      </div>
    </div>

    <h3>Velocity Magnitude Contours</h3>
    <ol>
      <li>Select <code>flow_results.vtu</code> in the Pipeline Browser.</li>
      <li><strong>Filters &rarr; Alphabetical &rarr; Contour</strong>.</li>
      <li>In Properties: check <strong>Compute Normals</strong> (off). Set <strong>Contour By</strong> to <code>Velocity</code> (or add a Calculator filter to compute <code>sqrt(Velocity_X^2 + Velocity_Y^2 + Velocity_Z^2)</code> named <code>Velocity_Mag</code>).</li>
      <li>Set <strong>Value Range</strong> to 0 to ~60 (adjust based on data). Click <strong>Apply</strong>.</li>
      <li>For filled contours, use the <strong>Contour</strong> filter with filled option, or extract a slice and use <strong>Filters &rarr; Data Analysis &rarr; Plot Data</strong> along a line.</li>
    </ol>

    <h3>Streamlines / Pathlines</h3>
    <ol>
      <li>Select <code>flow_results.vtu</code> in the Pipeline Browser.</li>
      <li><strong>Filters &rarr; Alphabetical &rarr; Stream Tracer</strong> (or <strong>Stream Tracer With Custom Source</strong>).</li>
      <li><strong>Seed Source:</strong> Change to <strong>Line Source</strong>. Place the line upstream of the airfoil (e.g., from <code>(-1.5, -0.5, 0)</code> to <code>(-1.5, 0.5, 0)</code>).</li>
      <li><strong>Integration Direction:</strong> FORWARD.</li>
      <li><strong>Maximum Streamline Length:</strong> 10.</li>
      <li>Click <strong>Apply</strong>. ParaView will trace streamlines through the velocity field.</li>
      <li>Color the streamlines by <code>Velocity</code> magnitude for a polished look.</li>
    </ol>

    <h3>Pressure Distribution (Cp) Along the Airfoil</h3>
    <ol>
      <li>Select <code>flow_results.vtu</code> in the Pipeline Browser.</li>
      <li><strong>Filters &rarr; Alphabetical &rarr; Plot Over Line</strong>.</li>
      <li>Set the line endpoints to approximately follow the airfoil surface (from trailing edge, over top, to leading edge, back along bottom). For a 2D airfoil spanning y from -0.06 to 0.06 at x/c intervals, draw the line <code>(0, 0, 0)</code> to <code>(1, 0, 0)</code> &mdash; but this gives chordwise data, not surface Cp.</li>
      <li>For true surface Cp: <strong>Filters &rarr; Alphabetical &rarr; Extract Surface</strong>, then <strong>Filters &rarr; Alphabetical &rarr; Plot Over Line</strong> along the airfoil boundary.</li>
      <li>In the resulting chart, plot <code>Pressure</code> or add a Calculator to compute $C_p = (P - P_\\infty) / (0.5 \\rho U_\\infty^2)$.</li>
    </ol>

    <h3>Mesh Inspection</h3>
    <ol>
      <li>Select <code>flow_results.vtu</code>.</li>
      <li>In Properties, set <strong>Representation</strong> to <strong>Wireframe</strong>.</li>
      <li>Zoom into the leading edge region to see the structured boundary layer quads transitioning to triangles.</li>
      <li>Use <strong>Filters &rarr; Alphabetical &rarr; Glyph</strong> with 3D arrows to visualize the velocity vector field.</li>
    </ol>

    <h3>Timestep Animation (if available)</h3>
    <ol>
      <li>If using the restart.dat for unsteady analysis, load as a time series.</li>
      <li>Use the VCR controls in the toolbar to play through time.</li>
      <li>Combine with Stream Tracer for animated streaklines.</li>
    </ol>

    </section>

  </main>
</div>

<footer class="site-footer">
  <p>&copy; 2026 &middot; Automated CFD Wind Tunnel &middot; NACA 0012 Analysis</p>
  <p style="margin-top: 6px;">
    <a href="https://github.com/ajeet/Airfoil_CFD">GitHub</a> &middot;
    SU2 &middot; Gmsh &middot; Matplotlib &middot; Dracula Theme
  </p>
</footer>

<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/prism.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/copy-to-clipboard/prism-copy-to-clipboard.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function () {
  // KaTeX auto-render
  renderMathInElement(document.body, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "$", right: "$", display: false }
    ],
    throwOnError: false
  });

  // Fade-in on scroll
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
  }, { threshold: 0.1 });
  document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

  // TOC generation
  const toc = document.getElementById('toc');
  if (toc) {
    const headings = document.querySelectorAll('main h2, main h3');
    headings.forEach(h => {
      if (!h.id) return;
      const a = document.createElement('a');
      a.href = '#' + h.id;
      a.textContent = h.textContent.replace(/^\\d+\\.\\s*/, '');
      if (h.tagName === 'H3') a.classList.add('h3');
      toc.appendChild(a);
    });
  }

  // TOC scroll-spy
  const tocLinks = document.querySelectorAll('.sidebar-toc a');
  if (tocLinks.length) {
    const observer2 = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          tocLinks.forEach(l => l.classList.remove('active'));
          const link = document.querySelector('.sidebar-toc a[href="#' + e.target.id + '"]');
          if (link) link.classList.add('active');
        }
      });
    }, { rootMargin: '-80px 0px -50% 0px' });
    document.querySelectorAll('section[id]').forEach(s => observer2.observe(s));
  }

  // Prism highlight all code blocks within details
  document.querySelectorAll('.code-block details').forEach(d => {
    d.addEventListener('toggle', function() {
      if (this.open) {
        Prism.highlightAllUnder(this);
      }
    });
  });
});
</script>
</body>
</html>"""

# Fix up per-AoA image paths to include AoA suffix
for aoa in [0, 4, 8, 12, 16]:
    for stem in ("mesh", "velocity", "pressure", "convergence"):
        old = f'aoa_{aoa}/{stem}.png'
        new = f'aoa_{aoa}/{stem}_{aoa}.png'
        HTML = HTML.replace(old, new)

(DOCS / "index.html").write_text(HTML)
print(f"Generated {DOCS / 'index.html'} ({len(HTML)} bytes)")

