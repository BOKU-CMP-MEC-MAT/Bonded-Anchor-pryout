import pyvista as pv
import numpy as np
import argparse
import math

# ==========================================
# COMMAND LINE ARGUMENT PARSING
# ==========================================
parser = argparse.ArgumentParser(description="Live render structural FEA results with PyVista.")
parser.add_argument("filename", type=str, help="Path to the EnSight .case file")
parser.add_argument("-t", "--threshold", type=float, default=0.3, 
                    help="Damage threshold for the fracture surface (default: 0.3)")
parser.add_argument("-w", "--warp", type=float, default=15.0, 
                    help="Displacement magnification factor (default: 15.0)")
parser.add_argument("-o", "--output", type=str, default="anchor_breakout.mp4", 
                    help="Output MP4 filename (default: anchor_breakout.mp4)")
args = parser.parse_args()

# ==========================================
# CONFIGURATION
# ==========================================
filename = args.filename
warp_factor = args.warp
damage_threshold = args.threshold
output_file = args.output

# Field Variables
disp_var = "nodeDisplacements"  
raw_damage_var = "nonlocalDamage"  
mapped_damage_var = "damage"       
damage_scale_factor = 0.0045       

block_names = {
    "concrete": "ASSEMBLY_CONCRETE-1_CONCRETE",
    "mortar": "ASSEMBLY_STEEL-1_MORTAR",
    "steel": "ASSEMBLY_STEEL-1_STEEL"
}

# --- COLORBAR CONFIGURATION ---
sargs = dict(
    title_font_size=32,
    label_font_size=32,
    vertical=True,
    position_x=0.05,  
    position_y=0.05,  
    height=0.5,       
    width=0.08        
)

# ==========================================
# INITIALIZATION 
# ==========================================
reader = pv.get_reader(filename)
available_times = np.array(reader.time_values)

plotter = pv.Plotter(window_size=[1280, 960])
plotter.open_movie(output_file, framerate=30)

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def extract_block(multiblock, name):
    for i in range(multiblock.n_blocks):
        block_name = multiblock.get_block_name(i)
        if block_name == name:
            return multiblock[i]
        if isinstance(multiblock[i], pv.MultiBlock):
            res = extract_block(multiblock[i], name)
            if res is not None:
                return res
    raise ValueError(f"Block '{name}' not found in the dataset.")

def interpolate_mesh(mesh_a, mesh_b, weight):
    interp_mesh = mesh_a.copy(deep=True)
    interp_mesh.points = mesh_a.points + weight * (mesh_b.points - mesh_a.points)
    
    # 1. Interpolate Displacement
    if disp_var in mesh_a.point_data and disp_var in mesh_b.point_data:
        interp_mesh.point_data[disp_var] = mesh_a.point_data[disp_var] + weight * (mesh_b.point_data[disp_var] - mesh_a.point_data[disp_var])
            
    # 2. Interpolate Raw Damage & Calculate Physical Damage
    if raw_damage_var in mesh_a.point_data and raw_damage_var in mesh_b.point_data:
        interp_kappa = mesh_a.point_data[raw_damage_var] + weight * (mesh_b.point_data[raw_damage_var] - mesh_a.point_data[raw_damage_var])
        interp_mesh.point_data[raw_damage_var] = interp_kappa
        interp_mesh.point_data[mapped_damage_var] = 1.0 - np.exp(-interp_kappa / damage_scale_factor)
            
    return interp_mesh

def get_clean_quad_surface(mesh):
    try:
        return mesh.extract_surface(nonlinear_subdivision=0)
    except TypeError:
        import vtk
        surface_filter = vtk.vtkDataSetSurfaceFilter()
        surface_filter.SetInputData(mesh)
        surface_filter.SetNonlinearSubdivisionLevel(0)
        surface_filter.Update()
        return pv.wrap(surface_filter.GetOutput())

cached_frames = {}
def get_raw_data_at_time(t):
    if t not in cached_frames:
        reader.set_active_time_value(t)
        cached_frames[t] = reader.read()
    return cached_frames[t]

# ==========================================
# PART 1: ANIMATE DEFORMATION & ZOOM
# ==========================================
t_min, t_max = available_times.min(), available_times.max()
time_steps = np.linspace(t_min, t_max, 100)

first_frame = True

for t in time_steps:
    idx_after = np.searchsorted(available_times, t)
    idx_before = max(0, idx_after - 1)
    if idx_after >= len(available_times):
        idx_after = len(available_times) - 1
        
    t_before = available_times[idx_before]
    t_after = available_times[idx_after]
    weight = (t - t_before) / (t_after - t_before) if t_after != t_before else 0.0
        
    data_before = get_raw_data_at_time(t_before)
    data_after = get_raw_data_at_time(t_after)
    
    concrete_a = extract_block(data_before, block_names["concrete"])
    concrete_b = extract_block(data_after, block_names["concrete"])
    mortar_a = extract_block(data_before, block_names["mortar"])
    mortar_b = extract_block(data_after, block_names["mortar"])
    steel_a = extract_block(data_before, block_names["steel"])
    steel_b = extract_block(data_after, block_names["steel"])
    
    concrete_w = interpolate_mesh(concrete_a, concrete_b, weight)
    mortar_w = interpolate_mesh(mortar_a, mortar_b, weight)
    steel_w = interpolate_mesh(steel_a, steel_b, weight)
    
    if disp_var in concrete_w.point_data:
        concrete_w.points += concrete_w.point_data[disp_var] * warp_factor
    if disp_var in mortar_w.point_data:
        mortar_w.points += mortar_w.point_data[disp_var] * warp_factor
    if disp_var in steel_w.point_data:
        steel_w.points += steel_w.point_data[disp_var] * warp_factor

    clean_concrete_w = get_clean_quad_surface(concrete_w)
    clean_mortar_w = get_clean_quad_surface(mortar_w)
    clean_steel_w = get_clean_quad_surface(steel_w)
    
    # reset_camera=False permanently prevents PyVista from attempting to auto-center the view
    plotter.add_mesh(clean_concrete_w, scalars=mapped_damage_var, cmap="coolwarm", clim=[0.0, 1.0], 
                     show_edges=True, edge_color="black", scalar_bar_args=sargs, 
                     reset_camera=False, name="concrete_mesh")
    plotter.add_mesh(clean_mortar_w, color="wheat", 
                     show_edges=True, edge_color="black", 
                     reset_camera=False, name="mortar_mesh")  
    plotter.add_mesh(clean_steel_w, color="silver", 
                     show_edges=True, edge_color="black", 
                     reset_camera=False, name="steel_mesh")   
    
    if first_frame:
        # Mathematically calculate a safe camera distance based on the diagonal length of the mesh
        cam_dist = clean_concrete_w.length * 0.8
        
        # Hardcode the camera setup relative to the (0, 0, 0) origin
        plotter.camera.position = (cam_dist, cam_dist, cam_dist)
        plotter.camera.focal_point = (0.0, 0.0, 0.0)
        plotter.camera.up = (0.0, 1.0, 0.0)
        
        plotter.show(auto_close=False, interactive_update=True)
        first_frame = False
    else:
        plotter.camera.zoom(1.002)
        plotter.update()
        
    plotter.write_frame()

# ==========================================
# PART 2: FADE OUT AND SHOW TRUE 2D CRACK SURFACE
# ==========================================
smooth_fracture = concrete_w.contour(isosurfaces=[damage_threshold], scalars=mapped_damage_var)
mirrored_fracture = smooth_fracture.reflect((0, 0, 1), point=(0, 0, 0))

fade_steps = 30
for step in range(fade_steps + 1):
    alpha_clipped = step / fade_steps
    alpha_full = 1.0 - (0.4 * alpha_clipped)
    
    plotter.add_mesh(clean_concrete_w, scalars=mapped_damage_var, cmap="coolwarm", clim=[0.0, 1.0], 
                     opacity=alpha_full, show_edges=True, edge_color="black", 
                     scalar_bar_args=sargs, reset_camera=False, name="concrete_mesh")
    
    plotter.add_mesh(smooth_fracture, scalars=mapped_damage_var, cmap="coolwarm", clim=[0.0, 1.0], 
                     opacity=alpha_clipped, show_edges=False, 
                     scalar_bar_args=sargs, reset_camera=False, name="fractured_mesh")
                     
    plotter.add_mesh(mirrored_fracture, scalars=mapped_damage_var, cmap="coolwarm", clim=[0.0, 1.0], 
                     opacity=alpha_clipped, show_edges=False, 
                     scalar_bar_args=sargs, reset_camera=False, name="mirrored_mesh")
    
    plotter.update()
    plotter.write_frame()

# ==========================================
# PART 3: SPIRALING ROTATION
# ==========================================
# Focal point and Up vectors are no longer declared here to ensure zero matrix disruption. 
# The camera naturally orbits the established 0,0,0 focal point.

rotation_frames = 120
total_target_azimuth = 360.0
total_target_elevation = -25.0 

azimuth_angles = []
elevation_angles = []

for i in range(1, rotation_frames + 1):
    progress_prev = (i - 1) / rotation_frames
    progress_curr = i / rotation_frames
    
    ease_prev = 0.5 * (1.0 - math.cos(progress_prev * math.pi))
    ease_curr = 0.5 * (1.0 - math.cos(progress_curr * math.pi))
    
    azi_delta = total_target_azimuth * (ease_curr - ease_prev)
    ele_delta = total_target_elevation * (ease_curr - ease_prev)
    
    azimuth_angles.append(azi_delta)
    elevation_angles.append(ele_delta)

for azi_step, ele_step in zip(azimuth_angles, elevation_angles):
    plotter.camera.azimuth += azi_step
    plotter.camera.elevation += ele_step
    plotter.update()
    plotter.write_frame()

# ==========================================
# CLEANUP
# ==========================================
print(f"Rendering complete! Close the interactive window to finalize and save '{output_file}'.")
plotter.show()
