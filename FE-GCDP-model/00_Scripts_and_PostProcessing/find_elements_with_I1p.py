from paraview.simple import *
from paraview import servermanager
import csv

# ==========================================================
# CONFIGURATION
# ==========================================================
VARIABLE_NAME = "I1p"  
THRESHOLD_VALUE = .05

# This path will now resolve on your LOCAL client machine
OUTPUT_CSV_PATH = "./centroid_coordinates_of_elements_to_refine.csv" 

# Set your desired decimal precision
DECIMAL_PRECISION = 10
# ==========================================================

def fetch_and_save_centroids():
    active_source = GetActiveSource()
    if not active_source:
        print("Error: No active source selected. Please select your dataset.")
        return

    print("Step 1: Applying Threshold...")
    threshold = Threshold(Input=active_source)
    threshold.Scalars = ['CELLS', VARIABLE_NAME]
    
    try:
        threshold.ThresholdMethod = 'Between'
        threshold.LowerThreshold = THRESHOLD_VALUE
        threshold.UpperThreshold = 1e30
    except AttributeError:
        threshold.ThresholdRange = [THRESHOLD_VALUE, 1e30]

    print("Step 2: Calculating Cell Centers...")
    cell_centers = CellCenters(Input=threshold)
    cell_centers.VertexCells = 1

    print("Step 3: Merging Blocks (Crucial for MultiBlock data)...")
    # This filter flattens the multi-block hierarchy into a single dataset
    merged_data = MergeBlocks(Input=cell_centers)

    # Force ParaView to evaluate the pipeline on the server
    UpdatePipeline()

    print("Step 4: Fetching data from server to client...")
    # Fetch now pulls the flattened UnstructuredGrid instead of the MultiBlock object
    local_data = servermanager.Fetch(merged_data)

    if not local_data:
        print("Error: Failed to fetch data to the client.")
        return

    num_points = local_data.GetNumberOfPoints()
    print(f"Step 5: Writing {num_points} coordinates to local CSV...")

    with open(OUTPUT_CSV_PATH, mode='w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        
        for i in range(num_points):
            # GetPoint now works because the dataset is a single, merged block
            x, y, z = local_data.GetPoint(i)
            
            formatted_row = [
                f"{x:.{DECIMAL_PRECISION}f}",
                f"{y:.{DECIMAL_PRECISION}f}",
                f"{z:.{DECIMAL_PRECISION}f}"
            ]
            
            csv_writer.writerow(formatted_row)

    print(f"Success: High-precision coordinates saved to {OUTPUT_CSV_PATH}")

# Run the pipeline
fetch_and_save_centroids()
