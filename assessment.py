import requests
import sqlite3
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt


REPO_OWNER = "apache"  
REPO_NAME = "tvm" 

GITHUB_TOKEN = "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"  
BASE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits"
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

def get_db_connection():
    """
    Establish and return a connection to the SQLite database.

    Returns:
        sqlite3.Connection: The database connection object.
    """
    return sqlite3.connect("github_commits.db")


def fetch_commits():
    """
    Fetch commits from the GitHub repository using the API and return the commit data.

    This function makes paginated requests to the GitHub API to fetch commits from the past 6 months.

    Returns:
        list: A list of dictionaries containing commit information such as SHA, committer login, commit date, and message.
    """
    global BASE_URL
    six_months_ago = datetime.now() - timedelta(days=180)
    params = {"since": six_months_ago.isoformat()}
    commits = []

    while True:
        try:
            response = requests.get(BASE_URL, headers=HEADERS, params=params)
            response.raise_for_status()  # raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            for commit in data:
                committer = commit.get("author")
                date = commit['commit']['author']['date']

                if committer:
                    commits.append({
                        "sha": commit["sha"],
                        "committer_login": committer.get("login"),
                        "commit_date": date,
                        "message": commit.get("message")
                    })

            if "next" not in response.links:
                break
            BASE_URL = response.links["next"]["url"]

        except requests.RequestException as e:
            print(f"Error fetching commits: {e}")
            break

    return commits


def create_commits_table(cursor):
    """
    Create the 'commits' table in the database if it doesn't exist.

    Args:
        cursor (sqlite3.Cursor): The SQLite cursor object used to execute SQL queries.
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS commits (
            sha TEXT PRIMARY KEY,
            committer_login TEXT,
            commit_date TEXT,
            message TEXT
        )
    """)


def load_to_database(commits):
    """
    Insert the fetched commit data into the database.

    Args:
        commits (list): A list of commit dictionaries containing SHA, committer login, commit date, and message.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    create_commits_table(cursor)

    for commit in commits:
        sha = commit["sha"]
        committer_login = commit["committer_login"]
        commit_date = commit["commit_date"]
        message = commit["message"]

        cursor.execute("""
            INSERT OR IGNORE INTO commits (sha, committer_login, commit_date, message)
            VALUES (?, ?, ?, ?)
        """, (sha, committer_login, commit_date, message))

    conn.commit()
    conn.close()


def top_committers(n):
    """
    Get the top 'n' committers based on the number of commits.

    Args:
        n (int): The number of top committers to return.

    Returns:
        str: A formatted string of the top 'n' committers.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT committer_login, COUNT(*) AS commit_count
        FROM commits
        GROUP BY committer_login
        ORDER BY commit_count DESC
        LIMIT ?;
    """, (n,))

    results = cursor.fetchall()

    output = f"Top {n} Committers:\n" + "\n".join([f"{row[0]}: {row[1]} commits" for row in results])
    conn.close()

    return output


def longest_commit_streak():
    """
    Find the longest streak of consecutive commits by any committer.

    Returns:
        str: A string describing the committer with the longest streak of commits.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        WITH streaks AS (
            SELECT
                committer_login,
                commit_date,
                DATE(commit_date) - ROW_NUMBER() OVER (PARTITION BY committer_login ORDER BY commit_date) AS streak_group
            FROM commits
            GROUP BY committer_login, DATE(commit_date)
        )
        SELECT committer_login, COUNT(*) AS streak_length
        FROM streaks
        GROUP BY committer_login, streak_group
        ORDER BY streak_length DESC
        LIMIT 1;
    """)

    results = cursor.fetchall()
    output = f"Longest streak: {results[0][0]} with {results[0][1]} consecutive commits" if results else "No streaks found."
    conn.close()

    return output


def heatmap():
    """
    Generate heatmap data for commits, grouped by day of the week and hourly block.

    Returns:
        list: A list of tuples containing day of the week, hour block, and commit count.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            CASE strftime('%w', commit_date)
                WHEN '0' THEN 'Sun' WHEN '1' THEN 'Mon' WHEN '2' THEN 'Tues'
                WHEN '3' THEN 'Wed' WHEN '4' THEN 'Thurs' WHEN '5' THEN 'Fri'
                WHEN '6' THEN 'Sat' END AS day_of_week,
            CASE
                WHEN (CAST(strftime('%H', commit_date) AS INTEGER) / 3) * 3 + 3 = 24
                THEN '22-00'
                ELSE printf('%02d-%02d',
                    (CAST(strftime('%H', commit_date) AS INTEGER) / 3) * 3 + 1,
                    (CAST(strftime('%H', commit_date) AS INTEGER) / 3) * 3 + 3
                )
            END AS hour_block,
            COUNT(*) AS commit_count
        FROM commits
        GROUP BY day_of_week, hour_block;
    """)

    results = cursor.fetchall()
    conn.close()

    return results


def plot_heatmap(data, top_committers, longest_streak):
    """
    Plot a heatmap based on commit data, highlighting commit frequency by day and hour.

    Args:
        data (list): Heatmap data with commit count by day and hour block.
        top_committers (str): Information about top committers to display.
        longest_streak (str): Information about the longest commit streak to display.
    """
    day_labels = ["Sun", "Mon", "Tues", "Wed", "Thurs", "Fri", "Sat"]
    hour_labels = ["01-03", "04-06", "07-09", "10-12", "13-15", "16-18", "19-21", "22-00"]

    day_to_index = {day: idx for idx, day in enumerate(day_labels)}
    hour_to_index = {hour: idx for idx, hour in enumerate(hour_labels)}

    heatmap_matrix = np.zeros((len(day_labels), len(hour_labels)))
    for day, hour_block, commit_count in data:
        day_index = day_to_index[day]
        hour_index = hour_to_index[hour_block]
        heatmap_matrix[day_index, hour_index] = commit_count

    plt.figure(figsize=(10, 8))
    plt.title("Commit Heatmap by Day of Week and Hour Ranges")
    plt.xlabel("Hour Ranges")
    plt.ylabel("Day of the Week")

    # add metadata to the heatmap
    plt.text(0.01, 0.999, top_committers, fontsize=14, ha="left", va="top", transform=plt.gcf().transFigure)
    plt.text(0.01, 0.82, longest_streak, fontsize=14, ha="left", va="top", transform=plt.gcf().transFigure)

    plt.imshow(heatmap_matrix, cmap="Greens", aspect="auto")
    plt.colorbar(label="Commit Count")

    plt.xticks(ticks=np.arange(len(hour_labels)), labels=hour_labels)
    plt.yticks(ticks=np.arange(len(day_labels)), labels=day_labels)

    # annotate each cell with commit count
    for i in range(heatmap_matrix.shape[0]):
        for j in range(heatmap_matrix.shape[1]):
            plt.text(j, i, int(heatmap_matrix[i, j]),
                     ha="center", va="center", color="black" if heatmap_matrix[i, j] > 0 else "white")

    plt.tight_layout(rect=[0, 0, 1, 0.85])  
    plt.show()


def delete_db():
    """
    Delete the 'commits' table from the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DROP TABLE IF EXISTS commits
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    # main execution flow
    commits = fetch_commits()
    load_to_database(commits)

    top_committers_info = top_committers(5)
    longest_streak_info = longest_commit_streak()
    heatmap_data = heatmap()

    plot_heatmap(heatmap_data, top_committers_info, longest_streak_info)