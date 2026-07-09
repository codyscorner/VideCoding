# Changelog

## v1.1.0 (2026-07-08)

- Persistent high-score table: top 5 scores saved to `localStorage`, shown in a bottom-right panel.
- Sound effects toggle: Web Audio API oscillator beeps for launch/explosion/hit/level-up/game-over, no external audio assets; on/off preference remembered between visits.
- Pause key: `P` or `Escape` pauses/resumes the game with a "PAUSED" overlay; input is ignored while paused.
- Difficulty settings: Easy/Normal/Hard dropdown adjusts enemy missile spawn rate and speed (applied immediately) and starting ammo (applied on restart).
- Fixed a pre-existing bug where "Click to Restart" on the Game Over screen didn't actually do anything — clicking the canvas after Game Over now resets the game.

## v1.0.0

Initial release — classic Missile Command gameplay with score, ammo, waves, and increasing difficulty.
