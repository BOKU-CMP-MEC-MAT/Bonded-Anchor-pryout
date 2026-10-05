"""Cubit generator: Edgebreakout set-up (drawings sheets 3-6), half model, symmetry plane z = 0.

Run (inside mesh/):   cubit -batch -nographics -noecho -input generate_edgebreakout_setup.py
then                  python3 modifyMesh.py        (element types, concrete UEL copy)

Axes: x = pull direction, towards the free edge (+x); y = vertical, top of concrete at y = 0;
z = across the slab, z = 0 is the anchor plane (the +z half is deleted). All lengths in mm.

NOTE: Cubit's -input driver feeds this file one physical line at a time, so every dict / list /
call must stay on ONE line (no multi-line brackets). Function and loop bodies are fine.
"""
import cubit
import math

cubit.cmd("reset")

# ================= PARAMETERS =================
c = 150.0                  # edge distance anchor axis -> free edge (parameter of the model)
back = 350.0               # concrete behind the anchor, Lc = c + 350
slab_x = c + back          # modelled concrete length (pull direction)
slab_h = 300.0             # concrete thickness (paper: slabs 100 x 250 x 30 cm)
half_w = 550.0             # half width: concrete extended to the timber width (1100)

# borehole / mortar / anchor (paper: M16 threaded bar, hef = 100, 1 mm mortar)
hole_r = 9.0
hole_d = 100.0
anchor_d = 100.0           # embedment hef
anchor_r = 8.0
anchor_top = 46.0          # anchor protrusion above the concrete (web 20 + washer 6 + nut 14 + 6 thread)

# sleeve, washer, nut (stack on the C web, all above y = 0)
sleeve_ro, sleeve_ri, sleeve_h = 25.0, anchor_r, 20.0
washer_ro, washer_ri, washer_h = 28.0, 9.0, 6.0
nut_R, nut_h = 24.0 / (2.0 * math.cos(math.radians(30.0))), 14.0

# C-section (half, z <= 0): web 20, flange 20, 100 wide, 80 high, 110 long, web hole = sleeve
c_len, c_w, c_hgt, c_t = 110.0, 100.0, 80.0, 20.0
c_hole_r = sleeve_ro

# L-angle beam (the one at z < 0): 100 x 100 x 10, web at z = -(c_w/2) - 10 ... -(c_w/2)
l_leg, l_t, l_hgt = 100.0, 10.0, 100.0
l_back = back              # L ends at the back face of the region
l_front = c + 100.0        # load end, 100 beyond the free edge
l_x0, l_x1 = c - slab_x, l_front

# support plate (50 x 50 x 10, top surface, at the free edge, 3c from the symmetry plane)
sup_w, sup_t = 50.0, 10.0
sup_z = 3.0 * c

# timber beam under the support (200 wide x 100 high, 200 side on the concrete)
tim_w, tim_h = 200.0, 100.0

# mesh sizes
mesh_size_steel = 4.0
mesh_size_c = 5.0
mesh_size_l = 5.0
mesh_size_l_x = 10.0
mesh_size_plate = 5.0
mesh_size_timber = 25.0
mesh_size_concrete_outer = 17.0

# breakout refinement (hollow rectangular pyramid), as in the SS-160 generator
vertical_angle = 35.0
lateral_angle = 60.0
band_x = 50.0
band_y = 15.0
band_z = 20.0
corner_r = 60.0
y_flat_limit = -170.0
bottom_angle = 5.0


# ================= HELPERS =================
def new_id():
    return cubit.get_last_id("volume")


def ring(ro, ri, y0, y1, name):
    """hollow (or solid if ri = 0) cylinder with axis y between y0 and y1"""
    h = y1 - y0
    cubit.cmd(f"create cylinder height {h} radius {ro}")
    v = new_id()
    cubit.cmd(f"rotate volume {v} angle 90 about x")
    cubit.cmd(f"move volume {v} y {(y0 + y1) / 2.0}")
    if ri > 0.0:
        cubit.cmd(f"create cylinder height {h + 2.0} radius {ri}")
        vh = new_id()
        cubit.cmd(f"rotate volume {vh} angle 90 about x")
        cubit.cmd(f"move volume {vh} y {(y0 + y1) / 2.0}")
        cubit.cmd(f"subtract volume {vh} from volume {v}")
        v = new_id()
    cubit.cmd(f"volume {v} name '{name}'")
    return v


def brick(x0, x1, y0, y1, z0, z1, name):
    cubit.cmd(f"create brick x {x1 - x0} y {y1 - y0} z {z1 - z0}")
    v = new_id()
    cubit.cmd(f"move volume {v} x {(x0 + x1) / 2.0} y {(y0 + y1) / 2.0} z {(z0 + z1) / 2.0}")
    cubit.cmd(f"volume {v} name '{name}'")
    return v


def name_surfaces(v, rules):
    """rules: list of (role, kind, value, tol). kind 'y','z','x' = planar face at that coordinate,
    'cyl' = cylindrical face with the given radius (bounding box x and z extent = 2 r), 'cylx' = same but x extent only (half cylinders)"""
    n = 0
    for s in cubit.get_relatives("volume", v, "surface"):
        bb = cubit.get_bounding_box("surface", s)
        xr, yr, zr = bb[2], bb[5], bb[8]
        for role, kind, val, tol in rules:
            hit = False
            if kind == "y" and yr < 1e-6 and abs(bb[3] - val) < tol:
                hit = True
            if kind == "z" and zr < 1e-6 and abs(bb[6] - val) < tol:
                hit = True
            if kind == "x" and xr < 1e-6 and abs(bb[0] - val) < tol:
                hit = True
            if kind == "cyl" and yr > 1e-6 and abs(xr - 2.0 * val) < 0.05 and abs(zr - 2.0 * val) < 0.05:
                hit = True
            if kind == "cylx" and yr > 1e-6 and abs(xr - 2.0 * val) < 0.05:
                hit = True
            if hit:
                n += 1
                cubit.cmd(f"surface {s} name '{role}_{v}_{n}'")


# ================= CONCRETE =================
cubit.cmd(f"create brick x {slab_x} y {slab_h} z {2.0 * half_w}")
v_slab = new_id()
cubit.cmd(f"move volume {v_slab} x {c - slab_x / 2.0} y {-slab_h / 2.0}")
cubit.cmd(f"volume {v_slab} name 'concrete_main'")

cubit.cmd(f"create cylinder height {hole_d} radius {hole_r}")
v_hole_tool = new_id()
id_cyl_surf = cubit.get_last_id("surface") - 2
cubit.cmd(f"surface {id_cyl_surf} name 'surface_borehole'")
cubit.cmd(f"rotate volume {v_hole_tool} angle 90 about x")
cubit.cmd(f"move volume {v_hole_tool} y {-hole_d / 2.0}")
cubit.cmd(f"subtract volume {v_hole_tool} from volume {v_slab}")
v_slab = new_id()
cubit.cmd(f"volume {v_slab} name 'concrete_main'")

# ================= MORTAR AND ANCHOR (as in the SS-160 generator) =================
cubit.cmd(f"create cylinder height {anchor_d} radius {hole_r}")
v_mortar_outer = new_id()
id_s = cubit.get_last_id("surface") - 2
cubit.cmd(f"surface {id_s} name 'surface_mortar_outer'")
cubit.cmd(f"rotate volume {v_mortar_outer} angle 90 about x")
cubit.cmd(f"move volume {v_mortar_outer} y {-anchor_d / 2.0}")
cubit.cmd(f"create cylinder height {anchor_d} radius {anchor_r}")
v_mortar_inner = new_id()
id_s = cubit.get_last_id("surface") - 2
cubit.cmd(f"surface {id_s} name 'surface_mortar_inner'")
cubit.cmd(f"rotate volume {v_mortar_inner} angle 90 about x")
cubit.cmd(f"move volume {v_mortar_inner} y {-anchor_d / 2.0}")
cubit.cmd(f"subtract volume {v_mortar_inner} from volume {v_mortar_outer}")
v_mortar = new_id()
cubit.cmd(f"volume {v_mortar} name 'mortar'")

anchor_len = anchor_d + anchor_top
cubit.cmd(f"create cylinder height {anchor_len} radius {anchor_r}")
v_anchor = new_id()
id_s = cubit.get_last_id("surface") - 2
cubit.cmd(f"surface {id_s} name 'surface_anchor_outer'")
cubit.cmd(f"rotate volume {v_anchor} angle 90 about x")
cubit.cmd(f"move volume {v_anchor} y {(-anchor_d + anchor_top) / 2.0}")
cubit.cmd(f"volume {v_anchor} name 'anchor'")

# ================= SLEEVE, WASHER, NUT =================
y_w0 = sleeve_h
y_n0 = y_w0 + washer_h
v_sleeve = ring(sleeve_ro, sleeve_ri, 0.0, sleeve_h, "sleeve")
name_surfaces(v_sleeve, [("sl_outer", "cyl", sleeve_ro, 0.05), ("sl_bore", "cyl", sleeve_ri, 0.05), ("sl_top", "y", sleeve_h, 1e-4), ("sl_bottom", "y", 0.0, 1e-4)])
v_washer = ring(washer_ro, washer_ri, y_w0, y_w0 + washer_h, "washer")
name_surfaces(v_washer, [("wa_top", "y", y_w0 + washer_h, 1e-4), ("wa_bottom", "y", y_w0, 1e-4)])
cubit.cmd(f"create prism height {nut_h} sides 6 radius {nut_R}")
v_nut = new_id()
cubit.cmd(f"rotate volume {v_nut} angle 90 about x")
cubit.cmd(f"rotate volume {v_nut} angle 90 about y")
cubit.cmd(f"move volume {v_nut} y {y_n0 + nut_h / 2.0}")
cubit.cmd(f"create cylinder height {nut_h + 2.0} radius {anchor_r}")
v_nb = new_id()
cubit.cmd(f"rotate volume {v_nb} angle 90 about x")
cubit.cmd(f"move volume {v_nb} y {y_n0 + nut_h / 2.0}")
cubit.cmd(f"subtract volume {v_nb} from volume {v_nut}")
v_nut = new_id()
cubit.cmd(f"volume {v_nut} name 'nut'")
name_surfaces(v_nut, [("nu_bore", "cyl", anchor_r, 0.05), ("nu_top", "y", y_n0 + nut_h, 1e-4), ("nu_bottom", "y", y_n0, 1e-4)])

# ================= C-SECTION (half): web layer with the hole + upper flange =================
cx0, cx1 = -c_len / 2.0, c_len / 2.0
v_cweb = brick(cx0, cx1, 0.0, c_t, -c_w / 2.0, 0.0, "csection_web")
cubit.cmd(f"create cylinder height {c_t + 2.0} radius {c_hole_r}")
v_ch = new_id()
cubit.cmd(f"rotate volume {v_ch} angle 90 about x")
cubit.cmd(f"move volume {v_ch} y {c_t / 2.0}")
cubit.cmd(f"subtract volume {v_ch} from volume {v_cweb}")
v_cweb = new_id()
cubit.cmd(f"volume {v_cweb} name 'csection_web'")
name_surfaces(v_cweb, [("c_hole", "cylx", c_hole_r, 0.05), ("c_bottom", "y", 0.0, 1e-4), ("c_webtop", "y", c_t, 1e-4), ("c_fout", "z", -c_w / 2.0, 1e-4)])
v_cfl = brick(cx0, cx1, c_t, c_hgt, -c_w / 2.0, -c_w / 2.0 + c_t, "csection_flange")
name_surfaces(v_cfl, [("c_fout", "z", -c_w / 2.0, 1e-4)])

# ================= L-ANGLE (the beam at z < 0) =================
v_lweb = brick(l_x0, l_x1, 0.0, l_hgt, -c_w / 2.0 - l_t, -c_w / 2.0, "lbeam_web")
name_surfaces(v_lweb, [("l_win", "z", -c_w / 2.0, 1e-4), ("l_bottom", "y", 0.0, 1e-4), ("l_end", "x", l_x1, 1e-4)])
v_lleg = brick(l_x0, l_x1, 0.0, l_t, -c_w / 2.0 - l_leg, -c_w / 2.0 - l_t, "lbeam_leg")
name_surfaces(v_lleg, [("l_bottom", "y", 0.0, 1e-4), ("l_end", "x", l_x1, 1e-4)])

# ================= SUPPORT PLATE AND TIMBER =================
v_plate = brick(c - sup_w, c, 0.0, sup_t, -sup_z - sup_w / 2.0, -sup_z + sup_w / 2.0, "support_plate")
name_surfaces(v_plate, [("p_bottom", "y", 0.0, 1e-4)])
# vertical part of the support: 10 thick plate against the free-edge face, same 50 x 50 footprint
v_hplate = brick(c, c + sup_t, -sup_w, 0.0, -sup_z - sup_w / 2.0, -sup_z + sup_w / 2.0, "support_hplate")
name_surfaces(v_hplate, [("hp_face", "x", c, 1e-4)])
v_tim = brick(c - slab_x, c, -slab_h - tim_h, -slab_h, -sup_z - tim_w / 2.0, -sup_z + tim_w / 2.0, "timber")
name_surfaces(v_tim, [("t_top", "y", -slab_h, 1e-4), ("t_bottom", "y", -slab_h - tim_h, 1e-4)])

# ================= DECOMPOSITION OF THE CONCRETE =================
cubit.cmd(f"webcut volume with name 'concrete_main' cylinder radius {hole_r} axis y")
# strips under the 50 mm support plate (horizontal support patch on the free edge face)
cubit.cmd(f"webcut volume with name 'concrete_*' plane zplane offset {-sup_z - sup_w / 2.0}")
cubit.cmd(f"webcut volume with name 'concrete_*' plane zplane offset {-sup_z + sup_w / 2.0}")
cubit.cmd(f"webcut volume with name 'concrete_*' plane yplane offset {-sup_w}")

# C web: split at x = 0 so that every piece has a single quarter hole (sweepable)
cubit.cmd(f"webcut volume with name 'csection_web' plane xplane offset 0")

# ================= SYMMETRY: keep z <= 0 =================
cubit.cmd("webcut volume all with plane zplane offset 0")
vols = cubit.parse_cubit_list("volume", "all")
vols_to_delete = []
for v in vols:
    cent = cubit.get_center_point("volume", v)
    if cent[2] > 0.01:
        vols_to_delete.append(str(v))
if vols_to_delete:
    cubit.cmd(f"delete volume {' '.join(vols_to_delete)}")

# ================= GROUPS, IMPRINT, MERGE =================
cubit.cmd("group 'grp_concrete' add volume with name 'concrete_*'")
cubit.cmd("group 'grp_mortar' add volume with name 'mortar*'")
cubit.cmd("group 'grp_anchor' add volume with name 'anchor*'")
cubit.cmd("group 'grp_sleeve' add volume with name 'sleeve*'")
cubit.cmd("group 'grp_washer' add volume with name 'washer*'")
cubit.cmd("group 'grp_nut' add volume with name 'nut*'")
cubit.cmd("group 'grp_csection' add volume with name 'csection_*'")
cubit.cmd("group 'grp_lbeam' add volume with name 'lbeam_*'")
cubit.cmd("group 'grp_plate' add volume with name 'support_plate*'")
cubit.cmd("group 'grp_hplate' add volume with name 'support_hplate*'")
cubit.cmd("group 'grp_timber' add volume with name 'timber*'")

# only parts that form ONE body are imprinted/merged; contacts and ties stay separate bodies
cubit.cmd("imprint volume in grp_concrete")
cubit.cmd("merge volume in grp_concrete")
cubit.cmd("merge volume in grp_mortar")
cubit.cmd("imprint volume in grp_csection")
cubit.cmd("merge volume in grp_csection")
cubit.cmd("imprint volume in grp_lbeam")
cubit.cmd("merge volume in grp_lbeam")

# ================= MESH SIZES =================
cubit.cmd(f"volume in grp_concrete size {mesh_size_concrete_outer}")
cubit.cmd(f"volume in grp_mortar size {mesh_size_steel}")
cubit.cmd(f"volume in grp_anchor size {mesh_size_steel}")
cubit.cmd(f"volume in grp_sleeve size {mesh_size_steel}")
cubit.cmd(f"volume in grp_washer size {mesh_size_steel}")
cubit.cmd(f"volume in grp_nut size {mesh_size_steel}")
cubit.cmd(f"volume in grp_csection size {mesh_size_c}")
cubit.cmd(f"volume in grp_lbeam size {mesh_size_l}")
cubit.cmd(f"curve in volume in grp_lbeam with length > 400 interval {int(round((l_x1 - l_x0) / mesh_size_l_x))}")
cubit.cmd(f"volume in grp_plate size {mesh_size_plate}")
cubit.cmd(f"volume in grp_hplate size {mesh_size_plate}")
cubit.cmd(f"volume in grp_timber size {mesh_size_timber}")

# ================= MESH =================
for g in ["grp_concrete", "grp_mortar", "grp_anchor", "grp_sleeve", "grp_washer", "grp_nut", "grp_csection", "grp_lbeam", "grp_plate", "grp_hplate", "grp_timber"]:
    cubit.cmd(f"mesh volume in {g}")
    ids = cubit.parse_cubit_list("volume", f"in {g}")
    unmeshed = [str(v) for v in ids if cubit.get_hex_count_in_volume(v) == 0] if hasattr(cubit, "get_hex_count_in_volume") else []
    print(f"MESHED {g}: volumes {ids} unmeshed {unmeshed}")

# ================= ELEMENT-LEVEL REFINEMENT (as in the SS-160 generator) =================
all_hexes = cubit.parse_cubit_list("hex", "in grp_concrete expand")
print(f"CONCRETE HEXES BEFORE REFINEMENT: {len(all_hexes)}")
breakout_hexes = []
x_start = -hole_r - 15.0
z_start = -hole_r - 10.0
y_start = -anchor_d - 20.0
x_angle_start = 1.8 * hole_r
vertical_tan = math.tan(math.radians(vertical_angle))
lateral_tan = math.tan(math.radians(lateral_angle))
bottom_tan = math.tan(math.radians(bottom_angle))
tol = mesh_size_concrete_outer / 2.0 + 1.0
support_inner_z = -(sup_z - sup_w / 2.0) + 1.0
for h in all_hexes:
    x, y, z = cubit.get_center_point("hex", h)
    if x < x_start or x > c + tol:
        continue
    if z < support_inner_z + tol:
        continue
    dx_z = max(0, x - x_start)
    dx_y = max(0, x - x_angle_start)
    y_lim_raw = y_start - dx_y * vertical_tan
    z_lim_raw = z_start - dx_z * lateral_tan
    y_floor = y_flat_limit - z * bottom_tan
    y_lim = max(y_lim_raw, y_floor)
    z_lim = max(z_lim_raw, support_inner_z)
    y_lim_eff = y_lim - tol
    z_lim_eff = z_lim - tol
    in_main = False
    if y >= y_lim_eff and z >= z_lim_eff:
        y_center = y_lim_eff + corner_r
        z_center = z_lim_eff + corner_r
        if y < y_center and z < z_center:
            if (y - y_center) ** 2 + (z - z_center) ** 2 <= corner_r ** 2:
                in_main = True
        else:
            in_main = True
    in_core = False
    if x >= x_start + band_x:
        y_in = y_lim + band_y + tol
        z_in = z_lim + band_z + tol
        if y_in < 0.1 and z_in < 0.1:
            if y >= y_in and z >= z_in:
                inner_r = max(0.0, corner_r - min(band_y, band_z))
                if inner_r > 0:
                    y_in_center = y_in + inner_r
                    z_in_center = z_in + inner_r
                    if y < y_in_center and z < z_in_center:
                        if (y - y_in_center) ** 2 + (z - z_in_center) ** 2 <= inner_r ** 2:
                            in_core = True
                    else:
                        in_core = True
                else:
                    in_core = True
    if in_main and not in_core:
        breakout_hexes.append(str(h))

if breakout_hexes:
    print(f"Found {len(breakout_hexes)} hexes in the hollow breakout band. Grouping and refining...")
    cubit.cmd("create group 'breakout_domain'")
    chunk_size = 200
    for i in range(0, len(breakout_hexes), chunk_size):
        chunk = " ".join(breakout_hexes[i:i + chunk_size])
        cubit.cmd(f"group 'breakout_domain' add hex {chunk}")
    cubit.cmd("create group 'adjacent_hexes'")
    cubit.cmd("group 'adjacent_hexes' add hex in face in hex in breakout_domain")
    cubit.cmd("group 'breakout_domain' add hex in adjacent_hexes")
    cubit.cmd("refine hex in breakout_domain depth 0 numsplit 1 smooth")
    print("Refinement complete.")
else:
    print("No hexes found within the specified breakout domain parameters.")

print(f"CONCRETE HEXES AFTER REFINEMENT: {len(cubit.parse_cubit_list('hex', 'in grp_concrete expand'))}")
# ================= BLOCKS =================
blocks = [("anchor", "grp_anchor"), ("mortar", "grp_mortar"), ("sleeve", "grp_sleeve"), ("washer", "grp_washer"), ("nut", "grp_nut"), ("csection", "grp_csection"), ("lbeam", "grp_lbeam"), ("plate", "grp_plate"), ("hplate", "grp_hplate"), ("timber", "grp_timber")]
bid = 0
steel_blocks = []
for bname, grp in blocks:
    bid += 1
    cubit.cmd(f"create block {bid}")
    cubit.cmd(f"block {bid} name '{bname}'")
    cubit.cmd(f"block {bid} add volume in {grp}")
    steel_blocks.append(str(bid))
bid += 1
concrete_bId = bid
cubit.cmd(f"create block {concrete_bId}")
cubit.cmd(f"block {concrete_bId} name 'dummy'")
cubit.cmd(f"block {concrete_bId} add volume in grp_concrete")
cubit.cmd(f"block {concrete_bId} element type hex20")

# ================= SIDESETS AND NODESETS =================
ss = [0]
ns = [0]


def sideset(name, cmd_tail, with_nodeset=False):
    ss[0] += 1
    cubit.cmd(f"create sideset {ss[0]}")
    cubit.cmd(f"sideset {ss[0]} name '{name}'")
    cubit.cmd(f"sideset {ss[0]} add {cmd_tail}")
    if with_nodeset:
        ns[0] += 1
        cubit.cmd(f"nodeset {ns[0]} add node in sideset {ss[0]}")
        cubit.cmd(f"nodeset {ns[0]} name '{name}'")


def nodeset(name, cmd_tail):
    ns[0] += 1
    cubit.cmd(f"create nodeset {ns[0]}")
    cubit.cmd(f"nodeset {ns[0]} name '{name}'")
    cubit.cmd(f"nodeset {ns[0]} add {cmd_tail}")


# concrete
sideset("concrete_top", "surface in grp_concrete expand with y_coord = 0")
sideset("concrete_bottom", f"surface in grp_concrete expand with y_coord = {-slab_h}")
sideset("back_support", f"surface in grp_concrete expand with x_coord = {c - slab_x}", True)
all_front = cubit.parse_cubit_list("surface", f"in grp_concrete expand with x_coord = {c} tolerance 0.01")
patch = []
free_edge = []
for s in all_front:
    cz = cubit.get_center_point("surface", s)
    if cz[2] > (-sup_z - sup_w / 2.0 - 0.01) and cz[2] < (-sup_z + sup_w / 2.0 + 0.01) and cz[1] > (-sup_w - 0.01):
        patch.append(str(s))
    else:
        free_edge.append(str(s))
if patch:
    sideset("front_support", f"surface {' '.join(patch)}", True)
if free_edge:
    sideset("free_edge", f"surface {' '.join(free_edge)}", True)
sideset("concrete_to_mortar", "surface in grp_concrete expand with name 'surface_borehole*'")

# mortar / anchor interfaces (tied)
sideset("mortar_to_anchor", "surface in grp_mortar expand with name 'surface_mortar_inner*'")
sideset("anchor_to_mortar", "surface in grp_anchor expand with name 'surface_anchor_outer*'")
sideset("mortar_to_concrete", "surface in grp_mortar expand with name 'surface_mortar_outer*'")

# sleeve: tied to the anchor, contact with the C web hole and the concrete top
sideset("sleeve_bore", "surface in grp_sleeve expand with name 'sl_bore*'")
sideset("sleeve_outer", "surface in grp_sleeve expand with name 'sl_outer*'")
sideset("sleeve_bottom", "surface in grp_sleeve expand with name 'sl_bottom*'")
sideset("sleeve_top", "surface in grp_sleeve expand with name 'sl_top*'")
# washer: tied to the C web top and the sleeve top; nut tied to the washer and the anchor
sideset("washer_bottom", "surface in grp_washer expand with name 'wa_bottom*'")
sideset("washer_top", "surface in grp_washer expand with name 'wa_top*'")
sideset("nut_bottom", "surface in grp_nut expand with name 'nu_bottom*'")
sideset("nut_bore", "surface in grp_nut expand with name 'nu_bore*'")
# C-section
sideset("c_hole", "surface in grp_csection expand with name 'c_hole*'")
sideset("c_bottom", "surface in grp_csection expand with name 'c_bottom*'")
sideset("c_webtop", "surface in grp_csection expand with name 'c_webtop*'")
sideset("c_flange_outer", "surface in grp_csection expand with name 'c_fout*'")
# L-angle
sideset("l_web_inner", "surface in grp_lbeam expand with name 'l_win*'")
sideset("l_bottom", "surface in grp_lbeam expand with name 'l_bottom*'")
# support plate and timber
sideset("plate_bottom", "surface in grp_plate expand with name 'p_bottom*'")
sideset("hplate_face", "surface in grp_hplate expand with name 'hp_face*'")
sideset("timber_top", "surface in grp_timber expand with name 't_top*'")

# nodesets for boundary conditions and loading
nodeset("load_end", f"node in grp_lbeam expand with x_coord = {l_x1} tolerance 0.01")
nodeset("l_back", f"node in grp_lbeam expand with x_coord = {l_x0} tolerance 0.01")
nodeset("plate_all", "node in grp_plate expand")
nodeset("hplate_all", "node in grp_hplate expand")
nodeset("timber_bottom", f"node in grp_timber expand with y_coord = {-slab_h - tim_h} tolerance 0.01")
nodeset("z_symm", "node in volume all expand with z_coord = 0 tolerance 0.001")

# ================= EXPORT =================
cubit.cmd(f'export abaqus "./steel.inp" block {" ".join(steel_blocks)} partial overwrite')
cubit.cmd(f'export abaqus "./concrete.inp" block {concrete_bId} partial overwrite')

# ================= QUALITY CHECK =================
cubit.cmd("quality volume all scaled jacobian global")
for g in ["grp_concrete", "grp_mortar", "grp_anchor", "grp_sleeve", "grp_washer", "grp_nut", "grp_csection", "grp_lbeam", "grp_plate", "grp_hplate", "grp_timber"]:
    print(f"QUALITY {g}")
    cubit.cmd(f"quality volume in {g} scaled jacobian global")
cubit.cmd("quality volume in grp_concrete scaled jacobian low 0.2")
print("EDGEBREAKOUT SETUP MESH DONE")
