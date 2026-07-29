"""
STANDALONE CUBIT GENERATOR -- M20, hef = 80 mm, OPTION F ONLY.

Contains the complete fixed model. It does not import or execute
Pryout_bondedAnchor.py or make_decks.py, accepts no parameters, and creates no
alternative load-introduction sets.

Run:
    cubit -nographics -batch -nojournal -input Pryout_elastic_bareanchor_section.py

It constructs and meshes the half model and writes into the parent case directory:
    ../

Fixed: M20; hef=80 mm; C3D8I; load at tPlate/3=6.6666667 mm through
option F's complete rigid cross-section; no plate, washer, or nut.
"""

import math
import os
import re
import shutil

import cubit

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
ROOT = os.path.dirname(HERE)
CASE_NAME = "Pryout_elastic_M20_hef80_bareanchor_section"
os.chdir(HERE)

# =============================================================================
# PARAMETERS
# =============================================================================


dAnchor = 20.0                            # fixed M20
hef = 80.0                                # fixed embedment depth

# --- concrete specimen (physical size; not a function of the anchor) ---------
slab_w = 500.0        # width, x and z
# Depth = 3 x hef, so the clamped bottom boundary cannot influence the breakout
# cone. At hef = 80 the previous 160 mm was only 2 x hef.
slab_h = 240.0        # total height, y

# --- borehole and mortar -----------------------------------------------------
anchor_r = dAnchor / 2.0
mortar_thickness = 1.0
hole_r = anchor_r + mortar_thickness         # borehole radius
hole_d = hef                                 # borehole depth
anchor_d = hef                               # bonded length

# Fixed load plane and retained free shaft length from the M20 fixture geometry.
# The fixture itself is absent.
tPlate = 20.0
plate_cut_h = 6.666666666666667
anchor_free_h = 41.8

# --- mesh sizes --------------------------------------------------------------
mesh_size_steel = 4.0
mesh_size_fastener = dAnchor / 8.0
# The mortar is the cohesive bond layer, so it is not left at the coarse steel
# size: this matches the journal's ~2 mm (24 intervals over the embedment).
mesh_size_mortar = dAnchor / 8.0
# Concrete sizes retuned when the model moved to M20 / hef = 80 / slab 240. At the
# previous 6.0 / 2.0 the model came out at 74,849 hexes, which broke TWO things:
#   1. Coreform Cubit Learn Edition refuses to export a block over 50k elements,
#      so concrete.inp was never written.
#   2. `refine hex ... depth 0` failed with "Refinement process resulted in an
#      invalid surface mesh", so the chalice refinement silently did nothing.
# 9.0 / 3.0 gives 36,908 concrete elements, exports cleanly, and the refinement
# succeeds. These two numbers are the levers if a full Cubit licence removes the cap.
mesh_size_concrete_inner = 9.0
mesh_size_concrete_outer = 18.0
mesh_size_slab_vertical = 3.0     # sizes the slab's vertical edge; ~4 mm layers
refine_r = slab_h / 2.0           # radius of the inner, finely meshed region

# --- chalice refinement envelope --------------------------------------------
# R(y) = R_bot + dR * ((y - y_bot)/dy)^2 , capped at refine_r
y_bot = -hole_d - 4.0
y_top = 0.0
dy = y_top - y_bot
R_bot = 3.0 * hole_r
dR = 1.2 * refine_r

TOL = 1e-3

# Half-width of the coordinate window that catches the load plane. plate_cut_h =
# tPlate/3 is not exactly representable in decimal, and the shaft node spacing there
# is of order 1 mm, so +-0.3 catches exactly one node plane -- never two, never none.
# The webcut below is what guarantees a node plane is there at all.
LOAD_PLANE_TOL = 0.3

# --- element formulation for the anchor ---------------------------------------
# THE ANCHOR MUST NOT BE C3D8R, which is what Cubit exports for a hex8 block by
# default and what every earlier version of this model used. Reduced integration
# carries hourglass modes that the stiffness cannot resist; they are controlled by an
# artificial stabilisation and can produce spurious displacement and stress
# oscillation in a bending shaft. Two further consequences matter here:
#   - a single-integration-point brick cannot represent the linear stress variation
#     through the shaft's own bending, so S is piecewise constant and noisy;
#   - the hourglass stabilisation forces are NOT included in NFORC, so nodal-force
#     post-processing of the loaded region silently loses part of the load path.
#
# C3D8I (incompatible modes) is the replacement. It has 8 nodes like C3D8R, so the
# mesh and its node numbering are untouched; it has NO hourglass modes and needs no
# stabilisation; and its incompatible modes make it bend correctly without the shear
# locking that fully integrated C3D8 would suffer -- which matters because this shaft
# IS a bending member. The extra internal degrees of freedom are eliminated at the
# element level, so on a part of a few thousand nodes the cost is negligible.
ANCHOR_ELEM = "C3D8I"                     # fixed
ANCHOR_ORDER = "hex8"

print("=" * 70)
print("STANDALONE M20 hef80 BARE ANCHOR, OPTION F RIGID SECTION")
print("  borehole r=%g depth=%g | NO plate, NO washer, NO nut" % (hole_r, hole_d))
print("  shaft protrusion %g | load plane y = %g (= tPlate/3)" % (anchor_free_h, plate_cut_h))
print("  anchor elements: %s (%s block) -- NOT C3D8R" % (ANCHOR_ELEM, ANCHOR_ORDER))
print("=" * 70)

cubit.cmd("reset")

# =============================================================================
# HELPERS
# =============================================================================


def y_cylinder(height, radius, y_center, lateral_name=None):
    """Create a cylinder aligned with y, centred at y_center. Returns volume id.

    If lateral_name is given the lateral surface is named. Cubit propagates
    surface names through boolean operations, so naming a *tool* cylinder is what
    lets the resulting hole be selected by name later instead of by a fragile
    coordinate predicate.
    """
    cubit.cmd("create cylinder height %g radius %g" % (height, radius))
    v = cubit.get_last_id("volume")
    if lateral_name:
        # a cylinder has 3 surfaces (lateral + 2 caps); the lateral is last - 2
        cubit.cmd("surface %d name '%s'" % (cubit.get_last_id("surface") - 2, lateral_name))
    cubit.cmd("rotate volume %d angle 90 about x" % v)
    cubit.cmd("move volume %d y %g" % (v, y_center))
    return v


def name_flat_surfaces(vol, y, name):
    """Name every surface of `vol` that lies flat at height y."""
    for s in cubit.parse_cubit_list("surface", "in volume %d" % vol):
        bb = cubit.get_bounding_box("surface", s)   # x:0,1,2  y:3,4,5  z:6,7,8
        if abs(bb[3] - y) < TOL and abs(bb[4] - y) < TOL:
            cubit.cmd("surface %d name '%s'" % (s, name))


def surfaces_named(pattern, ylo=None, yhi=None):
    """Ids of surfaces matching a name pattern, optionally inside a y band."""
    out = []
    for s in cubit.parse_cubit_list("surface", "with name '%s'" % pattern):
        if ylo is not None or yhi is not None:
            bb = cubit.get_bounding_box("surface", s)
            if ylo is not None and bb[3] < ylo - TOL:
                continue
            if yhi is not None and bb[4] > yhi + TOL:
                continue
        out.append(str(s))
    return out


_sid = [0]
_nid = [0]


def new_sideset(name, selector):
    """Create a named sideset and report how many faces it caught.

    Replaces the original script's two hand-incremented counters, one of which
    was already being used for the wrong entity type (a `sideset <nodeset_id> add`
    that only worked because the counters happened to be equal at that point).
    """
    _sid[0] += 1
    sid = _sid[0]
    cubit.cmd("create sideset %d" % sid)
    cubit.cmd("sideset %d name '%s'" % (sid, name))
    cubit.cmd("sideset %d add %s" % (sid, selector))
    try:
        n = len(cubit.parse_cubit_list("face", "in sideset %d" % sid))
    except Exception:
        n = -1
    print("  sideset %2d  %-20s %s" % (sid, name, "%6d faces" % n if n >= 0 else "(count n/a)"))
    if n == 0:
        print("  *** WARNING: sideset '%s' is EMPTY ***" % name)
    return sid


def new_nodeset(name, selector):
    _nid[0] += 1
    nid = _nid[0]
    cubit.cmd("create nodeset %d" % nid)
    cubit.cmd("nodeset %d name '%s'" % (nid, name))
    cubit.cmd("nodeset %d add %s" % (nid, selector))
    try:
        n = len(cubit.parse_cubit_list("node", "in nodeset %d" % nid))
    except Exception:
        n = -1
    print("  nodeset %2d  %-20s %s" % (nid, name, "%6d nodes" % n if n >= 0 else "(count n/a)"))
    if n == 0:
        print("  *** WARNING: nodeset '%s' is EMPTY ***" % name)
    return nid


# =============================================================================
# GEOMETRY
# =============================================================================

# --- 1. concrete slab with a blind borehole ---------------------------------
cubit.cmd("create brick x %g y %g z %g" % (slab_w, slab_h, slab_w))
v_slab = cubit.get_last_id("volume")
cubit.cmd("move volume %d y %g" % (v_slab, -slab_h / 2.0))
cubit.cmd("volume %d name 'concrete_main'" % v_slab)

v_hole_tool = y_cylinder(hole_d, hole_r, -hole_d / 2.0, "surface_borehole")
cubit.cmd("subtract volume %d from volume %d" % (v_hole_tool, v_slab))
v_slab = cubit.get_last_id("volume")
cubit.cmd("volume %d name 'concrete_main'" % v_slab)

# --- 2. mortar annulus -------------------------------------------------------
v_mortar = y_cylinder(anchor_d, hole_r, -anchor_d / 2.0, "surface_mortar_outer")
v_mortar_bore = y_cylinder(anchor_d, anchor_r, -anchor_d / 2.0, "surface_mortar_inner")
cubit.cmd("subtract volume %d from volume %d" % (v_mortar_bore, v_mortar))
v_mortar = cubit.get_last_id("volume")
cubit.cmd("volume %d name 'mortar'" % v_mortar)

# --- 3. steel anchor ---------------------------------------------------------
anchor_len = anchor_d + anchor_free_h
y_anchor_mid = (-anchor_d + anchor_free_h) / 2.0
v_anchor = y_cylinder(anchor_len, anchor_r, y_anchor_mid, "surface_anchor_outer")
cubit.cmd("volume %d name 'steel_anchor'" % v_anchor)

# --- 4/5/6. NO fixture plate, washer or nut in this variant -----------------
# The shaft protrusion (anchor_free_h) is retained at its full-fixture value so the
# geometry above the concrete is identical to the base model; everything above
# y = tPlate is simply a free stub.

# =============================================================================
# DECOMPOSITION FOR MESHING
# =============================================================================

# extend the borehole profile down through the solid concrete below the hole
cubit.cmd("webcut volume with name 'concrete_main' cylinder radius %g axis y" % hole_r)
# single cut separating the inner, finely meshed region from the outer slab
cubit.cmd("webcut volume with name 'concrete_*' cylinder radius %g axis y" % refine_r)

# shaft: split at the concrete surface, at the load plane and at y = tPlate, giving
# four lateral bands -> mortar / below load plane / above load plane / free stub. Each
# band is its own named surface, which is what anchor_to_mortar and the
# anchor_left_loading nodeset are selected from. It also keeps every shaft piece a
# simple sweepable quarter cylinder: one volume carrying several stacked lateral bands
# is not resolved by Cubit's autoscheme.
# The y=0 cut is essential -- without it the embedded band and the loaded band are
# a single surface and anchor_to_mortar comes out empty.
# The y=plate_cut_h cut makes the option-F rigid section a real, single mesh plane
# rather than selecting whichever node row happens to lie nearby.
cubit.cmd("webcut volume with name 'steel_anchor*' plane yplane offset 0")
cubit.cmd("webcut volume with name 'steel_anchor*' plane yplane offset %g" % plate_cut_h)
cubit.cmd("webcut volume with name 'steel_anchor*' plane yplane offset %g" % tPlate)

# --- symmetry: keep the z <= 0 half, then cut at x = 0 for hex meshing ------
cubit.cmd("webcut volume all with plane zplane offset 0")
to_delete = [str(v) for v in cubit.parse_cubit_list("volume", "all") if cubit.get_center_point("volume", v)[2] > 0.01]
if to_delete:
    cubit.cmd("delete volume %s" % " ".join(to_delete))
cubit.cmd("webcut volume all with plane xplane offset 0")

# =============================================================================
# GROUPING  -- one group per part, so merging never fuses two parts
# =============================================================================
GROUPS = [("grp_concrete", "concrete_*"), ("grp_mortar", "mortar*"), ("grp_anchor", "steel_anchor*")]
for g, pat in GROUPS:
    cubit.cmd("group '%s' add volume with name '%s'" % (g, pat))
    print("  %-14s %d volumes" % (g, len(cubit.parse_cubit_list("volume", "in %s" % g))))

# Imprint and merge WITHIN each group only. Nothing is imprinted across groups:
#  * shaft <-> plate must stay separate (they are a contact pair now, not merged)
#  * concrete <-> plate imprint would print the plate outline onto the concrete
#    top face and change the concrete mesh for no benefit; a surface-to-surface
#    contact pair does not need conforming meshes
for g, _ in GROUPS:
    cubit.cmd("imprint volume in %s" % g)
for g, _ in GROUPS:
    cubit.cmd("merge volume in %s" % g)

# =============================================================================
# MESH SIZING
# =============================================================================
cubit.cmd("volume all size %g" % mesh_size_steel)
cubit.cmd("volume in grp_mortar size %g" % mesh_size_mortar)

# Refine the shaft above the concrete surface. Here it is the loaded region rather
# than a contact slave surface, so a finer mesh keeps the prescribed-displacement
# patch well resolved.
shaft_upper = [str(v) for v in cubit.parse_cubit_list("volume", "in grp_anchor") if cubit.get_bounding_box("volume", v)[3] > -TOL]
if shaft_upper:
    cubit.cmd("volume %s size %g" % (" ".join(shaft_upper), mesh_size_fastener / 2.0))

# concrete: inner vs outer by radial extent of the bounding box
inner, outer = [], []
for v in cubit.parse_cubit_list("volume", "in grp_concrete"):
    bb = cubit.get_bounding_box("volume", v)
    max_r = max(abs(bb[0]), abs(bb[1]), abs(bb[6]), abs(bb[7]))
    (inner if max_r < refine_r + 0.1 else outer).append(str(v))
print("  concrete: %d inner volumes, %d outer volumes" % (len(inner), len(outer)))
if inner:
    cubit.cmd("volume %s size %g" % (" ".join(inner), mesh_size_concrete_inner))
if outer:
    cubit.cmd("volume %s size %g" % (" ".join(outer), mesh_size_concrete_outer))

# Vertical discretisation of the slab: size the outer corner's vertical edge and
# let interval matching propagate it through the height (~3 mm layers over 160).
cubit.cmd("curve in volume in grp_concrete expand with x_coord = %g tolerance 0.01 and z_coord = 0 tolerance 0.01 size %g" % (slab_w / 2.0, mesh_size_slab_vertical))

# NOTE: the base model needs explicit sweep schemes here for the washer and the
# hexagonal nut, which Cubit's autoscheme refuses. This variant has neither, and
# every remaining volume is a plain quarter cylinder or brick, so autoscheme copes.

# NOTE: no `control skew` anywhere. On this cylindrical concrete blocking it
# reports "SkewControlTool failed to correctly subdivide a loop" and adds
# constraints that make interval matching infeasible, so nothing meshes.

cubit.cmd("mesh volume all")

# =============================================================================
# CHALICE REFINEMENT
# =============================================================================
# Parabolic envelope flaring from the bottom of the borehole to the surface.
# This replaces the straight cone used by older versions of the journal, whose
# refinement always failed with "Refinement process resulted in an invalid
# surface mesh" and silently exported an unrefined concrete mesh.
chalice = []
for h in cubit.parse_cubit_list("hex", "in grp_concrete expand"):
    x, y, z = cubit.get_center_point("hex", h)
    if y_bot <= y <= y_top:
        r_y = R_bot + dR * ((y - y_bot) / dy) ** 2
        r2 = x * x + z * z
        if r2 < r_y * r_y and r2 < refine_r * refine_r:
            chalice.append(str(h))

if chalice:
    print("  chalice: refining %d hexes" % len(chalice))
    cubit.cmd("create group 'chalice_domain'")
    for i in range(0, len(chalice), 200):   # keep under Cubit's command length limit
        cubit.cmd("group 'chalice_domain' add hex %s" % " ".join(chalice[i:i + 200]))
    cubit.cmd("refine hex in chalice_domain depth 0")
    print("  refinement complete")
else:
    print("  *** WARNING: chalice domain is empty, nothing refined ***")

# =============================================================================
# BLOCKS
# =============================================================================
cubit.cmd("create material 'concrete' property_group 'CUBIT-ABAQUS'")
cubit.cmd("create material 'steelAnchor' property_group 'CUBIT-ABAQUS'")
cubit.cmd("create material 'mortar' property_group 'CUBIT-ABAQUS'")

# The mortar stays hex8: it is exported as COH3D8, a cohesive element with its own
# formulation, and has no hourglass problem to fix. Only the anchor's order follows
# ANCHOR_ELEM.
BLOCKS = [("anchor", "grp_anchor", ANCHOR_ORDER, "steelAnchor"), ("mortar", "grp_mortar", "hex8", "mortar"), ("concrete", "grp_concrete", "hex20", "concrete")]
bid = {}
for i, (name, grp, etype, mat) in enumerate(BLOCKS, start=1):
    cubit.cmd("create block %d" % i)
    cubit.cmd("block %d name '%s'" % (i, name))
    cubit.cmd("block %d add volume in %s" % (i, grp))
    cubit.cmd("block %d element type %s" % (i, etype))
    cubit.cmd("block %d material '%s'" % (i, mat))
    bid[name] = i

# =============================================================================
# SIDESETS
# =============================================================================
print("\nsidesets:")
# boundaries. concrete_top has no contact partner in this variant (there is no
# plate) but is kept as a useful output surface.
new_sideset("concrete_top", "surface in grp_concrete expand with y_coord = 0")

# mortar interfaces (tied) -- the only interactions left in this variant
new_sideset("concrete_to_mortar", "surface in grp_concrete expand with name 'surface_borehole*'")
new_sideset("mortar_to_concrete", "surface in grp_mortar expand with name 'surface_mortar_outer*'")
new_sideset("mortar_to_anchor", "surface in grp_mortar expand with name 'surface_mortar_inner*'")
new_sideset("anchor_to_mortar", "surface %s" % " ".join(surfaces_named("surface_anchor_outer*", yhi=0.0)))

# No alternative load-patch sideset: option F only.

# =============================================================================
# NODESETS
# =============================================================================
print("\nnodesets:")
new_nodeset("left", "node in grp_concrete expand with x_coord = %g" % (-slab_w / 2.0))
new_nodeset("right", "node in grp_concrete expand with x_coord = %g" % (slab_w / 2.0))
new_nodeset("back", "node in grp_concrete expand with z_coord = %g" % (-slab_w / 2.0))
new_nodeset("bottom", "node in grp_concrete expand with y_coord = %g" % (-slab_h))
new_nodeset("z_symm", "node in volume all expand with z_coord = 0")
# --- the loaded band: REFERENCE deck's BC, and every deck's output set -------
# The -x half of the shaft's lateral surface over the height the fixture plate used to
# occupy (y = 0 .. tPlate). surfaces_named() with the same y band that built
# anchor_to_plate in the base model gives those surfaces; the x_coord filter then keeps
# the -x half. In the z <= 0 half model this is the quadrant x <= 0, z <= 0.
#
# The REFERENCE deck prescribes u1 on all of it, which is the artifact under study:
# one u1 over a 20 mm tall band forces du1/dy = 0 and clamps rotation about z.
# Options A, B and E leave it unloaded and use it as an OUTPUT set only -- u1 plotted
# against y over these nodes is the direct test of whether rotation is free (flat
# means clamped). Do not prescribe u1 here in those decks: in B it would fight the
# coupling and overconstrain the model.
_load_surfs = " ".join(surfaces_named("surface_anchor_outer*", ylo=0.0, yhi=tPlate))
if not _load_surfs:
    raise RuntimeError("no exterior anchor surfaces found in 0 <= y <= tPlate")
_load_sel = "node in surface %s with x_coord < %g" % (_load_surfs, TOL)
new_nodeset("anchor_left_loading", _load_sel)

# --- OPTION F: the whole shaft cross-section at y = plate_cut_h ---------------
# Every other set above is a "node in surface ..." selection, so it only ever reaches
# the shaft's lateral surface. This one is a volume selection and therefore catches the
# INTERIOR nodes too: the complete cross-section on the plate_cut_h webcut plane, which
# is what a *COUPLING / *KINEMATIC constraint needs in order to make that section move
# as a rigid body pulled by a single reference node.
#
# The window is the ring's own +/- LOAD_PLANE_TOL, and it is safe: the neighbouring
# anchor node planes are at 5.333 and 7.879, i.e. 1.2 mm away, four times the window.
# The assertions below are what makes that a fact rather than a hope.
_sec_sel = "node in grp_anchor expand with y_coord > %g with y_coord < %g" % (plate_cut_h - LOAD_PLANE_TOL, plate_cut_h + LOAD_PLANE_TOL)
_sec_nid = new_nodeset("anchor_load_section", _sec_sel)
_sec_nodes = cubit.parse_cubit_list("node", "in nodeset %d" % _sec_nid)
# One node plane only. If the window ever caught two, u1 would be prescribed at two
# different heights through the constraint and the rotational clamp this whole study
# exists to remove would come straight back in.
_sec_off = [n for n in _sec_nodes if abs(cubit.get_nodal_coordinates(n)[1] - plate_cut_h) > TOL]
if _sec_off:
    raise RuntimeError("anchor_load_section caught %d node(s) off the y=%g plane (e.g. %d) -- LOAD_PLANE_TOL=%g is too wide" % (len(_sec_off), plate_cut_h, _sec_off[0], LOAD_PLANE_TOL))
# Interior nodes must be in there: a set of ~15 would mean the selection collapsed to
# the perimeter and the "rigid section" would just be a hoop.
if len(_sec_nodes) < 20:
    raise RuntimeError("anchor_load_section has only %d nodes -- expected the full cross-section, interior included; is the plate_cut_h webcut present?" % len(_sec_nodes))
_sec_r = max(math.hypot(cubit.get_nodal_coordinates(n)[0], cubit.get_nodal_coordinates(n)[2]) for n in _sec_nodes)
if abs(_sec_r - anchor_r) > 1e-3:
    raise RuntimeError("anchor_load_section reaches r=%.4f, expected the shaft radius %.4f" % (_sec_r, anchor_r))
print("  option F load plane y=%g: complete section = %d nodes, max radius %.4f" % (plate_cut_h, len(_sec_nodes), _sec_r))

# =============================================================================
# EXPORT
# =============================================================================
STEEL = os.path.join(HERE, "steel.inp")
CONCRETE = os.path.join(HERE, "concrete.inp")
_steel_blocks = "%d %d" % (bid["anchor"], bid["mortar"])
cubit.cmd('export abaqus "%s" block %s partial overwrite' % (STEEL, _steel_blocks))
cubit.cmd('export abaqus "%s" block %d partial overwrite' % (CONCRETE, bid["concrete"]))

# Cubit exports every hex8 block as C3D8R. Two of those types are wrong here, so both
# are patched in the exported file, which keeps it directly runnable with no manual sed
# step:
#   - the mortar carries a *COHESIVE SECTION, which requires COH3D8;
#   - the anchor must not be reduced-integration at all -- see ANCHOR_ELEM at the top
#     of this file for why. This patch is the ONLY place the anchor's type is set, so
#     grepping the exported steel.inp for C3D8R is a complete check that none is left.
with open(STEEL) as fh:
    txt = fh.read()
_mortar_old = "*ELEMENT, TYPE=C3D8R, ELSET=mortar"
_mortar_new = "*ELEMENT, TYPE=COH3D8, ELSET=mortar"
if _mortar_old in txt:
    txt = txt.replace(_mortar_old, _mortar_new)
    print("\npatched mortar element type -> COH3D8")
elif _mortar_new in txt:
    print("\nmortar element type already COH3D8")
else:
    print("\n*** WARNING: could not find the mortar *ELEMENT line to patch ***")
_m = re.search(r"\*ELEMENT, TYPE=([^,\s]+), ELSET=anchor\b", txt)
if _m is None:
    print("*** WARNING: could not find the anchor *ELEMENT line to patch ***")
elif _m.group(1) == ANCHOR_ELEM:
    print("anchor element type already %s" % ANCHOR_ELEM)
else:
    txt = txt.replace(_m.group(0), "*ELEMENT, TYPE=%s, ELSET=anchor" % ANCHOR_ELEM)
    print("patched anchor element type %s -> %s" % (_m.group(1), ANCHOR_ELEM))
with open(STEEL, "w") as fh:
    fh.write(txt)
_left = sorted(set(re.findall(r"\*ELEMENT, TYPE=(\S+), ELSET=(\w+)", txt)))
print("exported element types: %s" % ", ".join("%s=%s" % (b, t) for t, b in _left))
if any(t == "C3D8R" for t, _b in _left):
    print("*** WARNING: C3D8R survived in %s -- it must not be used for the steel ***" % STEEL)

cubit.cmd("quality volume all scaled jacobian global draw histogram draw mesh")
print("\ndone: %s, %s" % (STEEL, CONCRETE))


# =============================================================================
# FIXED OPTION-F ABAQUS CASE
# =============================================================================


def write_option_f_case():
    """Write the complete fixed Abaqus case."""
    anchor_input = """*Heading
** Job name: bondedAnchor Model name: Model-1
** Generated by: Abaqus/CAE 2019
**
** ############################################################
** BARE ANCHOR -- LOAD INTRODUCTION STUDY, OPTION F (rigid cross-section at tPlate/3)
** ############################################################
**
** Generated directly and completely by:
** mesh/Pryout_elastic_bareanchor_section.py
** This is the fixed standalone M20 / hef80 / option-F model.
**
** The load height is plate_cut_h = tPlate/3 = 6.667 mm, the plane where the
** full-fixture model
** prescribes its displacement on, so the shear resultant sits tPlate/3 above the
** concrete surface -- that eccentricity is what rotates the anchor.
**
** RF1 is a HALF-MODEL reaction: the full specimen force is 2 x RF1.
**
** OPTION F -- the WHOLE shaft cross-section at y = tPlate/3 tied to a reference node
** and made to move as a rigid body in the loading plane. u1 is prescribed at that
** reference node; its vertical translation and its rotation about z are left free.
**
** Physically: cut the shaft at a third of the plate height and load it there through a
** rigid diaphragm, instead of pushing on a patch of its outer skin. This is the only
** option that loads the complete section rather than the -x half of the lateral
** surface, so it has none of the local artifacts the others trade against -- no
** ovalisation restraint (A), no dimple (E), no lopsided patch centroid to place (B).
**
** Why rotation is NOT suppressed: the constraint fixes u1 and u2 only on ONE node
** plane. du1/dy is unconstrained, so rotation about z remains whatever the mechanics
** dictate -- and it is reported directly as UR3 at the reference node, which no other
** deck in this study measures.
**
** Why the eccentricity is EXACT: UR3 at the reference node is free and carries no
** load, so the constraint's reaction moment about z is identically zero. A force
** system with zero moment about that node has its line of action through it, and the
** node is at y = tPlate/3. Nothing acts on the shaft above the section, so the moment
** the concrete sees at y = 0 is V * tPlate/3 exactly. Check RM3 = 0 in the results;
** that is the whole argument, and it is one number.
**
** The accepted error: the cross-section is forced to stay plane and rigid, i.e. a
** Bernoulli assumption imposed over one node plane, which suppresses the shear warping
** of that section and stiffens it slightly. Judge it by comparing the secant stiffness
** against options A and B rather than by assertion.
**
** Global preprint options:
**  - echo=NO      : do not echo the input file to the .dat file
**  - model=NO     : do not print full model definition
**  - history=NO   : do not print history output definitions
**  - contact=NO   : do not print contact definitions
*Preprint, echo=NO, model=NO, history=NO, contact=NO

**
** ============================================================
** PART DEFINITIONS
** ============================================================
**
** Each *Part defines geometry, mesh, sections, and orientations
** independently before being assembled later.
**

*Part, name=concrete
** Import the concrete mesh from an external input file
*Include, input="./mesh/concrete.inp"

** Assign a solid (continuum) section to the concrete elements
**  - elset=concrete : element set defined in the included mesh
**  - material=concrete : material defined later
*Solid Section, elset=concrete, material=concrete
*End Part

** ------------------------------------------------------------

*Part, name=steel
** BARE ANCHOR -- the steel mesh holds the anchor and the mortar only. There is no
** fixture plate, washer or nut in this model.
**
** ELEMENT TYPE: the anchor is C3D8I, NOT C3D8R. Reduced integration with hourglass
** control produces spurious oscillation in both displacement and stress wherever the
** load is introduced over a few nodes -- which is what every deck in this study does
** -- and its stabilisation forces are invisible to NFORC, so nodal-force
** post-processing of the loaded region loses part of the load path. C3D8I has no
** hourglass modes, does not shear-lock in bending (the shaft IS a bending member),
** and keeps the same 8 nodes per element. Set in Pryout_bondedAnchor.py; grep
** ./mesh/steel.inp for C3D8R to confirm none is left.
*Include, input="./mesh/steel.inp"

** Assign material to the steel anchor elements
*Solid Section, elset=ANCHOR, material=STEEL_ANCHOR

** Define a cylindrical local coordinate system
** This is later used for the cohesive (mortar) behavior
*ORIENTATION, name=MORTAR_CYL, SYSTEM=CYLINDRICAL
0, 0, 0,   0, 1, 0
**
** First point: origin of the coordinate system
** Second point: direction of the cylinder axis

** ------------------------------------------------------------
** Cohesive section for the mortar layer
** ------------------------------------------------------------
**  - elset=MORTAR : cohesive elements
**  - material=stick_slip : traction-separation law
**  - response=TRACTION SEPARATION : cohesive formulation
**  - ORIENTATION=MORTAR_CYL : defines normal and shear directions
**  - STACK DIRECTION=ORIENTATION : thickness direction follows orientation
*COHESIVE SECTION, elset=MORTAR, material=stick_slip, response=TRACTION SEPARATION, ORIENTATION=MORTAR_CYL, STACK DIRECTION=ORIENTATION
*End Part

**
** ============================================================
** ASSEMBLY
** ============================================================
**
** NOTE ON FORMATTING: no blank lines anywhere from here to *End Assembly. A blank
** line after a *TIE data line is read as an empty surface name and is FATAL
** ("THE SECONDARY SURFACE NAME MUST BE GIVEN ON *CONTACT PAIR OR *TIE. NOTE THAT
** EMPTY LINES ARE NOT ACCEPTABLE AS DATA LINES"), and it cascades into bogus
** "SELF CONTACTING SURFACE IS CURRENTLY NOT ALLOWED FOR TYING SURFACES" errors that
** point nowhere near the cause -- 8 fatal errors from one blank line. Separate blocks
** with ** comment lines, never with blanks. (*SURFACE merely warns, which is why this
** is easy to miss.)
*Assembly, name=Assembly
** Create an instance of the concrete part
*Instance, name=concrete-1, part=concrete
*End Instance
** Create an instance of the steel part
*Instance, name=steel-1, part=steel
*End Instance
** ------------------------------------------------------------
** TIE CONSTRAINTS
** ------------------------------------------------------------
** Tie constraints enforce perfect bonding (no slip, no separation).
** First surface listed is the secondary (slave), second is the main (master).
**
** Only two ties in this variant, and NO contact pairs at all:
**   Tie anchor to mortar
**   Tie mortar to concrete
** With no fixture there is nothing to tie the nut/washer to and nothing bearing on
** the concrete surface. The shaft is still fully restrained through the mortar bond,
** so removing the plate introduces no rigid-body mode.
**
** KNOWN PRE-EXISTING ISSUE, common to all five decks and NOT caused by the load
** introduction: MORTAR_TO_CONCRETE reports 1018 nodes with no intersection found and
** explicit "SECONDARY NODE ... WILL NOT BE TIED TO THE MAIN SURFACE ... DISTANCE FROM
** THE MAIN SURFACE IS GREATER THAN THE POSITION TOLERANCE". With ADJUST=NO and a 9 mm
** hex20 concrete mesh against a 2.5 mm mortar mesh on a curved borehole, part of the
** mortar->concrete bond is simply absent. Note also that the coarse surface (concrete)
** is the SECONDARY here and the fine one (mortar) the MAIN, which is the inverse of
** the usual recommendation and a likely contributor. This affects load transfer into
** the concrete identically in every deck, so it does not disturb the comparison
** BETWEEN options -- but it should be resolved before any single curve is trusted
** against a test.
*TIE, NAME=ANCHOR_TO_MORTAR, ADJUST=NO, TYPE=SURFACE TO SURFACE
steel-1.mortar_to_anchor, steel-1.anchor_to_mortar
*TIE, NAME=MORTAR_TO_CONCRETE, ADJUST=NO, TYPE=SURFACE TO SURFACE
concrete-1.concrete_to_mortar, steel-1.mortar_to_concrete
** ------------------------------------------------------------
** LOAD INTRODUCTION -- RIGID CROSS-SECTION AT tPlate/3   *** VARIANT ***
** ------------------------------------------------------------
** Section reference node. The prescribed displacement is applied here, not on the
** shaft, and the total shear is read back as RF1 (x2 for the full specimen).
**
** ITS y IS THE LOAD ECCENTRICITY AND IS NOT COSMETIC. y = tPlate/3 = 6.66667 matches
** the full-fixture model, which prescribes its displacement on the plane
** plate_cut_h = tPlate/3 of the plate. It scales with dAnchor (tPlate = dAnchor);
** update it if the diameter changes.
**
** x and z, by contrast, ARE immaterial here, and that is a property of a KINEMATIC
** coupling rather than luck. The constraint is u_i = u_RP + omega x (x_i - x_RP), and
** the boundary conditions below set omega_x = omega_y = 0 (they are the half-model
** symmetry conditions, see the *Boundary block further down), which removes every term
** in which x_RP or z_RP could appear. The node is put on the shaft axis in the load
** plane so that its remaining free dofs read as the section's own centroidal quantities
** -- u2 is the anchor's uplift there, UR3 is the anchor's rotation there. It coincides
** with steel node 5004 at (0, 6.66667, 0); that is legal and harmless, since 5004 is
** simply a slave node with a zero lever arm.
**
** NOT named DRIVE: postproc/fit.py keys on a DRIVE nodeset to recognise option B's
** distributing coupling, and it must keep rejecting this deck -- the mechanism here is
** a different one.
*Node, nset=SECRP
999002, 0., 6.66667, 0.
** The 51 nodes of the shaft cross-section on the plate_cut_h webcut plane -- perimeter
** AND interior, which is why anchor_load_section had to be a volume selection in the
** journal while every other load set there is a "node in surface" selection. *COUPLING
** takes a surface, not a nodeset, so the nodeset is wrapped as a node-based surface.
**
** The trailing 1. is a nodal weight. *KINEMATIC never uses weights -- it is a rigid
** kinematic constraint, not a weighted distribution -- but with the field left blank
** Abaqus warns "THE CONTACT AREA OR DISTRIBUTING WEIGHT ASSOCIATED WITH 51 NODES IS
** ZERO OR NEGATIVE ... A ZERO IS ASSUMED FOR THE DISTRIBUTING WEIGHT FACTOR". Harmless
** here, but writing the 1. keeps this deck's datacheck output comparable to the others.
*Surface, type=NODE, name=sec_nodes
steel-1.anchor_load_section, 1.
** The constraint.
**
** *KINEMATIC, not *DISTRIBUTING: this one is meant to be rigid, and unlike
** *DISTRIBUTING it can couple a SUBSET of the translations. Dofs 1 and 2 are coupled,
** dof 3 is not. Both halves of what that means were MEASURED on a one-element test
** model (2026-07-29) rather than reasoned about, because the two are easy to confuse:
**
**   1. The dof list IS honoured. With "1, 2" the coupled face's u3 comes out nonzero and
**      varying (+-5.12e-3 on a 0.01 stroke); with "1, 3" it is 0.000 at every node. So
**      this section really is rigid in the loading plane and free out of it. It is NOT
**      quietly a full rigid body.
**   2. But a *BOUNDARY on dof 3 of a slave node is SILENTLY IGNORED. Abaqus takes all
**      three translations of a kinematic-coupling slave node out of reach of a direct
**      boundary condition even though it constrains only the ones listed. Same test
**      model: u3 = 0 imposed on one face node gives RF3 = -138 N with no coupling, and
**      with the coupling gives no reaction at all and an unchanged u3. A zSYMM-type BC
**      at least prints "DEGREE OF FREEDOM 3 HAS BEEN ELIMINATED ... ZSYMM MAY NOT BE
**      APPLIED AT THIS NODE"; a plain "node, 3, 3" prints NOTHING.
**
** So the price of "1, 2" is real and must not be glossed: 10 of the 51 section nodes lie
** on z = 0 and are in steel-1.z_symm, so the model asks for u3 = 0 there and does not
** get it. The symmetry plane has a 10-node hole in it at the load plane. The error is
** second order -- symmetric geometry loaded along x has u3 = 0 on that plane anyway, so
** those free dofs should simply come out at ~0 -- but it IS an error, so check it: max
** |u3| over those 10 nodes must be negligible against |u|.
**
** If exact symmetry there is ever preferred over the smaller restraint, changing "1, 2"
** to "1, 3" gives u3 = 0 at all 51 nodes exactly and drops no boundary condition. The
** price is that the section can then not breathe radially in z at all, a real extra
** stiffening of the same family as option A's ovalisation restraint. That is a modelling
** choice, not a bug fix -- do not make it silently.
**
** What dofs 1 and 2 buy: u1 uniform over the section and u2 linear across it, i.e.
** plane sections remain plane -- the Bernoulli approximation this option accepts. What
** they do NOT buy is any restraint on du1/dy, because this is ONE node plane. Rotation
** about z stays free, which is the entire point of the study; what WOULD suppress it is
** prescribing u1 at two different heights at once, as the REFERENCE deck does over a
** 20 mm band.
*Coupling, constraint name=SEC_RIGID, ref node=SECRP, surface=sec_nodes
*Kinematic
1, 2
*End Assembly
**
** ============================================================
** MATERIAL DEFINITIONS
** ============================================================
**
*Material, name=STEEL_ANCHOR
** Linear elastic steel properties
** Density (mass units consistent with model units)
*Elastic
200000., 0.33
*DENSITY
7.85e-9
** No STEEL_PLATE or STEEL_FASTENER material in this variant: no plate, washer or nut.
*Material, name=CONCRETE
** Simplified linear elastic concrete model
*Elastic
27000., 0.18
*DENSITY
2.4e-9
** ------------------------------------------------------------
** Cohesive (stick-slip) material for mortar
** ------------------------------------------------------------
*Material, name=stick_slip
** Elastic traction-separation stiffness
** Normal, shear-1, shear-2 stiffness values
*Elastic, type=TRACTION
5400, 2700, 2700
*DENSITY
2.0e-9
**
** ============================================================
** CONTACT INTERACTIONS
** ============================================================
**
** NONE. This variant has no contact anywhere: with the plate removed nothing rests on
** the concrete surface and nothing bears in a hole. All load transfer is through the
** two tie constraints above.
**
** ============================================================
** BOUNDARY CONDITIONS
** ============================================================
**
** Fully constrain outer concrete boundaries (encastre-like behavior)
*Boundary
concrete-1.left,   1, 1
concrete-1.left,   2, 2
concrete-1.left,   3, 3
concrete-1.right,  1, 1
concrete-1.right,  2, 2
concrete-1.right,  3, 3
concrete-1.back,   1, 1
concrete-1.back,   2, 2
concrete-1.back,   3, 3
concrete-1.bottom, 1, 1
concrete-1.bottom, 2, 2
concrete-1.bottom, 3, 3
**
** Symmetry boundary conditions in Z-direction
*Boundary
steel-1.z_symm, zSYMM
concrete-1.z_symm, zSYMM
**
** The section reference node carries the half-model symmetry conditions and nothing
** else. Dofs 3, 4, 5 = u3, UR1, UR2 -- exactly the triple zSYMM sets, applied here
** because SECRP is where the rigid section's rotational dofs live.
**
** These add NO restraint to the mechanics. UR2 = 0 forbids twist about the anchor axis
** and UR1 = 0 forbids out-of-plane tilt; both are zero by symmetry in a model whose
** loading is along x and whose geometry is mirrored at z = 0. RM1 and RM2 are their
** reactions and should come out at ~0 -- check them. u3 = 0 additionally removes a dof
** that appears in no constraint equation at all (dof 3 is not coupled), and would
** otherwise be a numerical singularity; its reaction RF3 is identically zero.
**
** Note that these three do NOT repair the 10 section nodes whose zSYMM is dropped (see
** the *Coupling comment): with dof 3 uncoupled, u3 at SECRP is connected to nothing.
**
** What is deliberately left FREE: dof 2, so the anchor may lift -- it does, by about a
** quarter of its lateral displacement in the other decks, which is the frictionless-rig
** idealisation -- and dof 6, UR3, the rotation this whole study exists to permit.
*Boundary
SECRP, 3, 3
SECRP, 4, 4
SECRP, 5, 5
**
** No base-state clamp on steel-1.anchor_left_loading in this deck. It carries no
** boundary condition at all -- the load goes in through the anchor_load_section nodeset
** and the coupling, and prescribing u1 here as well would fight the coupling and
** overconstrain the model. It is an output set only, and its u1(y) profile is still the
** rotation diagnostic.
**
** ============================================================
** ANALYSIS STEP
** ============================================================
**
*Step, name=loading, nlgeom=no, inc=100000
** Quasi-static dynamic step, used for convergence robustness. The fourth value caps
** the increment at 0.01 of the step, which keeps the frame spacing even across all
** five decks so their curves can be overlaid. Do not drop it.
*Dynamic, APPLICATION=QUASI-STATIC
0.0001, 1, 1e-08, 0.01
**
** ============================================================
** LOAD INTRODUCTION -- OPTION F (rigid cross-section at tPlate/3)  *** VARIANT ***
** ============================================================
** Driven at the section reference node: one scalar prescribed displacement, delivered
** to the whole cross-section at tPlate/3 through a rigid diaphragm. Displacement
** control is retained, so the softening branch after the pry-out peak stays traceable.
**
** Because UR3 is free and unloaded, RM3 = 0 at every increment and the line of action
** of the shear passes exactly through y = tPlate/3. That is the eccentricity, measured
** rather than argued -- one number in the history output.
*Boundary, type=displacement
SECRP, 1, 1, 5.
**
** ============================================================
** OUTPUT REQUESTS
** ============================================================
**

** Print contact information to the .dat file
*Print, contact=yes

** Write restart files every increment
*Restart, write, frequency=1, overlay

** Include external output request files
*Include, input="./incfiles/output.inc"
*Include, input="./incfiles/fileOutput.inc"

*End Step
"""
    output_inc = """*Output, field, time interval=0.001, time marks=NO
*Node Output
CF, RF, TF, U, VF, NT
*Element Output, elset=concrete-1.concrete, directions=YES
LE, NFORC, PE, PEEQ, PEMAG, S, SDV
*Element Output, elset=steel-1.anchor, directions=YES
LE, NFORC, PE, PEEQ, PEMAG, S, SDV
*Element Output, elset=steel-1.mortar, directions=YES
S
** No *Contact Output in this variant: with the plate, washer and nut removed there
** are no contact pairs at all, so CSTRESS/CDISP would have nothing to report.
**
** NFORC is requested on the anchor and is now meaningful: with C3D8I there is no
** hourglass stabilisation force for it to omit. It is still NOT the way to measure
** the load eccentricity -- tie-constraint forces on the y=0 node row contaminate it.
** Use a free body cut at y=0 for that; see the handover note.
**
** HISTORY OUTPUT -- the load-displacement curve of the test.
** Shear = RF1 at SECRP, a single node (x2 for the full specimen). UR3 is the anchor's rotation at the load plane; RM3 = 0 is the exact-eccentricity check. Also check RF2 = RF3 = 0 and RM1 = RM2 = ~0.
*Output, history, time interval=0.001, time marks=NO
*Node Output, nset=SECRP
U1, UR3, RF1, RM3
"""
    file_output_inc = """*el file, frequency=10
  S, E
*node file, frequency=10
  u, nt
** The driven set, every increment. Shear = RF1 at SECRP, a single node (x2 for the full specimen). UR3 is the anchor's rotation at the load plane; RM3 = 0 is the exact-eccentricity check. Also check RF2 = RF3 = 0 and RM1 = RM2 = ~0.
*node file, nset=SECRP, frequency=1
  u, rf
** The 20 mm band, in EVERY deck. u1 plotted against y over these 136 nodes is the
** direct test of whether the anchor is free to rotate: a straight line of nonzero
** slope means it rotates, a dead-flat profile means the load introduction has clamped
** it. Flat is the artifact this study exists to remove, and it is exactly what the
** REFERENCE deck produces by construction.
*node file, nset=steel-1.anchor_left_loading, frequency=10
  u, rf
"""
    case_dir = ROOT
    mesh_dir = HERE
    inc_dir = os.path.join(case_dir, "incfiles")
    os.makedirs(mesh_dir, exist_ok=True)
    os.makedirs(inc_dir, exist_ok=True)
    files = [(os.path.join(case_dir, "AnchorPryOut.inp"), anchor_input), (os.path.join(inc_dir, "output.inc"), output_inc), (os.path.join(inc_dir, "fileOutput.inc"), file_output_inc)]
    for path, contents in files:
        with open(path, "w") as fh:
            fh.write(contents)
    print("\ndone: standalone option-F case written to %s" % case_dir)


write_option_f_case()
