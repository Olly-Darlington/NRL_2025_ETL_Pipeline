"""
Rename the blank stat columns in team/player CSV files and concatenate
all CSV files into combined team and player statistics libraries.

Outputs two files:
    combined_team_stats.csv
    combined_player_stats.csv
"""

import os
import pandas as pd


# Dir config

pwd = r"YOUR_DIRECTORY_PATH"  # Replace with your actual directory path

team_dir = os.path.join(pwd, "team_stats")
player_dir = os.path.join(pwd, "player_stats")

# load, rename columns, combine

def combine_stats(input_dir, output_file):

    csv_files = [
        file for file in os.listdir(input_dir)
        if file.lower().endswith(".csv")
    ]

    dataframes = []

    for file in sorted(csv_files):
        file_path = os.path.join(input_dir, file)

        print(f"[INFO] Reading: {file}")

        df = pd.read_csv(file_path)

        # Rename the 4th and 8th columns
        df = df.rename(
            columns={
                df.columns[3]: "Rank",
                df.columns[7]: "stat_count"
            }
        )

        dataframes.append(df)

    # Concatenate all dataframes
    output_df = pd.concat(
        dataframes,
        ignore_index=True
    )

    # Save combined dataframe
    output_path = os.path.join(pwd, output_file)

    output_df.to_csv(
        output_path,
        index=False
    )

# combine team stats

combine_stats(team_dir, "combined_team_stats.csv")

# combine player stats

combine_stats(player_dir, "combined_player_stats.csv")
 
