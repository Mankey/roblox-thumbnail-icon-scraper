# Roblox Thumbnail & Icon Scraper

A lightweight Python GUI tool for scraping and downloading Roblox game thumbnails and icons directly from Roblox's public APIs.

Search for games by keyword, browse Roblox's top charts, filter games by their current player count, and automatically download their images for use in research, datasets, machine learning, or personal projects.

## Features

- **Keyword Search:** Search Roblox games using one or multiple keywords.
- **Top Charts:** Leave the keyword field empty to scrape games from Roblox's Discover rankings.
- **Thumbnail Scraping:** Download game thumbnails in multiple resolutions.
- **Icon Scraping:** Download square Roblox game icons.
- **Player Filtering:** Filter games by their current player count.
- **Multiple Images:** Download up to 10 thumbnails per game.
- **Duplicate Detection:** Automatically skips images that have already been downloaded.
- **Download Limits:** Set maximum game and image download limits.
- **Live Preview:** View downloaded images directly inside the application.
- **Progress Logging:** Monitor scraping progress and download results.
- **Custom Output:** Choose where downloaded images are saved.
- **Stop Control:** Stop an active scraping session at any time.

## Requirements

- Windows 10/11 recommended
- Python 3.10 or newer
- Internet connection
- Tkinter (included with most standard Windows Python installations)

No third-party Python packages are required by the GUI itself.

**Important:** The current source imports `scrape_top_games.py` as its core module. Make sure this file is included in the project before running the application.

## Installation

### 1. Install Python

Download Python from:

https://www.python.org/downloads/

During installation, make sure to enable:

- Add Python to PATH

Verify your installation:

```bash
python --version
```

### 2. Download the repository

Clone the repository using Git:

```bash
git clone https://github.com/Mankey/roblox-thumbnail-icon-scraper.git
```

Alternatively, download the repository as a ZIP file using GitHub's **Code → Download ZIP** option.

### 3. Open the project folder

```bash
cd roblox-thumbnail-icon-scraper
```

### 4. Check the project files

The application requires its GUI and core scraper module:

```text
roblox-thumbnail-icon-scraper/
│
├── scraper_gui.py
├── scrape_top_games.py
└── README.md
```

If `scrape_top_games.py` is missing, the application cannot start until that dependency is added.

### 5. Launch the application

Once all required files are present, run:

```bash
python scraper_gui.py
```

The graphical interface should open automatically.

## Usage

### Searching for games

Enter one or multiple keywords separated by commas.

Examples:

```text
christmas
christmas, winter, snow
simulator, tycoon
horror, survival
```

Leave the keyword field empty to retrieve games from Roblox's top charts.

### Choosing what to download

Select one of the available download types:

| Type | Description |
|---|---|
| Thumbnails | Wide 16:9 Roblox game thumbnails |
| Icons | Square Roblox game icons |

### Image resolutions

**Thumbnails:**
- 768x432
- 576x324
- 480x270
- 384x216
- 256x144

**Icons:**
- 512x512
- 256x256
- 150x150
- 128x128

### Filtering games

Use the player count fields to target games based on how many players are currently online.

For example:

```text
Players from: 100
Players to: 100000
```

Leave either field blank to remove that limit.

### Additional settings

| Setting | Description |
|---|---|
| Per game | Number of thumbnails to download per game (1–10) |
| Search pages | Number of Roblox search pages to process |
| Max games | Maximum number of games to process |
| Max new images | Maximum number of new images to download |
| Save to | Destination folder for downloaded images |

## Downloaded Files

Images are saved to your selected output directory.

The scraper also maintains a `_scraped_manifest.csv` file containing information about downloaded images.

The manifest includes:

- Filename
- Game name
- Game universe ID
- Place ID
- Current player count
- Game genre
- Image ID
- Scrape timestamp
- Search or ranking source

Previously downloaded images are automatically detected and skipped on subsequent runs.

## Troubleshooting

**Python is not recognized**

Make sure Python is installed and added to your system PATH.

**ModuleNotFoundError: scrape_top_games**

The required `scrape_top_games.py` core module is missing. Add it to the project directory.

**No images are downloaded**

Try a different keyword, increase the search page limit, or widen your player count range.

**Some images are missing**

Roblox may not have a completed thumbnail or icon available for every game.

**The application cannot connect**

Check your internet connection and make sure Roblox's public API endpoints are accessible.

## Roblox API

This project uses Roblox's publicly accessible API endpoints:

- Game Search: `https://apis.roblox.com/search-api/omni-search`
- Game Icons: `https://thumbnails.roblox.com/v1/games/icons`
- Game Thumbnails: `https://thumbnails.roblox.com/v1/games/multiget/thumbnails`

This project is not affiliated with, endorsed by, or sponsored by Roblox Corporation.

## Disclaimer

This tool is intended for educational, research, and personal use.

Downloaded images remain subject to their respective owners' copyrights and Roblox's applicable terms and policies. Always respect applicable API usage restrictions and intellectual property rights.

## Author

**Mankey**

GitHub: https://github.com/Mankey

---

If you find this project useful, consider giving the repository a ⭐!
