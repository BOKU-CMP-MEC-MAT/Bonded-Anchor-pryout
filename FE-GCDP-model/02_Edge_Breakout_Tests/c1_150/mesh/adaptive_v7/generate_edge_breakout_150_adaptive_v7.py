import cubit
import csv
import os

# Clear any existing geometry
cubit.cmd("reset")

# --- PARAMETERS ---

# CSV Refinement Parameters
csv_filepath = "./centroid_coordinates_of_elements_to_refine_3.csv" # Path to the CSV file containing target (x, y, z) centroids
csv_filepath = None
refine_sleeve = csv_filepath is not None
csv_tolerance = 3.5                     # Distance radius to match current elements to the imported centroids

# Far Field Parameters
far_x = 300.0        # Size of far field in -x direction
far_z = 150.0        # Size of far field in -z direction
ff_interval = 3

# Concrete Slab
edge_dist = 150.0     # Distance from anchor center to the free edge (+x direction)
nearfield_x = edge_dist + 50.0  # Length of the near field region in the x-direction (from free edge to start of far field)
support_w = 55.0     # Width of the support area at the outer corners of the breakout face

# Distance of the inner supports is 4 * edge_dist. Total width adds the support blocks.
nearfield_z = (6.0 * edge_dist) + (2.0 * support_w) 
nearfield_h = 300    # Total height (y)

# Derived Total Dimensions
total_x = nearfield_x + far_x
total_y = nearfield_h  # Removed far_y addition
total_z = nearfield_z + 2 * far_z # Symmetric addition before Z-cut

# Borehole & Mortar
hole_r = 9.0         # Borehole radius
hole_d = 100.0       # Borehole depth
anchor_d = 100.0     # Depth of the anchor within the borehole (must be <= hole_d)

# Steel Anchor
anchor_r = 8.0         # Anchor radius
anchor_free_h = 20.0   # Anchor height above the concrete slab
 
# Steel Plate
plate_w_z = 200.0        # Plate width in z direction (before symmetry cut)
plate_h = 20.0           # Plate thickness (y)

plate_x_max = 200.0
plate_x_min = edge_dist - total_x
plate_w_x = plate_x_max - plate_x_min
plate_center_x = (plate_x_max + plate_x_min) / 2.0

# Mesh Parameters
mesh_size_steel = 4.0
mesh_size_plate = 20.0
mesh_size_concrete_outer = 14.0  # Base size for the concrete block


# --- GEOMETRY CREATION ---

# 1. Concrete Slab with Far Fields
cubit.cmd(f"create brick x {total_x} y {total_y} z {total_z}")
v_base = cubit.get_last_id("volume")

# Shift so the +X face is at 'edge_dist', top face at 0, centered on Z
shift_x_base = edge_dist - (total_x / 2.0)
cubit.cmd(f"move volume {v_base} x {shift_x_base} y {-total_y / 2.0}")

# Webcut out the original slab boundary planes to isolate regions
cubit.cmd(f"webcut volume all with plane xplane offset {edge_dist - nearfield_x}")
cubit.cmd(f"webcut volume all with plane zplane offset {-nearfield_z / 2.0}")
cubit.cmd(f"webcut volume all with plane zplane offset {nearfield_z / 2.0}")

# Name the far fields and the main concrete block
cubit.cmd("volume all name 'concrete_far'")
cubit.cmd(f"volume with x_coord > {edge_dist - nearfield_x - 0.1} and z_coord > {-nearfield_z/2.0 - 0.1} and z_coord < {nearfield_z/2.0 + 0.1} name 'concrete_main'")

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
cubit.cmd(f"create brick x {plate_w_x} y {plate_h} z {plate_w_z}")
v_plate = cubit.get_last_id("volume")
cubit.cmd(f"move volume {v_plate} x {plate_center_x} y {plate_h / 2.0} z 0")

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

# 2. (Removed support boundaries webcuts on the free edge to avoid unnecessary volumes)


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
cubit.cmd(f"volume with name 'steel_plate*' size {mesh_size_plate}")
cubit.cmd(f"volume with name 'steel_anchor*' size {mesh_size_steel}")
cubit.cmd(f"curve in volume with name 'steel_anchor*' size {mesh_size_steel}")

# Set 4 intervals across plate thickness by targeting the vertical curves at the anchor interface
cubit.cmd(f"curve at {anchor_r} {anchor_free_h / 2.0} 0 interval 4")
cubit.cmd(f"curve at {-anchor_r} {anchor_free_h / 2.0} 0 interval 4")
cubit.cmd(f"volume in grp_mortar size {mesh_size_steel}")

# --- FAR FIELD MESH CONSTRAINTS (INTERVAL = 1) ---
center_x_far = edge_dist - nearfield_x - far_x / 2.0
center_z_far_neg = -nearfield_z / 2.0 - far_z / 2.0

cubit.cmd(f"curve in volume with name 'concrete_far*' expand with x_coord = {center_x_far} tolerance 0.1 interval {ff_interval}")
cubit.cmd(f"curve in volume with name 'concrete_far*' expand with z_coord = {center_z_far_neg} tolerance 0.1 interval {ff_interval}")


# Generate Base Mesh
cubit.cmd("mesh volume with name 'steel_*'")
cubit.cmd("mesh volume with name 'mortar*'")

# concrete meshing: tets!
cubit.cmd("mesh volume with name 'concrete_*'")

# cubit.cmd("disassociate mesh from volume all")

# ======================================================
# ELEMENT-LEVEL REFINEMENT (CSV IMPORT & BOREHOLE CONTACT)
# ======================================================
all_hexes = cubit.parse_cubit_list("hex", "in grp_concrete expand")
breakout_hexes = []
if refine_sleeve:

    print(f"--- CSV Refinement Mode Active ---")
    if os.path.exists(csv_filepath):
        print(f"Reading target centroids from {csv_filepath}...")
        target_coords = []
        with open(csv_filepath, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                try:
                    x_val, y_val, z_val = float(row[0]), float(row[1]), float(row[2])
                    target_coords.append((x_val, y_val, z_val))
                except (ValueError, IndexError):
                    continue
        
        print(f"Loaded {len(target_coords)} target coordinates. Finding matching hexes...")
        tol_sq = csv_tolerance**2
        
        for h in all_hexes:
            hx, hy, hz = cubit.get_center_point("hex", h)
            for tx, ty, tz in target_coords:
                dist_sq = (hx - tx)**2 + (hy - ty)**2 + (hz - tz)**2
                if dist_sq <= tol_sq:
                    if hz >= -3 * edge_dist + 8 :  # Only consider hexes within the nearfield region
                        breakout_hexes.append(str(h))
                        break 
    else:
        print(f"WARNING: CSV file not found at '{csv_filepath}'.")

    # --- ADD BOREHOLE CONTACT HEXES DIRECTLY ---
    print("Selecting all concrete hexes attached to the borehole...")

    borehole_hexes = cubit.parse_cubit_list("hex", "in node in surface with name 'surface_borehole*'")

    # filter all hexes with a depth above
    borehole_hexes = [h for h in borehole_hexes if cubit.get_center_point("hex", h)[1] > (-anchor_d - 70.01)]

    if borehole_hexes:
        all_concrete_hex_set = set(all_hexes)
        valid_borehole_hexes = [str(h) for h in borehole_hexes if h in all_concrete_hex_set]

        # actually let's remove them instead of extend:
        breakout_hexes.extend(valid_borehole_hexes)
        # breakout_hexes = [h for h in breakout_hexes if h not in valid_borehole_hexes]

        print(f"Added {len(valid_borehole_hexes)} concrete hexes to the refinement list.")
    else:
        print("WARNING: Could not find any hexes attached to the borehole surfaces.")

# Remove any duplicates 
breakout_hexes = list(set(breakout_hexes))

# --- EXECUTE REFINEMENT ON SELECTED HEXES ---
if breakout_hexes:
    print(f"Found {len(breakout_hexes)} unique target hexes in total. Grouping and refining...")
    cubit.cmd("create group 'breakout_domain'")
    
    chunk_size = 200
    for i in range(0, len(breakout_hexes), chunk_size):
        chunk = " ".join(breakout_hexes[i:i + chunk_size])
        cubit.cmd(f"group 'breakout_domain' add hex {chunk}")

    cubit.cmd("create group 'adjacent_hexes'")
    cubit.cmd("group 'adjacent_hexes' add hex in face in hex in breakout_domain")
    cubit.cmd("group 'breakout_domain' add hex in adjacent_hexes")
    
    # cubit.cmd("refine hex in breakout_domain depth 0 numsplit 1 smooth")
    cubit.cmd("refine hex in breakout_domain depth 0 numsplit 1 ")

    cubit.cmd("Volume all Smooth Scheme Condition Number beta 2.0 cpu 0.25")
    cubit.cmd("smooth volume all")

    print("Refinement complete.")
else:
    print("No hexes met the refinement criteria.")


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

# Concrete Front
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'concrete_front'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with x_coord = {edge_dist}")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'concrete_front'")
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

# --- Front Support, Top Support, Free Edge, and Back Top Edge via Geometric Search ---
all_concrete_nodes = cubit.parse_cubit_list("node", "in volume with name 'concrete_*'")
if not all_concrete_nodes:
    # Fallback to all nodes just in case
    all_concrete_nodes = cubit.parse_cubit_list("node", "all")

print(f"Total concrete nodes to search: {len(all_concrete_nodes)}")

front_support_nodes = []
top_support_nodes = []
free_edge_nodes = []
back_top_edge_nodes = []

tol = 0.1 # increased tolerance slightly to account for meshing precision
z_min = -nearfield_z / 2.0
z_max = -nearfield_z / 2.0 + support_w

for n in all_concrete_nodes:
    coords = cubit.get_nodal_coordinates(n)
    if coords is None:
        continue
    x, y, z = coords
    
    # 1. Frontal support & Free Edge
    if abs(x - edge_dist) < tol:
        if -50.0 - tol <= y <= 0.0 + tol and z_min - tol <= z <= z_max + tol:
            front_support_nodes.append(str(n))
        else:
            free_edge_nodes.append(str(n))
            
    # 2. Top support patch (y-direction support)
    if abs(y - 0.0) < tol:
        if edge_dist - 50.0 - tol <= x <= edge_dist + tol:
            if z_min - tol <= z <= z_max + tol:
                top_support_nodes.append(str(n))
                
    # 3. Back top edge
    if abs(x - (edge_dist - total_x)) < tol and abs(y - 0.0) < tol:
        back_top_edge_nodes.append(str(n))

print(f"Found {len(front_support_nodes)} nodes for front_support")
print(f"Found {len(top_support_nodes)} nodes for top_support")
print(f"Found {len(free_edge_nodes)} nodes for free_edge")
print(f"Found {len(back_top_edge_nodes)} nodes for back_top_edge")

def add_nodeset_in_chunks(ns_id, ns_name, nodes_list):
    if nodes_list:
        cubit.cmd(f"create nodeset {ns_id}")
        cubit.cmd(f"nodeset {ns_id} name '{ns_name}'")
        chunk_size = 200
        for i in range(0, len(nodes_list), chunk_size):
            chunk = " ".join(nodes_list[i:i + chunk_size])
            cubit.cmd(f"nodeset {ns_id} add node {chunk}")
        return True
    return False

if add_nodeset_in_chunks(currentnodeset_id, 'front_support', front_support_nodes):
    currentnodeset_id += 1

if add_nodeset_in_chunks(currentnodeset_id, 'top_support', top_support_nodes):
    currentnodeset_id += 1

if add_nodeset_in_chunks(currentnodeset_id, 'free_edge', free_edge_nodes):
    currentnodeset_id += 1

if add_nodeset_in_chunks(currentnodeset_id, 'back_top_edge', back_top_edge_nodes):
    currentnodeset_id += 1
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

cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'mortar_to_concrete'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_mortar expand with name 'surface_mortar_outer*'")
currentsideset_id += 1

# Shear Load Nodeset
cubit.cmd(f"create nodeset {currentnodeset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'shear_loading'")
cubit.cmd(f"nodeset {currentnodeset_id} add node in grp_steel expand with x_coord = {plate_x_max} tolerance 0.01")
currentnodeset_id += 1

# Plate Back Nodeset
cubit.cmd(f"create nodeset {currentnodeset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'plate_back'")
cubit.cmd(f"nodeset {currentnodeset_id} add node in grp_steel expand with x_coord = {plate_x_min} tolerance 0.01")
currentnodeset_id += 1

# Z-Symmetry Constraint
cubit.cmd(f"create nodeset {currentnodeset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'z_symm'")
cubit.cmd(f"nodeset {currentnodeset_id} add node in volume all expand with z_coord = 0")
currentnodeset_id += 1

# --- EXPORT ---
cubit.cmd(f'export abaqus "./steel.inp" block {anchor_bId} {mortar_bId} partial overwrite')
cubit.cmd(f'export abaqus "./concrete.inp" block {concrete_bId} partial overwrite')

# # --- EXPORT EXODUS all in one FOR VISUALIZATION ---
# cubit.cmd(f'export exodus "./full_model.exo" overwrite')

# # --- QUALITY CHECK ---
# cubit.cmd("quality volume all scaled jacobian global draw histogram draw mesh")

# show elements with negative scaled jacobian only:
cubit.cmd('quality volume all scaled jacobian global high 0 low -1 draw mesh')
