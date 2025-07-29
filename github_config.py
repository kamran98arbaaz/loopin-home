import os

# github_config.py
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "kamran98arbaaz"
REPO_NAME = "loopin-home"
FILE_PATH = "updates.json"
BRANCH = "master"


GITHUB_FILE_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FILE_PATH}"
