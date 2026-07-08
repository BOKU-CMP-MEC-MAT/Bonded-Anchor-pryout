import pyvista as pv
import numpy as np
reader = pv.get_reader('/home/matthias/Bokudrive/fischer_bonded_anchor_project/FE-GCDP-model/wanwendner_edge_breakout_c1_150/Edgebreakout_v8_rigid_support_strip_flexible_plate.case')
data = reader.read()
for p_name in ["ASSEMBLY_BOTTOM_PLATE-1_PLATE_ELEM", "ASSEMBLY_PLATE_NEG_X-1_PLATE_ELEM", "ASSEMBLY_PLATE_NEG_Y-1_PLATE_ELEM"]:
    b = data.get(p_name)
    if b:
        surf = b.extract_surface()
        surf.compute_normals(point_normals=True, inplace=True)
        print(f"{p_name} avg normal: {np.mean(surf.point_data['Normals'], axis=0)}")
