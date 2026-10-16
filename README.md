<h1 align="center">Filament Library</h1>

<p align="center">
  A phone-friendly page that shows every 3D-printer filament colour I own, in Latvian or English.
</p>

<p align="center">
  <a href="https://supred502.github.io/Filiment_Library/"><b>Open the library</b></a>
</p>

<p align="center">
  <img src="docs/screenshots/english.png" alt="Filament list in English" width="300">
  <img src="docs/screenshots/latvian.png" alt="Filament list in Latvian" width="300">
</p>

## Features

- A colour swatch, name and brand for every owned filament, grouped by material (PLA, PETG, …)
- Transparent filaments shown with a see-through checker pattern
- **LV / EN** switch; colour names are translated too, and the choice is remembered on each device
- Works on any phone, no app to install

## Updating the list

1. In HueForge, export the personal filament library (`personal_library_export.json`).
2. On this repo, open **Add file → Upload files** and drop in the new `personal_library_export.json`, replacing the old one.
3. Commit. The page updates on every device within a minute or two.

## Run locally

```bash
python3 -m http.server
```

Then open <http://localhost:8000>. (Opening `index.html` straight from disk won't load the list, because browsers block reading local files.)
