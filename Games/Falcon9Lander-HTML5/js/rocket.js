// Rocket Class
class Rocket {
    constructor(x, y) {
        this.x = x;
        this.y = y;
        this.vx = 0;
        this.vy = 0;
        this.angle = 0;
        this.angularVelocity = 0;

        // Mass
        this.mass = CONFIG.ROCKET_MASS_EMPTY;
        this.fuel = CONFIG.ROCKET_FUEL_MAX;

        // Engine
        this.throttle = 0;
        this.engineOn = false;

        // Systems
        this.legsDeployed = false;
        this.gridFinInput = 0;

        // Dimensions
        this.width = CONFIG.ROCKET_WIDTH;
        this.height = CONFIG.ROCKET_HEIGHT;

        // Particles for exhaust
        this.exhaustParticles = [];
    }

    update(wind) {
        const currentMass = this.mass + this.fuel;

        // Apply gravity
        this.vy += CONFIG.GRAVITY;

        // Apply drag
        const dragMult = this.legsDeployed ? (1 + CONFIG.LEG_DRAG_INCREASE) : 1;
        const speed = Math.sqrt(this.vx * this.vx + this.vy * this.vy);
        const dragX = -this.vx * speed * CONFIG.DRAG_COEFFICIENT * dragMult;
        const dragY = -this.vy * speed * CONFIG.DRAG_COEFFICIENT * dragMult;

        this.vx += dragX / currentMass;
        this.vy += dragY / currentMass;

        // Apply wind (stronger at higher altitudes)
        const altitude = CONFIG.CANVAS_HEIGHT - this.y;
        const windFactor = Math.min(altitude / 500, 1);
        this.vx += (wind.x * windFactor) / currentMass;
        this.vy += (wind.y * windFactor) / currentMass;

        // Apply engine thrust
        if (this.engineOn && this.fuel > 0) {
            const actualThrottle = Math.max(CONFIG.MIN_THROTTLE, Math.min(this.throttle, CONFIG.MAX_THROTTLE));
            const thrust = CONFIG.MAX_THRUST * actualThrottle;

            // Thrust in direction rocket is pointing
            const thrustX = Math.sin(this.angle) * thrust;
            const thrustY = -Math.cos(this.angle) * thrust;

            this.vx += thrustX / currentMass;
            this.vy += thrustY / currentMass;

            // Burn fuel
            this.fuel = Math.max(0, this.fuel - CONFIG.FUEL_BURN_RATE * actualThrottle);

            if (this.fuel <= 0) {
                this.engineOn = false;
            }

            // Create exhaust particles
            this.createExhaustParticles();
        }

        // Apply grid fin control (torque)
        if (this.gridFinInput !== 0) {
            const effectiveness = Math.min(
                CONFIG.GRID_FIN_EFFECTIVENESS_MIN + (Math.abs(this.vy) / 100) * (1 - CONFIG.GRID_FIN_EFFECTIVENESS_MIN),
                1
            );
            this.angularVelocity += this.gridFinInput * CONFIG.GRID_FIN_TORQUE * effectiveness;
        }

        // Apply angular damping
        this.angularVelocity *= 0.98;

        // Update rotation
        this.angle += this.angularVelocity;

        // Update position
        this.x += this.vx;
        this.y += this.vy;

        // Update exhaust particles
        this.updateExhaustParticles();

        // Keep within bounds (sides only)
        if (this.x < 0) this.x = 0;
        if (this.x > CONFIG.CANVAS_WIDTH) this.x = CONFIG.CANVAS_WIDTH;
    }

    createExhaustParticles() {
        const particleCount = Math.floor(this.throttle * 5);
        for (let i = 0; i < particleCount; i++) {
            // Particles spawn at bottom of rocket
            // Bottom is in the direction opposite to where the nose points
            const offsetX = -Math.sin(this.angle) * (this.height / 2);
            const offsetY = Math.cos(this.angle) * (this.height / 2);

            // Exhaust goes away from the bottom (opposite direction of thrust)
            const exhaustSpeed = 2 + Math.random() * 2;
            const spreadAngle = (Math.random() - 0.5) * 0.3;
            const exhaustAngle = this.angle + spreadAngle;

            const particle = {
                x: this.x + offsetX,
                y: this.y + offsetY,
                vx: this.vx - Math.sin(exhaustAngle) * exhaustSpeed,
                vy: this.vy + Math.cos(exhaustAngle) * exhaustSpeed,
                life: 30,
                maxLife: 30,
                size: 2 + Math.random() * 3
            };

            this.exhaustParticles.push(particle);
        }

        // Limit particle count
        if (this.exhaustParticles.length > CONFIG.EXHAUST_PARTICLES) {
            this.exhaustParticles.shift();
        }
    }

    updateExhaustParticles() {
        for (let i = this.exhaustParticles.length - 1; i >= 0; i--) {
            const p = this.exhaustParticles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.life--;

            if (p.life <= 0) {
                this.exhaustParticles.splice(i, 1);
            }
        }
    }

    throttleUp(amount) {
        this.throttle = Math.min(CONFIG.MAX_THROTTLE, this.throttle + amount);
        if (!this.engineOn && this.fuel > 0) {
            this.engineOn = true;
        }
    }

    throttleDown(amount) {
        this.throttle = Math.max(0, this.throttle - amount);
    }

    toggleEngine() {
        if (this.fuel > 0) {
            this.engineOn = !this.engineOn;
        }
    }

    deployLegs() {
        this.legsDeployed = true;
    }

    setGridFinInput(input) {
        this.gridFinInput = input;
    }

    getTWR() {
        if (!this.engineOn) return 0;
        const currentMass = this.mass + this.fuel;
        const weight = currentMass * CONFIG.GRAVITY;
        const thrust = CONFIG.MAX_THRUST * this.throttle;
        return thrust / weight;
    }

    getFuelPercentage() {
        return (this.fuel / CONFIG.ROCKET_FUEL_MAX) * 100;
    }

    getAltitude() {
        return CONFIG.CANVAS_HEIGHT - this.y - (this.height / 2);
    }

    getAngleDegrees() {
        let deg = this.angle * (180 / Math.PI);
        // Normalize to -180 to 180
        while (deg > 180) deg -= 360;
        while (deg < -180) deg += 360;
        return deg;
    }

    calculateImpactPoint() {
        // Simple ballistic prediction
        if (this.vy < 0) return null;

        const altitude = this.getAltitude();
        const timeToGround = altitude / this.vy;
        return this.x + this.vx * timeToGround;
    }

    draw(ctx) {
        ctx.save();
        ctx.translate(this.x, this.y);
        ctx.rotate(this.angle);

        // Draw exhaust particles first (behind rocket)
        ctx.restore();
        this.drawExhaust(ctx);
        ctx.save();
        ctx.translate(this.x, this.y);
        ctx.rotate(this.angle);

        // Draw landing legs
        if (this.legsDeployed) {
            this.drawLegs(ctx);
        }

        // Draw rocket body
        ctx.fillStyle = CONFIG.COLOR_ROCKET;
        ctx.fillRect(-this.width / 2, -this.height / 2, this.width, this.height);

        // Draw grid fins
        this.drawGridFins(ctx);

        // Draw nose cone
        ctx.beginPath();
        ctx.moveTo(-this.width / 2, -this.height / 2);
        ctx.lineTo(0, -this.height / 2 - 15);
        ctx.lineTo(this.width / 2, -this.height / 2);
        ctx.closePath();
        ctx.fillStyle = '#999';
        ctx.fill();

        // Draw engine bell
        ctx.fillStyle = '#333';
        ctx.fillRect(-this.width / 2 + 5, this.height / 2, this.width - 10, 10);

        ctx.restore();
    }

    drawExhaust(ctx) {
        this.exhaustParticles.forEach(p => {
            const alpha = p.life / p.maxLife;
            ctx.fillStyle = `rgba(255, ${Math.floor(102 * alpha)}, 0, ${alpha})`;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
        });
    }

    drawGridFins(ctx) {
        const finAngle = this.gridFinInput * 0.2; // Slight rotation for visual feedback

        ctx.fillStyle = CONFIG.COLOR_GRID_FIN;

        // Left fins
        ctx.save();
        ctx.translate(-this.width / 2 - 5, 0);
        ctx.rotate(finAngle);
        ctx.fillRect(-CONFIG.GRID_FIN_SIZE, -CONFIG.GRID_FIN_SIZE / 2, CONFIG.GRID_FIN_SIZE, CONFIG.GRID_FIN_SIZE);
        ctx.restore();

        // Right fins
        ctx.save();
        ctx.translate(this.width / 2 + 5, 0);
        ctx.rotate(finAngle);
        ctx.fillRect(0, -CONFIG.GRID_FIN_SIZE / 2, CONFIG.GRID_FIN_SIZE, CONFIG.GRID_FIN_SIZE);
        ctx.restore();
    }

    drawLegs(ctx) {
        ctx.strokeStyle = CONFIG.COLOR_LEG;
        ctx.lineWidth = 3;

        // Left leg
        ctx.beginPath();
        ctx.moveTo(-this.width / 2, this.height / 2 - 10);
        ctx.lineTo(-this.width / 2 - CONFIG.LEG_SIZE, this.height / 2 + CONFIG.LEG_SIZE);
        ctx.stroke();

        // Right leg
        ctx.beginPath();
        ctx.moveTo(this.width / 2, this.height / 2 - 10);
        ctx.lineTo(this.width / 2 + CONFIG.LEG_SIZE, this.height / 2 + CONFIG.LEG_SIZE);
        ctx.stroke();
    }
}
