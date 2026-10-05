# Edgebreakout set-up model (Cubit + Abaqus)

Half model (symmetry plane z = 0 through the anchor axis) of the region marked in red on sheets 3-6
of `../Edgebreakout_support_dimensions/`. Units mm, N, MPa, tonne. c = 150 is the parameter
(`c` in `mesh/generate_edgebreakout_setup.py`); lengths follow c: concrete Lc = c + 350 behind the
free edge, support plate at 3c from the symmetry plane.

## Run order
```
cd mesh
cubit -batch -nographics -noecho -input generate_edgebreakout_setup.py   # meshes + exports steel.inp / concrete.inp
python3 modifyMesh.py                                                    # C3D8I / COH3D8 / concrete UEL copy -> modified/
cd ..
python3 check_model.py                                                   # static checks, no solver
abaqus job=Edgebreakout user=<UEL file> ...                              # run yourself (deck: Edgebreakout.inp)
```
Cubit's `-input` driver reads one physical line at a time: keep every dict/list/call on one line.

## Axes
x = pull direction (towards the free edge at x = c), y up (concrete top y = 0, bottom y = -300),
z across (z = 0 symmetry, concrete to z = -550).

## Parts (element sets in `steel.inp` / `concrete.inp`)
| elset | geometry | type |
|---|---|---|
| dummy / concrete | 500 x 300 x 550 (x, y, z), borehole O18 x 100, breakout refinement | C3D20R + UEL U004 (GCDP, `incfiles/uelprops_GCDP.inc` unchanged from SS-160) |
| mortar | 1 mm sleeve around the anchor, 120 deep | COH3D8 |
| anchor | M16, y = -100 ... +46 (hef = 100) | C3D8I |
| sleeve | O50 x 20, bore O16, y = 0 ... 20 | C3D8I |
| washer | O56 x 6, hole O18, y = 20 ... 26 | C3D8I |
| nut | M16, 24 AF x 14, y = 26 ... 40 | C3D8I |
| csection | half C: web 20 with O50 hole, flange 20, 110 x 100 x 80 | C3D8I |
| lbeam | L100x100x10, x = -350 ... c + 100, web at z = -60 ... -50 | C3D8I |
| plate | 50 x 50 x 10 at x = c-50 ... c, z = -475 ... -425 (3c = 450) | C3D8I |
| hplate | vertical part of the support: 10 x 50 x 50 plate on the free-edge face, x = c ... c + 10, y = -50 ... 0, z = -475 ... -425 | C3D8I |
| timber | 200 x 100 under the plate, z = -550 ... -350, x = -350 ... c | C3D8I |

## Interactions in the deck
* Ties: anchor-mortar, mortar-concrete (as SS-160); sleeve bore-anchor; washer-sleeve top, washer-C web top;
  nut-washer, nut-anchor; **L web - C flange (replaces the six M14 bolts)**.
* Contact (frictionless, `*Surface Behavior, DIRECT, pressure-overclosure=HARD`): C bottom, L leg, sleeve bottom and
  support plate on the concrete top; concrete bottom on the timber; **sleeve outer / C web hole** (pressure-overclosure,
  `adjust=0.2` removes the faceting gap between the two O50 circles).
* BCs: concrete back face u2 = 0; both support plates and the timber bottom encastre (the front plate carries the horizontal reaction through frictionless contact with the free-edge face); zSYMM on all parts at z = 0.
* Load: u1 = 5 mm on the L-beam end face (x = c + 100), u2 = u3 = 0 there (jack, as in the shared model document).
* L-beam back end (x = -350): u2 = u3 = 0 (clamps), free in x; the C-section, sleeve, L-beam leg and both support plates rest on the concrete top by frictionless hard contact.

## Assumptions to confirm
* Anchor M16, hef = 100, slab 300 thick and the 1 mm mortar (O18 borehole) follow Ninčević and Wan-Wendner (2021)
  (M16 threaded bars, hef = 100 mm, slabs 100 x 250 x 30 cm) and the shared model document. The first version of this
  model used the SS-160 script values (M20, hef 120, 250) and was wrong.
* Support as two fixed 50 x 50 plates at 3c (top plate 10 thick on the slab, front plate 10 thick on the free-edge face, both aligned with the timber), frictionless contact as in the document. The paper supports the slab with two steel beams spaced 6c1 (inner faces); SS-160 used 4c.
* Timber E = 11000 MPa, nu = 0.3 (placeholder); the shared document replaces it by a frictionless rigid base.
  The paper puts a PTFE sheet between slab and steel attachment, hence frictionless contacts.
* L-beam / C-section holes and bolts are not meshed (tie of the faces instead).
* Washer O56 x 6 and nut 24 AF x 14 for M16 are chosen to fit the 60 mm clear width of the C; anchor protrudes 46.
* Concrete properties are the SS-160 calibration. Steel is elastic (anchor yield 1080 MPa not used).

## Mesh facts (c = 150)
* 49,637 hexes in total: concrete 41,401, steel parts and timber 8,236 (without the UEL copy).
* Cubit Learn Edition refuses to export a file with 50k elements or more: `mesh_size_concrete_outer = 17`
  keeps concrete at 41.4k. Do not refine without checking the count after the breakout refinement.
* Scaled Jacobian: steel parts >= 0.56, concrete min 0.0015 (35 of 41,401 elements below 0.2, all in the refinement
  transition).
* `modifyMesh.py` fails if any C3D8R is left; `check_model.py` checks bounding boxes and the sets used by the deck.
* The deck has not been run (no Abaqus here): please run it yourself.
