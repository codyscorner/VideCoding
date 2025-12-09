// Main Game Class
class Game {
    constructor() {
        this.canvas = document.getElementById('gameCanvas');
        this.ctx = this.canvas.getContext('2d');

        // Set canvas size
        this.canvas.width = CONFIG.CANVAS_WIDTH;
        this.canvas.height = CONFIG.CANVAS_HEIGHT;

        // Game objects
        this.rocket = null;
        this.levelManager = new LevelManager();
        this.hud = new HUD();

        // Game state
        this.gameState = 'start'; // start, playing, gameOver, success
        this.keys = {};

        // UI Elements
        this.startOverlay = document.getElementById('startOverlay');
        this.gameOverlay = document.getElementById('gameOverlay');
        this.overlayTitle = document.getElementById('overlayTitle');
        this.overlayMessage = document.getElementById('overlayMessage');
        this.startBtn = document.getElementById('startBtn');
        this.restartBtn = document.getElementById('restartBtn');
        this.nextBtn = document.getElementById('nextBtn');

        this.setupEventListeners();
        this.showStartScreen();
    }

    setupEventListeners() {
        // Keyboard input
        window.addEventListener('keydown', (e) => {
            this.keys[e.key] = true;
            this.keys[e.code] = true;

            // Handle single-press keys
            if (e.code === 'Space') {
                e.preventDefault();
                if (this.gameState === 'playing' && this.rocket) {
                    this.rocket.toggleEngine();
                }
            }

            if (e.key === 'l' || e.key === 'L') {
                if (this.gameState === 'playing' && this.rocket) {
                    this.rocket.deployLegs();
                }
            }
        });

        window.addEventListener('keyup', (e) => {
            this.keys[e.key] = false;
            this.keys[e.code] = false;
        });

        // Button clicks
        this.startBtn.addEventListener('click', () => this.startGame());
        this.restartBtn.addEventListener('click', () => this.restartLevel());
        this.nextBtn.addEventListener('click', () => this.loadNextLevel());
    }

    showStartScreen() {
        this.startOverlay.classList.remove('hidden');
        this.gameOverlay.classList.add('hidden');
    }

    startGame() {
        this.startOverlay.classList.add('hidden');
        this.loadLevel(0);
    }

    loadLevel(index) {
        this.levelManager.loadLevel(index);
        const startPos = this.levelManager.getStartPosition();

        this.rocket = new Rocket(startPos.x, startPos.y);
        this.gameState = 'playing';

        this.hud.updateLevelInfo(this.levelManager);
        this.gameLoop();
    }

    restartLevel() {
        this.gameOverlay.classList.add('hidden');
        this.loadLevel(this.levelManager.currentLevelIndex);
    }

    loadNextLevel() {
        this.gameOverlay.classList.add('hidden');
        if (this.levelManager.hasNextLevel()) {
            this.levelManager.nextLevel();
            const startPos = this.levelManager.getStartPosition();
            this.rocket = new Rocket(startPos.x, startPos.y);
            this.gameState = 'playing';
            this.hud.updateLevelInfo(this.levelManager);
            this.gameLoop();
        } else {
            this.showGameComplete();
        }
    }

    gameLoop() {
        if (this.gameState !== 'playing') return;

        this.update();
        this.render();

        requestAnimationFrame(() => this.gameLoop());
    }

    update() {
        if (!this.rocket) return;

        // Handle continuous key input
        let gridFinInput = 0;

        // Throttle control
        if (this.keys['w'] || this.keys['W'] || this.keys['ArrowUp']) {
            this.rocket.throttleUp(0.01);
        }
        if (this.keys['s'] || this.keys['S'] || this.keys['ArrowDown']) {
            this.rocket.throttleDown(0.01);
        }

        // Grid fin control
        if (this.keys['a'] || this.keys['A'] || this.keys['ArrowLeft']) {
            gridFinInput = 1;
        }
        if (this.keys['d'] || this.keys['D'] || this.keys['ArrowRight']) {
            gridFinInput = -1;
        }

        this.rocket.setGridFinInput(gridFinInput);

        // Update game objects
        const wind = this.levelManager.getWind();
        this.rocket.update(wind);
        this.levelManager.update();

        // Update HUD
        this.hud.update(this.rocket, this.levelManager);

        // Check for landing or crash
        const landingResult = this.levelManager.checkLanding(this.rocket);
        if (landingResult) {
            if (landingResult.success) {
                this.handleSuccess(landingResult.reason);
            } else {
                this.handleCrash(landingResult.reason);
            }
        }

        // Check if rocket went off top (mission failure)
        if (this.rocket.y < -100) {
            this.handleCrash("Rocket went out of bounds!");
        }
    }

    render() {
        // Clear canvas
        this.ctx.fillStyle = '#000814';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw stars
        this.drawStars();

        // Draw level elements
        this.levelManager.draw(this.ctx);

        // Draw impact marker
        const impactX = this.rocket.calculateImpactPoint();
        if (impactX) {
            this.levelManager.drawImpactMarker(this.ctx, impactX);
        }

        // Draw rocket
        this.rocket.draw(this.ctx);
    }

    drawStars() {
        this.ctx.fillStyle = '#FFFFFF';
        // Draw some random stars (seeded for consistency)
        for (let i = 0; i < 100; i++) {
            const x = (i * 13) % this.canvas.width;
            const y = (i * 17) % (this.canvas.height * 0.7); // Only upper 70%
            const size = (i % 3) === 0 ? 2 : 1;
            this.ctx.fillRect(x, y, size, size);
        }
    }

    handleSuccess(message) {
        this.gameState = 'success';
        this.overlayTitle.textContent = 'MISSION SUCCESS!';
        this.overlayMessage.textContent = message;

        if (this.levelManager.hasNextLevel()) {
            this.nextBtn.classList.remove('hidden');
        } else {
            this.nextBtn.classList.add('hidden');
            this.overlayMessage.textContent += '\n\nCongratulations! You have completed all missions!';
        }

        this.gameOverlay.classList.remove('hidden');
    }

    handleCrash(reason) {
        this.gameState = 'gameOver';
        this.overlayTitle.textContent = 'MISSION FAILED';
        this.overlayMessage.textContent = reason;
        this.nextBtn.classList.add('hidden');
        this.gameOverlay.classList.remove('hidden');
    }

    showGameComplete() {
        this.overlayTitle.textContent = 'GAME COMPLETE!';
        this.overlayMessage.textContent = 'You have mastered the hoverslam! All missions complete!';
        this.nextBtn.classList.add('hidden');
        this.gameOverlay.classList.remove('hidden');
    }
}

// Initialize game when page loads
window.addEventListener('load', () => {
    const game = new Game();
});
