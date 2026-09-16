# Merged-Anchor-Plate-FreeBC

Variant of `../Merged-Anchor-Plate` (anchor merged with the plate (shared nodes, no washer/nut)).
Created 2026-09-02 from that model's `AnchorPryOut.inp`, `incfiles/` and `mesh/`.
No results are stored here yet.

## Geometry (corrected 2026-09-16)

M20, **hef = 70 mm**, plate **100 mm (x, load direction) x 250 mm (z) x 20 mm**
(half model: z from -125 to 0), slab 500 x 240 x 500 mm, the same as
`../Pryout_mergedplate`. `mesh/concrete.inp` is identical to that case's;
`mesh/steel.inp` has the same nodes, elements and sets plus the four
`plate_left_h*` sets.

## What differs from the original

1. **Concrete boundary conditions.** Only the `right` concrete face
   (x = +250 mm, the face the plate is pushed towards) is fixed in all three
   directions. The `left`, `back` and `bottom` faces are free. The original
   fixes all four faces. The z-symmetry plane is unchanged.
2. **Four loading node sets** on the plate left face (x = -50 mm) in
   `mesh/steel.inp`, h = tPlate = 20 mm:

   | set | y (mm) | note |
   |-----|--------|------|
   | `plate_left_h0`   | 0      | plate bottom |
   | `plate_left_h1_3` | 6.667  | same nodes as `plate_left_loading` |
   | `plate_left_h2_3` | 13.333 | |
   | `plate_left_h1`   | 20     | plate top |

   The deck still loads `plate_left_loading` (h/3). To load at another height
   change the set name in the two `*Boundary` lines of `AnchorPryOut.inp`.
   `fileOutput.inc` writes RF for all four sets already.

The sets were produced with `../add_plate_left_nodesets.py`; the Cubit script
in `mesh/` also creates them on a re-mesh.
