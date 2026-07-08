import pyvista as pv
import numpy as np
import argparse
import math
import os
import vtk
import warnings

# Suppress PyVista FutureWarnings to keep the terminal output clean
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*algorithm.*")

# ==========================================
# COMMAND LINE ARGUMENT PARSING
# ==========================================
parser = argparse.ArgumentParser(description="Offscreen render structural FEA results with PyVista.")
parser.add_argument("filename", type=str, help="Path to the EnSight .case file")
parser.add_argument("-t", "--threshold", type=float, default=0.8,
                    help="Damage threshold for the fracture surface (default: 0.8)")
parser.add_argument("-w", "--warp", type=float, default=1.0,
                    help="Displacement magnification factor (default: 1.0)")
parser.add_argument("-g", "--glyphscale", type=float, default=0.002,
                    help="Scale factor for the reaction force arrows (default: 0.002)")
parser.add_argument("-p", "--platethick", type=float, default=10.0,
                    help="Thickness of the rigid plates in negative normal direction (default: 10.0)")
parser.add_argument("-o", "--output", type=str, default=None,
                    help="Output MP4 filename (default: same as case file name)")
parser.add_argument("-l", "--label", type=str, default="",
                    help="Custom text label to display on the animation")
parser.add_argument("-c", "--csv", type=str, default="",
                    help="Path to CSV file (defaults to matching .case filename)")
parser.add_argument("-m", "--maxtime", type=float, default=None,
                    help="Maximum time until results are considered")
args = parser.parse_args()

# ==========================================
# CONFIGURATION
# ==========================================
filename = args.filename
warp_factor = args.warp
damage_threshold = args.threshold
glyph_scale = args.glyphscale
plate_thickness = args.platethick
output_file = args.output
if output_file is None:
    output_file = "".join(os.path.basename(filename).split(".")[:-1]) + ".mp4"
custom_label = args.label
max_time_arg = args.maxtime

csv_file = args.csv if args.csv else filename.replace(".case", ".csv")

disp_var = "nodeDisplacements"
raw_damage_var = "nonlocalDamage"
mapped_damage_var = "damage"
rf_var = "nodeReactionForces" 
damage_scale_factor = 0.0037

block_names = {
    "concrete": "ASSEMBLY_CONCRETE-1_CONCRETE",
    "mortar": "ASSEMBLY_STEEL-1_MORTAR",
    "steel": "ASSEMBLY_STEEL-1_STEEL",
    "load_nodes": "NSET_ASSEMBLY_STEEL-1_SHEAR_LOADING" 
}

rigid_plates = [
    "ASSEMBLY_TOP_PLATE-1_PLATE_ELEM",
    "ASSEMBLY_BOTTOM_PLATE-1_PLATE_ELEM",
    "ASSEMBLY_PLATE_NEG_X-1_PLATE_ELEM",
    "ASSEMBLY_PLATE_NEG_Y-1_PLATE_ELEM"
]

sargs = dict(
    vertical=True,
    position_x=0.03,
    position_y=0.05,
    height=0.5,
    width=0.08,
    title_font_size=30,   
    label_font_size=30    
)

# Custom Arrow Geometry: Tip sits at (0,0,0), tail stretches backward.
force_arrow = pv.Arrow(start=(-1.0, 0.0, 0.0), direction=(1.0, 0.0, 0.0))

# ==========================================
# INITIALIZATION 
# ==========================================
reader = pv.get_reader(filename)
available_times = np.array(reader.time_values)

t_min_orig = available_times.min()
t_max_orig = available_times.max()
t_max = min(t_max_orig, max_time_arg) if max_time_arg is not None else t_max_orig

time_fraction = (t_max - t_min_orig) / (t_max_orig - t_min_orig) if t_max_orig > t_min_orig else 1.0

# Reverted strictly back to off_screen=False to restore hardware OpenGL chart rendering
plotter = pv.Plotter(window_size=[1280, 960], off_screen=False)
plotter.open_movie(output_file, framerate=30)
plotter.set_background("white")

if custom_label:
    plotter.add_text(custom_label, position="upper_left", font_size=30, color="black")

# ==========================================
# 2D CHART METADATA
# ==========================================
has_csv = os.path.exists(csv_file)
if has_csv:
    csv_data = np.genfromtxt(csv_file, delimiter=',', skip_header=1)
    csv_time = csv_data[:, 0]
    csv_load = csv_data[:, 1] * 2.0 / 1000.
    csv_disp = csv_data[:, 2]
else:
    print(f"\nWARNING: Could not find CSV file at '{csv_file}'. 2D chart generation skipped.\n")

active_chart = None

def draw_dynamic_chart(current_disp_val):
    global active_chart
    if not has_csv:
        return

    if active_chart is not None:
        plotter.remove_chart(active_chart)

    active_chart = pv.Chart2D(size=(0.35, 0.35), loc=(0.62, 0.62))
    active_chart.background_color = (1.0, 1.0, 1.0, 0.7)  

    active_chart.x_label = "U (mm)"
    active_chart.y_label = "RF (kN)"

    # Restored font sizes to 30
    active_chart.x_axis.label_size = 30
    active_chart.y_axis.label_size = 30
    active_chart.x_axis.tick_label_size = 30
    active_chart.y_axis.tick_label_size = 30

    mask_full = csv_disp <= max_disp_val
    if np.any(mask_full):
        active_chart.line(csv_disp[mask_full], csv_load[mask_full], color="grey", width=4.0)

    mask_progress = csv_disp <= current_disp_val
    if np.any(mask_progress):
        active_chart.line(csv_disp[mask_progress], csv_load[mask_progress], color="red", width=6.0)

    current_load = np.interp(current_disp_val, csv_disp, csv_load)
    active_chart.scatter(np.array([current_disp_val]), np.array([current_load]), color="red", size=25)

    plotter.add_chart(active_chart)

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

    if disp_var in mesh_a.point_data and disp_var in mesh_b.point_data:
        interp_mesh.point_data[disp_var] = mesh_a.point_data[disp_var] + weight * (mesh_b.point_data[disp_var] - mesh_a.point_data[disp_var])

    if rf_var in mesh_a.point_data and rf_var in mesh_b.point_data:
        interp_mesh.point_data[rf_var] = mesh_a.point_data[rf_var] + weight * (mesh_b.point_data[rf_var] - mesh_a.point_data[rf_var])

    if raw_damage_var in mesh_a.point_data and raw_damage_var in mesh_b.point_data:
        interp_kappa = mesh_a.point_data[raw_damage_var] + weight * (mesh_b.point_data[raw_damage_var] - mesh_a.point_data[raw_damage_var])
        interp_mesh.point_data[raw_damage_var] = interp_kappa
        interp_mesh.point_data[mapped_damage_var] = 1.0 - np.exp(-interp_kappa / damage_scale_factor)

    return interp_mesh

def get_clean_quad_surface(mesh):
    try:
        return mesh.extract_surface(nonlinear_subdivision=0, algorithm='dataset_surface')
    except (TypeError, ValueError):
        try:
            return mesh.extract_surface(nonlinear_subdivision=0)
        except Exception:
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
# DISPLACEMENT-BASED SYNC METADATA
# ==========================================
load_indices = None
disp_component_idx = 0
max_disp_val = 0.0

if has_csv:
    print("\n--- Identifying loading nodes and displacement component ---")
    try:
        init_data = get_raw_data_at_time(t_min_orig)
        load_nodes_ref = extract_block(init_data, block_names["load_nodes"])
        all_nodes_ref = extract_block(init_data, "ALL")
        
        load_pts = load_nodes_ref.points
        all_pts = all_nodes_ref.points
        
        load_indices = []
        for pt in load_pts:
            diff = np.linalg.norm(all_pts - pt, axis=1)
            idx = np.argmin(diff)
            load_indices.append(idx)
            
        final_data = get_raw_data_at_time(t_max)
        if "ALL" in final_data.keys() and disp_var in final_data["ALL"].point_data:
            all_disp = final_data["ALL"].point_data[disp_var]
            final_disp_vec = np.mean(all_disp[load_indices], axis=0)
            csv_disp_max = csv_disp.max()
            disp_component_idx = int(np.argmin(np.abs(np.abs(final_disp_vec) - csv_disp_max)))
            max_disp_val = np.abs(final_disp_vec[disp_component_idx])
            print(f"Detected loading displacement component: {disp_component_idx} (based on final average displacement vector {final_disp_vec} and CSV max displacement {csv_disp_max})")
        else:
            print("WARNING: Could not determine displacement component. Defaulting to index 0.")
            max_disp_val = csv_disp.max()
    except Exception as e:
        print(f"WARNING: An error occurred during displacement component detection: {e}. Defaulting to component 0.")
        max_disp_val = csv_disp.max() if has_csv else 0.0

# ==========================================
# PRE-CALCULATE MAXIMUM FORCE FOR COLORMAP LIMITS
# ==========================================
print("\n--- Scanning dataset for global maximum reaction force ---")
global_max_rf = 0.0

for t in available_times[available_times <= t_max]:
    temp_data = get_raw_data_at_time(t)
    try:
        temp_load = extract_block(temp_data, block_names["load_nodes"])
        if rf_var in temp_load.point_data:
            rf_vecs = np.array(temp_load.point_data[rf_var])
            if rf_vecs.ndim == 1:
                rf_vecs = rf_vecs.reshape(-1, 3)
            current_sum = np.sum(np.abs(rf_vecs[:, 0]))
            if current_sum > global_max_rf:
                global_max_rf = current_sum
    except ValueError:
        pass

if global_max_rf == 0.0: 
    global_max_rf = 1.0  

print(f"Global Maximum Force found: {global_max_rf:.2f}")

# ==========================================
# PART 1: ANIMATE DEFORMATION & ZOOM 
# ==========================================
print("\n--- Starting Video Generation Pipeline ---")
time_steps = np.linspace(t_min_orig, t_max, 200)

first_frame = True

print("Part 1/3: Processing Deformation & Chart Sync (200 frames)...")
for i, t in enumerate(time_steps):
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
    
    try:
        load_nodes_a = extract_block(data_before, block_names["load_nodes"])
        load_nodes_b = extract_block(data_after, block_names["load_nodes"])
        load_nodes_w = interpolate_mesh(load_nodes_a, load_nodes_b, weight)
    except ValueError:
        load_nodes_w = None

    concrete_w = interpolate_mesh(concrete_a, concrete_b, weight)
    mortar_w = interpolate_mesh(mortar_a, mortar_b, weight)
    steel_w = interpolate_mesh(steel_a, steel_b, weight)

    if disp_var in concrete_w.point_data:
        concrete_w.points += concrete_w.point_data[disp_var] * warp_factor
    if disp_var in mortar_w.point_data:
        mortar_w.points += mortar_w.point_data[disp_var] * warp_factor
    if disp_var in steel_w.point_data:
        steel_w.points += steel_w.point_data[disp_var] * warp_factor
    if load_nodes_w is not None and disp_var in load_nodes_w.point_data:
        load_nodes_w.points += load_nodes_w.point_data[disp_var] * warp_factor

    clean_concrete_w = get_clean_quad_surface(concrete_w)
    clean_mortar_w = get_clean_quad_surface(mortar_w)
    clean_steel_w = get_clean_quad_surface(steel_w)

    plotter.add_mesh(clean_concrete_w, scalars=mapped_damage_var, cmap="coolwarm", clim=[0.0, 1.0],
                     show_edges=True, edge_color="black", scalar_bar_args=sargs,
                     reset_camera=False, name="concrete_mesh")
    plotter.add_mesh(clean_mortar_w, color="wheat", show_edges=True, edge_color="black",
                     reset_camera=False, name="mortar_mesh")
    plotter.add_mesh(clean_steel_w, color="silver", show_edges=True, edge_color="black",
                     reset_camera=False, name="steel_mesh")

    # ==================== PLATE EXTRUSION LOGIC ====================
    extruded_plates = []
    for p_name in rigid_plates:
        try:
            p_a = extract_block(data_before, p_name)
            p_b = extract_block(data_after, p_name)
            p_w = interpolate_mesh(p_a, p_b, weight)

            if disp_var in p_w.point_data:
                p_w.points += p_w.point_data[disp_var] * warp_factor

            p_surf = get_clean_quad_surface(p_w)
            if p_surf.n_points > 0:
                p_surf.compute_normals(cell_normals=False, point_normals=True, inplace=True)
                avg_normal = np.mean(p_surf.point_data["Normals"], axis=0)
                norm_mag = np.linalg.norm(avg_normal)
                if norm_mag > 1e-8:
                    avg_normal = avg_normal / norm_mag
                else:
                    avg_normal = np.array([0.0, 0.0, 1.0])
                    
                extrude_vec = avg_normal * -plate_thickness
                p_solid = p_surf.extrude(extrude_vec, capping=True)
                extruded_plates.append((p_name, p_solid))
        except ValueError:
            pass 
            
    for p_name, p_solid in extruded_plates:
        plotter.add_mesh(p_solid, color="dimgrey", show_edges=True, edge_color="black",
                         reset_camera=False, name=p_name)
    # ===============================================================

    if load_nodes_w is not None and rf_var in load_nodes_w.point_data:
        rf_vectors = np.array(load_nodes_w.point_data[rf_var])
        if rf_vectors.ndim == 1:
            rf_vectors = rf_vectors.reshape(-1, 3)
            
        rf_x_vectors = np.zeros_like(rf_vectors)
        rf_x_vectors[:, 0] = rf_vectors[:, 0]
        
        rf_x_mag = np.abs(rf_vectors[:, 0])
        
        nset_center = np.mean(load_nodes_w.points, axis=0)
        nset_center[2] = 0.0  # Force the arrow origin to the z=0 symmetry plane
        
        summed_rf_x = np.sum(rf_x_vectors, axis=0).reshape(1, 3)
        current_frame_force = np.sum(rf_x_mag)
        
        if current_frame_force > 1e-5:
            single_point_mesh = pv.PolyData(nset_center.reshape(1, 3))
            single_point_mesh.point_data["rf_x_vectors"] = summed_rf_x
            
            rf_glyphs = single_point_mesh.glyph(
                orient="rf_x_vectors", 
                scale="rf_x_vectors", 
                factor=glyph_scale, 
                geom=force_arrow 
            )
            
            force_color_array = np.full(rf_glyphs.n_points, current_frame_force)
            
            plotter.add_mesh(rf_glyphs, scalars=force_color_array, cmap="jet", clim=[0.0, global_max_rf],
                             show_scalar_bar=False, reset_camera=False, name="rf_glyphs")

    if has_csv and load_indices is not None:
        try:
            disp_before = data_before["ALL"].point_data[disp_var][load_indices]
            disp_after = data_after["ALL"].point_data[disp_var][load_indices]
            disp_w = disp_before + weight * (disp_after - disp_before)
            current_disp_val = np.abs(np.mean(disp_w[:, disp_component_idx]))
        except Exception:
            current_disp_val = 0.0
    else:
        current_disp_val = 0.0

    draw_dynamic_chart(current_disp_val)

    if first_frame:
        cam_dist = clean_concrete_w.length * 0.8
        plotter.camera.position = (cam_dist, cam_dist, cam_dist)
        plotter.camera.focal_point = (0.0, 0.0, 0.0)
        plotter.camera.up = (0.0, 1.0, 0.0)
        first_frame = False
    else:
        plotter.camera.zoom(1.001)

    plotter.write_frame()
    if (i+1) % 50 == 0:
        print(f"  > Generated frame {i+1}/200")

# ==========================================
# PART 2: FADE OUT AND SHOW TRUE 2D CRACK SURFACE 
# ==========================================
print("Part 2/3: Processing Transition Fade (60 frames)...")
smooth_fracture = concrete_w.contour(isosurfaces=[damage_threshold], scalars=mapped_damage_var)
mirrored_fracture = smooth_fracture.reflect((0, 0, 1), point=(0, 0, 0))

fade_steps = 60
for step in range(fade_steps + 1):
    alpha_clipped = step / fade_steps
    alpha_full = 1.0 - (0.8 * alpha_clipped)

    plotter.add_mesh(clean_concrete_w, scalars=mapped_damage_var, cmap="coolwarm", clim=[0.0, 1.0],
                     opacity=alpha_full, show_edges=True, edge_color="black",
                     scalar_bar_args=sargs, reset_camera=False, name="concrete_mesh")

    plotter.add_mesh(smooth_fracture, scalars=mapped_damage_var, cmap="coolwarm", clim=[0.0, 1.0],
                     opacity=alpha_clipped, show_edges=False,
                     scalar_bar_args=sargs, reset_camera=False, name="fractured_mesh")

    plotter.add_mesh(mirrored_fracture, scalars=mapped_damage_var, cmap="coolwarm", clim=[0.0, 1.0],
                     opacity=alpha_clipped, show_edges=False,
                     scalar_bar_args=sargs, reset_camera=False, name="mirrored_mesh")
                     
    for p_name, p_solid in extruded_plates:
        plotter.add_mesh(p_solid, color="dimgrey", show_edges=True, edge_color="black",
                         reset_camera=False, name=p_name)

    draw_dynamic_chart(max_disp_val) 
    plotter.write_frame()

# ==========================================
# PART 3: SPIRALING ROTATION 
# ==========================================
print("Part 3/3: Processing Orbital Camera Motion (240 frames)...")
rotation_frames = 240
total_target_azimuth = 360.0
total_target_elevation = -25.0

azimuth_angles = []
elevation_angles = []

for i in range(1, rotation_frames + 1):
    progress_prev = (i - 1) / rotation_frames
    progress_curr = i / rotation_frames

    entropy_prev = 0.5 * (1.0 - math.cos(progress_prev * math.pi))
    entropy_curr = 0.5 * (1.0 - math.cos(progress_curr * math.pi))

    azi_delta = total_target_azimuth * (entropy_curr - entropy_prev)
    ele_delta = total_target_elevation * (entropy_curr - entropy_prev)

    azimuth_angles.append(azi_delta)
    elevation_angles.append(ele_delta)

for i, (azi_step, ele_step) in enumerate(zip(azimuth_angles, elevation_angles)):
    plotter.camera.azimuth += azi_step
    plotter.camera.elevation += ele_step

    draw_dynamic_chart(max_disp_val) 
    plotter.write_frame()
    if (i+1) % 60 == 0:
        print(f"  > Generated frame {i+1}/240")

# ==========================================
# CLEANUP
# ==========================================
plotter.close()
print(f"\nSuccess! Video file compiled and saved to: {output_file}")
