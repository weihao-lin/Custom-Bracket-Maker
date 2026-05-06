# Custom Bracket Maker (Windows-friendly)

A desktop bracket maker with a working UI built using Python + Tkinter.

## Features

- Up to **512 participants** entered as newline-separated names.
- Automatic handling of non-power-of-two sizes with randomized **bye slots**.
- Bracket title field.
- Bracket modes:
  - **Regular bracket** (single elimination, base mode)
  - **Double elimination** (basic winners + losers bracket flow)
  - **Best-of** addon (choose 3/5/7 and optional per-match score notes)
- Randomize seeding button:
  - Before first round: randomizes initial matchups.
  - After bracket starts: randomizes **current round** matchups (with confirmation).
- Scrollable/pannable bracket canvas for large brackets.
- Save completed bracket to JSON.
- Save options helper explains PDF/image/JSON tradeoffs.

## Run

```bash
python bracket_maker.py
```

## Save format recommendation

Current implementation saves a `.json` file to preserve structure, winners, round state,
and score notes reliably. The UI also includes a helper explaining when PDF/image export
would be useful for sharing/printing.
