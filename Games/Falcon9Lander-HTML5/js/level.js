// Level Manager
class LevelManager {
    constructor() {
        this.currentLevelIndex = 0;
        this.currentLevel = LEVELS[0];
        this.landingZoneX = this.currentLevel.landingZoneX;
        this.landingZoneY = CONFIG.CANVAS_HEIGHT - 20;
        this.droneShipOffset = 0;
        this.droneShipDirection = 1;
    }

    loadLevel(index) {
        if (index < 0 || index >= LEVELS.length) return false;

        this.currentLevelIndex = index;
        this.currentLevel = LEVELS[index];
        this.landingZoneX = this.currentLevel.landingZoneX;
        this.droneShipOffset = 0;

        return true;
    }

    nextLevel() {
        return this.loadLevel(this.currentLevelIndex + 1);
    }

    update() {
        // Update drone ship bobbing if applicable
        if (this.currentLevel.isDroneShip) {
            this.droneShipOffset = Math.sin(Date.now() / 1000) * 30;
        }
    }

    draw(ctx) {
        // Draw ground
        ctx.fillStyle = CONFIG.COLOR_GROUND;
        ctx.fillRect(0, CONFIG.CANVAS_HEIGHT - 20, CONFIG.CANVAS_WIDTH, 20);

        // Draw landing zone
        const zoneX = this.landingZoneX + this.droneShipOffset;
        const zoneWidth = this.currentLevel.landingZoneWidth;
        const zoneY = CONFIG.CANVAS_HEIGHT - 20;

        // Landing pad base
        ctx.fillStyle = CONFIG.COLOR_LANDING_ZONE;
        ctx.fillRect(zoneX - zoneWidth / 2, zoneY, zoneWidth, 20);

        // Landing pad outline
        ctx.strokeStyle = '#00FF00';
        ctx.lineWidth = 2;
        ctx.strokeRect(zoneX - zoneWidth / 2, zoneY, zoneWidth, 20);

        // Center cross (SpaceX style)
        ctx.beginPath();
        ctx.moveTo(zoneX - 10, zoneY + 10);
        ctx.lineTo(zoneX + 10, zoneY + 10);
        ctx.moveTo(zoneX, zoneY);
        ctx.lineTo(zoneX, zoneY + 20);
        ctx.stroke();

        // Drone ship label
        if (this.currentLevel.isDroneShip) {
            ctx.fillStyle = '#00FF00';
            ctx.font = '12px Courier New';
            ctx.textAlign = 'center';
            ctx.fillText('OCISLY', zoneX, zoneY - 5);
        }
    }

    drawImpactMarker(ctx, impactX) {
        if (!impactX) return;

        const markerY = CONFIG.CANVAS_HEIGHT - 20;

        ctx.strokeStyle = CONFIG.COLOR_IMPACT_MARKER;
        ctx.lineWidth = 2;

        // Draw X marker
        ctx.beginPath();
        ctx.moveTo(impactX - 10, markerY - 10);
        ctx.lineTo(impactX + 10, markerY + 10);
        ctx.moveTo(impactX + 10, markerY - 10);
        ctx.lineTo(impactX - 10, markerY + 10);
        ctx.stroke();
    }

    checkLanding(rocket) {
        const zoneX = this.landingZoneX + this.droneShipOffset;
        const zoneWidth = this.currentLevel.landingZoneWidth;
        const zoneY = CONFIG.CANVAS_HEIGHT - 20;

        // Check if rocket is at ground level
        const rocketBottom = rocket.y + rocket.height / 2;
        if (rocketBottom < zoneY - 5) return null; // Not landed yet

        // Check if within landing zone
        const inZone = rocket.x > (zoneX - zoneWidth / 2) && rocket.x < (zoneX + zoneWidth / 2);
        if (!inZone) {
            return {
                success: false,
                reason: "Missed the landing zone!"
            };
        }

        // Check landing criteria
        const vertSpeed = Math.abs(rocket.vy);
        const horizSpeed = Math.abs(rocket.vx);
        const angle = Math.abs(rocket.getAngleDegrees());

        const speedOk = vertSpeed <= CONFIG.MAX_LANDING_VERTICAL_SPEED;
        const horizOk = horizSpeed <= CONFIG.MAX_LANDING_HORIZONTAL_SPEED;
        const angleOk = angle <= CONFIG.MAX_LANDING_ANGLE;
        const legsOk = rocket.legsDeployed;

        if (speedOk && horizOk && angleOk && legsOk) {
            return {
                success: true,
                reason: "Perfect landing!"
            };
        } else {
            let reasons = [];
            if (!speedOk) reasons.push(`Vertical speed too high (${vertSpeed.toFixed(1)} m/s)`);
            if (!horizOk) reasons.push(`Horizontal speed too high (${horizSpeed.toFixed(1)} m/s)`);
            if (!angleOk) reasons.push(`Tilt angle too steep (${angle.toFixed(1)}°)`);
            if (!legsOk) reasons.push("Landing legs not deployed");

            return {
                success: false,
                reason: reasons.join(", ")
            };
        }
    }

    getWind() {
        return this.currentLevel.wind;
    }

    getStartPosition() {
        return {
            x: this.currentLevel.startX,
            y: this.currentLevel.startY
        };
    }

    getLevelInfo() {
        return {
            name: this.currentLevel.name,
            description: this.currentLevel.description
        };
    }

    hasNextLevel() {
        return this.currentLevelIndex < LEVELS.length - 1;
    }
}
