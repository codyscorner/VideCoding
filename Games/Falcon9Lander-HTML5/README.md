# Falcon 9 Lander - HTML5 Version

A realistic rocket landing simulation game inspired by SpaceX's Falcon 9 booster recovery missions. Master the art of the "hoverslam" (suicide burn) to safely land your rocket!

## Features

- **Realistic Physics**: Gravity, atmospheric drag, wind, and fuel consumption
- **Suicide Burn Mechanic**: Minimum throttle of 40% means you can't hover - time your burn perfectly!
- **Grid Fins**: Speed-dependent atmospheric steering (more effective at higher speeds)
- **Landing Legs**: Deploy at the right time to absorb impact
- **Telemetry HUD**: Real-time altitude, velocity, fuel, TWR, and more
- **Impact Predictor**: Shows where your rocket will land based on current trajectory
- **4 Progressive Levels**:
  1. The Grasshopper - Tutorial landing
  2. Return to Launch Site (LZ-1) - Land at a distance with wind
  3. Of Course I Still Love You - Moving drone ship
  4. Falcon Heavy Center Core - High-speed precision landing

## How to Play

### Installation

1. Download all files to a folder
2. Open `index.html` in a modern web browser (Chrome, Firefox, Edge recommended)
3. No server required - runs entirely in the browser!

### Controls

- **W / ↑**: Throttle up (increases engine power)
- **S / ↓**: Throttle down (decreases engine power)
- **A / ←**: Grid fins left (rotate rocket left)
- **D / →**: Grid fins right (rotate rocket right)
- **SPACE**: Toggle engine on/off (MECO - Main Engine Cut Off)
- **L**: Deploy landing legs

### Gameplay Tips

#### 1. The Suicide Burn (Hoverslam)

The Falcon 9's Merlin engine has a minimum throttle of 40%. When the rocket is nearly empty, even at minimum throttle, the thrust-to-weight ratio (TWR) exceeds 1.0, meaning you **cannot hover**.

You must time your landing burn so that you reach:
- Zero altitude
- Zero velocity
- At the exact same moment!

**Burn timing formula**: Start burn when `altitude ≈ velocity² / (2 × TWR × gravity)`

#### 2. Grid Fins

- Grid fins provide steering by creating drag in the atmosphere
- They're more effective at higher speeds
- Use them early to correct your trajectory
- Less effective when falling slowly

#### 3. Landing Legs

- Deploy around 100m altitude
- Too early = increased drag and potential damage
- Too late = crash without shock absorption
- Must be deployed for successful landing!

#### 4. Fuel Management

- You have limited fuel - every second of burn counts
- As fuel depletes, the rocket gets lighter
- Lighter rocket = higher TWR = more challenging to land
- Plan your burn carefully!

### Success Criteria

For a successful landing, ALL conditions must be met:

- ✅ Vertical speed ≤ 3 m/s
- ✅ Horizontal speed ≤ 1.5 m/s
- ✅ Tilt angle ≤ 10 degrees
- ✅ Landing legs deployed
- ✅ Touch down within landing zone

### HUD Elements

**Left Panel - Telemetry:**
- **Altitude**: Distance from ground
- **Vertical Speed**: Color-coded (green = safe, yellow = caution, red = danger)
- **Horizontal Speed**: Lateral drift
- **Angle**: Rocket tilt from vertical

**Right Panel - Systems:**
- **Fuel**: Remaining fuel percentage and gauge
- **Throttle**: Current engine power setting
- **TWR**: Thrust-to-Weight Ratio (>1.0 means you're gaining altitude)
- **Engine**: Engine status (ON/OFF/NO FUEL)
- **Legs**: Landing leg deployment status

**Impact Marker:**
- Red X on the ground shows predicted landing point
- Only visible when descending
- Use this to aim for the landing zone!

## Level Guide

### Level 1: The Grasshopper
- **Difficulty**: Tutorial
- **Start Height**: Low (200m)
- **Wind**: None
- **Landing Zone**: Large, centered
- **Tips**: Practice basic throttle control and timing

### Level 2: Return to Launch Site (LZ-1)
- **Difficulty**: Medium
- **Start Position**: Offset from landing zone
- **Wind**: Moderate lateral wind
- **Landing Zone**: Medium size
- **Tips**: Use grid fins early to correct trajectory, compensate for wind drift

### Level 3: Of Course I Still Love You
- **Difficulty**: Hard
- **Start Position**: Far from target
- **Wind**: Strong lateral wind
- **Landing Zone**: Small, moving drone ship
- **Tips**: Track the moving target, time your approach carefully

### Level 4: Falcon Heavy Center Core
- **Difficulty**: Expert
- **Start Height**: Very high with high entry speed
- **Wind**: Strong and variable
- **Landing Zone**: Small, precise landing required
- **Tips**: Early burn to kill horizontal velocity, precise final descent control

## Technical Details

### Technologies Used
- **HTML5 Canvas**: Rendering
- **Vanilla JavaScript**: Game logic
- **CSS3**: UI styling
- **Physics**: Custom implementation (no external physics engine)

### Browser Compatibility
- Chrome 90+
- Firefox 88+
- Edge 90+
- Safari 14+

### Performance
- Runs at 60 FPS on modern hardware
- Lightweight - no heavy dependencies
- Total size: ~50KB

## Customization

Want to modify the game? Here's where to look:

- **`js/config.js`**: Physics constants, level definitions, game parameters
- **`js/rocket.js`**: Rocket physics and behavior
- **`js/level.js`**: Level management and landing zone logic
- **`css/style.css`**: Visual styling and HUD appearance

### Example Modifications

**Make it easier:**
```javascript
// In config.js
MAX_LANDING_VERTICAL_SPEED: 10,  // Allow faster landings
MIN_THROTTLE: 0.2,  // Lower minimum throttle
```

**Make it harder:**
```javascript
// In config.js
MAX_LANDING_VERTICAL_SPEED: 3,  // Require softer landings
ROCKET_FUEL_MAX: 10000,  // Less fuel
```

**Add new levels:**
```javascript
// In config.js LEVELS array
{
    name: "Custom Mission",
    description: "Your description here",
    startX: 400,
    startY: 100,
    landingZoneX: 900,
    landingZoneWidth: 40,
    wind: { x: 0.15, y: 0 },
    isDroneShip: true
}
```

## Known Limitations

- 2D only (no 3D perspective)
- Simplified aerodynamics
- No sound effects (can be added)
- Single rocket type
- Keyboard-only controls

## Future Enhancements

Potential features to add:
- Sound effects (engine roar, sonic boom, explosions)
- Music soundtrack
- Score/leaderboard system
- Time attack mode
- Fuel efficiency rating
- Replay system
- Mobile touch controls
- Multiple rocket types
- Weather effects (rain, fog)
- Day/night cycle

## Credits

Inspired by SpaceX's incredible Falcon 9 booster recovery program and the legendary video game "Lunar Lander."

## License

Free to use and modify for educational and personal projects.

---

**Good luck, and may your landings be soft!** 🚀
