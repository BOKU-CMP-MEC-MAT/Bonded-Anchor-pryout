"""
Bonded-anchor pry-out model: concrete slab + mortar + anchor + fixture plate +
flat washer + hex nut, meshed with Cubit and exported for AnchorPryOut.inp.

Master build script. Parametric in the anchor diameter and embedment depth; the
defaults are d = 20, hef = 80, matching AnchorPryOut.inp as shipped.

Two reduced variants live in sibling directories, each with its own copy of this
script: ../../Pryout_elastic_M20_hef80_bareanchor (no fixture at all, load applied
straight to the shaft) and ../../Pryout_elastic_M20_hef80_mergedplate (plate only,
zero clearance, plate merged to the shaft). Fixes made here should be mirrored there.

Under Cubit, pass parameters in the ENVIRONMENT. Cubit's "-input" mode hands the
script an empty sys.argv and tries to interpret any extra command-line words as
journal files ("Could not open file: --"), so command-line flags cannot reach it:

    PRYOUT_D=12 PRYOUT_HEF=60 cubit -nographics -batch -nojournal -input Pryout_bondedAnchor.py

Run directly instead (cubit module on PYTHONPATH) and either form works:

    python3 Pryout_bondedAnchor.py --d=12 --hef=60

Writes ./steel.inp (anchor, plate, mortar, washer, nut) and ./concrete.inp
(concrete), then rewrites continuum steel blocks to C3D8I and the mortar block
to COH3D8 because AnchorPryOut.inp assigns it a *COHESIVE SECTION.

The journal twin, Pryout_bondedAnchor.jou, builds the same model; this file is the
one to edit.

EDITING CONSTRAINT
------------------
Cubit's "-input <file>.py" driver feeds this file to Python one physical line at a
time, so a *top-level* statement must never be split across lines:

    v = f(a,          # <-- SyntaxError: '(' was never closed
          b)

Keep every top-level statement on one line (introduce a temporary variable if it
gets long). Compound statements (def / for / if / with) are accumulated correctly,
so their bodies may wrap freely.
"""

import math
import os
import sys

import cubit

# =============================================================================
# PARAMETERS
# =============================================================================


def _param(flag, env, default):
    """Read a float parameter from --<flag>=value, then $<env>, else default.

    Only recognised flags are consumed, so this is safe when Cubit puts its own
    arguments in sys.argv.
    """
    for a in sys.argv[1:]:
        if a.startswith("--%s=" % flag):
            return float(a.split("=", 1)[1])
    return float(os.environ.get(env, default))


dAnchor = _param("d", "PRYOUT_D", 20.0)      # anchor diameter
hef = _param("hef", "PRYOUT_HEF", 80.0)      # embedment depth

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

# --- fixture plate -----------------------------------------------------------
plate_w = 4.0 * dAnchor
tPlate = dAnchor                             # plate thickness
plate_cut_h = tPlate / 3.0                   # load is applied on this plane

# --- fastener: hex nut (ISO 4032 / DIN 934) and flat washer (DIN 125A / ISO 7089)
# Ratios fitted to the standard tables, deviation < 3% over M12..M24:
#
#   d     nut s (flats)   nut m (height)   washer d1   washer d2   washer h
#   M12       18              10.8            13          24         2.5
#   M16       24              14.8            17          30         3
#   M20       30              18.0            21          37         3
#   M24       36              21.5            25          44         4
#
sNut = 1.5 * dAnchor                         # width across flats
eNut = 2.0 * sNut / math.sqrt(3.0)           # across corners; prism radius = eNut/2
hNut = 0.9 * dAnchor                         # nut height
dWasherOut = 1.9 * dAnchor                   # washer outer diameter
tWasher = 0.19 * dAnchor                     # washer thickness

# Clearance-hole diameter, shared by the washer bore AND the plate hole (DIN 125
# d1 = d + 1 for M12..M24). The nut bore is deliberately NOT this: it is dAnchor,
# coincident with the shaft, because the nut is threaded on and gets a tie.
dClearance = dAnchor + 1.0

alphaNut = 0.0        # nut rotation about its axis; 0 or 30 are both symmetric
stickOut = 0.0        # free thread above the nut

# Shaft protrusion must carry plate + washer + nut, otherwise the shaft top is
# flush with the plate top and there is no room for the fastener.
anchor_free_h = tPlate + tWasher + hNut + stickOut
yWasherBot = tPlate
yNutBot = tPlate + tWasher
yShaftTop = anchor_free_h

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

print("=" * 70)
print("Pryout_bondedAnchor: d = %g, hef = %g" % (dAnchor, hef))
print("  borehole r=%g depth=%g | plate %gx%g thick %g" % (hole_r, hole_d, plate_w, plate_w, tPlate))
print("  nut s=%g m=%g | washer d1=%g d2=%g h=%g" % (sNut, hNut, dClearance, dWasherOut, tWasher))
print("  shaft protrusion %g (plate %g + washer %g + nut %g)" % (anchor_free_h, tPlate, tWasher, hNut))
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

# --- 4. fixture plate, with a d+1 clearance hole ----------------------------
# The hole is dClearance, NOT the anchor diameter: there is a
# (dClearance - dAnchor)/2 radial gap, so the plate travels that gap before it
# bears on the shaft, which is the real behaviour of a bolted fixture.
cubit.cmd("create brick x %g y %g z %g" % (plate_w, tPlate, plate_w))
v_plate = cubit.get_last_id("volume")
cubit.cmd("move volume %d y %g" % (v_plate, tPlate / 2.0))

v_plate_hole = y_cylinder(4.0 * tPlate, dClearance / 2.0, tPlate / 2.0, "surface_plate_hole")
cubit.cmd("subtract volume %d from volume %d" % (v_plate_hole, v_plate))
v_plate = cubit.get_last_id("volume")
cubit.cmd("volume %d name 'steel_plate'" % v_plate)
name_flat_surfaces(v_plate, 0.0, "surface_plate_bot")
name_flat_surfaces(v_plate, tPlate, "surface_plate_top")

# --- 5. flat washer ----------------------------------------------------------
v_washer = y_cylinder(tWasher, dWasherOut / 2.0, yWasherBot + tWasher / 2.0)
v_washer_bore = y_cylinder(4.0 * tWasher, dClearance / 2.0, yWasherBot + tWasher / 2.0)
cubit.cmd("subtract volume %d from volume %d" % (v_washer_bore, v_washer))
v_washer = cubit.get_last_id("volume")
cubit.cmd("volume %d name 'fix_washer'" % v_washer)
name_flat_surfaces(v_washer, yWasherBot, "surface_washer_bot")
name_flat_surfaces(v_washer, yNutBot, "surface_washer_top")

# --- 6. hex nut (plain prism: no chamfer, no fillets, no thread) ------------
cubit.cmd("create prism height %g sides 6 radius %g" % (hNut, eNut / 2.0))
v_nut = cubit.get_last_id("volume")
cubit.cmd("rotate volume %d angle 90 about x" % v_nut)
if alphaNut:
    cubit.cmd("rotate volume %d angle %g about y" % (v_nut, alphaNut))
cubit.cmd("move volume %d y %g" % (v_nut, yNutBot + hNut / 2.0))
# bore == anchor diameter, so the tie surfaces are exactly coincident
v_nut_bore = y_cylinder(4.0 * hNut, anchor_r, yNutBot + hNut / 2.0, "surface_nut_bore")
cubit.cmd("subtract volume %d from volume %d" % (v_nut_bore, v_nut))
v_nut = cubit.get_last_id("volume")
cubit.cmd("volume %d name 'fix_nut'" % v_nut)
name_flat_surfaces(v_nut, yNutBot, "surface_nut_bot")

# =============================================================================
# DECOMPOSITION FOR MESHING
# =============================================================================

# extend the borehole profile down through the solid concrete below the hole
cubit.cmd("webcut volume with name 'concrete_main' cylinder radius %g axis y" % hole_r)
# single cut separating the inner, finely meshed region from the outer slab
cubit.cmd("webcut volume with name 'concrete_*' cylinder radius %g axis y" % refine_r)

# plate: horizontal cut on the load plane, and a cut at the washer outer edge so
# the plate is better resolved under the washer
cubit.cmd("webcut volume with name 'steel_plate*' plane yplane offset %g" % plate_cut_h)
cubit.cmd("webcut volume with name 'steel_plate*' cylinder radius %g axis y" % (dWasherOut / 2.0))

# shaft: split at the concrete surface, the plate top and the nut bottom, giving
# four lateral bands -> mortar / plate hole / washer gap / nut. Each band is then
# its own named surface, which is what anchor_to_mortar, anchor_to_plate and
# anchor_to_nut are selected from. It also keeps every shaft piece a simple
# sweepable quarter cylinder: one volume carrying several stacked lateral bands is
# not resolved by Cubit's autoscheme.
# The y=0 cut is essential -- without it the embedded band and the plate band are
# a single surface and both anchor_to_mortar and anchor_to_plate come out empty.
cubit.cmd("webcut volume with name 'steel_anchor*' plane yplane offset 0")
cubit.cmd("webcut volume with name 'steel_anchor*' plane yplane offset %g" % tPlate)
cubit.cmd("webcut volume with name 'steel_anchor*' plane yplane offset %g" % yNutBot)

# --- symmetry: keep the z <= 0 half, then cut at x = 0 for hex meshing ------
cubit.cmd("webcut volume all with plane zplane offset 0")
to_delete = [str(v) for v in cubit.parse_cubit_list("volume", "all") if cubit.get_center_point("volume", v)[2] > 0.01]
if to_delete:
    cubit.cmd("delete volume %s" % " ".join(to_delete))
cubit.cmd("webcut volume all with plane xplane offset 0")

# =============================================================================
# GROUPING  -- one group per part, so merging never fuses two parts
# =============================================================================
GROUPS = [("grp_concrete", "concrete_*"), ("grp_mortar", "mortar*"), ("grp_anchor", "steel_anchor*"), ("grp_plate", "steel_plate*"), ("grp_washer", "fix_washer*"), ("grp_nut", "fix_nut*")]
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
cubit.cmd("volume in grp_washer size %g" % mesh_size_fastener)
cubit.cmd("volume in grp_nut size %g" % mesh_size_fastener)
cubit.cmd("volume in grp_mortar size %g" % mesh_size_mortar)

# Refine the shaft above the concrete surface. This keeps the shaft the FINER side
# of both fixture interfaces, which is what AnchorPryOut.inp assumes: it lists
# anchor_to_nut and anchor_to_plate first, i.e. as the slave surfaces, and Abaqus
# wants the finer mesh as the slave. Half the fastener size is needed, not the same
# size: the nut/washer source faces are paved and come out finer than a swept
# quarter cylinder at equal nominal size.
shaft_upper = [str(v) for v in cubit.parse_cubit_list("volume", "in grp_anchor") if cubit.get_bounding_box("volume", v)[3] > -TOL]
if shaft_upper:
    cubit.cmd("volume %s size %g" % (" ".join(shaft_upper), mesh_size_fastener / 2.0))

# Refine the plate around the clearance hole. This matters for accuracy, not just
# looks: the hole is the MASTER surface of the bearing contact pair, and Abaqus
# enforces contact against its flat facet chords, not the true cylinder. At the
# coarse steel size the hole had only 4 facets per quadrant (22.5 deg chords),
# whose sagitta is ~0.16 mm -- a third of the 0.5 mm clearance. Abaqus then
# reported the initial gap as 0.457/0.427 instead of 0.500, and the rendered
# cylinders visibly overlap. The webcut at dWasherOut/2 isolates this annulus.
plate_inner = []
for v in cubit.parse_cubit_list("volume", "in grp_plate"):
    bb = cubit.get_bounding_box("volume", v)
    if max(abs(bb[0]), abs(bb[1]), abs(bb[6]), abs(bb[7])) < dWasherOut / 2.0 + 0.1:
        plate_inner.append(str(v))
if plate_inner:
    cubit.cmd("volume %s size %g" % (" ".join(plate_inner), mesh_size_fastener))

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

# The nut is a hexagon/circle annulus: Cubit's autoscheme refuses it
# ("must have its meshing scheme explicitly specified"), so state the sweep
# direction. Pave the source face so the unequal boundary intervals are fine.
for g, ybot in (("grp_washer", yWasherBot), ("grp_nut", yNutBot)):
    cubit.cmd("surface in volume in %s with y_coord < %g scheme pave" % (g, ybot + TOL))
    cubit.cmd("volume in %s scheme sweep vector 0 1 0" % g)

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
cubit.cmd("create material 'steelPlate' property_group 'CUBIT-ABAQUS'")
cubit.cmd("create material 'steelFastener' property_group 'CUBIT-ABAQUS'")
cubit.cmd("create material 'mortar' property_group 'CUBIT-ABAQUS'")

BLOCKS = [("anchor", "grp_anchor", "hex8", "steelAnchor"), ("plate", "grp_plate", "hex8", "steelPlate"), ("mortar", "grp_mortar", "hex8", "mortar"), ("washer", "grp_washer", "hex8", "steelFastener"), ("nut", "grp_nut", "hex8", "steelFastener"), ("concrete", "grp_concrete", "hex20", "concrete")]
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
# boundaries
new_sideset("concrete_top", "surface in grp_concrete expand with y_coord = 0")
new_sideset("plate_bottom", "surface with name 'surface_plate_bot*'")
new_sideset("plate_top", "surface with name 'surface_plate_top*'")

# mortar interfaces (tied)
new_sideset("concrete_to_mortar", "surface in grp_concrete expand with name 'surface_borehole*'")
new_sideset("mortar_to_concrete", "surface in grp_mortar expand with name 'surface_mortar_outer*'")
new_sideset("mortar_to_anchor", "surface in grp_mortar expand with name 'surface_mortar_inner*'")
new_sideset("anchor_to_mortar", "surface %s" % " ".join(surfaces_named("surface_anchor_outer*", yhi=0.0)))

# shaft <-> plate hole (hard contact, with the d+1 clearance gap)
new_sideset("anchor_to_plate", "surface %s" % " ".join(surfaces_named("surface_anchor_outer*", ylo=0.0, yhi=tPlate)))
new_sideset("plate_to_anchor", "surface with name 'surface_plate_hole*'")

# washer <-> plate top (hard contact)
new_sideset("washer_bottom", "surface with name 'surface_washer_bot*'")

# nut <-> washer and nut <-> shaft (tied)
new_sideset("washer_to_nut", "surface with name 'surface_washer_top*'")
new_sideset("nut_to_washer", "surface with name 'surface_nut_bot*'")
new_sideset("nut_to_anchor", "surface with name 'surface_nut_bore*'")
new_sideset("anchor_to_nut", "surface %s" % " ".join(surfaces_named("surface_anchor_outer*", ylo=yNutBot)))

# =============================================================================
# NODESETS
# =============================================================================
print("\nnodesets:")
new_nodeset("left", "node in grp_concrete expand with x_coord = %g" % (-slab_w / 2.0))
new_nodeset("right", "node in grp_concrete expand with x_coord = %g" % (slab_w / 2.0))
new_nodeset("back", "node in grp_concrete expand with z_coord = %g" % (-slab_w / 2.0))
new_nodeset("bottom", "node in grp_concrete expand with y_coord = %g" % (-slab_h))
new_nodeset("z_symm", "node in volume all expand with z_coord = 0")
_load_sel = "node in grp_plate expand with y_coord = %g tolerance 0.01 and x_coord = %g tolerance 0.01" % (plate_cut_h, -plate_w / 2.0)
new_nodeset("plate_left_loading", _load_sel)
# Four loading node sets on the plate left face at h = 0, h/3, 2h/3, h (h = tPlate).
# plate_left_h1_3 duplicates plate_left_loading; the extra sets let the load
# height be changed in the .inp without re-meshing. The 2h/3 and h layers only
# exist because the plate mesh size divides tPlate/3, so the count is checked.
for _name, _y in (("plate_left_h0", 0.0), ("plate_left_h1_3", tPlate / 3.0),
                  ("plate_left_h2_3", 2.0 * tPlate / 3.0), ("plate_left_h1", tPlate)):
    new_nodeset(_name, "node in grp_plate expand with y_coord = %g tolerance 0.01 and x_coord = %g tolerance 0.01" % (_y, -plate_w / 2.0))

# =============================================================================
# EXPORT
# =============================================================================
STEEL = "./steel.inp"
CONCRETE = "./concrete.inp"
_steel_blocks = "%d %d %d %d %d" % (bid["anchor"], bid["plate"], bid["mortar"], bid["washer"], bid["nut"])
cubit.cmd('export abaqus "%s" block %s partial overwrite' % (STEEL, _steel_blocks))
cubit.cmd('export abaqus "%s" block %d partial overwrite' % (CONCRETE, bid["concrete"]))

# Cubit exports the linear hex blocks as C3D8R. Replace every continuum steel
# block with incompatible-mode C3D8I to avoid the reduced-integration/hourglass
# artefacts observed in the load path. Mortar remains a cohesive COH3D8 block.
# Patch the exported keywords here so every regenerated deck is directly runnable.
with open(STEEL) as fh:
    txt = fh.read()
replacements = {
    "anchor": "C3D8I",
    "plate": "C3D8I",
    "washer": "C3D8I",
    "nut": "C3D8I",
    "mortar": "COH3D8",
}
for elset, target in replacements.items():
    old = "*ELEMENT, TYPE=C3D8R, ELSET=%s" % elset
    new = "*ELEMENT, TYPE=%s, ELSET=%s" % (target, elset)
    if old in txt:
        txt = txt.replace(old, new)
        print("\npatched %s element type -> %s" % (elset, target))
    elif new in txt:
        print("\n%s element type already %s" % (elset, target))
    else:
        print("\n*** WARNING: could not find the %s *ELEMENT line to patch ***" % elset)
with open(STEEL, "w") as fh:
    fh.write(txt)

cubit.cmd("quality volume all scaled jacobian global draw histogram draw mesh")
print("\ndone: %s, %s" % (STEEL, CONCRETE))
