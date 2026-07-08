import sys

with open("pyvista_make_ani_edge_breakout_cinematic_3.py", "r") as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if 734 <= i + 1 <= 738:
        # We will manually replace these lines
        continue
    elif 739 <= i + 1 <= 855:
        # Dedent by 4 spaces
        if line.startswith("    "):
            new_lines.append(line[4:])
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

# Insert the proper logic at line 734
insertion = """    # ==========================================
    # PART 0: CINEMATIC INTRODUCTION SETUP
    # ==========================================
"""
new_lines.insert(733, insertion)

# We need to add "if not no_intro:" around line 856
for i, line in enumerate(new_lines):
    if "intro_frames = 605" in line:
        new_lines.insert(i, "    if not no_intro:\n        print(\"\\n--- Generating Cinematic Introduction (605 frames) ---\")\n")
        break

# Now we need to indent the rest of the intro and symmetry reveal?
# Wait! "intro_frames = 605" is already indented at 8 spaces in the original!
# If we just put "if not no_intro:" at 4 spaces, then the 8-space indentation for the loops is ALREADY correct!
pass
