"""
This is a script to rename blank stat columns and concatenate the returned .csv files into seperate player and team files as combined_<player/team>_stats.csv.
This will allow for the concatenation of all stat dataframes into one dataframe for analysis.
"""
import os
import pandas as pd 

pwd = " **DIRECTORY PATH** "
    # **DIRECTORY PATH/FILE_PATH replaced with file address
for file in os.listdir(os.path.join(" **FILE_PATH_TEAMS ** ")):
    if file.endswith(".csv"):
        file_path = os.path.join(" **FILE_PATH_TEAMS** ", file)
        df = pd.read_csv(file_path)

output_df = pd.concat([pd.read_csv(os.path.join(pwd, file)).rename(columns={df.columns[3]: 'Stat_Rank', df.columns[7]: 'stat_count'}) for file in os.listdir(os.path.join(pwd, "team_stats")) if file.endswith(".csv")], ignore_index=True)
output_df.to_csv(os.path.join(pwd, "combined_team_stats.csv"), index=False)

for file in os.listdir(os.path.join(" **FLE_PATH_PLAYERS** ")):
    if file.endswith(".csv"):
        file_path = os.path.join(" **FILE_PATH_PLAYERS", file)
        df = pd.read_csv(file_path)

output_df = pd.concat([pd.read_csv(os.path.join(pwd, file)).rename(columns={df.columns[3]: 'Stat_Rank', df.columns[7]: 'stat_count'}) for file in os.listdir(os.path.join(pwd, "player_stats")) if file.endswith(".csv")], ignore_index=True)
output_df.to_csv(os.path.join(pwd, "combined_player_stats.csv"), index=False)
