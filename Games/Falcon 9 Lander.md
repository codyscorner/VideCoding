# Game Design Document: Falcon 9 "Hoverslam" Lander

---

## 1. Concept Overview

- **Genre:** Physics Simulation / Arcade Lander  
- **Core Loop:** Control a falling rocket booster, manage fuel and momentum, and land upright on a target zone.  
- **Twist:** Unlike the moon, Earth has an atmosphere and high gravity. The rocket is tall and top-heavy. You must perform a **suicide burn** (engines cannot throttle low enough to hover indefinitely, so you must hit 0 velocity exactly as you touch the ground).

---

## 2. Core Physics Mechanics

### A. Gravity & Environment
- Gravity: Standard Earth gravity (9.8 m/s²).  
- Atmosphere: Implement drag/air resistance based on velocity.  
- Wind: Variable lateral force applied at higher altitudes.  

### B. Rocket Physics
- **Thrust Vectoring:** Falcon 9 pivots the engine (gimbaling) instead of rotating the whole ship.  
- **Visual:** Flame angles slightly opposite to the turn.  
- **Inertia:** Long cylinder, high moment of inertia. Rotates slowly but carries momentum.  
- **Fuel Mass:** As fuel burns, rocket gets lighter, increasing TWR (Thrust-to-Weight Ratio).  

---

## 3. Falcon 9 Unique Mechanics

### A. Grid Fins
- Replace RCS thrusters with Grid Fins for steering in atmosphere.  
- Effectiveness scales with vertical velocity (more speed = more control).  

### B. Landing Legs
- **State Machine:** Retracted → Deploying → Locked.  
- **Risk:** Too early = drag increase or legs snap off. Too late = crash.  
- **Suspension:** Legs absorb impact with spring logic to prevent tipping.  

### C. Suicide Burn (Hoverslam)
- **Throttle Floor:** Minimum throttle ~40%.  
- **Challenge:** Even at minimum throttle, TWR > 1.0 (empty tank). Cannot hover. Must time burn to reach 0 altitude and 0 velocity simultaneously.  

---

## 4. Controls

- **W / Up Arrow:** Main Engine (Throttle up)  
- **S / Down Arrow:** Throttle down (to minimum cutoff)  
- **A / D or Left/Right:** Actuate Grid Fins (Rotate/Lateral movement)  
- **Spacebar:** Cut engine (MECO) / Re-light engine  
- **L key:** Deploy Landing Legs  

---

## 5. User Interface (HUD)

### A. Telemetry
- Altitude: Distance to ground  
- Vertical Velocity: Color-coded (Green = Safe, Red = Crash)  
- Horizontal Velocity: Must be near zero to prevent tipping  
- Fuel Gauge: Critical resource  

### B. Impact Point Predictor
- Shows a calculated "X" on the ground where rocket will land based on trajectory.  
- Essential for aiming at drone ships.  

---

## 6. Level Progression

1. **The Grasshopper (Tutorial)**  
   - Low altitude hop  
   - No wind  
   - Wide concrete landing pad  

2. **Return to Launch Site (LZ-1)**  
   - Drop from sub-orbital height  
   - Steer back to land  
   - Introduces wind  

3. **"Of Course I Still Love You" (Drone Ship)**  
   - Smaller landing target  
   - Target moves/bobs with waves  

4. **Falcon Heavy Center Core**  
   - Higher entry speed  
   - Must land precisely between two side boosters (visual obstacles)  

---

## 7. Visuals & Audio

### Visuals
- Soot accumulation on rocket body  
- Engine exhaust:  
  - Wide plume at high altitude (underexpanded)  
  - Tight plume with shock diamonds at low altitude (overexpanded)  
- Explosions: Spectacular failure animations (RUD - Rapid Unscheduled Disassembly)  

### Audio
- Sonic booms on descent  
- Venting noises (cold gas thrusters)  
- Callouts (e.g., "Landing burn startup," "Legs deployment")  

---

## 8. Technical Stack (Recommended)

- **Engine:** Unity (C#) or Godot (GDScript) for built-in physics 2D/3D engines  
- **Web-Based:** HTML5 Canvas + Matter.js (for 2D physics)  

---