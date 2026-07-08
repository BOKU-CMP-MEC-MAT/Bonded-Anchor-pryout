import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def plot_load_displacement(folders):
    # Set up a beautiful, professional plot style
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Track if we successfully plotted any data to show the legend later
    data_plotted = False

    for folder_path in folders:
        folder = Path(folder_path)
        
        if not folder.is_dir():
            print(f"Warning: '{folder_path}' is not a valid directory. Skipping.")
            continue

        # Find all .csv files in the directory
        for csv_file in folder.glob('*.csv'):
            try:
                # Read the CSV file
                df = pd.read_csv(csv_file)
                
                # Verify required columns exist
                if 'sum_RF1' not in df.columns or 'avg_U1' not in df.columns:
                    print(f"Skipping '{csv_file.name}': Required columns ('sum_RF1', 'avg_U1') not found.")
                    continue

                # Extract and transform the data
                displacement_mm = df['avg_U1']
                
                # Multiply force by 2, and convert from N to kN (divide by 1000)
                force_kn = (df['sum_RF1'] * 2.0) / 1000.0

                # Plot the curve
                ax.plot(displacement_mm, force_kn, label=csv_file.stem, linewidth=2, alpha=0.8)
                data_plotted = True
                print(f"Successfully plotted '{csv_file.name}'")
                
            except Exception as e:
                print(f"Error reading '{csv_file.name}': {e}")

    # Finalize plot aesthetics
    if data_plotted:
        ax.set_title('Load-Displacement Curves', fontsize=16, fontweight='bold', pad=15)
        ax.set_xlabel('Displacement (mm)', fontsize=13, fontweight='bold')
        ax.set_ylabel('Force (kN)', fontsize=13, fontweight='bold')
        
        # Customize grid and ticks
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.tick_params(axis='both', which='major', labelsize=11)
        
        # Add legend
        ax.legend(title='File Name', loc='best', fontsize=10, title_fontsize=11, frameon=True)
        
        # Ensure layout fits well
        plt.tight_layout()
        
        # Display the plot
        plt.show()
    else:
        print("No valid CSV files were found or plotted.")

if __name__ == "__main__":
    # Set up argument parsing for command line usage
    parser = argparse.ArgumentParser(description="Plot load-displacement curves from one or more folders.")
    parser.add_argument(
        'folders', 
        nargs='+', 
        help="Paths to one or more folders containing the .csv files."
    )
    
    args = parser.parse_args()
    plot_load_displacement(args.folders)
