*Output, field, time interval=0.001, time marks=NO
*Node Output
CF, RF, TF, U, VF, NT
*Element Output, elset=concrete-1.concrete, directions=YES
LE, NFORC, PE, PEEQ, PEMAG, S, SDV
*Element Output, elset=steel-1.anchor, directions=YES
LE, NFORC, PE, PEEQ, PEMAG, S, SDV
*Element Output, elset=steel-1.plate, directions=YES
LE, NFORC, PE, PEEQ, PEMAG, S, SDV
*Element Output, elset=steel-1.washer, directions=YES
LE, NFORC, PE, PEEQ, PEMAG, S, SDV
*Element Output, elset=steel-1.nut, directions=YES
LE, NFORC, PE, PEEQ, PEMAG, S, SDV
*Element Output, elset=steel-1.mortar, directions=YES
S
** Contact output. REQUIRED explicitly: declaring *Node Output / *Element Output
** above suppresses Abaqus' default contact output, so without this the ODB holds
** no contact variables at all and contact status can only be guessed from the
** deformed shape.
**   CSTRESS -> CPRESS (contact pressure), CSHEAR
**   CDISP   -> COPEN  (clearance / overclosure), CSLIP
** No surface list, so both remaining pairs are covered: plate/concrete and
** shaft/plate-hole. (Washer/plate is a tie now, not a contact pair.)
*Contact Output
CSTRESS, CDISP
*Output, history, frequency=0

