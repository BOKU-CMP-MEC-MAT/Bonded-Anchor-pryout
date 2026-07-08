import cubit

# Clear any existing geometry
cubit.cmd("reset")

# --- PARAMETERS ---
# Concrete Slab
slab_w = 500.0        # Width (x and z)
slab_h = 160.0        # Total height (y)

# Borehole & Mortar
hole_r = 9.0          # Borehole radius
hole_d = 50.0         # Borehole depth
anchor_d = 50.0       # Depth of the anchor within the borehole (must be <= hole_d)

# Refinement Region
refine_r = 80.0       # Radius of the inner refined concrete region

# Steel Anchor
anchor_r = 8.0        # Anchor radius
anchor_free_h = 16.0  # Anchor height above the concrete slab

# Steel Plate
plate_w = 64.0        # Plate width (x and z)
plate_h = 16.0        # Plate thickness (y)
#webcut plate at y = plate_h/3.0
plate_cut_h = plate_h / 3.0

# Mesh Parameters
mesh_size_steel = 4.0
mesh_size_concrete_inner = 6.0
mesh_size_concrete_outer = 18.0


# Chalice Domain Parameters
y_bot = -hole_d * 1.0 - 4.0
y_top = 0
dy = y_top - y_bot  # 10.0
R_bot = 3 * hole_r         # Radius at the bottom of the chalice
dR = refine_r * 1.2            # Radius expansion amount at the top


# --- GEOMETRY CREATION ---

# 1. Concrete Slab (Full unified block)
cubit.cmd(f"create brick x {slab_w} y {slab_h} z {slab_w}")
v_slab = cubit.get_last_id("volume")
cubit.cmd(f"move volume {v_slab} y {-slab_h / 2.0}")
cubit.cmd(f"volume {v_slab} name 'concrete_main'")

cubit.cmd(f"create cylinder height {hole_d} radius {hole_r}")
v_hole_tool = cubit.get_last_id("volume")
id_cyl_surf = cubit.get_last_id("surface") - 2
cubit.cmd(f"surface {id_cyl_surf} name 'surface_borehole'")

cubit.cmd(f"rotate volume {v_hole_tool} angle 90 about x")
cubit.cmd(f"move volume {v_hole_tool} y {-hole_d / 2.0}")

# Subtract the borehole tool, leaving a blind hole in the unified slab
cubit.cmd(f"subtract volume {v_hole_tool} from volume {v_slab}")
v_slab = cubit.get_last_id("volume")
cubit.cmd(f"volume {v_slab} name 'concrete_main'")

# 2. Adhesive Mortar (Hollow Cylinder)
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

# 3. Steel Anchor (Solid Cylinder)
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

# 1. Extend the borehole profile down through the solid section of the unified concrete block
cubit.cmd(f"webcut volume with name 'concrete_main' cylinder radius {hole_r} axis y")

# 2. Create the larger inner refined region across all concrete blocks
cubit.cmd(f"webcut volume with name 'concrete_*' cylinder radius {refine_r} axis y")

cubit.cmd(f"webcut volume with name 'steel_plate' plane yplane offset {plate_cut_h}")

# --- SYMMETRY AND DECOMPOSITION ---

# 1. Exploit Z-Symmetry: Webcut along Z plane and delete the POSITIVE Z half to keep the other half
cubit.cmd("webcut volume all with plane zplane offset 0")

vols = cubit.parse_cubit_list("volume", "all")
vols_to_delete = []
for v in vols:
    cent = cubit.get_center_point("volume", v)
    if cent[2] > 0.01:  # Identify volumes on the positive Z side
        vols_to_delete.append(str(v))
        
if vols_to_delete:
    cubit.cmd(f"delete volume {' '.join(vols_to_delete)}")

# 2. Hex meshing decomposition: Webcut the remaining half-model with X-plane
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
# Apply default mesh size for steel/mortar components
cubit.cmd(f"volume all size {mesh_size_steel}")

# Sort concrete volumes into inner vs outer sets based on radial distance
concrete_vols = cubit.parse_cubit_list("volume", "in grp_concrete")
inner_vols = []
outer_vols = []

for v in concrete_vols:
    # A vector of coordinates describing the entity's bounding box. Ten (10) values will be returned in axis-min, axis-max, and axis-range order, repeated for x-axis, y-axis, and z-axis and ending with the total diagonal measure.
    bbox = cubit.get_bounding_box("volume", v)
    # Determine the maximum radial extent of this volume's bounding box
    max_r = max(abs(bbox[0]), abs(bbox[1]), abs(bbox[6]), abs(bbox[7]))
    
    # Add a small tolerance to account for floating point inaccuracies
    if max_r < refine_r + 0.1:
        inner_vols.append(str(v))
    else:
        outer_vols.append(str(v))

print(f"Identified {len(inner_vols)} inner concrete volumes and {len(outer_vols)} outer concrete volumes.")
print(f"Inner volumes: {', '.join(inner_vols)}")
print(f"Outer volumes: {', '.join(outer_vols)}")

# Apply the respective mesh sizes
if inner_vols:
    cubit.cmd(f"volume {' '.join(inner_vols)} size {mesh_size_concrete_inner}")
if outer_vols:
    cubit.cmd(f"volume {' '.join(outer_vols)} size {mesh_size_concrete_outer}")


#special treatment for the height in the slab.
# select the front right curves in the slab and set a size there to control the height of the elements in the slab:
cubit.cmd(f"curve all in volume in grp_concrete expand with x_coord = {slab_w/2.0} tolerance 0.01 and z_coord = 0 tolerance 0.01 size 2.0")

# Enforce pure hexahedral meshing
# cubit.cmd("volume all scheme sweep")
cubit.cmd("mesh volume all")





# ==========================================
# 4. CHALICE DOMAIN SELECTION
# ==========================================
# Fetch all hex IDs from the meshed concrete
all_hexes = cubit.parse_cubit_list("hex", "in grp_concrete expand")
chalice_hexes = []

for h in all_hexes:
    # Get the (x, y, z) centroid of the current hex
    x, y, z = cubit.get_center_point("hex", h)
    
    if y_bot <= y <= y_top:
        # Calculate the parabolic radius at this specific Y height
        radius_y = R_bot + dR * ((y - y_bot) / dy)**2
        
        # Check if the hex falls inside the chalice radius
        if (x**2 + z**2) < (radius_y**2) and (x**2 + z**2) < refine_r**2:
            chalice_hexes.append(str(h))

# ==========================================
# 5. GROUPING AND REFINEMENT
# ==========================================
if chalice_hexes:
    print(f"Found {len(chalice_hexes)} hexes in the chalice domain. Grouping and refining...")
    
    # Create an empty group
    cubit.cmd("create group 'chalice_domain'")
    
    # Chunk the list to avoid exceeding Cubit's maximum command line character limit
    chunk_size = 200
    for i in range(0, len(chalice_hexes), chunk_size):
        chunk = " ".join(chalice_hexes[i:i + chunk_size])
        cubit.cmd(f"group 'chalice_domain' add hex {chunk}")
    

    # Apply the hex refinement to the group
    cubit.cmd("refine hex in chalice_domain depth 0")

    
    print("Refinement complete.")
else:
    print("No hexes found within the specified chalice domain parameters.")


#create blocks
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


#make concrete quadratic shape functions:
cubit.cmd(f"block {concrete_bId} element type hex20")

#create sidesets
currentsideset_id = 1
currentnodeset_id = 1

# Create sideset for concrete top:
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'concrete_top'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with y_coord = 0")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'concrete_top'")
currentsideset_id += 1
currentnodeset_id += 1

## Create sideset for concrete bottom:
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'bottom'")
cubit.cmd(f"sideset {currentnodeset_id} add surface in grp_concrete expand with y_coord = {-slab_h}")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'bottom'")
currentsideset_id += 1
currentnodeset_id += 1

# Create sideset for concrtee x_min:
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'left'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with x_coord = {-slab_w/2.0}")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'left'")
currentsideset_id += 1
currentnodeset_id += 1

# Create sideset for concrete x_max:
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'right'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with x_coord = {slab_w/2.0}")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'right'")
currentsideset_id += 1
currentnodeset_id += 1

# Create sideset for concrete z_min:
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'back'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with z_coord = {-slab_w/2.0}")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'back'")
currentsideset_id += 1
currentnodeset_id += 1

# Create sideset for plate bottom:
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'plate_bottom'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_steel expand with y_coord = 0")
cubit.cmd(f"nodeset {currentnodeset_id} add node in sideset {currentsideset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'plate_bottom'")
currentsideset_id += 1
currentnodeset_id += 1

# create side set for borehole inner surface in concrete:
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'concrete_to_mortar'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_concrete expand with name 'surface_borehole*'")
currentsideset_id += 1

# create side set for mortar inner:
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'mortar_to_anchor'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_mortar expand with name 'surface_mortar_inner*'")
currentsideset_id += 1

# create side set for mortar inner:
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'anchor_to_mortar'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_steel expand with name 'surface_anchor_outer*'")
currentsideset_id += 1

# create side set for mortar outer:
cubit.cmd(f"create sideset {currentsideset_id}")
cubit.cmd(f"sideset {currentsideset_id} name 'mortar_to_concrete'")
cubit.cmd(f"sideset {currentsideset_id} add surface in grp_mortar expand with name 'surface_mortar_outer*'")
currentsideset_id += 1


#Create a node set for application of the load at the plate where we placed the webcut:
cubit.cmd(f"create nodeset {currentnodeset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'plate_left_loading'")
cubit.cmd(f"nodeset {currentnodeset_id} add node in grp_steel expand with y_coord = {plate_cut_h} tolerance 0.01 and x_coord = -{plate_w/2.0} tolerance 0.01")
currentnodeset_id += 1



# Create a z-sym nodeset add z = 0 for all nodes in all volumes:
cubit.cmd(f"create nodeset {currentnodeset_id}")
cubit.cmd(f"nodeset {currentnodeset_id} name 'z_symm'")
cubit.cmd(f"nodeset {currentnodeset_id} add node in volume all expand with z_coord = 0")
currentnodeset_id += 1


cubit.cmd(f'export abaqus "./steel.inp" block {anchor_bId} {mortar_bId} partial overwrite')
cubit.cmd(f'export abaqus "./concrete.inp" block {concrete_bId} partial overwrite')

############################################################################################# quality metrics
cubit.cmd("quality volume all scaled jacobian global draw histogram draw mesh")
