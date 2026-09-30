ETL Pipeline ReadMe

This project represents my first attempt at an ETL pipeline. I chose to conduct this process on the 2025 National Rugby League season as it is a sport I have a real passion for, and to make for a more exciting challenge than simply ripping a dataset from a repository on GitHub or a site like Kaggle.

The Pipeline Process

Extract

Extracting data from the webpage represented an interesting challenge. Take a look at the structure of the data on the webpage:

https://www.nrl.com/stats/?competition=111&season=2025

The lack of a publicly available API shows that the best way the extract data from the webpage is through a python based web scraper. Inspecting the webpage elements, the tables containing the data are react apps that load via JavaScript after the webpage loads, this means a simple web scraper using a module such as the beautifulsoup4 python library. Consulting Anthropic’s Claude to suggest a possible solution, it suggested using the selenium library to drive a headless chromium based browser through each individual stat containing table, followed by beautifulsoup4 to extract this data to a Pandas dataframe.

I went about writing a python script to make this process happen. An important consideration is that each statistic is assigned its own ‘statID’ in the URL of the website, and these IDs seemingly follow no pattern, preventing me from simply iterating through values and scraping the next in turn. The webpage follows the following formula.

…./stats/teams/?competition={competitionID}&season={SeasonYear}&stat={StatID}

Swapping teams for players returns the stats for the top 50 players in each stat category.

The men’s NRL premiership has a competitionID of 111, and for this project a season year of 2025. This analysis can be easily repeated for all years on public record by iterating through the SeasonYear variable, or for the other competitions by altering the competitionID. (Women’s Premiership = 161, Men’s origin series = 116 etc.)

For a note on statIDs, the ID for ‘points’ = 76, and ‘post contact meters’ = 1000112. To obtain the StatID’s for all stats I wanted to scrape, I deemed the quickest way to obtain all of the StatIDs I wanted was to manually read the relevant URLs. There are only 33 total categories, 21 of which I wanted for further analysis, so this was not a time consuming process.

Running the script for both teams and players returned 42 total CSVs to move forward in the pipeline.

Transform

Within the CSVs, 8 columns were returned, Season containing the year (2025), stat_category containing the mane assigned to the statID variable, stat_ID, a blank column showing the play/teams rank compared to the other 17 teams or the top 50 players in that stat. Team/Player category, containing the team name and for players, a concatenation of the players first name, surname and team (e.g NathanClearyPanthers or PayneHaasBroncos). Next was a Matches_played category, a blank column containing the stat total and finally Source_URL.

The first step to clean this data was to assign headers to blank rows and concatenate all CSVs into one file. This was conducted through a the pandas script known as ‘column_rename.py’

With two complete .csv’s, I could begin cleaning the data using excel. I began by filtering for any blank data or rows, to which I did not find any. Should any have been present, I would have seen if I could locate the missing data and input it or delete the row in its entirety should it not be present.  The next step was to break the player category containing the name and team into three columns, name, surname and team. This was achievable using excels flash fill feature after inputting the first row. This did trip up in two areas – Double barrelled surnames, and the ‘Sea Eagles’. Double barrelled surnames were not an issue as the players are easily identifiable from the forename and second part of the double barrel which was returned. For the Sea eagles, I simply filtered the team column for ‘Eagles’ and replaced all with ‘Sea Eagles’.

I chose to create an column listing the per-game averages for each statistic for both teams and players to allow for comparability down the line in the analysis pipeline. This was simply done by dividing the games played statistic by the total in each category and was done inside excel.

This process left two tables ready to proceed to the load phase:

<img width="978" height="452" alt="Image" src="https://github.com/user-attachments/assets/0c859b51-ab8d-45a8-9040-ab34eb215d05" />

Load

The two CSV’s can now be loaded into PostgreSQL to allow the use of the SQL language to query the dataset and return data that can be used to answer analytical questions, for example does a teams error count show a significant negative correlation with the amount of tries or point they score in a given season.

I plan to conduct analysis on this data as a future project.

The cleaned finalised data can be seen in the Team_stats and Player_stats .csv files. Direct outputs from the web scraper can be seen as the pre_cleaning_*_.csv files

References

Higgins, J., Gross, P., Wang, J., et al. (2004-Present), The Selenium Project. https://github.com/SeleniumHQ/ (accessed 26/09/29)

Richardson, L (2004-Present), Beautiful Soup Documentation.

The pandas development team. (2020). Pandas-dev/pandas: Pandas.
