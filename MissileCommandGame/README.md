# Missile Command Game

A browser-based Missile Command arcade game built with HTML5 Canvas and JavaScript. No installation required — open and play instantly.

## How to Play

Open `index.html` in any modern web browser.

## Controls

| Input | Action |
|-------|--------|
| Mouse click | Launch interceptor missile at click location (or restart after Game Over) |
| P / Escape | Pause / resume |

## Objective

Defend your cities from incoming missiles. Click to launch interceptors that explode on contact with enemy missiles. You have limited ammo — use it wisely!

- **Score** is shown in the top-left
- **Ammo** count is displayed below the score
- Missiles come in waves — survive as long as possible
- Choose a **Difficulty** (Easy/Normal/Hard) in the top-right — spawn rate/speed apply immediately; starting ammo applies on the next restart
- Toggle **Sound Effects** in the top-right; the preference is remembered between visits
- Your top 5 **High Scores** are saved in the browser and shown in the bottom-right panel

## Requirements

Any modern web browser. No Python, no server, no dependencies.

## Files

| File | Description |
|------|-------------|
| `index.html` | Main game page |
| `main.js` | All game logic (physics, rendering, input) |
