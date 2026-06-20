
# **PLAN FOR A SINGLE‑FILE HTML ASTEROIDS GAME**

## **1. Project Goal**
Create a complete Asteroids‑style arcade game using **only one HTML file**.  
All logic, rendering, input handling, and styling must be inside this single file.

No external assets, no external scripts, no modules.

---

## **2. File Structure**
Only one file exists:

```
index.html
```

This file contains:

1. `<canvas>` element  
2. `<style>` block for minimal styling  
3. `<script>` block containing **all game code**  

---

## **3. Required HTML Structure**
Claude should generate:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Asteroids</title>
  <style>
    /* inline CSS for centering canvas and background */
  </style>
</head>
<body>
  <canvas id="game" width="800" height="600"></canvas>

  <script>
    // ALL GAME CODE HERE
  </script>
</body>
</html>
```

---

## **4. Game Features to Implement (Inside the Script Tag)**

### **4.1 Player Ship**
- Triangle‑shaped vector ship drawn with canvas lines  
- Rotation left/right  
- Thrust forward with inertia  
- Friction applied each frame  
- Shooting bullets in facing direction  
- 3 lives, respawn with invincibility blink  

### **4.2 Asteroids**
- Large → Medium → Small  
- Random polygon shapes  
- Drift with random velocity  
- Wrap around screen  
- Splitting behavior when hit  

### **4.3 Bullets**
- Straight‑line movement  
- Limited lifetime  
- Max bullets on screen  

### **4.4 Collisions**
- Bullet → Asteroid  
- Ship → Asteroid  
- Use simple circle collision for performance  

### **4.5 Game States**
- Title screen (“Press Space to Start”)  
- Playing  
- Game Over (“Press Space to Restart”)  

### **4.6 HUD**
- Score  
- Lives  
- Optional wave number  

---

## **5. Game Loop**
Inside the `<script>` tag, Claude must implement:

- `requestAnimationFrame(loop)`  
- `update(dt)`  
- `draw(ctx)`  
- Input handling via `keydown` / `keyup`  
- Entity arrays:
  - `asteroids`
  - `bullets`
  - `ship`

---

## **6. Controls**
- Left Arrow → rotate left  
- Right Arrow → rotate right  
- Up Arrow → thrust  
- Space → shoot  

---

## **7. Constraints**
- **Everything must be inside one HTML file.**
- No external JS, CSS, images, or modules.
- No imports.
- No build tools.
- Must run by simply opening `index.html` in a browser.

---

## **8. Stretch Goals (Optional)**
- UFO enemy  
- Screen shake  
- Starfield background  
- LocalStorage high scores  

---

