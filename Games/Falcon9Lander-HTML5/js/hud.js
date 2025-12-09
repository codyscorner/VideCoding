// HUD Controller
class HUD {
    constructor() {
        // Telemetry elements
        this.altitudeEl = document.getElementById('altitude');
        this.verticalSpeedEl = document.getElementById('verticalSpeed');
        this.horizontalSpeedEl = document.getElementById('horizontalSpeed');
        this.angleEl = document.getElementById('angle');

        // Systems elements
        this.fuelEl = document.getElementById('fuel');
        this.fuelFillEl = document.getElementById('fuelFill');
        this.throttleEl = document.getElementById('throttle');
        this.throttleFillEl = document.getElementById('throttleFill');
        this.twrEl = document.getElementById('twr');
        this.engineStatusEl = document.getElementById('engineStatus');
        this.legsStatusEl = document.getElementById('legsStatus');

        // Level info
        this.levelNameEl = document.getElementById('levelName');
        this.levelDescEl = document.getElementById('levelDesc');
    }

    update(rocket, levelManager) {
        // Altitude
        const altitude = rocket.getAltitude();
        this.altitudeEl.textContent = `${Math.max(0, altitude).toFixed(1)} m`;

        // Vertical Speed (negative is down in our coordinate system)
        const vertSpeed = -rocket.vy; // Flip sign for display
        this.verticalSpeedEl.textContent = `${vertSpeed.toFixed(1)} m/s`;
        this.updateColorClass(this.verticalSpeedEl, Math.abs(vertSpeed), 3, 6);

        // Horizontal Speed
        const horizSpeed = rocket.vx;
        this.horizontalSpeedEl.textContent = `${horizSpeed.toFixed(1)} m/s`;
        this.updateColorClass(this.horizontalSpeedEl, Math.abs(horizSpeed), 1.5, 3);

        // Angle
        const angle = rocket.getAngleDegrees();
        this.angleEl.textContent = `${angle.toFixed(1)}°`;
        this.updateColorClass(this.angleEl, Math.abs(angle), 10, 30);

        // Fuel
        const fuelPercent = rocket.getFuelPercentage();
        this.fuelEl.textContent = `${fuelPercent.toFixed(0)}%`;
        this.fuelFillEl.style.width = `${fuelPercent}%`;
        this.updateProgressBarColor(this.fuelFillEl, fuelPercent, 30, 10);

        // Throttle
        const throttlePercent = rocket.throttle * 100;
        this.throttleEl.textContent = `${throttlePercent.toFixed(0)}%`;
        this.throttleFillEl.style.width = `${throttlePercent}%`;

        // TWR
        const twr = rocket.getTWR();
        this.twrEl.textContent = `${twr.toFixed(2)}`;
        if (twr > 1.0) {
            this.twrEl.classList.remove('warning', 'danger');
            this.twrEl.classList.add('safe');
        } else if (twr > 0.5) {
            this.twrEl.classList.remove('safe', 'danger');
            this.twrEl.classList.add('warning');
        } else {
            this.twrEl.classList.remove('safe', 'warning');
        }

        // Engine Status
        if (rocket.fuel <= 0) {
            this.engineStatusEl.textContent = 'NO FUEL';
            this.engineStatusEl.classList.remove('status-on', 'status-off');
            this.engineStatusEl.classList.add('danger');
        } else if (rocket.engineOn) {
            this.engineStatusEl.textContent = 'ON';
            this.engineStatusEl.classList.remove('status-off', 'danger');
            this.engineStatusEl.classList.add('status-on');
        } else {
            this.engineStatusEl.textContent = 'OFF';
            this.engineStatusEl.classList.remove('status-on', 'danger');
            this.engineStatusEl.classList.add('status-off');
        }

        // Legs Status
        if (rocket.legsDeployed) {
            this.legsStatusEl.textContent = 'DEPLOYED';
            this.legsStatusEl.classList.remove('status-warning');
            this.legsStatusEl.classList.add('safe');
        } else {
            this.legsStatusEl.textContent = 'RETRACTED';
            this.legsStatusEl.classList.remove('safe');
            this.legsStatusEl.classList.add('status-warning');
        }
    }

    updateColorClass(element, value, safeThreshold, dangerThreshold) {
        element.classList.remove('safe', 'warning', 'danger');

        if (value <= safeThreshold) {
            element.classList.add('safe');
        } else if (value <= dangerThreshold) {
            element.classList.add('warning');
        } else {
            element.classList.add('danger');
        }
    }

    updateProgressBarColor(element, percent, warningThreshold, dangerThreshold) {
        element.classList.remove('warning', 'danger');

        if (percent <= dangerThreshold) {
            element.classList.add('danger');
        } else if (percent <= warningThreshold) {
            element.classList.add('warning');
        }
    }

    updateLevelInfo(levelManager) {
        const info = levelManager.getLevelInfo();
        this.levelNameEl.textContent = info.name;
        this.levelDescEl.textContent = info.description;
    }
}
