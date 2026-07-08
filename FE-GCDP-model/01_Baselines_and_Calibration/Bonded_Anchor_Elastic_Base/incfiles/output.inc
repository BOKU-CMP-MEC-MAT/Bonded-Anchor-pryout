*Output, field, time interval=0.001, time marks=NO
*Node Output
CF, RF, TF, U, VF, NT
*Element Output, elset=concrete-1.concrete, directions=YES
LE, NFORC, PE, PEEQ, PEMAG, S, SDV
*Element Output, elset=steel-1.anchor, directions=YES
LE, NFORC, PE, PEEQ, PEMAG, S, SDV
*Element Output, elset=steel-1.plate, directions=YES
LE, NFORC, PE, PEEQ, PEMAG, S, SDV
*Element Output, elset=steel-1.mortar, directions=YES
S
*Output, history, frequency=0

