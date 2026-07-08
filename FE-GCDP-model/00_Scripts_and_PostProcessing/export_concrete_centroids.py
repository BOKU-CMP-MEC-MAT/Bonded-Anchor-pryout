#!/usr/bin/env python3
import pyvista as pv
import numpy as np
import argparse
import sys
import os
import warnings

# Suppress PyVista warnings to keep output clean
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*algorithm.*")

def find_block(multiblock, name):
    """
    Finds a block in the multiblock dataset.
    First tries an exact case-insensitive match, then suffix match, then substring match.
    """
    target = name.upper()
    
    # 1. Exact Match
    def search_exact(block):
        for i in range(block.n_blocks):
            block_name = block.get_block_name(i)
            if block_name is not None and block_name.upper() == target:
                return block[i], block_name
            if isinstance(block[i], pv.MultiBlock):
                res = search_exact(block[i])
                if res is not None:
                    return res
        return None

    res = search_exact(multiblock)
    if res is not None:
        return res
        
    # 2. Suffix Match
    def search_suffix(block):
        for i in range(block.n_blocks):
            block_name = block.get_block_name(i)
            if block_name is not None:
                bn_upper = block_name.upper()
                if bn_upper.endswith(target) or bn_upper.endswith("_" + target) or bn_upper.endswith("-" + target):
                    return block[i], block_name
            if isinstance(block[i], pv.MultiBlock):
                res = search_suffix(block[i])
                if res is not None:
                    return res
        return None

    res = search_suffix(multiblock)
    if res is not None:
        return res

    # 3. Substring Match
    def search_substring(block):
        for i in range(block.n_blocks):
            block_name = block.get_block_name(i)
            if block_name is not None and target in block_name.upper():
                return block[i], block_name
            if isinstance(block[i], pv.MultiBlock):
                res = search_substring(block[i])
                if res is not None:
                    return res
        return None

    return search_substring(multiblock)

def main():
    parser = argparse.ArgumentParser(
        description="Export cell centroids of a concrete block where a variable exceeds a threshold."
    )
    parser.add_argument("filename", type=str, help="Path to the EnSight .case file")
    parser.add_argument("variable", type=str, help="Name of the variable to threshold (e.g., damage, alphaD)")
    parser.add_argument("threshold", type=float, help="Threshold value")
    parser.add_argument("output", type=str, help="Path to the output space-separated .csv file")
    parser.add_argument("-b", "--block", type=str, default="CONCRETE",
                        help="Block name to find (default: CONCRETE, matches ASSEMBLY_CONCRETE-1_CONCRETE)")
    parser.add_argument("-t", "--time", type=float, default=None,
                        help="Time value to read (defaults to the last timestep)")
    parser.add_argument("-s", "--step", type=int, default=None,
                        help="Timestep index to read (defaults to the last timestep)")
    args = parser.parse_args()

    if not os.path.exists(args.filename):
        print(f"Error: Case file '{args.filename}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"Reading case file: {args.filename}")
    reader = pv.get_reader(args.filename)
    
    # Determine the time step to load
    available_times = np.array(reader.time_values)
    if not len(available_times):
        print("Error: No timesteps found in the case file.", file=sys.stderr)
        sys.exit(1)
        
    if args.step is not None:
        if args.step < 0 or args.step >= len(available_times):
            print(f"Error: Step index {args.step} is out of bounds (0 to {len(available_times)-1}).", file=sys.stderr)
            sys.exit(1)
        time_val = available_times[args.step]
        print(f"Selected step index {args.step} (time: {time_val})")
    elif args.time is not None:
        idx = np.argmin(np.abs(available_times - args.time))
        time_val = available_times[idx]
        print(f"Selected closest time: {time_val} (requested: {args.time})")
    else:
        time_val = available_times[-1]
        print(f"Selected last time step: {time_val}")

    reader.set_active_time_value(time_val)
    data = reader.read()

    # Find target block
    res = find_block(data, args.block)
    if res is None:
        print(f"Error: Block matching '{args.block}' not found in the dataset.", file=sys.stderr)
        print("\nAvailable blocks in dataset:", file=sys.stderr)
        def list_blocks(block, prefix=""):
            if isinstance(block, pv.MultiBlock):
                for i in range(block.n_blocks):
                    name = block.get_block_name(i)
                    print(f"{prefix}- {name}", file=sys.stderr)
                    list_blocks(block[i], prefix + "  ")
        list_blocks(data)
        sys.exit(1)

    block, actual_block_name = res
    print(f"Found target block: '{actual_block_name}'")

    # Locate the variable in the block
    var_name = args.variable
    if var_name in block.cell_data:
        values = block.cell_data[var_name]
    elif var_name in block.point_data:
        print(f"Variable '{var_name}' found in point data. Converting to cell data...")
        block_cell = block.point_data_to_cell_data()
        values = block_cell.cell_data[var_name]
        block = block_cell
    else:
        print(f"Error: Variable '{var_name}' not found in cell or point data of block '{actual_block_name}'.", file=sys.stderr)
        print("\nAvailable cell data keys:", list(block.cell_data.keys()), file=sys.stderr)
        print("Available point data keys:", list(block.point_data.keys()), file=sys.stderr)
        sys.exit(1)

    # Handle multi-component arrays (e.g. vector fields) by computing magnitude
    if len(values.shape) > 1 and values.shape[1] > 1:
        print(f"Warning: Variable '{var_name}' has multiple components. Using component magnitude.")
        values = np.linalg.norm(values, axis=1)

    # Filter cells exceeding the threshold
    mask = values > args.threshold
    n_matching = np.sum(mask)
    print(f"Cells exceeding threshold ({args.threshold}): {n_matching} out of {block.n_cells}")

    if n_matching == 0:
        print(f"Writing empty output file to: {args.output}")
        # Save an empty array
        np.savetxt(args.output, np.empty((0, 3)), delimiter=" ")
    else:
        # Extract matching cells
        filtered_mesh = block.extract_cells(mask)
        # Compute cell centers (centroids)
        centroids = filtered_mesh.cell_centers().points
        print(f"Exporting {centroids.shape[0]} centroids to: {args.output}")
        # Save as space-separated CSV coordinates
        np.savetxt(args.output, centroids, fmt="%.8f", delimiter=" ")

    print("Success!")

if __name__ == "__main__":
    main()
