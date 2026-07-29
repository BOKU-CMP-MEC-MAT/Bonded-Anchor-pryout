*el file, frequency=10
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
