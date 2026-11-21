"""Window for downloading Roblox game thumbnails or icons.

  - Keywords: search Roblox like the site's search box ("christmas", or several: "christmas, winter, snow").
    Leave blank to use the top charts (every ranking list on the discover page) instead.
  - Type: Thumbnails (wide 16:9 images) or Icons (square game icons).
  - Players: only games with this many people playing right now, e.g. 100 to 100000. Blank = no limit.

Run:  python tools\\scraper_gui.py   (or scraper_gui.bat)
Uses the same skip-what-you-already-have logic as scrape_top_games.py.
"""
import csv
import queue
import re
import sys
import threading
import time
import tkinter as tk
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from tkinter import filedialog, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scrape_top_games as core  # noqa: E402

THUMB_OUT = core.DEFAULT_OUT
ICON_OUT = core.ROOT / "Training Icons"
THUMB_SIZES = ["768x432", "576x324", "480x270", "384x216", "256x144"]
ICON_SIZES = ["512x512", "256x256", "150x150", "128x128"]
ICON_HASH = re.compile(r"_([0-9a-f]{32})\.(png|jpe?g|webp)$", re.I)   # icon_<game>_<hash>.png
URL_HASH = re.compile(r"-([0-9a-f]{32})/", re.I)                      # .../180DAY-<hash>/512/512/...

BG, PANEL, FG, MUTED, ACCENT = "#15171c", "#1f232b", "#e6e8ec", "#8b93a1", "#4f8cff"


# ---------------------------------------------------------------- data

def search_games(keyword, max_pages, log, stop):
    """Games from Roblox's search for one keyword, in search order."""
    sid, token, games = str(uuid.uuid4()), None, []
    for page in range(max_pages):
        if stop.is_set():
            break
        q = {"searchQuery": keyword, "sessionId": sid, "pageType": "all"}
        if token:
            q["pageToken"] = token
        data = core.get_json(f"https://apis.roblox.com/search-api/omni-search?{urllib.parse.urlencode(q)}")
        for group in data.get("searchResults", []):
            if group.get("contentGroupType") != "Game":
                continue
            for g in group.get("contents", []):
                if g.get("contentType", "Game") == "Game" and not g.get("isSponsored"):
                    games.append({**g, "sort": f"search:{keyword}"})
        token = data.get("nextPageToken")
        log(f"  '{keyword}' page {page + 1}: {len(games)} games so far")
        if not token:
            break
        time.sleep(0.3)
    return games


def icons(universe_ids, size, stop):
    """{universeId: [(hash, url)]} for each game's square icon."""
    out = {}
    for i in range(0, len(universe_ids), 50):
        if stop.is_set():
            break
        batch = universe_ids[i:i + 50]
        for attempt in range(4):
            q = urllib.parse.urlencode({"universeIds": ",".join(map(str, batch)), "size": size,
                                        "format": "Png", "isCircular": "false"})
            data = core.get_json(f"https://thumbnails.roblox.com/v1/games/icons?{q}")["data"]
            pending = any(e["state"] == "Pending" for e in data)
            for e in data:
                m = URL_HASH.search(e.get("imageUrl") or "")
                if e["state"] == "Completed" and m:
                    out[e["targetId"]] = [(m.group(1).lower(), e["imageUrl"])]
            if not pending:
                break
            time.sleep(2)
        time.sleep(0.3)
    return out


def thumbnails(universe_ids, per_game, size, stop):
    """Like core.thumbnails but with a chosen size and a stop button."""
    out = {}
    for i in range(0, len(universe_ids), 25):
        if stop.is_set():
            break
        batch = universe_ids[i:i + 25]
        for attempt in range(4):
            q = urllib.parse.urlencode({"universeIds": ",".join(map(str, batch)), "countPerUniverse": per_game,
                                        "defaults": "true", "size": size, "format": "Png", "isCircular": "false"})
            data = core.get_json(f"https://thumbnails.roblox.com/v1/games/multiget/thumbnails?{q}")["data"]
            pending = False
            for e in data:
                thumbs = e.get("thumbnails") or []
                pending |= any(t["state"] == "Pending" for t in thumbs)
                out[e["universeId"]] = [(str(t["targetId"]), t["imageUrl"]) for t in thumbs
                                        if t["state"] == "Completed" and t.get("imageUrl")]
            if not pending:
                break
            time.sleep(2)
        time.sleep(0.3)
    return out


def already_have(out: Path, manifest: Path):
    ids = core.already_have(out, manifest)
    for p in out.rglob("*"):
        m = ICON_HASH.search(p.name) if p.is_file() else None
        if m:
            ids.add(m.group(1).lower())
    return ids


def run_scrape(opts, log, preview, stop):
    out: Path = opts["out"]
    out.mkdir(parents=True, exist_ok=True)
    manifest = out / "_scraped_manifest.csv"
    have = already_have(out, manifest)
    log(f"Already have {len(have)} images in {out.name} - those will be skipped.")

    # 1. find games
    games, seen = [], set()
    if opts["keywords"]:
        for kw in opts["keywords"]:
            log(f"Searching '{kw}'...")
            for g in search_games(kw, opts["pages"], log, stop):
                if g["universeId"] not in seen:
                    seen.add(g["universeId"])
                    games.append(g)
    else:
        log("Fetching top charts...")
        games = core.ranked_games(None, 0)
    if stop.is_set():
        return log("Stopped.")

    lo, hi = opts["min_players"], opts["max_players"]
    before = len(games)
    games = [g for g in games if (lo is None or (g.get("playerCount") or 0) >= lo)
             and (hi is None or (g.get("playerCount") or 0) <= hi)]
    log(f"{before} games found, {len(games)} within the player range.")
    if opts["max_games"]:
        games = games[:opts["max_games"]]
    if not games:
        return log("Nothing to download. Try a wider player range or another keyword.")

    # 2. image lists
    log(f"Fetching {opts['kind'].lower()} for {len(games)} games...")
    ids = [g["universeId"] for g in games]
    if opts["kind"] == "Icons":
        images = icons(ids, opts["size"], stop)
    else:
        images = thumbnails(ids, opts["per_game"], opts["size"], stop)

    # 3. download
    prefix = "icon" if opts["kind"] == "Icons" else "rbx"
    saved = skipped = missing = 0
    new_file = not manifest.exists()
    with open(manifest, "a", newline="", encoding="utf-8") as mf:
        w = csv.writer(mf)
        if new_file:
            w.writerow(["file", "rank", "game", "universeId", "placeId", "players", "genre", "sort", "imageId", "scraped"])
        for rank, g in enumerate(games, 1):
            if stop.is_set():
                log("Stopped.")
                break
            if opts["max_new"] and saved >= opts["max_new"]:
                log(f"Reached the limit of {opts['max_new']} new images.")
                break
            imgs = images.get(g["universeId"], [])
            if not imgs:
                missing += 1
                continue
            for image_id, url in imgs:
                if image_id in have:
                    skipped += 1
                    continue
                if (opts["max_new"] and saved >= opts["max_new"]) or stop.is_set():
                    break
                path = out / f"{prefix}_{core.slug(g['name'])}_{image_id}.png"
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": core.UA["User-Agent"]})
                    with urllib.request.urlopen(req, timeout=60) as r:
                        path.write_bytes(r.read())
                except Exception as e:
                    log(f"  {g['name'][:40]}: download failed: {e}")
                    continue
                saved += 1
                have.add(image_id)
                w.writerow([path.name, rank, g["name"], g["universeId"], g.get("rootPlaceId"), g.get("playerCount"),
                            g.get("genreL1", ""), g["sort"], image_id, time.strftime("%Y-%m-%d %H:%M")])
                mf.flush()
                log(f"  {g['name'][:40]:<40} {g.get('playerCount') or 0:>8,} playing  -> {path.name}")
                preview(path)
                time.sleep(0.15)
    log(f"\nDone: {saved} new, {skipped} already had, {missing} games had no image.")


# ---------------------------------------------------------------- window

class App:
    def __init__(self, root):
        self.root, self.q, self.stop, self.worker, self._img = root, queue.Queue(), threading.Event(), None, None
        root.title("Roblox Thumbnail Scraper")
        root.configure(bg=BG)
        root.minsize(760, 560)
        self._style()

        form = ttk.Frame(root, padding=14, style="Panel.TFrame")
        form.pack(fill="x", padx=12, pady=(12, 6))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        def label(text, r, c):
            ttk.Label(form, text=text, style="Panel.TLabel").grid(row=r, column=c, sticky="w", padx=(0, 8), pady=5)

        label("Keywords", 0, 0)
        self.keywords = tk.StringVar(value="christmas")
        ttk.Entry(form, textvariable=self.keywords).grid(row=0, column=1, columnspan=3, sticky="ew", pady=5)
        ttk.Label(form, text="comma-separated; blank = top charts", style="Muted.TLabel").grid(
            row=1, column=1, columnspan=3, sticky="w")

        label("Type", 2, 0)
        self.kind = tk.StringVar(value="Thumbnails")
        kind = ttk.Combobox(form, textvariable=self.kind, values=["Thumbnails", "Icons"], state="readonly", width=14)
        kind.grid(row=2, column=1, sticky="w", pady=5)
        kind.bind("<<ComboboxSelected>>", lambda e: self._kind_changed())

        label("Size", 2, 2)
        self.size = tk.StringVar(value=THUMB_SIZES[0])
        self.size_box = ttk.Combobox(form, textvariable=self.size, values=THUMB_SIZES, state="readonly", width=12)
        self.size_box.grid(row=2, column=3, sticky="w", pady=5)

        label("Players from", 3, 0)
        prow = ttk.Frame(form, style="Panel.TFrame")
        prow.grid(row=3, column=1, columnspan=3, sticky="w", pady=5)
        self.min_p, self.max_p = tk.StringVar(value="100"), tk.StringVar(value="100000")
        ttk.Entry(prow, textvariable=self.min_p, width=12).pack(side="left")
        ttk.Label(prow, text="  to  ", style="Panel.TLabel").pack(side="left")
        ttk.Entry(prow, textvariable=self.max_p, width=12).pack(side="left")
        ttk.Label(prow, text="   playing now (blank = no limit)", style="Muted.TLabel").pack(side="left")

        label("Per game", 4, 0)
        self.per_game = tk.StringVar(value="1")
        self.per_box = ttk.Spinbox(form, from_=1, to=10, textvariable=self.per_game, width=6)
        self.per_box.grid(row=4, column=1, sticky="w", pady=5)

        label("Search pages", 4, 2)
        self.pages = tk.StringVar(value="10")
        ttk.Spinbox(form, from_=1, to=50, textvariable=self.pages, width=6).grid(row=4, column=3, sticky="w", pady=5)

        label("Max games", 5, 0)
        self.max_games = tk.StringVar(value="")
        ttk.Entry(form, textvariable=self.max_games, width=8).grid(row=5, column=1, sticky="w", pady=5)

        label("Max new images", 5, 2)
        self.max_new = tk.StringVar(value="")
        ttk.Entry(form, textvariable=self.max_new, width=8).grid(row=5, column=3, sticky="w", pady=5)

        label("Save to", 6, 0)
        self.out = tk.StringVar(value=str(THUMB_OUT))
        ttk.Entry(form, textvariable=self.out).grid(row=6, column=1, columnspan=2, sticky="ew", pady=5)
        ttk.Button(form, text="Browse...", command=self._browse).grid(row=6, column=3, sticky="w", padx=(8, 0))

        bar = ttk.Frame(root, style="Bg.TFrame")
        bar.pack(fill="x", padx=12, pady=4)
        self.go = ttk.Button(bar, text="Start", style="Accent.TButton", command=self._start)
        self.go.pack(side="left")
        self.halt = ttk.Button(bar, text="Stop", command=self.stop.set, state="disabled")
        self.halt.pack(side="left", padx=8)
        ttk.Button(bar, text="Open folder", command=self._open_folder).pack(side="left")
        self.status = ttk.Label(bar, text="Ready", style="Muted.TLabel")
        self.status.pack(side="right")

        body = ttk.Frame(root, style="Bg.TFrame")
        body.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        self.log_box = tk.Text(body, bg=PANEL, fg=FG, insertbackground=FG, relief="flat", wrap="none",
                               font=("Consolas", 9), padx=8, pady=6)
        self.log_box.pack(side="left", fill="both", expand=True)
        self.pic = tk.Label(body, bg=PANEL, fg=MUTED, text="latest image", width=40)
        self.pic.pack(side="right", fill="y", padx=(8, 0))

        self._kind_changed()
        root.after(100, self._pump)

    def _style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, bordercolor="#2c313b",
                    lightcolor=PANEL, darkcolor=PANEL, font=("Segoe UI", 10))
        s.configure("Bg.TFrame", background=BG)
        s.configure("Panel.TFrame", background=PANEL)
        s.configure("Panel.TLabel", background=PANEL, foreground=FG)
        s.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        s.configure("TEntry", fieldbackground=BG, foreground=FG, insertcolor=FG)
        s.configure("TSpinbox", fieldbackground=BG, foreground=FG, arrowcolor=FG, background=PANEL)
        s.configure("TCombobox", fieldbackground=BG, foreground=FG, arrowcolor=FG, background=PANEL)
        s.map("TCombobox", fieldbackground=[("readonly", BG)], foreground=[("readonly", FG)],
              selectbackground=[("readonly", BG)], selectforeground=[("readonly", FG)])
        s.configure("TButton", background="#2a2f3a", foreground=FG, padding=(12, 5))
        s.map("TButton", background=[("active", "#353b48"), ("disabled", "#1c1f26")],
              foreground=[("disabled", MUTED)])
        s.configure("Accent.TButton", background=ACCENT, foreground="white")
        s.map("Accent.TButton", background=[("active", "#3f7aeb"), ("disabled", "#2a3a5c")])
        self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)

    def _kind_changed(self):
        icon = self.kind.get() == "Icons"
        sizes = ICON_SIZES if icon else THUMB_SIZES
        self.size_box["values"] = sizes
        self.size.set(sizes[0])
        self.per_box.configure(state="disabled" if icon else "normal")  # a game has only one icon
        # switch the default folder, but leave a folder the user picked alone
        if self.out.get() in (str(THUMB_OUT), str(ICON_OUT)):
            self.out.set(str(ICON_OUT if icon else THUMB_OUT))

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.out.get() or str(core.ROOT))
        if d:
            self.out.set(d)

    def _open_folder(self):
        p = Path(self.out.get())
        p.mkdir(parents=True, exist_ok=True)
        import os
        os.startfile(p)

    def _num(self, var, name):
        t = var.get().replace(",", "").strip()
        if not t:
            return None
        if not t.isdigit():
            raise ValueError(f"{name} must be a whole number")
        return int(t)

    def _start(self):
        try:
            opts = {
                "keywords": [k.strip() for k in self.keywords.get().split(",") if k.strip()],
                "kind": self.kind.get(), "size": self.size.get(),
                "min_players": self._num(self.min_p, "Players from"),
                "max_players": self._num(self.max_p, "Players to"),
                "per_game": max(1, min(10, self._num(self.per_game, "Per game") or 1)),
                "pages": max(1, self._num(self.pages, "Search pages") or 10),
                "max_games": self._num(self.max_games, "Max games") or 0,
                "max_new": self._num(self.max_new, "Max new images") or 0,
                "out": Path(self.out.get().strip() or THUMB_OUT),
            }
        except ValueError as e:
            self.status.configure(text=str(e))
            return
        if opts["min_players"] is not None and opts["max_players"] is not None and opts["min_players"] > opts["max_players"]:
            self.status.configure(text="'Players from' is bigger than 'to'")
            return
        self.log_box.delete("1.0", "end")
        self.stop.clear()
        self.go.configure(state="disabled")
        self.halt.configure(state="normal")
        self.status.configure(text="Working...")

        def work():
            try:
                run_scrape(opts, lambda m: self.q.put(("log", m)), lambda p: self.q.put(("img", p)), self.stop)
            except Exception as e:
                self.q.put(("log", f"Error: {e}"))
            self.q.put(("done", None))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _pump(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "log":
                    self.log_box.insert("end", val + "\n")
                    self.log_box.see("end")
                elif kind == "img":
                    self._show(val)
                elif kind == "done":
                    self.go.configure(state="normal")
                    self.halt.configure(state="disabled")
                    self.status.configure(text="Ready")
        except queue.Empty:
            pass
        self.root.after(100, self._pump)

    def _show(self, path):
        try:
            img = tk.PhotoImage(file=str(path))
            factor = max(1, -(-img.width() // 280))  # shrink to ~280px wide
            self._img = img.subsample(factor, factor)
            self.pic.configure(image=self._img, text="")
        except tk.TclError:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
