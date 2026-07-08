import cubit
import math

# Clear any existing geometry
cubit.cmd("reset")

# --- PARAMETERS ---
# Far Field Parameters
far_x = 150.0        # Size of far field in -x direction
far_y = 100.0        # Size of far field in -y direction
far_z = 150.0        # Size of far field in -z direction
ff_interval = 3

# Concrete Slab
edge_dist = 150.0     # Distance from anchor center to the free edge (+x direction)
nearfield_x = edge_dist + 50.0  # Length of the near field region in the x-direction (from free edge to start of far field)
support_w = 20.0     # Width of the support area at the outer corners of the breakout face

# Distance of the inner supports is 4 * edge_dist. Total width adds the support blocks.
nearfield_z = (6.0 * edge_dist) + (2.0 * support_w) 
nearfield_h = 200    # Total height (y)

# Derived Total Dimensions
total_x = nearfield_x + far_x
total_y = nearfield_h + far_y
total_z = nearfield_z + 2 * far_z # Symmetric addition before Z-cut

# Borehole & Mortar
hole_r = 9.0         # Borehole radius
hole_d = 100.0       # Borehole depth
anchor_d = 100.0     # Depth of the anchor within the borehole (must be <= hole_d)

# Refinement Domain (Hollow Rectangular Pyramid Shell)
vertical_angle = 30.0          # Angle (in degrees) of the downward vertical opening towards the free edge
vertical_start_dist_x = 25.0  # Distance in front of the anchor where the vertical downward angle begins
lateral_angle = 60.0          # Angle (in degrees) of the lateral opening towards the supports
band_x = 50.0e0               # Thickness of the solid refined block in front of the anchor (x-dir)
band_y = 15.0e0               # Thickness of the refined shell from the top surface (y-dir)
band_z = 20.0e0               # Thickness of the refined shell from the symmetry plane (z-dir)
corner_r = 0.0                # Radius to round off the outer lower pyramid edge (-y and -z)
y_flat_limit = -150.0         # Base Y-coord where the downward pyramid expansion hits the floor
bottom_angle = 0.0            # Inclination angle (degrees) rotating around the X-axis
pyramid_start_depth_y = 140.0 # Adjust this to change the starting depth below the anchor 

# Steel Anchor
anchor_r = 8.0         # Anchor radius
anchor_free_h = 20.0   # Anchor height above the concrete slab

# Steel Plate
plate_w = 80.0         # Plate width (x and z)
plate_h = 20.0         # Plate thickness (y)
plate_cut_h = plate_h / 3.0 # Webcut plate for load application

# Mesh Parameters
mesh_size_steel = 4.0
mesh_size_concrete_outer = 12.0  # Base size for the concrete block


# --- GEOMETRY CREATION ---

# 1. Concrete Slab with Far Fields
cubit.cmd(f"create brick x {total_x} y {total_y} z {total_z}")
v_base = cubit.get_last_id("volume")

# Shift so the +X face is at 'edge_dist', top face at 0, centered on Z
shift_x_base = edge_dist - (total_x / 2.0)
cubit.cmd(f"move volume {v_base} x {shift_x_base} y {-total_y / 2.0}")

# Webcut out the original slab boundary planes to isolate regions
cubit.cmd(f"webcut volume all with plane yplane offset {-nearfield_h}")
cubit.cmd(f"webcut volume all with plane xplane offset {edge_dist - nearfield_x}")
cubit.cmd(f"webcut volume all with plane zplane offset {-nearfield_z / 2.0}")
cubit.cmd(f"webcut volume all with plane zplane offset {nearfield_z / 2.0}")

# Name the far fields and the main concrete block
cubit.cmd("volume all name 'concrete_far'")
cubit.cmd(f"volume with x_coord > {edge_dist - nearfield_x - 0.1} and y_coord > {-nearfield_h - 0.1} and z_coord > {-nearfield_z/2.0 - 0.1} and z_coord < {nearfield_z/2.0 + 0.1} name 'concrete_main'")

# Retrieve the inner slab ID for the borehole subtraction
v_slab_list = cubit.parse_cubit_list("volume", "with name 'concrete_main'")
v_slab = v_slab_list[0]

# Create and subtract the borehole tool
cubit.cmd(f"create cylinder height {hole_d} radius {hole_r}")
v_hole_tool = cubit.get_last_id("volume")
id_cyl_surf = cubit.get_last_id("surface") - 2
cubit.cmd(f"surface {id_cyl_surf} name 'surface_borehole'")

cubit.cmd(f"rotate volume {v_hole_tool} angle 90 about x")
cubit.cmd(f"move volume {v_hole_tool} y {-hole_d / 2.0}")

cubit.cmd(f"subtract volume {v_hole_tool} from volume {v_slab}")
v_slab = cubit.get_last_id("volume")
cubit.cmd(f"volume {v_slab} name 'concrete_main'")

# 2. Adhesive Mortar
cubit.cmd(f"create cylinder height {anchor_d} radius {hole_r}")
v_mortar_outer = cubit.get_last_id("volume")
id_mortar_surf = cubit.get_last_id("surface") - 2
cubit.cmd(f"surface {id_mortar_surf} name 'surface_mortar_outer'")
cubit.cmd(f"rotate volume {v_mortar_outer} angle 90 about x")
cubit.cmd(f"move volume {v_mortar_outer} y {-anchor_d / 2.0}")

cubit.cmd(f"create cylinder height {anchor_d} radius {anchor_r}")
v_mortar_inner = cubit.get_last_id("volume")
id_mortar_surf = cubit.get_last_id("surface") - 2
cubit.cmd(f"surface {id_mortar_surf} name 'surface_mortar_inner'")
cubit.cmd(f"rotate volume {v_mortar_inner} angle 90 about x")
cubit.cmd(f"move volume {v_mortar_inner} y {-anchor_d / 2.0}")

cubit.cmd(f"subtract volume {v_mortar_inner} from volume {v_mortar_outer}")
v_mortar = cubit.get_last_id("volume")
cubit.cmd(f"volume {v_mortar} name 'mortar'")

# 3. Steel Anchor
anchor_len = anchor_d + anchor_free_h
anchor_y_pos = (-anchor_d + anchor_free_h) / 2.0
cubit.cmd(f"create cylinder height {anchor_len} radius {anchor_r}")
v_anchor = cubit.get_last_id("volume")
id_anchor_surf = cubit.get_last_id("surface") - 2
cubit.cmd(f"surface {id_anchor_surf} name 'surface_anchor_outer'")
cubit.cmd(f"rotate volume {v_anchor} angle 90 about x")
cubit.cmd(f"move volume {v_anchor} y {anchor_y_pos}")
cubit.cmd(f"volume {v_anchor} name 'steel_anchor'")

# 4. Steel Plate
cubit.cmd(f"create brick x {plate_w} y {plate_h} z {plate_w}")
v_plate = cubit.get_last_id("volume")
cubit.cmd(f"move volume {v_plate} y {plate_h / 2.0}")

cubit.cmd(f"create cylinder height {plate_h} radius {anchor_r}")
v_plate_hole = cubit.get_last_id("volume")
cubit.cmd(f"rotate volume {v_plate_hole} angle 90 about x")
cubit.cmd(f"move volume {v_plate_hole} y {plate_h / 2.0}")

cubit.cmd(f"subtract volume {v_plate_hole} from volume {v_plate}")
v_plate = cubit.get_last_id("volume")
cubit.cmd(f"volume {v_plate} name 'steel_plate'")


# --- STRUCTURAL DECOMPOSITION FOR MESHING ---

# 1. Extend the borehole profile down for clean hex sweeping
cubit.cmd(f"webcut volume with name 'concrete_main' cylinder radius {hole_r} axis y")

# 2. Create the support boundaries on the free edge
cubit.cmd(f"webcut volume with name 'concrete_*' plane zplane offset {-nearfield_z/2.0 + support_w}")
cubit.cmd(f"webcut volume with name 'concrete_*' plane zplane offset {nearfield_z/2.0 - support_w}")

# 3. Webcut plate for loading zone
cubit.cmd(f"webcut volume with name 'steel_plate' plane yplane offset {plate_cut_h}")

# --- SYMMETRY AND DECOMPOSITION ---

# 1. Exploit Z-Symmetry (Delete +Z)
cubit.cmd("webcut volume all with plane zplane offset 0")

vols = cubit.parse_cubit_list("volume", "all")
vols_to_delete = []
for v in vols:
    cent = cubit.get_center_point("volume", v)
    if cent[2] > 0.01:
        vols_to_delete.append(str(v))
        
if vols_to_delete:
    cubit.cmd(f"delete volume {' '.join(vols_to_delete)}")


# --- GROUPING ---
cubit.cmd("group 'grp_concrete' add volume with name 'concrete_*'")
cubit.cmd("group 'grp_mortar' add volume with name 'mortar*'")
cubit.cmd("group 'grp_steel' add volume with name 'steel_*'")

# --- TOPOLOGY & MESH CONSTRAINTS ---
cubit.cmd("imprint volume in grp_steel")
cubit.cmd("imprint volume in grp_concrete")

cubit.cmd("merge volume in grp_concrete")
cubit.cmd("merge volume in grp_mortar")
cubit.cmd("merge volume in grp_steel")


# --- BASE MESH GENERATION ---
# Apply default sizes
cubit.cmd(f"volume in grp_concrete size {mesh_size_concrete_outer}")
cubit.cmd(f"volume in grp_steel size {mesh_size_steel}")
cubit.cmd(f"volume in grp_mortar size {mesh_size_steel}")

# --- FAR FIELD MESH CONSTRAINTS (INTERVAL = 1) ---
center_x_far = edge_dist - nearfield_x - far_x / 2.0
center_y_far = -nearfield_h - far_y / 2.0
center_z_far_neg = -nearfield_z / 2.0 - far_z / 2.0

cubit.cmd(f"curve in volume with name 'concrete_far*' expand with x_coord = {center_x_far} tolerance 0.1 interval {ff_interval}")
cubit.cmd(f"curve in volume with name 'concrete_far*' expand with y_coord = {center_y_far} tolerance 0.1 interval {ff_interval}")
cubit.cmd(f"curve in volume with name 'concrete_far*' expand with z_coord = {center_z_far_neg} tolerance 0.1 interval {ff_interval}")


# Generate Base Mesh
cubit.cmd("mesh volume all")


# ======================================================
# ELEMENT-LEVEL REFINEMENT (HOLLOW RECTANGULAR PYRAMID)
# ======================================================
all_hexes = cubit.parse_cubit_list("hex", "in grp_concrete expand")
breakout_hexes = []

# Refactored Tracking Parameters for Geometric Clarity
x_start = -hole_r - 15.0
pyramid_start_z = -hole_r - 10.0
lateral_start_dist_x = 1.8 * hole_r  # Focal x-coordinate where lateral expansion originates

# Implemented dynamic depth definition relative to global top plane (y=0)
pyramid_start_y = -pyramid_start_depth_y 

# Calculate expansion slopes
vertical_tan = math.tan(math.radians(vertical_angle))
lateral_tan = math.tan(math.radians(lateral_angle))
bottom_tan = math.tan(math.radians(bottom_angle))

tol = mesh_size_concrete_outer / 2.0 + 1.0 
support_inner_z = -nearfield_z / 2.0 + 1.0 * support_w

for h in all_hexes:
    x, y, z = cubit.get_center_point("hex", h)
    
    if x < x_start or x > edge_dist + tol:
        continue
        
    # Cut off refinement entirely within the supports
    if z < support_inner_z + tol:
        continue
        
    # Calculate lateral and vertical offsets independently
    dx_z = max(0, x - x_start)                         # Lateral expansion along Z
    dx_y = max(0, x - vertical_start_dist_x)           # Vertical expansion along Y (starts further forward)
    
    # 1. OUTLINE THE OUTER PYRAMID
    y_lim_raw = pyramid_start_y - dx_y * vertical_tan
    z_lim_raw = pyramid_start_z - dx_z * lateral_tan
    
    # Calculate the inclined floor (rotation around the X-axis)
    y_floor = y_flat_limit - z * bottom_tan
    
    # CLAMP the lateral expansion to the support boundary and vertical to the inclined floor.
    y_lim = max(y_lim_raw, y_floor)
    z_lim = max(z_lim_raw, support_inner_z)
    
    y_lim_eff = y_lim - tol
    z_lim_eff = z_lim - tol
    
    in_main = False
    if y >= y_lim_eff and z >= z_lim_eff:
        # Check corner rounding logic
        y_center = y_lim_eff + corner_r
        z_center = z_lim_eff + corner_r
        
        # If element is in the lower -y and -z quadrant of the corner
        if y < y_center and z < z_center:
            # Must fall inside the radial distance
            if (y - y_center)**2 + (z - z_center)**2 <= corner_r**2:
                in_main = True
        else:
            in_main = True

    # 2. OUTLINE THE INNER UNCRACKED CORE
    in_core = False
    if x >= x_start + band_x:
        y_in = y_lim + band_y + tol
        z_in = z_lim + band_z + tol
        
        if y_in < 0.1 and z_in < 0.1:
            if y >= y_in and z >= z_in:
                # Apply proportional rounding to the inner core to prevent thinning
                inner_r = max(0.0, corner_r - min(band_y, band_z))
                if inner_r > 0:
                    y_in_center = y_in + inner_r
                    z_in_center = z_in + inner_r
                    
                    if y < y_in_center and z < z_in_center:
                        if (y - y_in_center)**2 + (z - z_in_center)**2 <= inner_r**2:
                            in_core = True
                    else:
                        in_core = True
                else:
                    in_core = True

    # 3. SELECTION LOGIC
    if in_main and not in_core:
        breakout_hexes.append(str(h))


if breakout_hexes:
    print(f"Found {len(breakout_hexes)} hexes in the hollow breakout band. Grouping and refining...")
    cubit.cmd("create group 'breakout_domain'")
    
    chunk_size = 200
    for i in range(0, len(breakout_hexes), chunk_size):
        chunk = " ".join(breakout_hexes[i:i + chunk_size])
        cubit.cmd(f"group 'breakout_domain' add hex {chunk}")

    # Create adjacent hexes group and permanently merge into breakout_domain
    cubit.cmd("create group 'adjacent_hexes'")
    cubit.cmd("group 'adjacent_hexes' add hex in face in hex in breakout_domain")
    cubit.cmd("group 'breakout_domain' add hex in adjacent_hexes")
    
    # Refine the combined group in one pass
    cubit.cmd("refine hex in breakout_domain depth 0 numsplit 1 smooth")
    print("Refinement complete.")
else:
    print("No hexes found within the specified breakout domain parameters.")


# --- BLOCKS ---
anchor_bId = 1
cubit.cmd(f"create block {anchor_bId}")
cubit.cmd(f"block {anchor_bId} name 'steel'")
cubit.cmd(f"block {anchor_bId} add volume in grp_steel")

mortar_bId = 2
cubit.cmd(f"create block {mortar_bId}")
cubit.cmd(f"block {mortar_bId} name 'mortar'")
cubit.cmd(f"block {mortar_bId} add volume in grp_mortar")

concrete_bId = 3
cubit.cmd(f"create block {concrete_bId}")
cubit.cmd(f"block {concrete_bId} name 'concrete'")
cubit.cmd(f"block {concrete_bId} add volume in grp_concrete")
cubit.cmd(f"block {concrete_bId} element type hex20")


# --- SIDESETS & NODESETS ---
currentsideset_id = 1
currentnodeset_id = 1

# Concrete Top
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'concrete_top'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with y_coord = 0")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'concrete_top'")
currentsideset_id += 1; currentnodeset_id += 1

# Concrete Bottom
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'bottom'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with y_coord = {-total_y}")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'bottom'")
currentsideset_id += 1; currentnodeset_id += 1

# Concrete Back Face Support
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'back_support'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with x_coord = {edge_dist - total_x}")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'back_support'")
currentsideset_id += 1; currentnodeset_id += 1

# --- Split the Front Face into Free Edge and Front Support ---
all_front_surfs = cubit.parse_cubit_list("surface", f"in grp_concrete expand with x_coord = {edge_dist} tolerance 0.01")
support_surfs = []
free_edge_surfs = []

for s in all_front_surfs:
    cent = cubit.get_center_point("surface", s)
    if cent[2] < (-nearfield_z/2.0 + support_w + 0.01) and cent[2] > (-nearfield_z/2.0 - 0.01):
        support_surfs.append(str(s))
    else:
        free_edge_surfs.append(str(s))

# Front Support
if support_surfs:
    cubit.cmd(f"create sideset {currentsideset_id}")
    cubit.cmd(f"sideset {currentsideset_id} name 'front_support'")
    cubit.cmd(f"sideset {currentsideset_id} add surface {' '.join(support_surfs)}")
    cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
    cubit.cmd(f"nodeset {currentnodeset_id} name 'front_support'")
    currentsideset_id += 1; currentnodeset_id += 1

# Free Edge
if free_edge_surfs:
    cubit.cmd(f"create sideset {currentsideset_id}")
    cubit.cmd(f"sideset {currentsideset_id} name 'free_edge'")
    cubit.cmd(f"sideset {currentsideset_id} add surface {' '.join(free_edge_surfs)}")
    cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
    cubit.cmd(f"nodeset {currentnodeset_id} name 'free_edge'")
    currentsideset_id += 1; currentnodeset_id += 1
# -----------------------------------------------------------

# Z-Symmetry Back Plane
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'z_minus_bound'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with z_coord = {-nearfield_z/2.0 - far_z}")
currentsideset_id += 1

# Plate Bottom
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'plate_bottom'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_steel expand with y_coord = 0")
currentsideset_id += 1

# Interfaces
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'concrete_to_mortar'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with name 'surface_borehole*'")
currentsideset_id += 1

cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'mortar_to_anchor'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_mortar expand with name 'surface_mortar_inner*'")
currentsideset_id += 1

cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'anchor_to_mortar'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_steel expand with name 'surface_anchor_outer*'")
currentsideset_id += 1

# --- EXPORT ---
cubit.cmd(f'export abaqus "./steel.inp" block {anchor_bId} {mortar_bId} partial overwrite')
cubit.cmd(f'export abaqus "./concrete.inp" block {concrete_bId} partial overwrite')

# --- EXPORT EXODUS all in one FOR VISUALIZATION ---
cubit.cmd(f'export exodus "./full_model.exo" overwrite')


# --- QUALITY CHECK ---
cubit.cmd("quality volume all scaled jacobian global draw histogram draw mesh") 


