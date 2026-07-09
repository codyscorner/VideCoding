const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const scoreDisplay = document.getElementById('score');
const ammoDisplay = document.getElementById('ammo');
const difficultySelect = document.getElementById('difficulty');
const soundToggle = document.getElementById('soundToggle');
const highscoreList = document.getElementById('highscoreList');

const HIGH_SCORE_KEY = 'missileCommandHighScores';
const SOUND_PREF_KEY = 'missileCommandSoundEnabled';
const MAX_HIGH_SCORES = 5;

const DIFFICULTY_SETTINGS = {
    easy:   { spawnMultiplier: 0.6, speedMultiplier: 0.8, startingAmmo: 40 },
    normal: { spawnMultiplier: 1.0, speedMultiplier: 1.0, startingAmmo: 30 },
    hard:   { spawnMultiplier: 1.6, speedMultiplier: 1.3, startingAmmo: 24 },
};

let score = 0;
let gameRunning = true;
let gameState = 'playing'; // 'playing' | 'paused' | 'gameover'
let level = 1;
let missilesDestroyed = 0;
let levelThreshold = 10;  // Missiles destroyed to level up
let ammo = 30;

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

// ---- Sound effects (Web Audio API, no external assets) ----
let audioCtx = null;
function getAudioCtx() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioCtx;
}

function playTone(freq, duration, type = 'sine', volume = 0.15) {
    if (!soundToggle.checked) return;
    try {
        const ctxA = getAudioCtx();
        const osc = ctxA.createOscillator();
        const gain = ctxA.createGain();
        osc.type = type;
        osc.frequency.value = freq;
        gain.gain.value = volume;
        gain.gain.exponentialRampToValueAtTime(0.001, ctxA.currentTime + duration);
        osc.connect(gain);
        gain.connect(ctxA.destination);
        osc.start();
        osc.stop(ctxA.currentTime + duration);
    } catch (e) {
        // Audio unavailable (e.g. no user interaction yet) — ignore.
    }
}

function playLaunchSound() { playTone(600, 0.1, 'square', 0.08); }
function playExplosionSound() { playTone(120, 0.3, 'sawtooth', 0.15); }
function playHitSound() { playTone(80, 0.4, 'square', 0.2); }
function playLevelUpSound() { playTone(880, 0.25, 'triangle', 0.15); }
function playGameOverSound() { playTone(200, 0.8, 'sawtooth', 0.2); }

soundToggle.addEventListener('change', () => {
    localStorage.setItem(SOUND_PREF_KEY, soundToggle.checked ? '1' : '0');
});
(function restoreSoundPref() {
    const saved = localStorage.getItem(SOUND_PREF_KEY);
    if (saved !== null) {
        soundToggle.checked = saved === '1';
    }
})();

// ---- High scores (localStorage) ----
function loadHighScores() {
    try {
        const raw = localStorage.getItem(HIGH_SCORE_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch (e) {
        return [];
    }
}

function saveHighScore(finalScore, finalLevel) {
    const scores = loadHighScores();
    scores.push({ score: finalScore, level: finalLevel, date: new Date().toISOString().slice(0, 10) });
    scores.sort((a, b) => b.score - a.score);
    const top = scores.slice(0, MAX_HIGH_SCORES);
    localStorage.setItem(HIGH_SCORE_KEY, JSON.stringify(top));
    return top;
}

function renderHighScores(scores) {
    scores = scores || loadHighScores();
    highscoreList.innerHTML = '';
    if (scores.length === 0) {
        highscoreList.innerHTML = '<li style="list-style:none;margin-left:-20px;color:#888;">No scores yet</li>';
        return;
    }
    scores.forEach(entry => {
        const li = document.createElement('li');
        li.textContent = `${entry.score} pts (Lvl ${entry.level})`;
        highscoreList.appendChild(li);
    });
}

renderHighScores();

// ---- Difficulty ----
function getDifficulty() {
    return DIFFICULTY_SETTINGS[difficultySelect.value] || DIFFICULTY_SETTINGS.normal;
}

// ---- Pause ----
document.addEventListener('keydown', (e) => {
    if (e.key === 'p' || e.key === 'P' || e.key === 'Escape') {
        if (gameState === 'playing') {
            gameState = 'paused';
        } else if (gameState === 'paused') {
            gameState = 'playing';
        }
    }
});

// Event listeners
canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    mouseX = e.clientX - rect.left;
    mouseY = e.clientY - rect.top;
});

canvas.addEventListener('click', (e) => {
    if (gameState === 'gameover') {
        resetGame();
        return;
    }
    if (gameState !== 'playing') return;

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
        playLaunchSound();
    }
});

// ---- Reset / restart ----
function resetGame() {
    score = 0;
    level = 1;
    missilesDestroyed = 0;
    levelThreshold = 10;
    ammo = getDifficulty().startingAmmo;
    missiles = [];
    explosions = [];
    playerMissile = null;
    bases.forEach(b => b.active = true);
    cities.forEach(c => c.active = true);
    gameRunning = true;
    gameState = 'playing';
}

ammo = getDifficulty().startingAmmo;

// Game loop
function gameLoop() {
    if (gameState === 'playing') {
        update();
    }
    draw();
    requestAnimationFrame(gameLoop);
}

// Update game state
function update() {
    const difficulty = getDifficulty();

    // Spawn enemy missiles
    let spawnChance = (0.02 + (level - 1) * 0.005) * difficulty.spawnMultiplier;
    if (Math.random() < spawnChance) {
        let startX = Math.random() * 1024;
        missiles.push({
            x: startX,
            y: 0,
            startX: startX,
            startY: 0,
            targetX: Math.random() * 1024,
            targetY: 768,
            speed: (1 + Math.random() * 1) * difficulty.speedMultiplier
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
            playExplosionSound();
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
                    playLevelUpSound();
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
                playHitSound();
            }
        });
        bases.forEach((base, bIndex) => {
            if (base.active && Math.abs(missile.x - base.x) < 20 && Math.abs(missile.y - base.y) < 20) {
                base.active = false;
                missiles.splice(index, 1);
                playHitSound();
            }
        });
    });

    // Check game over
    if (cities.every(c => !c.active) && bases.every(b => !b.active)) {
        gameRunning = false;
        gameState = 'gameover';
        playGameOverSound();
        const updated = saveHighScore(score, level);
        renderHighScores(updated);
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

    if (gameState === 'paused') {
        drawPaused();
    } else if (gameState === 'gameover') {
        drawGameOver();
    }
}

function drawPaused() {
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = 'white';
    ctx.font = '48px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('PAUSED', canvas.width / 2, canvas.height / 2);
    ctx.font = '20px Arial';
    ctx.fillText('Press P to resume', canvas.width / 2, canvas.height / 2 + 40);
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
