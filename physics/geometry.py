import numpy as np

def generate_naca_4digit(m, p, t, num_points=120):
    """
    Generates upper and lower coordinates for a NACA 4-digit airfoil.
    Parameters:
        m (float): Maximum camber (e.g., 0.02 for NACA 2412)
        p (float): Position of maximum camber (e.g., 0.4 for NACA 2412)
        t (float): Maximum thickness (e.g., 0.12 for NACA 2412)
        num_points (int): Number of points along the chord
    Returns:
        tuple: (upper_coords, lower_coords) as Nx2 numpy arrays
    """
    x = np.linspace(0, 1, num_points)
    
    # 1. Thickness distribution (yt)
    yt = 5 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
    
    # 2. Camber line (yc) and slope (dyc/dx)
    yc = np.zeros_like(x)
    dyc_dx = np.zeros_like(x)
    
    for i, xi in enumerate(x):
        if m == 0 or p == 0:
            # Symmetric airfoil (e.g. NACA 0012)
            yc[i] = 0.0
            dyc_dx[i] = 0.0
        elif xi < p:
            yc[i] = (m / p**2) * (2 * p * xi - xi**2)
            dyc_dx[i] = (2 * m / p**2) * (p - xi)
        else:
            yc[i] = (m / (1 - p)**2) * ((1 - 2 * p) + 2 * p * xi - xi**2)
            dyc_dx[i] = (2 * m / (1 - p)**2) * (p - xi)
            
    # 3. Combine coordinates perpendicular to the camber line
    theta = np.arctan(dyc_dx)
    
    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    
    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)
    
    upper_coords = np.vstack((xu, yu)).T
    lower_coords = np.vstack((xl, yl)).T
    
    return upper_coords, lower_coords

def save_dat_file(upper, lower, filename):
    """
    Saves the airfoil coordinates in Selig format (closed loop from TE, over the top, 
    around LE, and back to TE along bottom) into a .dat file.
    """
    # Exclude trailing edge duplicating points if any, and form closed loop:
    # upper[::-1] goes from TE (x=1) to LE (x=0)
    # lower[1:] goes from LE (x>0) to TE (x=1)
    coords = np.vstack((upper[::-1], lower[1:]))
    np.savetxt(filename, coords, fmt='%f %f')
