# -*- coding: utf-8 -*-

"""
This script extracts XY data (avg U1 and sum RF1) for a specific node-set
from an ODB file provided via the command line and saves it as a CSV.
"""

from odbAccess import openOdb
import sys
import os
import csv

# ---- Command Line Argument Parsing ----
# Abaqus command line arguments place the script name somewhere in sys.argv.
# The user-provided arguments typically follow it. We will grab the last argument.
if len(sys.argv) < 2:
    print("Error: No ODB file provided.")
    print("Usage: abaqus python extract_rf.py <path_to_odb_file.odb>")
    sys.exit(1)

odb_path = sys.argv[-1]

if not odb_path.lower().endswith(".odb"):
    print("Error: The provided file '{}' does not appear to be an .odb file.".format(odb_path))
    sys.exit(1)

# Generate the output CSV path (same name, .csv extension)
out_csv = os.path.splitext(odb_path)[0] + ".csv"

# ---- Inputs ----
node_set_name = "STEEL-1.PLATE_LEFT_LOADING"  # Update this if your set name changes

# ---- Open ODB ----
print("Opening ODB: {}".format(odb_path))
odb = openOdb(path=odb_path, readOnly=True)
RA = odb.rootAssembly

# ---- Resolve NodeSet (assembly- or instance-level) ----
instance_name = None
set_name = node_set_name
if "." in node_set_name:
    instance_name, set_name = node_set_name.split(".", 1)

odb_set = None

# Try assembly-level
if set_name in RA.nodeSets:
    odb_set = RA.nodeSets[set_name]

# Try instance-level (+ "-1" fallback)
if odb_set is None and instance_name is not None:
    inst_key = instance_name
    if inst_key not in RA.instances and (instance_name + "-1") in RA.instances:
        inst_key = instance_name + "-1"
    if inst_key in RA.instances:
        inst = RA.instances[inst_key]
        if set_name in inst.nodeSets:
            odb_set = inst.nodeSets[set_name]

if odb_set is None:
    odb.close()
    raise ValueError("Could not find node set '{}'".format(node_set_name))

# Validate nodes present
if len(odb_set.nodes) == 0:
    odb.close()
    raise ValueError("Node set '{}' contains 0 nodes.".format(node_set_name))

print("Resolved node set '{}', nodes: {}".format(node_set_name, len(odb_set.nodes)))

# ---- Prepare output ----
rows = [("time", "sum_RF1", "avg_U1")]

# ---- Iterate steps/frames ----
print("Extracting data...")
for step_name, step in odb.steps.items():
    for frame in step.frames:
        t = frame.frameValue
        sum_rf1 = 0.0
        u1_vals = []

        rf_field = frame.fieldOutputs["RF"] if "RF" in frame.fieldOutputs else None
        u_field  = frame.fieldOutputs["U"]  if "U"  in frame.fieldOutputs  else None

        # Sum RF1 over the node set
        if rf_field is not None:
            rf_sub = rf_field.getSubset(region=odb_set)
            for v in rf_sub.values:
                sum_rf1 += float(v.data[0])

        # Average U1 over the node set
        if u_field is not None:
            u_sub = u_field.getSubset(region=odb_set)
            for v in u_sub.values:
                u1_vals.append(float(v.data[0]))

        avg_u1 = (sum(u1_vals) / len(u1_vals)) if u1_vals else float("nan")
        rows.append((t, sum_rf1, avg_u1))

# ---- Save CSV ----
with open(out_csv, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print("Extraction complete. Created: {}".format(out_csv))
odb.close()
