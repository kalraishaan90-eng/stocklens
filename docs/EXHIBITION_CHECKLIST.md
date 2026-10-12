# StockLens Exhibition Checklist

## The night before

- [ ] Charge the laptop and pack its power adapter; confirm the battery holds charge.
- [ ] Pack a phone or hotspot with enough data as a backup internet connection.
- [ ] Run `python scripts/warm_cache.py` to fetch all nine project pairs.
- [ ] Run `python scripts/build_demo_snapshots.py` while internet and API access are available.
- [ ] Run `python scripts/preflight.py` and resolve the red checks that matter for the planned demo.
- [ ] Record a backup video of a complete comparison, including the anomaly explanations and verdict.
- [ ] Keep the recording and the project report available locally.

## At the venue

- [ ] Connect to venue Wi-Fi or the backup mobile hotspot and open StockLens once before visitors arrive.
- [ ] Set browser zoom for the display and check that chart labels and the footer remain readable.
- [ ] Turn off screen sleep and automatic lock while plugged in.
- [ ] Enter browser full screen with **F11** (Windows/Linux) or **Control+Command+F** (macOS).
- [ ] Confirm the offline demo badge shows its capture date when using saved snapshots.
- [ ] Use presenter mode with **P**; press **Escape** to exit. Type `?kiosk=1` for kiosk mode.
- [ ] If the network drops, use a saved pair snapshot or play the backup recording.
