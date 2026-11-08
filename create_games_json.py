import json
import urllib.request
import urllib.parse
import re
from pathlib import Path

# ==========================================
# CONFIGURATION
# ==========================================

GITHUB_USER = "chessgrandest-prog"
REPO_NAME = "2026"
BRANCH = "main"

GAMES_FOLDER = "games/"
THUMBNAILS_FOLDER = "thumbnails/"

JSON_FILE = Path("games.json")

# ==========================================
# HELPERS
# ==========================================

def normalize(name):
    """Normalize filenames for matching."""
    name = urllib.parse.unquote(name)
    return re.sub(r"[^a-z0-9]", "", name.lower())


def github_request(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Games-JSON-Updater"}
    )

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


# ==========================================
# GET ALL REPOSITORY FILES
# ==========================================

print("Scanning GitHub repository...")

api_url = (
    f"https://api.github.com/repos/"
    f"{GITHUB_USER}/{REPO_NAME}/git/trees/{BRANCH}?recursive=1"
)

data = github_request(api_url)

if data.get("truncated"):
    raise RuntimeError(
        "GitHub returned a truncated file list. "
        "Use the Contents API or paginate the repository scan."
    )

files = data["tree"]

games = {}
thumbnails = {}

# Find games and thumbnails
for file in files:

    if file["type"] != "blob":
        continue

    path = file["path"]

    if path.startswith(GAMES_FOLDER) and path.lower().endswith(".html"):
        filename = path.split("/")[-1]
        title = urllib.parse.unquote(filename[:-5])

        games[normalize(title)] = {
            "title": title,
            "path": path
        }

    elif path.startswith(THUMBNAILS_FOLDER):
        filename = path.split("/")[-1]
        extension = Path(filename).suffix.lower()

        if extension in [".png", ".jpg", ".jpeg", ".webp"]:
            name = Path(filename).stem

            thumbnails[normalize(name)] = path


print(f"Found {len(games)} games.")
print(f"Found {len(thumbnails)} thumbnails.")

# ==========================================
# LOAD EXISTING GAMES.JSON
# ==========================================

if JSON_FILE.exists():
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        existing_games = json.load(f)
else:
    existing_games = []

if not isinstance(existing_games, list):
    raise ValueError("games.json must contain a JSON array.")

existing_titles = {
    normalize(game["title"])
    for game in existing_games
    if "title" in game
}

# ==========================================
# GENERATE NEW ENTRIES
# ==========================================

raw_base = (
    f"https://raw.githubusercontent.com/"
    f"{GITHUB_USER}/{REPO_NAME}/{BRANCH}/"
)

added = 0
missing = 0

for game_id, game in games.items():

    title = game["title"]

    # Skip games already in JSON
    if game_id in existing_titles:
        continue

    # Find matching thumbnail
    thumbnail_path = thumbnails.get(game_id)

    if not thumbnail_path:
        print(f"[SKIPPED] No thumbnail found: {title}")
        missing += 1
        continue

    game_url = raw_base + urllib.parse.quote(
        game["path"], safe="/"
    )

    image_url = raw_base + urllib.parse.quote(
        thumbnail_path, safe="/"
    )

    new_game = {
        "title": title,
        "url": game_url,
        "image": image_url
    }

    existing_games.append(new_game)
    existing_titles.add(game_id)

    print(f"[ADDED] {title}")
    added += 1

# ==========================================
# SAVE UPDATED JSON
# ==========================================

with open(JSON_FILE, "w", encoding="utf-8") as f:
    json.dump(
        existing_games,
        f,
        indent=2,
        ensure_ascii=False
    )

print("\n================================")
print("UPDATE COMPLETE")
print("================================")
print(f"New games added: {added}")
print(f"Missing thumbnails: {missing}")
print(f"Total games in JSON: {len(existing_games)}")
print("Saved to games.json")