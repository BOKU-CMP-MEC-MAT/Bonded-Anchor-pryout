"""Static consistency check of the Edgebreakout set-up (no solver needed).

1. bounding box of every element set against the expected geometry (c = 150, drawings sheets 3-6)
2. every set / surface referenced by Edgebreakout.inp exists in the meshes
3. no C3D8R left in the patched meshes
Run from this folder:  python3 check_model.py
"""
import re
import sys

c = 150.0
EXPECT = {
    "steel": {
        "anchor": ((-8, -100, -8), (8, 46, 0)),
        "mortar": ((-9, -100, -9), (9, 0, 0)),
        "sleeve": ((-25, 0, -25), (25, 20, 0)),
        "washer": ((-28, 20, -28), (28, 26, 0)),
        "nut": ((-13.86, 26, -12), (13.86, 40, 0)),
        "csection": ((-55, 0, -50), (55, 80, 0)),
        "lbeam": ((-350, 0, -150), (c + 100, 100, -50)),
        "plate": ((c - 50, 0, -475), (c, 10, -425)),
        "hplate": ((c, -50, -475), (c + 10, 0, -425)),
        "timber": ((c - 500, -400, -550), (c, -300, -350)),
    },
    "concrete": {"dummy": ((c - 500, -300, -550), (c, 0, 0)), "concrete": ((c - 500, -300, -550), (c, 0, 0))},
}


def read(fn):
    nodes, elems, nsets, surfs, cur, mode = {}, {}, {}, set(), None, None
    for line in open(fn):
        if line.startswith("**"):
            continue
        if line.startswith("*"):
            u = line.upper()
            mode = None
            if u.startswith("*NODE"):
                mode = "node"
            elif u.startswith("*ELEMENT"):
                mode = "elem"
                cur = re.search(r"ELSET=(\w+)", line, re.I).group(1).lower()
                elems.setdefault(cur, [])
            elif u.startswith("*NSET"):
                mode = "nset"
                cur = re.search(r"NSET=(\w+)", line, re.I).group(1).lower()
                nsets.setdefault(cur, [])
            elif u.startswith("*SURFACE"):
                surfs.add(re.search(r"NAME=(\w+)", line, re.I).group(1).lower())
            continue
        t = [x for x in line.replace("\n", "").split(",") if x.strip()]
        if mode == "node":
            nodes[int(t[0])] = (float(t[1]), float(t[2]), float(t[3]))
        elif mode == "elem":
            elems[cur].append([int(x) for x in t[1:]]) if len(t) > 1 else None
        elif mode == "nset":
            nsets[cur].extend(int(x) for x in t)
    return nodes, elems, nsets, surfs


ok = True
allsets, allsurfs = set(), set()
for part, fn in (("steel", "mesh/modified/steel.inp"), ("concrete", "mesh/modified/concrete.inp")):
    nodes, elems, nsets, surfs = read(fn)
    allsets |= set(nsets)
    allsurfs |= surfs
    txt = open(fn).read().upper()
    if "TYPE=C3D8R" in txt:
        print(f"FAIL {fn}: C3D8R present")
        ok = False
    for name, (lo, hi) in EXPECT[part].items():
        ids = set(n for e in elems.get(name, []) for n in e)
        if not ids:
            print(f"FAIL {part}.{name}: empty element set")
            ok = False
            continue
        pts = [nodes[i] for i in ids]
        mn = tuple(min(p[k] for p in pts) for k in range(3))
        mx = tuple(max(p[k] for p in pts) for k in range(3))
        good = all(abs(mn[k] - lo[k]) < 0.5 and abs(mx[k] - hi[k]) < 0.5 for k in range(3))
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {part}.{name:9s} n_el={len(elems[name]):6d} min={tuple(round(v, 2) for v in mn)} max={tuple(round(v, 2) for v in mx)}")
    for k, v in nsets.items():
        print(f"     nset {part}.{k}: {len(set(v))} nodes")

deck = open("Edgebreakout.inp").read()
refs = set(m.lower() for m in re.findall(r"(?:steel|concrete)-1\.(\w+)", deck))
elsets_ok = set(["anchor", "mortar", "sleeve", "washer", "nut", "csection", "lbeam", "plate", "hplate", "timber", "concrete", "dummy"])
for r in sorted(refs):
    if r not in allsets and r not in allsurfs and r not in elsets_ok:
        print(f"FAIL deck references steel-1/concrete-1.{r}: not in the meshes")
        ok = False
print("ALL CHECKS PASSED" if ok else "CHECKS FAILED")
sys.exit(0 if ok else 1)
