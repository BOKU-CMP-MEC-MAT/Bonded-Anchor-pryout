*el file, elset=concrete-1.concrete, position=integration point, frequency=10
  sdv
*el file, elset=steel-1.anchor, position=integration point, frequency=10
  S, E
*el file, elset=steel-1.sleeve, position=integration point, frequency=10
  S, E
*el file, elset=steel-1.csection, position=integration point, frequency=10
  S, E
*el file, elset=steel-1.lbeam, position=integration point, frequency=10
  S, E
*node file, frequency=10
  u, nt
*node file, nset=steel-1.load_end, frequency=10
  rf
