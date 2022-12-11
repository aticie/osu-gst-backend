import os
from itertools import cycle, islice

import pandas as pd
from sqlalchemy import create_engine

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(SQLALCHEMY_DATABASE_URL)


def add_mappool():
    mappools = pd.read_excel("GSTLIVE 2022 MAPPOOLS 1.xlsx")
    mappools.drop("Unnamed: 0", axis=1, inplace=True)
    mappools["youtube"] = ["https://www.youtube.com/watch?v=N1-t-RcSwaA",
                           "https://www.youtube.com/watch?v=3ORdWKEoyaY",
                           "https://www.youtube.com/watch?v=M7QDL5O8vno",
                           "https://www.youtube.com/watch?v=ry3wmRxhXkc",
                           "https://www.youtube.com/watch?v=y4IsBEYdt7o",
                           "https://www.youtube.com/watch?v=PsoFJkTtolU",
                           "https://www.youtube.com/watch?v=VI6w78iPkIk",
                           "https://www.youtube.com/watch?v=LWvwMJ1mwls",
                           "https://www.youtube.com/watch?v=7QDu4UMTH7w"]
    mappools.to_sql("mappools", con=engine, index=True, index_label="_id", if_exists="replace")


def add_results():
    results_file = "gstlive results.xlsx"
    map_columns = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9"]

    player_results = pd.read_excel(results_file, sheet_name="indiv results", header=None,
                                   names=["username"] + map_columns)
    player_results["score"] = player_results[map_columns].values.tolist()
    player_results.drop(map_columns, inplace=True, axis=1)
    player_results = player_results.explode("score")
    player_results["map_id"] = list(islice(cycle(map_columns), len(player_results)))
    player_results = player_results.reset_index()
    player_results.drop("index", axis=1, inplace=True)

    team_results = pd.read_excel(results_file, sheet_name="results", header=None,
                                 names=["teamname"] + map_columns)
    team_results.drop([33, 34, 35], inplace=True)
    team_results["score"] = team_results[map_columns].values.tolist()
    team_results.drop(map_columns, inplace=True, axis=1)
    team_results = team_results.explode("score")
    team_results["map_id"] = list(islice(cycle(map_columns), len(team_results)))
    team_results = team_results.reset_index()
    team_results.drop("index", axis=1, inplace=True)

    player_results.to_sql("player_scores", con=engine, index=True, if_exists="replace")
    team_results.to_sql("team_scores", con=engine, index=True, if_exists="replace")


if __name__ == '__main__':
    add_mappool()
