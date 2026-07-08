import cubit

# Clear any existing geometry
cubit.cmd("reset")

# --- PARAMETERS ---
# Edge Breakout Parameters
hef = 80.0            # Effective embedment depth
edge_dist = 50.0      # Edge distance in the positive X direction

# Concrete Slab (Shifted to create the free edge)
slab_x_min = -300.0   # Sufficient length in the supported -x direction
slab_x_max = edge_dist 
slab_w_x = slab_x_max - slab_x_min
slab_w_z = 600.0      # Sufficient width in z 
slab_h = 240.0        # Sufficient depth

# Borehole & Mortar
hole_r = 9.0          
hole_d = hef          
anchor_d = hef        

# Refinement Region
refine_r = 120.0      

# Steel Anchor
anchor_r = 8.0        
anchor_free_h = 16.0  

# Steel Plate
plate_w = 64.0        
plate_h = 16.0        
plate_cut_h = plate_h / 3.0

# Mesh Parameters
mesh_size_steel = 4.0
mesh_size_concrete_inner = 6.0
mesh_size_concrete_outer = 24.0

# Chalice Domain Parameters
y_bot = -hole_d * 1.0 - 4.0
y_top = 0
dy = y_top - y_bot  
R_bot = 3 * hole_r         
dR = refine_r * 1.2            


# --- GEOMETRY CREATION ---

# 1. Concrete Slab (Shifted unified block)
cubit.cmd(f"create brick x {slab_w_x} y {slab_h} z {slab_w_z}")
v_slab = cubit.get_last_id("volume")
slab_cen_x = (slab_x_max + slab_x_min) / 2.0
cubit.cmd(f"move volume {v_slab} x {slab_cen_x} y {-slab_h / 2.0} z 0")
cubit.cmd(f"volume {v_slab} name 'concrete_main'")

cubit.cmd(f"create cylinder height {hole_d} radius {hole_r}")
v_hole_tool = cubit.get_last_id("volume")
id_cyl_surf = cubit.get_last_id("surface") - 2
cubit.cmd(f"surface {id_cyl_surf} name 'surface_borehole'")

cubit.cmd(f"rotate volume {v_hole_tool} angle 90 about x")
cubit.cmd(f"move volume {v_hole_tool} y {-hole_d / 2.0}")

# Subtract the borehole tool
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

# 1. Extend the borehole profile down
cubit.cmd(f"webcut volume with name 'concrete_main' cylinder radius {hole_r} axis y")

# 2. Create the larger inner refined region
cubit.cmd(f"webcut volume with name 'concrete_*' cylinder radius {refine_r} axis y")

cubit.cmd(f"webcut volume with name 'steel_plate' plane yplane offset {plate_cut_h}")

# --- SYMMETRY AND DECOMPOSITION ---

# 1. Exploit Z-Symmetry: Webcut along Z plane and delete the POSITIVE Z half
cubit.cmd("webcut volume all with plane zplane offset 0")

vols = cubit.parse_cubit_list("volume", "all")
vols_to_delete = []
for v in vols:
    cent = cubit.get_center_point("volume", v)
    if cent[2] > 0.01:
        vols_to_delete.append(str(v))
        
if vols_to_delete:
    cubit.cmd(f"delete volume {' '.join(vols_to_delete)}")

# 2. Hex meshing decomposition
cubit.cmd("webcut volume all with plane xplane offset 0")


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


# --- MESH GENERATION ---
cubit.cmd(f"volume all size {mesh_size_steel}")

concrete_vols = cubit.parse_cubit_list("volume", "in grp_concrete")
inner_vols = []
outer_vols = []

for v in concrete_vols:
    bbox = cubit.get_bounding_box("volume", v)
    max_r = max(abs(bbox[0]), abs(bbox[1]), abs(bbox[6]), abs(bbox[7]))
    
    if max_r < refine_r + 0.1:
        inner_vols.append(str(v))
    else:
        outer_vols.append(str(v))

print(f"Identified {len(inner_vols)} inner concrete volumes and {len(outer_vols)} outer concrete volumes.")

if inner_vols:
    cubit.cmd(f"volume {' '.join(inner_vols)} size {mesh_size_concrete_inner}")
if outer_vols:
    cubit.cmd(f"volume {' '.join(outer_vols)} size {mesh_size_concrete_outer}")

# Special treatment for the height in the slab at the free edge boundary
cubit.cmd(f"curve all in volume in grp_concrete expand with x_coord = {slab_x_max} tolerance 0.01 and z_coord = 0 tolerance 0.01 size 2.0")

cubit.cmd("mesh volume all")


# ==========================================
# 4. CHALICE DOMAIN SELECTION
# ==========================================
all_hexes = cubit.parse_cubit_list("hex", "in grp_concrete expand")
chalice_hexes = []

for h in all_hexes:
    x, y, z = cubit.get_center_point("hex", h)
    
    if y_bot <= y <= y_top:
        radius_y = R_bot + dR * ((y - y_bot) / dy)**2
        
        if (x**2 + z**2) < (radius_y**2) and (x**2 + z**2) < refine_r**2:
            chalice_hexes.append(str(h))

# ==========================================
# 5. GROUPING AND REFINEMENT
# ==========================================
if chalice_hexes:
    print(f"Found {len(chalice_hexes)} hexes in the chalice domain. Grouping and refining...")
    cubit.cmd("create group 'chalice_domain'")
    
    chunk_size = 200
    for i in range(0, len(chalice_hexes), chunk_size):
        chunk = " ".join(chalice_hexes[i:i + chunk_size])
        cubit.cmd(f"group 'chalice_domain' add hex {chunk}")
    
    cubit.cmd("refine hex in chalice_domain depth 0")
    print("Refinement complete.")
else:
    print("No hexes found within the specified chalice domain parameters.")


# --- EXPORT BLOCKS ---
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


# --- BOUNDARY CONDITIONS (SIDESETS / NODESETS) ---
currentsideset_id = 1
currentnodeset_id = 1

# Concrete top
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'concrete_top'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with y_coord = 0")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'concrete_top'")
currentsideset_id += 1
currentnodeset_id += 1

# Concrete bottom
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'bottom'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with y_coord = {-slab_h}")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'bottom'")
currentsideset_id += 1
currentnodeset_id += 1

# Concrete left (-x)
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'left'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with x_coord = {slab_x_min}")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'left'")
currentsideset_id += 1
currentnodeset_id += 1

# NOTE: The positive X boundary condition ('right') has been intentionally omitted for the free edge.

# Concrete back (-z)
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'back'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with z_coord = {-slab_w_z/2.0}")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'back'")
currentsideset_id += 1
currentnodeset_id += 1

# Plate bottom
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'plate_bottom'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_steel expand with y_coord = 0")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'plate_bottom'")
currentsideset_id += 1
currentnodeset_id += 1

# Internal Contact / Interfaces
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

# Plate Loading
cubit.cmd(f"create nodeset {currentnodeset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'plate_left_loading'")
cubit.cmd(f"nodeset {currentnodeset_id} add node in grp_steel expand with y_coord = {plate_cut_h} tolerance 0.01 and x_coord = -{plate_w/2.0} tolerance 0.01")
currentnodeset_id += 1

# Z-Symmetry
cubit.cmd(f"create nodeset {currentnodeset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'z_symm'")
cubit.cmd(f"nodeset {currentnodeset_id} add node in volume all expand with z_coord = 0")
currentnodeset_id += 1

# Export
cubit.cmd(f'export abaqus "./steel.inp" block {anchor_bId} {mortar_bId} partial overwrite')
cubit.cmd(f'export abaqus "./concrete.inp" block {concrete_bId} partial overwrite')

# Quality metrics
cubit.cmd("quality volume all scaled jacobian global draw histogram draw mesh")
