import os

# github_config.py
GITHUB_TOKEN = os.getenv("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")
REPO_OWNER = "kamran98arbaaz"
REPO_NAME = "loopin-home"
FILE_PATH = "updates.json"
BRANCH = "master"


GITHUB_FILE_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FILE_PATH}"
