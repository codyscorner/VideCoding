# Falcon 9 Lander - Unity Version

## Setup Instructions

### 1. Create a New Unity Project
- Open Unity Hub
- Create a new 2D project named "Falcon9Lander"
- Unity version: 2021.3 or newer recommended

### 2. Import Scripts
Copy all scripts from the `Scripts` folder into your Unity project's `Assets/Scripts` folder:
- `RocketController.cs` - Main physics and rocket control
- `PlayerInput.cs` - Handles keyboard input
- `LandingZone.cs` - Landing zone detection and validation
- `HUDController.cs` - Heads-up display and telemetry
- `GameManager.cs` - Level management and game flow
- `VisualEffects.cs` - Particle effects and visual feedback

### 3. Create the Rocket GameObject

1. **Create Main Rocket Object:**
   - Right-click in Hierarchy → Create Empty → Name it "Rocket"
   - Add Components:
     - Rigidbody2D (set Gravity Scale to 0)
     - Capsule Collider 2D (adjust size to match your sprite)
     - RocketController script
     - PlayerInput script
     - VisualEffects script

2. **Add Rocket Visual:**
   - Create a child Sprite Renderer (or import a rocket sprite)
   - Scale to approximately 1x7 units (tall and narrow)
   - Assign to VisualEffects.rocketSprite

3. **Add Engine Exhaust:**
   - Create child GameObject named "EngineExhaust"
   - Add Particle System component
   - Position at bottom of rocket
   - Configure:
     - Start Lifetime: 0.5
     - Start Speed: 5-10
     - Start Size: 0.5-2
     - Start Color: Orange/Yellow gradient
     - Emission Rate: 100
     - Shape: Cone, Angle: 15
   - Assign to VisualEffects.engineExhaust

4. **Add Grid Fins:**
   - Create 4 small rectangles as children (left/right, top/bottom)
   - Position on sides of rocket body
   - Assign left and right to VisualEffects

5. **Add Landing Legs:**
   - Create 4 leg GameObjects as children
   - Position at bottom of rocket
   - Assign to VisualEffects.landingLegs array

### 4. Create the Landing Zone

1. Create a new GameObject named "LandingZone"
2. Add BoxCollider2D (set as Trigger)
3. Add LandingZone script
4. Add visual (sprite or simple quad) to show landing target

### 5. Create the Ground

1. Create a long BoxCollider2D at y=0 for the ground
2. Tag it as "Ground"

### 6. Setup HUD

1. Create UI Canvas:
   - Right-click Hierarchy → UI → Canvas
   - Set Render Mode to Screen Space - Overlay

2. Add TextMeshPro elements for:
   - Altitude
   - Vertical Velocity
   - Horizontal Velocity
   - Fuel Gauge
   - Throttle
   - TWR (Thrust-to-Weight Ratio)
   - Legs Status
   - Engine Status

3. Create a GameObject named "HUDController"
4. Add HUDController script
5. Assign all UI elements in inspector
6. Assign rocket reference

### 7. Setup Game Manager

1. Create empty GameObject named "GameManager"
2. Add GameManager script
3. Configure level data in inspector:

**Level 1 - Grasshopper:**
- Start Position: (0, 100)
- Landing Zone: (0, 0)
- Wind: (0, 0)
- Is Drone Ship: false

**Level 2 - Return to Launch Site:**
- Start Position: (0, 500)
- Landing Zone: (50, 0)
- Wind: (5, 0)
- Is Drone Ship: false

**Level 3 - Drone Ship:**
- Start Position: (0, 800)
- Landing Zone: (100, 0)
- Wind: (8, 0)
- Is Drone Ship: true

**Level 4 - Falcon Heavy Center:**
- Start Position: (0, 1000)
- Landing Zone: (0, 0)
- Wind: (10, 0)
- Is Drone Ship: false

### 8. Configure Physics

1. Edit → Project Settings → Physics2D
2. Gravity Y: 0 (we handle gravity manually)

### 9. Controls

- **W / Up Arrow:** Throttle up and ignite engine
- **S / Down Arrow:** Throttle down
- **A / Left Arrow:** Rotate left (grid fins)
- **D / Right Arrow:** Rotate right (grid fins)
- **Spacebar:** Toggle engine on/off (MECO)
- **L:** Deploy landing legs

## Gameplay Tips

1. **Suicide Burn Timing:**
   - Watch altitude and vertical velocity
   - Calculate when to start burn: time = velocity / (TWR * gravity)
   - Minimum throttle is 40%, so you can't hover!

2. **Grid Fins:**
   - More effective at high speeds
   - Use early to correct trajectory

3. **Landing Legs:**
   - Deploy around 100m altitude
   - Too early = extra drag
   - Too late = crash

4. **Fuel Management:**
   - Limited fuel, plan your burn
   - Lighter rocket = higher TWR as fuel depletes

## Success Criteria

Landing is successful when ALL conditions are met:
- Vertical speed ≤ 5 m/s
- Horizontal speed ≤ 2 m/s
- Tilt angle ≤ 10 degrees
- Landing legs deployed
- Touch landing zone

## Additional Enhancements

To make the game even better, consider adding:

1. **Audio:**
   - Engine rumble sound
   - Sonic boom on descent
   - "Landing burn startup" callouts
   - Explosion sound for crashes

2. **Visual Effects:**
   - Shock diamonds in exhaust plume
   - Screen shake on engine ignition
   - Camera zoom/follow rocket
   - Explosion particle effects

3. **Polish:**
   - Main menu
   - Pause functionality
   - Replay system
   - Leaderboards (time/fuel efficiency)

Enjoy your Falcon 9 landing experience!
