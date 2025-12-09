# Falcon 9 Lander - Quick Start Guide

## Play Right Now (HTML5 Version)

**Fastest way to play:**

1. Navigate to the `Falcon9Lander-HTML5` folder
2. Double-click `index.html`
3. The game opens in your browser - **ready to play!**

That's it! No installation, no setup.

---

## Unity Version Setup (30-60 minutes)

### Prerequisites
- Unity Hub installed
- Unity 2021.3 LTS or newer

### Steps

1. **Create New Project**
   - Open Unity Hub
   - Click "New Project"
   - Select "2D" template
   - Name it "Falcon9Lander"
   - Click "Create Project"

2. **Import Scripts**
   - In Unity, create folder: `Assets/Scripts`
   - Copy all `.cs` files from `Falcon9Lander-Unity/Scripts/` to `Assets/Scripts/`

3. **Setup Scene**
   - Follow the detailed instructions in `Falcon9Lander-Unity/README.md`
   - Key steps:
     - Create Rocket GameObject with Rigidbody2D
     - Add RocketController, PlayerInput, and VisualEffects scripts
     - Create Landing Zone with trigger collider
     - Setup HUD Canvas with TextMeshPro elements
     - Create GameManager

4. **Play**
   - Press Play button in Unity
   - Use W/A/S/D or Arrow Keys to control

---

## Controls (Both Versions)

```
W or ↑     = Throttle Up
S or ↓     = Throttle Down
A or ←     = Rotate Left (Grid Fins)
D or →     = Rotate Right (Grid Fins)
SPACE      = Toggle Engine On/Off
L          = Deploy Landing Legs
```

---

## First Mission Tips

### Tutorial Level: The Grasshopper

1. **Launch Phase (First 3 seconds)**
   - Press W to throttle up to ~60%
   - Let the rocket rise to ~150m
   - Keep it centered with A/D if drifting

2. **Descent Phase**
   - Press SPACE to cut the engine
   - Watch the altitude and vertical speed
   - Deploy legs with L around 100m

3. **Suicide Burn**
   - When altitude is ~50m and falling fast
   - Press W to throttle up
   - Aim for vertical speed of 3-5 m/s when you touch down
   - Fine-tune with S to throttle down if needed

4. **Landing**
   - Keep angle near 0° (vertical)
   - Touch down on the green landing pad
   - Success! 🚀

### Key Numbers to Watch

- **Altitude**: When it hits 0, you land (or crash!)
- **Vertical Speed**: Should be GREEN (< 5 m/s) at landing
- **TWR (Thrust-to-Weight Ratio)**:
  - < 1.0 = You're falling
  - = 1.0 = You're hovering (impossible at min throttle!)
  - > 1.0 = You're rising
- **Fuel**: Don't run out!

---

## Troubleshooting

### HTML5 Version

**Game doesn't load:**
- Make sure JavaScript is enabled in your browser
- Try a different browser (Chrome, Firefox, Edge recommended)
- Check browser console (F12) for errors

**Controls don't work:**
- Click on the game canvas to focus it
- Make sure keyboard focus is on the browser window

### Unity Version

**Scripts have errors:**
- Make sure all 6 script files are copied
- Check Unity version is 2021.3 or newer
- If using TextMeshPro for first time, import TMP Essentials when prompted

**Rocket falls through ground:**
- Make sure ground has a Collider2D component
- Check rocket has Rigidbody2D component

**No movement:**
- Make sure PlayerInput script is attached
- Check RocketController is attached
- Verify scripts don't have compile errors

---

## Next Steps

1. **Master Level 1** before moving on
2. **Read the full README** in your chosen version's folder
3. **Experiment** with the controls and physics
4. **Try all 4 levels** - each adds new challenges
5. **Customize** the game (see README files for how)

---

## Need Help?

1. Check the main project README: `Falcon9-Lander-Project-README.md`
2. Check version-specific README:
   - Unity: `Falcon9Lander-Unity/README.md`
   - HTML5: `Falcon9Lander-HTML5/README.md`
3. Review the original design doc: `Falcon 9 Lander.md`

---

## Have Fun!

Landing a rocket is hard - even virtually! Don't get discouraged if you crash a few times. That's how SpaceX learned too! 😄

**Pro tip:** Watch some real SpaceX landing videos to see the suicide burn in action!

🚀 Good luck, astronaut! 🚀
