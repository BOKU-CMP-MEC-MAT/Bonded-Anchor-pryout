import numpy as np
from paraview.simple import *

# ---------------------------------------------------------
# Step 1: Locate the existing filter
# ---------------------------------------------------------

# Method A: Get it by its exact name in the Pipeline Browser
time_filter = FindSource('GenerateTimeSteps1') 

# Method B: Alternatively, if you already have it clicked/selected in the UI:
# time_filter = GetActiveSource()

if time_filter is None:
    print("Error: Could not find the filter. Check the name.")
else:
    # ---------------------------------------------------------
    # Step 2: Generate your new timestep distribution
    # ---------------------------------------------------------
    
    # Example: Generating 50 logarithmically spaced steps
    num_steps = 100
    new_timesteps = [1.0 + 1.0 - np.cos(i * np.pi / (num_steps )) for i in range(num_steps + 1 )]  # Cosine distribution example
    new_timesteps += [2.0 + np.cos(i * np.pi / (num_steps )) for i in range(num_steps + 1 )]  # Cosine distribution example
    print(new_timesteps)

    # ---------------------------------------------------------
    # Step 3: Apply the new values to the filter
    # ---------------------------------------------------------
    
    # Overwrite the TimeStepValues property
    time_filter.TimeStepValues = new_timesteps
    
    # Force the pipeline to update and re-evaluate with the new steps
    UpdatePipeline()
    
    # Update the UI rendering
    Render()
    
    print(f"Successfully updated '{time_filter.SMProxy.GetXMLName()}' with {len(new_timesteps)} new timesteps.")
