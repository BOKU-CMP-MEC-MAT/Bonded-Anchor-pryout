*Output, field, time interval=0.001, time marks=NO
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
