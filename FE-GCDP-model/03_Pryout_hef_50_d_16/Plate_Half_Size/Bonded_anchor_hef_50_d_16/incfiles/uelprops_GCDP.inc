*UEL Property, Elset=concrete-1.CONCRETE
** First are the material (GCDP) properties, then the element properties (none in this case)
****1****,  ****2****,  ****3****,  ****4****,  ****5****,  ****6****,  ****7****,  ****8****,  
**E         nu          fcy         fcu         fbu         ftu         Df          Ah
30000.0,    0.2,        9.3,        28,         33,         2.2,      0.85,       0.08,
**Bh        Ch          Dh          As          epsF,       lDamage     m           maxDmg
0.003,      2.0,        0.000001,   15,         0.0130,     2,          1.00,       0.99,
**drvdvMthd dTThrshHold viscosity   density    UNUSED      UNUSED      UNUSED      UNUSED      
0,          1e-12,      1e-6,       3e-9,      0,          0,          0,          0,          
**
** INTEGER PROPERTIES come always after the real (float) properties
**
** el-code  mat-code    nPropEl     nPropMat    addDef      
11412016,   114155,     1,         23,          0
