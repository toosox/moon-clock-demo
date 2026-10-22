# Moon Clock Demo

Moon Clock Demo is a free, offline preview of Moon Clock for Linux and Windows.

The demo includes:

- the computer’s live local date and time;
- the calculated Moon graphic and current phase;
- waxing or waning direction;
- the next major Moon phase and its local date and time; and
- a calendar for previewing other dates.

Lunar age and illumination percentage are reserved for the paid edition.

## Downloads

- Linux: `dist/moon-clock-demo_0.1.0~demo1_all.deb`
- Windows: `dist/windows/MoonClock-Demo-Setup-0.1.0-demo1.exe`

## Licence

The demo may be shared without charge only as a complete, exact, unmodified
copy with `DEMO-LICENSE.txt` and all notices intact. It may not be sold,
monetised, included in a paid bundle, or commercially distributed.

This is a source-available noncommercial demo, not an open-source release.

## Local checks

```bash
python3 -m unittest -v
python3 -m py_compile app_linux.py moon_phase.py windows/app_windows.py
```
