*el file, elset=concrete-1.concrete, position=integration point, frequency=10
  sdv
*el file, elset=steel-1.anchor, position=integration point, frequency=10
  S, E
*el file, elset=steel-1.plate, position=integration point, frequency=10
  S, E
*el file, elset=steel-1.mortar, position=integration point, frequency=10
  S, E
*node file, frequency=10
  u, nt
*node file, nset=steel-1.plate_left_loading, frequency=10
  rf
