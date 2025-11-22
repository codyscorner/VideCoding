const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const scoreDisplay = document.getElementById('score');
const ammoDisplay = document.getElementById('ammo');

let score = 0;
let gameRunning = true;
let level = 1;
let missilesDestroyed = 0;
let levelThreshold = 10;  // Missiles destroyed to level up
let ammo = 30; // Add ammo counter

// Game objects
let missiles = [];
let explosions = [];
let bases = [
    { x: 200, y: 768, active: true },
    { x: 512, y: 768, active: true },
    { x: 824, y: 768, active: true }
];
let cities = [];
for (let i = 0; i < 6; i++) {
    cities.push({ x: 100 + i * 150, y: 768, active: true });
}

// Player's missile
let playerMissile = null;

// Mouse position
let mouseX = 512;
let mouseY = 384;

// Event listeners
canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    mouseX = e.clientX - rect.left;
    mouseY = e.clientY - rect.top;
});

canvas.addEventListener('click', (e) => {
    if (!playerMissile && ammo > 0 && bases.some(b => b.active)) {
        // Find active base closest to mouse
        let activeBases = bases.filter(b => b.active);
        let targetBase = activeBases.reduce((closest, base) => {
            return Math.abs(base.x - mouseX) < Math.abs(closest.x - mouseX) ? base : closest;
        });
        playerMissile = {
            x: targetBase.x,
            y: targetBase.y - 20,
            targetX: mouseX,
            targetY: mouseY,
            speed: 5
        };
        ammo--;
    }
});

// Game loop
function gameLoop() {
    if (!gameRunning) return;

    update();
    draw();
    requestAnimationFrame(gameLoop);
}

// Update game state
function update() {
    // Spawn enemy missiles
    let spawnChance = 0.02 + (level - 1) * 0.005;  // Increase spawn rate with level
    if (Math.random() < spawnChance) {
        let startX = Math.random() * 1024;
        missiles.push({
            x: startX,
            y: 0,
            startX: startX,
            startY: 0,
            targetX: Math.random() * 1024,
            targetY: 768,
            speed: 1 + Math.random() * 1
        });
    }

    // Update missiles
    missiles.forEach((missile, index) => {
        missile.prevX = missile.x;
        missile.prevY = missile.y;
        const dx = missile.targetX - missile.x;
        const dy = missile.targetY - missile.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > missile.speed) {
            missile.x += (dx / dist) * missile.speed;
            missile.y += (dy / dist) * missile.speed;
        } else {
            // Missile hit target - create explosion
            explosions.push({
                x: missile.targetX,
                y: missile.targetY,
                radius: 0,
                maxRadius: 50,
                growing: true
            });
            missiles.splice(index, 1);
        }
    });

    // Update player missile
    if (playerMissile) {
        const dx = playerMissile.targetX - playerMissile.x;
        const dy = playerMissile.targetY - playerMissile.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > playerMissile.speed) {
            playerMissile.x += (dx / dist) * playerMissile.speed;
            playerMissile.y += (dy / dist) * playerMissile.speed;
        } else {
            // Player missile exploded
            explosions.push({
                x: playerMissile.targetX,
                y: playerMissile.targetY,
                radius: 0,
                maxRadius: 80,
                growing: true
            });
            playerMissile = null;
        }
    }

    // Update explosions
    explosions.forEach((explosion, index) => {
        if (explosion.growing) {
            explosion.radius += 2;
            if (explosion.radius >= explosion.maxRadius) {
                explosion.growing = false;
            }
        } else {
            explosion.radius -= 2;
            if (explosion.radius <= 0) {
                explosions.splice(index, 1);
            }
        }

        // Check for collisions
        missiles.forEach((missile, mIndex) => {
            const dx = missile.x - explosion.x;
            const dy = missile.y - explosion.y;
            if (Math.sqrt(dx * dx + dy * dy) < explosion.radius) {
                missiles.splice(mIndex, 1);
                score += 10;
                missilesDestroyed++;
                if (missilesDestroyed >= levelThreshold) {
                    level++;
                    missilesDestroyed = 0;
                    levelThreshold += 5;  // Increase threshold for next level
                    alert(`Level ${level}!`);
                }
            }
        });
    });

    // Check for missile hits on cities and bases
    missiles.forEach((missile, index) => {
        cities.forEach((city, cIndex) => {
            if (city.active && Math.abs(missile.x - city.x) < 20 && Math.abs(missile.y - city.y) < 20) {
                city.active = false;
                missiles.splice(index, 1);
            }
        });
        bases.forEach((base, bIndex) => {
            if (base.active && Math.abs(missile.x - base.x) < 20 && Math.abs(missile.y - base.y) < 20) {
                base.active = false;
                missiles.splice(index, 1);
            }
        });
    });

    // Check game over
    if (cities.every(c => !c.active) && bases.every(b => !b.active)) {
        gameRunning = false;
        drawGameOver();
    }

    scoreDisplay.textContent = `Score: ${score} | Level: ${level}`;
    ammoDisplay.textContent = `Ammo: ${ammo}`;
}

// Draw game
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw ground
    ctx.fillStyle = 'green';
    ctx.fillRect(0, 750, 1024, 18);

    // Draw cities
    cities.forEach(city => {
        if (city.active) {
            ctx.fillStyle = 'blue';
            ctx.fillRect(city.x - 15, city.y - 15, 30, 15);
        }
    });

    // Draw bases
    bases.forEach(base => {
        if (base.active) {
            ctx.fillStyle = 'red';
            ctx.fillRect(base.x - 10, base.y - 20, 20, 20);
        }
    });

    // Draw missiles
    ctx.strokeStyle = 'white';
    ctx.lineWidth = 3;
    missiles.forEach(missile => {
        ctx.beginPath();
        ctx.moveTo(missile.startX, missile.startY);
        ctx.lineTo(missile.x, missile.y);
        ctx.stroke();
        ctx.fillStyle = 'yellow';
        ctx.fillRect(missile.x - 2, missile.y - 2, 4, 4);
    });

    // Draw player missile
    if (playerMissile) {
        ctx.strokeStyle = 'white';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(playerMissile.x, playerMissile.y);
        ctx.lineTo(playerMissile.targetX, playerMissile.targetY);
        ctx.stroke();
        ctx.fillStyle = 'cyan';
        ctx.fillRect(playerMissile.x - 2, playerMissile.y - 2, 4, 4);
        ctx.lineWidth = 3;  // Reset for missiles
    }

    // Draw explosions
    explosions.forEach(explosion => {
        ctx.beginPath();
        ctx.arc(explosion.x, explosion.y, explosion.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 100, 0, ${explosion.growing ? 0.5 : 0.3})`;
        ctx.fill();
    });
}

// Draw game over screen
function drawGameOver() {
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = 'white';
    ctx.font = '48px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('GAME OVER', canvas.width / 2, canvas.height / 2 - 50);
    ctx.font = '24px Arial';
    ctx.fillText(`Final Score: ${score}`, canvas.width / 2, canvas.height / 2);
    ctx.fillText(`Level Reached: ${level}`, canvas.width / 2, canvas.height / 2 + 30);
    ctx.fillText('Click to Restart', canvas.width / 2, canvas.height / 2 + 70);
}

gameLoop();

