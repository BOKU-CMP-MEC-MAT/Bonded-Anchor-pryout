import pyvista as pv
import numpy as np
import argparse
import math
import os
import vtk
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*algorithm.*")

def draw_dynamic_chart(current_time, plotter, active_chart, has_csv, csv_disp, csv_load, csv_time, t_max):
    if not has_csv:
        return

    if active_chart is not None:
        plotter.remove_chart(active_chart)

    active_chart = pv.Chart2D(size=(0.35, 0.35), loc=(0.62, 0.62))
    active_chart.background_color = (1.0, 1.0, 1.0, 0.7)

    active_chart.x_label = "displacement (mm)"
    active_chart.y_label = "reaction force(kN)"

    active_chart.x_axis.label_size = 30
    active_chart.y_axis.label_size = 30
    active_chart.x_axis.tick_label_size = 30
    active_chart.y_axis.tick_label_size = 30

    idx_max = np.searchsorted(csv_time, t_max)
    if idx_max >= len(csv_time):
        idx_max = len(csv_time) - 1

    csv_disp_clipped = csv_disp[:idx_max+1]
    csv_load_clipped = csv_load[:idx_max+1]

    csv_max_disp = csv_disp_clipped.max()
    csv_max_load = csv_load_clipped.max()
    
    # Always draw the full CSV curve up to the animation max bound in gray
    active_chart.line(csv_disp_clipped, csv_load_clipped, color="grey", width=4.0)
    active_chart.x_axis.behavior = "fixed"
    active_chart.x_axis.range = [0.0, csv_max_disp * 1.05]
    active_chart.y_axis.behavior = "fixed"
    active_chart.y_axis.range = [0.0, csv_max_load * 1.05]

    idx = np.searchsorted(csv_time, current_time)
    if idx >= len(csv_time):
        idx = len(csv_time) - 1
    if idx > idx_max:
        idx = idx_max

    mask_progress = np.arange(len(csv_disp_clipped)) <= idx
    if np.any(mask_progress):
        active_chart.line(csv_disp_clipped[mask_progress], csv_load_clipped[mask_progress], color="red", width=6.0)

    current_disp_val = csv_disp[idx]
    current_load = csv_load[idx]
    active_chart.scatter(np.array([current_disp_val]), np.array([current_load]), color="red", size=25)

    plotter.add_chart(active_chart)
    return active_chart

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

def try_get_block(multiblock, name):
    try:
        return extract_block(multiblock, name)
    except ValueError:
        return None

def find_bc_block(multiblock, name):
    """
    Finds a block in the multiblock dataset.
    First tries an exact case-insensitive match, then substring match.
    """
    target = name.upper()
    
    def search_exact(block):
        for i in range(block.n_blocks):
            block_name = block.get_block_name(i)
            if block_name is not None and block_name.upper() == target:
                return block[i]
            if isinstance(block[i], pv.MultiBlock):
                res = search_exact(block[i])
                if res is not None:
                    return res
        return None

    exact_res = search_exact(multiblock)
    if exact_res is not None:
        return exact_res
        
    def search_substring(block):
        for i in range(block.n_blocks):
            block_name = block.get_block_name(i)
            if block_name is not None and target in block_name.upper():
                return block[i]
            if isinstance(block[i], pv.MultiBlock):
                res = search_substring(block[i])
                if res is not None:
                    return res
        return None

    return search_substring(multiblock)

def create_bc_glyphs(nodes_mesh, direction_vector, size=8.0):
    """
    Creates cones pointing along direction_vector at each point of nodes_mesh.
    The tip of the cone is located at the node.
    """
    if nodes_mesh is None or nodes_mesh.n_points == 0:
        return None
    
    dir_np = np.array(direction_vector, dtype=float)
    dir_len = np.linalg.norm(dir_np)
    if dir_len > 1e-8:
        dir_np = dir_np / dir_len
    
    cone_geom = pv.Cone(
        center=-dir_np * size / 2.0,
        direction=dir_np,
        height=size,
        radius=size * 0.3,
        resolution=12
    )
    
    glyphs = nodes_mesh.glyph(geom=cone_geom, orient=False, scale=False)
    return glyphs

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
def get_raw_data_at_time(t, reader, t_min_orig, t_max_orig, time_fraction, warp_factor):
    if t not in cached_frames:
        reader.set_active_time_value(t)
        cached_frames[t] = reader.read()
    return cached_frames[t]

def get_cinematic_state(f, default_pos, default_focal, plates_pos, plates_focal, back_pos, back_focal):
    opacities = {"bottom_plate": 0.0, "concrete": 0.0, "mortar": 0.0, "steel": 0.0,
                 "support_plates": 0.0, "bc": 0.0, "back_support_bc": 0.0}
    cam_pos = default_pos
    cam_focal = default_focal
    annotation = ""
    plate_offset_scalar = 0.0
    steel_offset_y = 0.0
    
    # Phase 1: Fade in bottom plate (0 to 29)
    if f < 30:
        progress = f / 29.0
        opacities["bottom_plate"] = 0.5 * (1.0 - math.cos(progress * math.pi)) * 0.9999
        annotation = "bottom support plate"
    elif f < 45:
        opacities["bottom_plate"] = 0.9999
        annotation = "bottom support plate"
        
    # Phase 2: Fade in concrete (45 to 89)
    elif f < 90:
        progress = (f - 45) / 44.0
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.5 * (1.0 - math.cos(progress * math.pi)) * 0.9999
        annotation = "concrete slab"
    elif f < 105:
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        annotation = "concrete slab"
        
    # Phase 3: Fade in mortar (105 to 149)
    elif f < 150:
        progress = (f - 105) / 44.0
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.5 * (1.0 - math.cos(progress * math.pi)) * 0.9999
        annotation = "chemical mortar"
    elif f < 165:
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        annotation = "chemical mortar"
        
    # Phase 4: Fade in steel loading plate (165 to 194)
    elif f < 195:
        progress = (f - 165) / 29.0
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.5 * (1.0 - math.cos(progress * math.pi)) * 0.9999
        steel_offset_y = 120.0
        annotation = "anchor plate"
    elif f < 205:
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        steel_offset_y = 120.0
        annotation = "anchor plate"
        
    # Phase 4b: Move steel plate into position (205 to 234)
    elif f < 235:
        progress = (f - 205) / 29.0
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        steel_offset_y = 120.0 - (0.5 * (1.0 - math.cos(progress * math.pi)) * 120.0)
        annotation = "anchor plate"
    elif f < 245:
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        steel_offset_y = 0.0
        annotation = "anchor plate"
        
    # Phase 5: Move camera to support plates, fade in support plates (245 to 289)
    elif f < 290:
        progress = (f - 245) / 44.0
        t = 0.5 * (1.0 - math.cos(progress * math.pi))
        cam_pos = tuple(p0 + t * (p1 - p0) for p0, p1 in zip(default_pos, plates_pos))
        cam_focal = tuple(f0 + t * (f1 - f0) for f0, f1 in zip(default_focal, plates_focal))
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        opacities["support_plates"] = 0.5 * (1.0 - math.cos(progress * math.pi)) * 0.9999
        annotation = "rigid support plates"
    elif f < 295:
        cam_pos = plates_pos
        cam_focal = plates_focal
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        opacities["support_plates"] = 0.9999
        annotation = "rigid support plates"
        
    # Phase 5b: Move plates apart (295 to 324)
    elif f < 325:
        progress = (f - 295) / 29.0
        plate_offset_scalar = 0.5 * (1.0 - math.cos(progress * math.pi)) * 30.0
        cam_pos = plates_pos
        cam_focal = plates_focal
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        opacities["support_plates"] = 0.9999
        annotation = "frictionless contact"
    elif f < 340:
        plate_offset_scalar = 30.0
        cam_pos = plates_pos
        cam_focal = plates_focal
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        opacities["support_plates"] = 0.9999
        annotation = "frictionless contact"
    
    # Phase 5c: Move plates back (340 to 369)
    elif f < 370:
        progress = (f - 340) / 29.0
        plate_offset_scalar = 30.0 - (0.5 * (1.0 - math.cos(progress * math.pi)) * 30.0)
        cam_pos = plates_pos
        cam_focal = plates_focal
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        opacities["support_plates"] = 0.9999
        annotation = "frictionless contact"
    elif f < 380:
        plate_offset_scalar = 0.0
        cam_pos = plates_pos
        cam_focal = plates_focal
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        opacities["support_plates"] = 0.9999
        annotation = "frictionless contact"

    # Phase 6: Move camera back (380 to 424)
    elif f < 425:
        progress = (f - 380) / 44.0
        t = 0.5 * (1.0 - math.cos(progress * math.pi))
        cam_pos = tuple(p0 + t * (p1 - p0) for p0, p1 in zip(plates_pos, default_pos))
        cam_focal = tuple(f0 + t * (f1 - f0) for f0, f1 in zip(plates_focal, default_focal))
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        opacities["support_plates"] = 0.9999
        annotation = "anchor plate"
    elif f < 440:
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        opacities["support_plates"] = 0.9999
        annotation = "anchor plate"
        
    # Phase 7: Fade in BCs (440 to 469)
    elif f < 470:
        progress = (f - 440) / 29.0
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        opacities["support_plates"] = 0.9999
        opacities["bc"] = 0.5 * (1.0 - math.cos(progress * math.pi)) * 0.9999
        annotation = "support plates: Y & Z BCs"
    elif f < 485:
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        opacities["support_plates"] = 0.9999
        opacities["bc"] = 0.9999
        annotation = "support plates: Y & Z BCs"

    # Phase 8: Pan camera 90° left, fade in back support BCs (485 to 529)
    elif f < 530:
        progress = (f - 485) / 44.0
        t = 0.5 * (1.0 - math.cos(progress * math.pi))
        cam_pos = tuple(p0 + t * (p1 - p0) for p0, p1 in zip(default_pos, back_pos))
        cam_focal = tuple(f0 + t * (f1 - f0) for f0, f1 in zip(default_focal, back_focal))
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        opacities["support_plates"] = 0.9999
        opacities["bc"] = 0.9999
        opacities["back_support_bc"] = 0.5 * (1.0 - math.cos(progress * math.pi)) * 0.9999
        annotation = "back support: Y & Z BCs"
    elif f < 545:
        cam_pos = back_pos
        cam_focal = back_focal
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        opacities["support_plates"] = 0.9999
        opacities["bc"] = 0.9999
        opacities["back_support_bc"] = 0.9999
        annotation = "back support: Y & Z BCs"

    # Phase 9: Pan camera back (545 to 589)
    elif f < 590:
        progress = (f - 545) / 44.0
        t = 0.5 * (1.0 - math.cos(progress * math.pi))
        cam_pos = tuple(p0 + t * (p1 - p0) for p0, p1 in zip(back_pos, default_pos))
        cam_focal = tuple(f0 + t * (f1 - f0) for f0, f1 in zip(back_focal, default_focal))
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        opacities["support_plates"] = 0.9999
        opacities["bc"] = 0.9999
        opacities["back_support_bc"] = 0.9999
        annotation = "back support: Y & Z BCs"
    else:
        opacities["bottom_plate"] = 0.9999
        opacities["concrete"] = 0.9999
        opacities["mortar"] = 0.9999
        opacities["steel"] = 0.9999
        opacities["support_plates"] = 0.9999
        opacities["bc"] = 0.9999
        opacities["back_support_bc"] = 0.9999
        annotation = "back support: Y & Z BCs"

    return opacities, cam_pos, cam_focal, annotation, plate_offset_scalar, steel_offset_y


def main():
    def interpolate_mesh(mesh_a, mesh_b, weight, out_mesh=None):
        if out_mesh is None:
            out_mesh = mesh_a.copy(deep=True)
        out_mesh.points = mesh_a.points + weight * (mesh_b.points - mesh_a.points)
    
        if disp_var in mesh_b.point_data:
            a_disp = mesh_a.point_data[disp_var] if disp_var in mesh_a.point_data else np.zeros_like(mesh_b.point_data[disp_var])
            out_mesh.point_data[disp_var] = a_disp + weight * (mesh_b.point_data[disp_var] - a_disp)
    
        if rf_var in mesh_b.point_data:
            a_rf = mesh_a.point_data[rf_var] if rf_var in mesh_a.point_data else np.zeros_like(mesh_b.point_data[rf_var])
            out_mesh.point_data[rf_var] = a_rf + weight * (mesh_b.point_data[rf_var] - a_rf)
    
        if raw_damage_var in mesh_a.point_data and raw_damage_var in mesh_b.point_data:
            interp_kappa = mesh_a.point_data[raw_damage_var] + weight * (mesh_b.point_data[raw_damage_var] - mesh_a.point_data[raw_damage_var])
            out_mesh.point_data[raw_damage_var] = interp_kappa
            out_mesh.point_data[mapped_damage_var] = 1.0 - np.exp(-interp_kappa / damage_scale_factor)
            
        if "S" in mesh_b.cell_data:
            a_s = mesh_a.cell_data["S"] if "S" in mesh_a.cell_data else np.zeros_like(mesh_b.cell_data["S"])
            out_mesh.cell_data["S"] = a_s + weight * (mesh_b.cell_data["S"] - a_s)
    
        return out_mesh

    # Suppress PyVista FutureWarnings to keep the terminal output clean

    # ==========================================
    # COMMAND LINE ARGUMENT PARSING
    # ==========================================
    parser = argparse.ArgumentParser(description="Offscreen render structural FEA results with PyVista (Cinematic Intro).")
    parser.add_argument("filename", type=str, help="Path to the EnSight .case file")
    parser.add_argument("--steel-vm", action="store_true", help="Plot von Mises stress on the steel anchor (cell data S)")
    parser.add_argument("-t", "--threshold", type=float, default=0.8,
                        help="Damage threshold for the fracture surface (default: 0.8)")
    parser.add_argument("-w", "--warp", type=float, default=1.0,
                        help="Displacement magnification factor (default: 1.0)")
    parser.add_argument("-g", "--glyphscale", type=float, default=0.002,
                        help="Scale factor for the reaction force arrows (default: 0.002)")
    parser.add_argument("-p", "--platethick", type=float, default=10.0,
                        help="Thickness of the rigid plates in negative normal direction (default: 10.0)")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output MP4 filename (default: same as case file name with _cinematic suffix)")
    parser.add_argument("-l", "--label", type=str, default="",
                        help="Custom text label to display on the animation")
    parser.add_argument("-c", "--csv", type=str, default="",
                        help="Path to CSV file (defaults to matching .case filename)")
    parser.add_argument("-m", "--maxtime", type=float, default=None,
                        help="Maximum time until results are considered")
    parser.add_argument("-b", "--bcsize", type=float, default=12.0,
                        help="Height of the boundary condition support cones (default: 8.0)")
    parser.add_argument("--hide-bc", action="store_true",
                        help="Hide boundary condition support cones in the visualization")
    parser.add_argument("--no-intro", action="store_true", help="Skip the cinematic intro and jump straight to deformation")
    parser.add_argument("-d", "--maxdisp", type=float, default=None,
                        help="Maximum displacement (mm) to consider in the animation")
    args = parser.parse_args()

    # ==========================================
    # CONFIGURATION
    # ==========================================
    filename = args.filename
    warp_factor = args.warp
    damage_threshold = args.threshold
    glyph_scale = args.glyphscale
    plate_thickness = args.platethick
    bc_size = args.bcsize
    show_bc = not args.hide_bc

    output_file = args.output
    if output_file is None:
        base = "".join(os.path.basename(filename).split(".")[:-1])
        suffix = "_cinematic"
        if args.no_intro:
            suffix += "_nointro"
        if args.steel_vm:
            suffix += "_vm"
        suffix += f"_w{args.warp}_t{args.threshold}_p{args.platethick}"
        if args.maxdisp is not None:
            suffix += f"_d{args.maxdisp}"
        if args.maxtime is not None:
            suffix += f"_m{args.maxtime}"
        output_file = base + suffix + ".mp4"
    custom_label = args.label
    max_time_arg = args.maxtime
    max_disp_arg = args.maxdisp
    no_intro = args.no_intro

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
        "ASSEMBLY_BOTTOM_PLATE-1_PLATE_ELEM",
        "ASSEMBLY_PLATE_NEG_X-1_PLATE_ELEM",
        "ASSEMBLY_PLATE_NEG_Y-1_PLATE_ELEM"
    ]

    bc_configs = [
        {
            "block": "PLATE_BACK",
            "constraints": ["Y", "Z"]
        },
        {
            "block": "SHEAR_LOADING",
            "constraints": ["Y", "Z"]
        }
    ]

    back_support_bc_config = {
        "block": "NSET_ASSEMBLY_CONCRETE-1_BACK_SUPPORT",
        "constraints": ["Y", "Z"]
    }

    sargs = dict(
        vertical=True,
        position_x=0.03,
        position_y=0.03,
        height=0.5,
        width=0.08,
        title_font_size=30,   
        label_font_size=30,
        fmt="%.1f"
    )

    sargs_vm = dict(
        title="von Mises (MPa)",
        vertical=True,
        position_x=0.11,
        position_y=0.03,
        height=0.5,
        width=0.08,
        title_font_size=30,   
        label_font_size=30,
        fmt="%.0f"
    )

    # Custom Arrow Geometry: Tail sits at (0,0,0), tip stretches forward.
    force_arrow = pv.Arrow(start=(0.0, 0.0, 0.0), direction=(1.0, 0.0, 0.0))

    # ==========================================
    # INITIALIZATION 
    # ==========================================
    reader = pv.get_reader(filename)
    available_times = np.array(reader.time_values)

    t_min_orig = available_times.min()
    t_max_orig = available_times.max()
    t_max = min(t_max_orig, max_time_arg) if max_time_arg is not None else t_max_orig
    t_max += 1e-4

    time_fraction = (t_max - t_min_orig) / (t_max_orig - t_min_orig) if t_max_orig > t_min_orig else 1.0

    # Set off_screen=False to restore hardware OpenGL chart rendering
    plotter = pv.Plotter(window_size=[1280*2, 960*2], off_screen=False)
    plotter.open_movie(output_file, framerate=30)
    plotter.set_background("white")
    plotter.enable_depth_peeling(number_of_peels=4, occlusion_ratio=0.0)

    if custom_label:
        plotter.add_text(custom_label, position="upper_left", font_size=30, color="black")

    plotter.add_axes(viewport=(0.0, 0.8, 0.2, 1.0))

    # ==========================================
    # 2D CHART METADATA
    # ==========================================
    has_csv = os.path.exists(csv_file)
    if has_csv:
        try:
            with open(csv_file, 'r') as f:
                header = f.readline().strip().split(',')
            header = [h.strip().lower() for h in header]

            time_idx = 0
            load_idx = 1
            disp_idx = 2

            for idx, name in enumerate(header):
                if 'time' in name:
                    time_idx = idx
                    break
            for idx, name in enumerate(header):
                if any(k in name for k in ['disp', 'u1', 'u2', 'u3', 'displ', 'u_']):
                    disp_idx = idx
                    break
            for idx, name in enumerate(header):
                if idx != time_idx and idx != disp_idx:
                    if any(k in name for k in ['rf', 'force', 'load', 'f1', 'f2', 'f3']):
                        load_idx = idx
                        break

            csv_data = np.genfromtxt(csv_file, delimiter=',', skip_header=1)
            csv_time = csv_data[:, time_idx]
            csv_load = csv_data[:, load_idx] * 2.0 / 1000.
            csv_disp = csv_data[:, disp_idx]

            # Auto-convert displacement from meters to millimeters if needed
            if np.abs(csv_disp).max() < 0.1:
                print("Auto-detected CSV displacement in meters. Converting to millimeters for visualization.")
                csv_disp = csv_disp * 1000.0

            print(f"Parsed CSV columns: time={header[time_idx]} (col {time_idx}), load={header[load_idx]} (col {load_idx}), disp={header[disp_idx]} (col {disp_idx})")
        except Exception as e:
            print(f"WARNING: Error parsing CSV headers: {e}. Falling back to default column mapping.")
            csv_data = np.genfromtxt(csv_file, delimiter=',', skip_header=1)
            csv_time = csv_data[:, 0]
            csv_load = csv_data[:, 1] * 2.0 / 1000.
            csv_disp = csv_data[:, 2]
    else:
        print(f"\nWARNING: Could not find CSV file at '{csv_file}'. 2D chart generation skipped.\n")
        csv_time = None

    if has_csv and len(csv_time) > 0:
        # Enforce absolute values to prevent negative charts
        csv_disp = np.abs(csv_disp)
        csv_load = np.abs(csv_load)

        # Enforce monotonicity for step time resets (e.g., Abaqus multiple steps)
        for i in range(1, len(csv_time)):
            if csv_time[i] < csv_time[i-1]:
                csv_time[i:] += csv_time[i-1]

    active_chart = None

    # Calculate displacement-based cropping if maxdisp option is specified
    if max_disp_arg is not None:
        if has_csv:
            matching_indices = np.where(np.abs(csv_disp) >= max_disp_arg)[0]
            if len(matching_indices) > 0:
                t_max_disp = csv_time[matching_indices[0]]

                if t_max_disp > t_min_orig:
                    t_max = min(t_max, t_max_disp)
                    print(f"Cropping animation at VTK t={t_max:.4f} (displacement reached maximum of {max_disp_arg} mm)")
                else:
                    print(f"WARNING: Maximum displacement {max_disp_arg} is reached at CSV time {t_max_disp:.4f}, "
                          f"which maps to VTK time before/at the first step t_min={t_min_orig:.4f}. "
                          f"No cropping applied. Please check the units of your displacement option.")
        else:
            print(f"No CSV file found. Scanning case file to find timestep where displacement >= {max_disp_arg} mm...")
            try:
                init_data = get_raw_data_at_time(t_min_orig, reader, t_min_orig, t_max_orig, time_fraction, warp_factor)
                load_nodes_ref = extract_block(init_data, block_names["load_nodes"])
                all_nodes_ref = extract_block(init_data, "ALL")
                load_pts = load_nodes_ref.points
                all_pts = all_nodes_ref.points
                load_indices_temp = []
                for pt in load_pts:
                    diff = np.linalg.norm(all_pts - pt, axis=1)
                    idx = np.argmin(diff)
                    load_indices_temp.append(idx)

                t_max_disp = None
                for t in available_times:
                    temp_data = get_raw_data_at_time(t, reader, t_min_orig, t_max_orig, time_fraction, warp_factor)
                    if "ALL" in temp_data.keys() and disp_var in temp_data["ALL"].point_data:
                        all_disp = temp_data["ALL"].point_data[disp_var]
                        avg_disp = np.abs(np.mean(all_disp[load_indices_temp, 0]))
                        if avg_disp >= max_disp_arg:
                            t_max_disp = t
                            break
                if t_max_disp is not None:
                    if t_max_disp > t_min_orig:
                        t_max = min(t_max, t_max_disp)
                        print(f"Cropping animation at t={t_max:.4f} (displacement reached maximum of {max_disp_arg} mm)")
                    else:
                        print(f"WARNING: Maximum displacement {max_disp_arg} is reached at/before the first step. No cropping applied.")
            except Exception as e:
                print(f"WARNING: Could not parse displacement from case file: {e}")

    print(f"\nAnimation bounds: t_min={t_min_orig:.4f}, t_max={t_max:.4f}")

    active_chart = None

    # ==========================================
    # HELPER FUNCTIONS
    # ==========================================
    # ==========================================
    # DISPLACEMENT-BASED SYNC METADATA
    # ==========================================
    load_indices = None
    disp_component_idx = 0
    max_disp_val = 0.0

    if has_csv:
        print("\n--- Identifying loading nodes and displacement component ---")
        try:
            init_data = get_raw_data_at_time(t_min_orig, reader, t_min_orig, t_max_orig, time_fraction, warp_factor)
            load_nodes_ref = extract_block(init_data, block_names["load_nodes"])
            all_nodes_ref = extract_block(init_data, "ALL")

            load_pts = load_nodes_ref.points
            all_pts = all_nodes_ref.points

            load_indices = []
            for pt in load_pts:
                diff = np.linalg.norm(all_pts - pt, axis=1)
                idx = np.argmin(diff)
                load_indices.append(idx)

            final_data = get_raw_data_at_time(t_max, reader, t_min_orig, t_max_orig, time_fraction, warp_factor)
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

    if max_disp_arg is not None:
        max_disp_val = max_disp_arg

    # ==========================================
    # PRE-CALCULATE MAXIMUM FORCE FOR COLORMAP LIMITS
    # ==========================================
    print("\n--- Scanning dataset for global maximum reaction force ---")
    global_max_rf = 0.0

    for t in available_times[available_times <= t_max + 1e-4]:
        temp_data = get_raw_data_at_time(t, reader, t_min_orig, t_max_orig, time_fraction, warp_factor)
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
    # HELPER FOR CINEMATIC INTRO STATES
    # ==========================================
    # ==========================================
    # ==========================================
    # PART 0: CINEMATIC INTRODUCTION SETUP
    # ==========================================
    init_data = get_raw_data_at_time(t_min_orig, reader, t_min_orig, t_max_orig, time_fraction, warp_factor)

    # Extract and prepare geometries
    concrete_init = try_get_block(init_data, block_names["concrete"])
    mortar_init = try_get_block(init_data, block_names["mortar"])
    steel_init = try_get_block(init_data, block_names["steel"])

    clean_concrete = get_clean_quad_surface(concrete_init) if concrete_init else None
    if clean_concrete:
        if raw_damage_var in clean_concrete.point_data:
            clean_concrete.point_data[mapped_damage_var] = 1.0 - np.exp(-clean_concrete.point_data[raw_damage_var] / damage_scale_factor)
        else:
            clean_concrete.point_data[mapped_damage_var] = np.zeros(clean_concrete.n_points)

    clean_mortar = get_clean_quad_surface(mortar_init) if mortar_init else None
    clean_steel = get_clean_quad_surface(steel_init) if steel_init else None

    # Extrude bottom plate
    bottom_plate_init = try_get_block(init_data, "ASSEMBLY_BOTTOM_PLATE-1_PLATE_ELEM")
    bottom_plate_solid = None
    if bottom_plate_init:
        bp_surf = get_clean_quad_surface(bottom_plate_init)
        if bp_surf.n_points > 0:
            bp_surf.compute_normals(cell_normals=False, point_normals=True, inplace=True)
            avg_normal = np.mean(bp_surf.point_data["Normals"], axis=0)
            norm_mag = np.linalg.norm(avg_normal)
            avg_normal = avg_normal / norm_mag if norm_mag > 1e-8 else np.array([0.0, 0.0, 1.0])
            bottom_plate_solid = bp_surf.extrude(avg_normal * -plate_thickness, capping=True)
            bottom_plate_solid.points += avg_normal * -0.01

    # Extrude support plates
    neg_x_plate_init = try_get_block(init_data, "ASSEMBLY_PLATE_NEG_X-1_PLATE_ELEM")
    neg_x_plate_solid = None
    if neg_x_plate_init:
        nx_surf = get_clean_quad_surface(neg_x_plate_init)
        if nx_surf.n_points > 0:
            nx_surf.compute_normals(cell_normals=False, point_normals=True, inplace=True)
            avg_normal = np.mean(nx_surf.point_data["Normals"], axis=0)
            norm_mag = np.linalg.norm(avg_normal)
            avg_normal = avg_normal / norm_mag if norm_mag > 1e-8 else np.array([0.0, 0.0, 1.0])
            neg_x_plate_solid = nx_surf.extrude(avg_normal * -plate_thickness, capping=True)
            neg_x_plate_solid.points += avg_normal * -0.01

    neg_y_plate_init = try_get_block(init_data, "ASSEMBLY_PLATE_NEG_Y-1_PLATE_ELEM")
    neg_y_plate_solid = None
    if neg_y_plate_init:
        ny_surf = get_clean_quad_surface(neg_y_plate_init)
        if ny_surf.n_points > 0:
            ny_surf.compute_normals(cell_normals=False, point_normals=True, inplace=True)
            avg_normal = np.mean(ny_surf.point_data["Normals"], axis=0)
            norm_mag = np.linalg.norm(avg_normal)
            avg_normal = avg_normal / norm_mag if norm_mag > 1e-8 else np.array([0.0, 0.0, 1.0])
            neg_y_plate_solid = ny_surf.extrude(avg_normal * -plate_thickness, capping=True)
            neg_y_plate_solid.points += avg_normal * -0.01

    # Determine camera positions
    if clean_concrete:
        cam_dist = clean_concrete.length * 0.8
    else:
        cam_dist = 500.0

    default_pos = (cam_dist, cam_dist, cam_dist)
    default_focal = (0.0, 0.0, 0.0)

    plates_to_center = []
    if neg_x_plate_init: plates_to_center.append(neg_x_plate_init)
    if neg_y_plate_init: plates_to_center.append(neg_y_plate_init)

    if plates_to_center:
        xmin, xmax, ymin, ymax, zmin, zmax = plates_to_center[0].bounds
        for p in plates_to_center[1:]:
            b = p.bounds
            xmin = min(xmin, b[0])
            xmax = max(xmax, b[1])
            ymin = min(ymin, b[2])
            ymax = max(ymax, b[3])
            zmin = min(zmin, b[4])
            zmax = max(zmax, b[5])

        plates_focal = ((xmin + xmax)/2.0, (ymin + ymax)/2.0, (zmin + zmax)/2.0)
    else:
        if clean_concrete:
            cb = clean_concrete.bounds
            plates_focal = (cb[0] * 0.6 + cb[1] * 0.4, cb[2] * 0.6 + cb[3] * 0.4, cb[4] * 0.5 + cb[5] * 0.5)
        else:
            plates_focal = (-250.0, -250.0, -250.0)

    # Compute the view direction offset from default camera to keep zoom level constant (panning only)
    cam_offset = np.array(default_pos) - np.array(default_focal)
    plates_pos = tuple(np.array(plates_focal) + cam_offset)

    # Compute back_pos/back_focal: camera (and focal) rotated -90° around the Y axis
    # through the concrete corner at (min_x, 0, max_z).
    # This swings the camera around to see the back of the concrete where BACK_SUPPORT lives.
    # Rotation direction: -90° around Y (clockwise from above) = opposite of previous.
    _rot_matrix = np.array([
        [ 0.0,  0.0, -1.0],
        [ 0.0,  1.0,  0.0],
        [ 1.0,  0.0,  0.0]
    ])
    if clean_concrete:
        _cb = clean_concrete.bounds
        _rot_center = np.array([_cb[0], 0.0, _cb[5]])  # corner: min(x), max(z)
    else:
        _rot_center = np.zeros(3)

    back_pos   = tuple(_rot_center + _rot_matrix @ (np.array(default_pos)   - _rot_center))
    back_focal = list(_rot_center + _rot_matrix @ (np.array(default_focal) - _rot_center))
    # Override z: look at the concrete's Z midpoint so we face the back surface squarely
    if clean_concrete:
        _cb = clean_concrete.bounds
        back_focal[2] = 0.5 * (_cb[4] + _cb[5])
    back_focal = tuple(back_focal)

    if not no_intro:
        print("\n--- Generating Cinematic Introduction (605 frames) ---")
        intro_frames = 605
        for f in range(intro_frames):
            opacities, cam_pos, cam_focal, annotation, plate_offset_scalar, steel_offset_y = get_cinematic_state(
                f, default_pos, default_focal, plates_pos, plates_focal, back_pos, back_focal)

            plotter.camera.position = cam_pos
            plotter.camera.focal_point = cam_focal
            plotter.camera.up = (0.0, 1.0, 0.0)

            if bottom_plate_solid is not None:
                p_b = bottom_plate_solid.copy(deep=True) if plate_offset_scalar > 0 else bottom_plate_solid
                if plate_offset_scalar > 0: p_b.points += np.array([0.0, -1.0, 0.0]) * plate_offset_scalar
                plotter.add_mesh(p_b, color="dimgrey", show_edges=True, edge_color="black",
                                 opacity=opacities["bottom_plate"], reset_camera=False, name="ASSEMBLY_BOTTOM_PLATE-1_PLATE_ELEM")

            if clean_concrete is not None:
                plotter.add_mesh(clean_concrete, scalars=mapped_damage_var, cmap="coolwarm", clim=[0.0, 1.0],
                                 opacity=opacities["concrete"], show_edges=True, edge_color="black",
                                 scalar_bar_args=sargs, show_scalar_bar=False, reset_camera=False, name="concrete_mesh")

            if clean_mortar is not None:
                plotter.add_mesh(clean_mortar, color="#3CB371", show_edges=True, edge_color="black",
                                 opacity=opacities["mortar"], reset_camera=False, name="mortar_mesh")

            if clean_steel is not None:
                s_mesh = clean_steel.copy(deep=True) if steel_offset_y > 0 else clean_steel
                if steel_offset_y > 0: s_mesh.points += np.array([0.0, 1.0, 0.0]) * steel_offset_y
                
                if args.steel_vm and "S" in s_mesh.cell_data:
                    s = s_mesh.cell_data["S"]
                    if s.shape[1] >= 6:
                        vm = np.sqrt(0.5 * ((s[:, 0] - s[:, 1])**2 + (s[:, 1] - s[:, 2])**2 + (s[:, 2] - s[:, 0])**2 + 6.0 * (s[:, 3]**2 + s[:, 4]**2 + s[:, 5]**2)))
                    else:
                        vm = np.zeros(s.shape[0])
                    s_mesh.cell_data["von_Mises"] = vm
                    plotter.add_mesh(s_mesh, scalars="von_Mises", cmap="copper_r", show_edges=True, edge_color="black",
                                     opacity=opacities["steel"], reset_camera=False, name="steel_mesh", preference="cell",
                                     clim=[0.0, 1080.0], scalar_bar_args=sargs_vm, show_scalar_bar=False)
                else:
                    plotter.add_mesh(s_mesh, color="silver", show_edges=True, edge_color="black",
                                     opacity=opacities["steel"], reset_camera=False, name="steel_mesh")

            if neg_x_plate_solid is not None:
                p_x = neg_x_plate_solid.copy(deep=True) if plate_offset_scalar > 0 else neg_x_plate_solid
                if plate_offset_scalar > 0: p_x.points += np.array([1.0, 0.0, 0.0]) * plate_offset_scalar
                plotter.add_mesh(p_x, color="dimgrey", show_edges=True, edge_color="black",
                                 opacity=opacities["support_plates"], reset_camera=False, name="ASSEMBLY_PLATE_NEG_X-1_PLATE_ELEM")

            if neg_y_plate_solid is not None:
                p_y = neg_y_plate_solid.copy(deep=True) if plate_offset_scalar > 0 else neg_y_plate_solid
                if plate_offset_scalar > 0: p_y.points += np.array([0.0, 1.0, 0.0]) * plate_offset_scalar
                plotter.add_mesh(p_y, color="dimgrey", show_edges=True, edge_color="black",
                                 opacity=opacities["support_plates"], reset_camera=False, name="ASSEMBLY_PLATE_NEG_Y-1_PLATE_ELEM")

            if show_bc and opacities["bc"] > 0.0:
                for bc_cfg in bc_configs:
                    bc_mesh = find_bc_block(init_data, bc_cfg["block"])
                    if bc_mesh is not None:
                        for constr in bc_cfg["constraints"]:
                            if constr == "Y":
                                dir_vec = (0, 1, 0)
                                color = "green"
                                name = f"bc_{bc_cfg['block']}_Y"
                            elif constr == "Z":
                                dir_vec = (0, 0, 1)
                                color = "blue"
                                name = f"bc_{bc_cfg['block']}_Z"
                            else:
                                continue

                            glyphs = create_bc_glyphs(bc_mesh, dir_vec, size=bc_size)
                            if glyphs is not None:
                                plotter.add_mesh(glyphs, color=color, show_edges=False,
                                                 opacity=opacities["bc"], reset_camera=False, name=name)
            else:
                for bc_cfg in bc_configs:
                    for constr in bc_cfg["constraints"]:
                        try:
                            plotter.remove_actor(f"bc_{bc_cfg['block']}_{constr}")
                        except Exception:
                            pass

            # Back support BCs (Phase 8/9)
            if show_bc and opacities["back_support_bc"] > 0.0:
                bc_mesh = find_bc_block(init_data, back_support_bc_config["block"])
                if bc_mesh is not None:
                    for constr in back_support_bc_config["constraints"]:
                        if constr == "Y":
                            dir_vec = (0, 1, 0)
                            color = "green"
                            name = f"bc_{back_support_bc_config['block']}_Y"
                        elif constr == "Z":
                            dir_vec = (0, 0, 1)
                            color = "blue"
                            name = f"bc_{back_support_bc_config['block']}_Z"
                        else:
                            continue
                        glyphs = create_bc_glyphs(bc_mesh, dir_vec, size=bc_size)
                        if glyphs is not None:
                            plotter.add_mesh(glyphs, color=color, show_edges=False,
                                             opacity=opacities["back_support_bc"], reset_camera=False, name=name)
            else:
                for constr in back_support_bc_config["constraints"]:
                    try:
                        plotter.remove_actor(f"bc_{back_support_bc_config['block']}_{constr}")
                    except Exception:
                        pass

            if annotation:
                actor = plotter.add_text(annotation, position=(0.5, 0.90), font_size=30, color="black",
                                          name="cinematic_annotation", viewport=True)
                actor.GetTextProperty().SetJustificationToCentered()
            else:
                try:
                    plotter.remove_actor("cinematic_annotation")
                except Exception:
                    pass

            plotter.write_frame()
            if (f + 1) % 60 == 0:
                print(f"  > Generated intro frame {f + 1}/{intro_frames}")

        # Clean up annotations
        try:
            plotter.remove_actor("cinematic_annotation")
        except Exception:
            pass

        # ==========================================
        # SYMMETRY REVEAL (between intro and Part 1)
        # ==========================================
        print("\n--- Symmetry Reveal (75 frames) ---")

        # Build mirrored copies of the half-model geometry (reflect across z=0)
        _sym_meshes = []
        if clean_concrete is not None:
            _sym_meshes.append(("sym_concrete", clean_concrete.reflect((0, 0, 1), point=(0, 0, 0)),
                                dict(scalars=mapped_damage_var, cmap="coolwarm", clim=[0.0, 1.0],
                                     show_edges=True, edge_color="black", scalar_bar_args=sargs,
                                     show_scalar_bar=False)))
        if clean_mortar is not None:
            _sym_meshes.append(("sym_mortar", clean_mortar.reflect((0, 0, 1), point=(0, 0, 0)),
                                dict(color="#3CB371", show_edges=True, edge_color="black")))
        if clean_steel is not None:
            sym_steel = clean_steel.reflect((0, 0, 1), point=(0, 0, 0))
            if args.steel_vm and "S" in sym_steel.cell_data:
                s = sym_steel.cell_data["S"]
                if s.shape[1] >= 6:
                    vm = np.sqrt(0.5 * ((s[:, 0] - s[:, 1])**2 + (s[:, 1] - s[:, 2])**2 + (s[:, 2] - s[:, 0])**2 + 6.0 * (s[:, 3]**2 + s[:, 4]**2 + s[:, 5]**2)))
                else:
                    vm = np.zeros(s.shape[0])
                sym_steel.cell_data["von_Mises"] = vm
                _sym_meshes.append(("sym_steel", sym_steel,
                                    dict(scalars="von_Mises", cmap="copper_r", show_edges=True, edge_color="black", preference="cell", clim=[0.0, 1080.0], scalar_bar_args=sargs_vm, show_scalar_bar=False)))
            else:
                _sym_meshes.append(("sym_steel", sym_steel,
                                    dict(color="silver", show_edges=True, edge_color="black")))
        if bottom_plate_solid is not None:
            _sym_meshes.append(("sym_bottom_plate", bottom_plate_solid.reflect((0, 0, 1), point=(0, 0, 0)),
                                dict(color="dimgrey", show_edges=True, edge_color="black")))
        if neg_x_plate_solid is not None:
            _sym_meshes.append(("sym_neg_x", neg_x_plate_solid.reflect((0, 0, 1), point=(0, 0, 0)),
                                dict(color="dimgrey", show_edges=True, edge_color="black")))
        if neg_y_plate_solid is not None:
            _sym_meshes.append(("sym_neg_y", neg_y_plate_solid.reflect((0, 0, 1), point=(0, 0, 0)),
                                dict(color="dimgrey", show_edges=True, edge_color="black")))

        _sym_fade_in  = 30
        _sym_hold     = 15
        _sym_fade_out = 30
        _sym_total    = _sym_fade_in + _sym_hold + _sym_fade_out  # 75 frames

        # Camera stays at default position throughout
        plotter.camera.position   = default_pos
        plotter.camera.focal_point = default_focal
        plotter.camera.up = (0.0, 1.0, 0.0)

        for _s in range(_sym_total):
            if _s < _sym_fade_in:
                progress = _s / (_sym_fade_in - 1)
                _alpha = 0.5 * (1.0 - math.cos(progress * math.pi)) * 0.9999
            elif _s < _sym_fade_in + _sym_hold:
                _alpha = 0.9999
            else:
                progress = (_s - _sym_fade_in - _sym_hold) / (_sym_fade_out - 1)
                _alpha = 0.5 * (1.0 + math.cos(progress * math.pi)) * 0.9999
            _alpha = float(np.clip(_alpha, 0.0, 0.9999))

            for _sym_name, _sym_mesh, _sym_kwargs in _sym_meshes:
                plotter.add_mesh(_sym_mesh, opacity=_alpha, reset_camera=False,
                                 name=_sym_name, **_sym_kwargs)

            _ann = plotter.add_text("Z-symmetry: only half the specimen modeled",
                                     position=(0.5, 0.90), font_size=30, color="black",
                                     name="sym_annotation", viewport=True)
            _ann.GetTextProperty().SetJustificationToCentered()

            plotter.write_frame()
            if (_s + 1) % 30 == 0:
                print(f"  > Symmetry reveal frame {_s + 1}/{_sym_total}")

        # Clean up mirrored actors and annotation before Part 1
        for _sym_name, _, _ in _sym_meshes:
            try:
                plotter.remove_actor(_sym_name)
            except Exception:
                pass
        try:
            plotter.remove_actor("sym_annotation")
        except Exception:
            pass

        # Ensure damage scale bar displays when simulation starts
        if clean_concrete is not None:
            plotter.add_mesh(clean_concrete, scalars=mapped_damage_var, cmap="coolwarm", clim=[0.0, 1.0],
                             opacity=0.9999, show_edges=True, edge_color="black",
                             scalar_bar_args=sargs, show_scalar_bar=True, reset_camera=False, name="concrete_mesh")

        # ==========================================

    # PART 1: ANIMATE DEFORMATION & ZOOM
    # ==========================================
    print("\nPart 1/3: Processing Deformation & Chart Sync (200 frames)...")
    time_steps = np.linspace(t_min_orig, t_max, 200)

    first_frame = True
    all_time_max_stress = 0.0

    for i, t in enumerate(time_steps):
        idx_after = np.searchsorted(available_times, t)
        idx_before = max(0, idx_after - 1)
        if idx_after >= len(available_times):
            idx_after = len(available_times) - 1

        t_before = available_times[idx_before]
        t_after = available_times[idx_after]
        weight = (t - t_before) / (t_after - t_before) if t_after != t_before else 0.0

        data_before = get_raw_data_at_time(t_before, reader, t_min_orig, t_max_orig, time_fraction, warp_factor)
        data_after = get_raw_data_at_time(t_after, reader, t_min_orig, t_max_orig, time_fraction, warp_factor)

        # Extract blocks for this step
        concrete_a = try_get_block(data_before, block_names["concrete"])
        concrete_b = try_get_block(data_after, block_names["concrete"])
        mortar_a = try_get_block(data_before, block_names["mortar"])
        mortar_b = try_get_block(data_after, block_names["mortar"])
        steel_a = try_get_block(data_before, block_names["steel"])
        steel_b = try_get_block(data_after, block_names["steel"])
        # Extract and interpolate load_nodes for force vectors
        load_nodes_a = try_get_block(data_before, block_names["load_nodes"])
        load_nodes_b = try_get_block(data_after, block_names["load_nodes"])
        if not hasattr(plotter, '_prealloc_load_nodes_w') and load_nodes_a:
            plotter._prealloc_load_nodes_w = load_nodes_a.copy(deep=True)
        load_nodes_w = interpolate_mesh(load_nodes_a, load_nodes_b, weight, getattr(plotter, '_prealloc_load_nodes_w', None)) if load_nodes_a else None
        if load_nodes_w and disp_var in load_nodes_w.point_data:
            load_nodes_w.points += load_nodes_w.point_data[disp_var] * warp_factor

        # Interpolate meshes IN-PLACE if they haven't been pre-allocated yet, allocate them
        if not hasattr(plotter, '_prealloc_concrete_w') and concrete_a:
            plotter._prealloc_concrete_w = concrete_a.copy(deep=True)
        if not hasattr(plotter, '_prealloc_mortar_w') and mortar_a:
            plotter._prealloc_mortar_w = mortar_a.copy(deep=True)
        if not hasattr(plotter, '_prealloc_steel_w') and steel_a:
            plotter._prealloc_steel_w = steel_a.copy(deep=True)

        concrete_w = interpolate_mesh(concrete_a, concrete_b, weight, getattr(plotter, '_prealloc_concrete_w', None)) if concrete_a else None
        mortar_w = interpolate_mesh(mortar_a, mortar_b, weight, getattr(plotter, '_prealloc_mortar_w', None)) if mortar_a else None
        steel_w = interpolate_mesh(steel_a, steel_b, weight, getattr(plotter, '_prealloc_steel_w', None)) if steel_a else None

        if concrete_w and disp_var in concrete_w.point_data:
            concrete_w.points += concrete_w.point_data[disp_var] * warp_factor
        if mortar_w and disp_var in mortar_w.point_data:
            mortar_w.points += mortar_w.point_data[disp_var] * warp_factor
        if steel_w and disp_var in steel_w.point_data:
            steel_w.points += steel_w.point_data[disp_var] * warp_factor

        clean_concrete_w = get_clean_quad_surface(concrete_w) if concrete_w else None
        clean_mortar_w = get_clean_quad_surface(mortar_w) if mortar_w else None
        clean_steel_w = get_clean_quad_surface(steel_w) if steel_w else None

        if clean_concrete_w:
            plotter.add_mesh(clean_concrete_w, scalars=mapped_damage_var, cmap="coolwarm", clim=[0.0, 1.0], show_edges=True, edge_color="black", scalar_bar_args=sargs, opacity=0.9999, reset_camera=False, name="concrete_mesh")
        if clean_mortar_w:
            plotter.add_mesh(clean_mortar_w, color="#3CB371", show_edges=True, edge_color="black", opacity=0.9999, reset_camera=False, name="mortar_mesh")
        if clean_steel_w:
            if args.steel_vm and "S" in clean_steel_w.cell_data:
                s = clean_steel_w.cell_data["S"]
                if s.shape[1] >= 6:
                    vm = np.sqrt(0.5 * ((s[:, 0] - s[:, 1])**2 + (s[:, 1] - s[:, 2])**2 + (s[:, 2] - s[:, 0])**2 + 6.0 * (s[:, 3]**2 + s[:, 4]**2 + s[:, 5]**2)))
                else:
                    vm = np.zeros(s.shape[0])
                clean_steel_w.cell_data["von_Mises"] = vm
                plotter.add_mesh(clean_steel_w, scalars="von_Mises", cmap="copper_r", show_edges=True, edge_color="black", opacity=0.9999, reset_camera=False, name="steel_mesh", preference="cell", clim=[0.0, 1080.0], scalar_bar_args=sargs_vm)
                
                # Add indicator for Max Stress
                if "S" in steel_w.cell_data and steel_w.cell_data["S"].shape[1] >= 6:
                    s_vol = steel_w.cell_data["S"]
                    vm_vol = np.sqrt(0.5 * ((s_vol[:, 0] - s_vol[:, 1])**2 + (s_vol[:, 1] - s_vol[:, 2])**2 + (s_vol[:, 2] - s_vol[:, 0])**2 + 6.0 * (s_vol[:, 3]**2 + s_vol[:, 4]**2 + s_vol[:, 5]**2)))
                    max_idx = np.argmax(vm_vol)
                    max_loc = steel_w.cell_centers().points[max_idx]
                    max_val = vm_vol[max_idx]
                    all_time_max_stress = max(all_time_max_stress, max_val)
                    
                    if max_val > 0.1:  # Only show if there's meaningful stress
                        try:
                            plotter.remove_actor("max_stress_marker")
                            plotter.remove_actor("max_stress_line")
                        except Exception:
                            pass
                        label_text = f"Current Max: {max_val:.0f} MPa\nAll-time Peak: {all_time_max_stress:.0f} MPa"
                        plotter.add_point_labels([max_loc], [label_text], point_size=10, point_color="red", text_color="red", name="max_stress_label", font_size=30, shape_color="white", shape_opacity=0.6, always_visible=True)
            else:
                plotter.add_mesh(clean_steel_w, color="silver", show_edges=True, edge_color="black", opacity=0.9999, reset_camera=False, name="steel_mesh")

        # ==================== BOUNDARY CONDITIONS RENDERING ====================
        if show_bc:
            for bc_cfg in bc_configs + [back_support_bc_config]:
                try:
                    bc_a = find_bc_block(data_before, bc_cfg["block"])
                    bc_b = find_bc_block(data_after, bc_cfg["block"])
                    if bc_a is not None and bc_b is not None:
                        if not hasattr(plotter, '_prealloc_bc_w'):
                            plotter._prealloc_bc_w = {}
                        if bc_cfg["block"] not in plotter._prealloc_bc_w:
                            plotter._prealloc_bc_w[bc_cfg["block"]] = bc_a.copy(deep=True)

                        bc_w = interpolate_mesh(bc_a, bc_b, weight, plotter._prealloc_bc_w[bc_cfg["block"]])
                        if disp_var in bc_w.point_data:
                            bc_w.points += bc_w.point_data[disp_var] * warp_factor

                        for constr in bc_cfg["constraints"]:
                            if constr == "Y":
                                dir_vec = (0, 1, 0)
                                color = "green"
                                name = f"bc_{bc_cfg['block']}_Y"
                            elif constr == "Z":
                                dir_vec = (0, 0, 1)
                                color = "blue"
                                name = f"bc_{bc_cfg['block']}_Z"
                            else:
                                continue

                            glyphs = create_bc_glyphs(bc_w, dir_vec, size=bc_size)
                            if glyphs is not None:
                                plotter.add_mesh(glyphs, color=color, show_edges=False,
                                                 reset_camera=False, name=name)
                except Exception:
                    pass
        # =======================================================================

        # ==================== PLATE EXTRUSION LOGIC ====================
        extruded_plates = []
        if not hasattr(plotter, '_prealloc_plates_w'):
            plotter._prealloc_plates_w = {}

        for p_name in rigid_plates:
            try:
                p_a = try_get_block(data_before, p_name)
                p_b = try_get_block(data_after, p_name)
                if not p_a: continue

                if p_name not in plotter._prealloc_plates_w:
                    plotter._prealloc_plates_w[p_name] = p_a.copy(deep=True)

                p_w = interpolate_mesh(p_a, p_b, weight, plotter._prealloc_plates_w[p_name])

                if disp_var in p_w.point_data:
                    p_w.points += p_w.point_data[disp_var] * warp_factor

                p_surf = get_clean_quad_surface(p_w)
                if p_surf.n_points > 0:
                    p_surf.compute_normals(cell_normals=False, point_normals=True, inplace=True)
                    avg_normal = np.mean(p_surf.point_data["Normals"], axis=0)
                    norm_mag = np.linalg.norm(avg_normal)
                    avg_normal = avg_normal / norm_mag if norm_mag > 1e-8 else np.array([0.0, 0.0, 1.0])

                    extrude_vec = avg_normal * -plate_thickness
                    p_solid = p_surf.extrude(extrude_vec, capping=True)
                    p_solid.points += avg_normal * -0.01
                    extruded_plates.append((p_name, p_solid))
            except ValueError:
                pass

        for p_name, p_solid in extruded_plates:
            if p_name == "ASSEMBLY_BOTTOM_PLATE-1_PLATE_ELEM" and bottom_plate_solid:
                bottom_plate_solid.copy_from(p_solid)
                _mesh_to_plot = bottom_plate_solid
            elif p_name == "ASSEMBLY_PLATE_NEG_X-1_PLATE_ELEM" and neg_x_plate_solid:
                neg_x_plate_solid.copy_from(p_solid)
                _mesh_to_plot = neg_x_plate_solid
            elif p_name == "ASSEMBLY_PLATE_NEG_Y-1_PLATE_ELEM" and neg_y_plate_solid:
                neg_y_plate_solid.copy_from(p_solid)
                _mesh_to_plot = neg_y_plate_solid
            else:
                _mesh_to_plot = p_solid
                
            plotter.add_mesh(_mesh_to_plot, color="dimgrey", show_edges=True, edge_color="black", opacity=0.9999, reset_camera=False, name=p_name)
        # ===============================================================

        if load_nodes_w is not None and rf_var in load_nodes_w.point_data:
            rf_vectors = np.array(load_nodes_w.point_data[rf_var])
            if rf_vectors.ndim == 1:
                rf_vectors = rf_vectors.reshape(-1, 3)

            rf_x_vectors = np.zeros_like(rf_vectors)
            rf_x_vectors[:, 0] = rf_vectors[:, 0]

            rf_x_mag = np.abs(rf_vectors[:, 0])

            nset_center = np.mean(load_nodes_w.points, axis=0)
            nset_center[2] = 0.0  # Force arrow to z=0 symmetry plane

            # Do NOT negate the reaction force. The arrow geometry's start=(0,0,0) ensures it points away properly.
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
                all_a = try_get_block(data_before, "ALL")
                all_b = try_get_block(data_after, "ALL")
                disp_before = all_a.point_data[disp_var][load_indices]
                disp_after = all_b.point_data[disp_var][load_indices]
                disp_w = disp_before + weight * (disp_after - disp_before)
                current_disp_val = np.abs(np.mean(disp_w[:, disp_component_idx]))
            except Exception:
                current_disp_val = 0.0

        active_chart = draw_dynamic_chart(t, plotter, active_chart, has_csv, csv_disp, csv_load, csv_time, t_max)

        if first_frame:
            cam_dist = clean_concrete.length * 0.8
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
    print("\nPart 2/3: Processing Transition Fade (60 frames)...")
    if concrete_w:
        smooth_fracture = concrete_w.contour(isosurfaces=[damage_threshold], scalars=mapped_damage_var)
    else:
        # Fallback just in case concrete_w is None (should not happen)
        smooth_fracture = pv.PolyData()
    mirrored_fracture = smooth_fracture.reflect((0, 0, 1), point=(0, 0, 0))

    plotter.add_mesh(smooth_fracture, scalars=mapped_damage_var, cmap="coolwarm", clim=[0.0, 1.0],
                     opacity=0.0, show_edges=False,
                     scalar_bar_args=sargs, reset_camera=False, name="fractured_mesh")
    plotter.add_mesh(mirrored_fracture, scalars=mapped_damage_var, cmap="coolwarm", clim=[0.0, 1.0],
                     opacity=0.0, show_edges=False,
                     scalar_bar_args=sargs, reset_camera=False, name="mirrored_mesh")

    fade_steps = 60
    for step in range(fade_steps + 1):
        alpha_clipped = step / fade_steps
        alpha_full = 1.0 - (0.8 * alpha_clipped)

        if "concrete_mesh" in plotter.actors:
            plotter.actors["concrete_mesh"].GetProperty().SetOpacity(alpha_full)
        if "fractured_mesh" in plotter.actors:
            plotter.actors["fractured_mesh"].GetProperty().SetOpacity(alpha_clipped)
        if "mirrored_mesh" in plotter.actors:
            plotter.actors["mirrored_mesh"].GetProperty().SetOpacity(alpha_clipped)

        # Fade BCs out together with the concrete
        if show_bc:
            all_bc_names = (
                [f"bc_{bc_cfg['block']}_{c}" for bc_cfg in bc_configs for c in bc_cfg["constraints"]]
                + [f"bc_{back_support_bc_config['block']}_{c}" for c in back_support_bc_config["constraints"]]
            )
            for name in all_bc_names:
                if name in plotter.actors:
                    plotter.actors[name].GetProperty().SetOpacity(alpha_full)

        active_chart = draw_dynamic_chart(t_max, plotter, active_chart, has_csv, csv_disp, csv_load, csv_time, t_max)
        plotter.write_frame()

    # Remove all BC actors cleanly before Part 3 orbital rotation
    all_bc_names = (
        [f"bc_{bc_cfg['block']}_{c}" for bc_cfg in bc_configs for c in bc_cfg["constraints"]]
        + [f"bc_{back_support_bc_config['block']}_{c}" for c in back_support_bc_config["constraints"]]
    )
    for _name in all_bc_names:
        try:
            plotter.remove_actor(_name)
        except Exception:
            pass

    # ==========================================
    # PART 3: SPIRALING ROTATION 
    # ==========================================
    print("\nPart 3/3: Processing Orbital Camera Motion (240 frames)...")
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

        active_chart = draw_dynamic_chart(t_max, plotter, active_chart, has_csv, csv_disp, csv_load, csv_time, t_max)
        plotter.write_frame()
        if (i+1) % 60 == 0:
            print(f"  > Generated frame {i+1}/240")

    # ==========================================
    # CLEANUP
    # ==========================================
    plotter.close()
    print(f"\nSuccess! Cinematic video file compiled and saved to: {output_file}")


if __name__ == "__main__":
    main()
