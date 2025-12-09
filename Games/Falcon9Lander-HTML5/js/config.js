// Game Configuration
const CONFIG = {
    // Canvas
    CANVAS_WIDTH: 1200,
    CANVAS_HEIGHT: 800,

    // Physics
    GRAVITY: 0.05, // Scaled down from 9.8 m/s² for game units (much slower)
    DRAG_COEFFICIENT: 0.004,

    // Rocket Physics
    ROCKET_MASS_EMPTY: 25000, // kg
    ROCKET_FUEL_MAX: 15000, // kg
    ROCKET_WIDTH: 20,
    ROCKET_HEIGHT: 140,

    // Engine
    MAX_THRUST: 4000, // Scaled for proper TWR (needs to overcome gravity + provide control)
    MIN_THROTTLE: 0.4, // 40% minimum
    MAX_THROTTLE: 1.0,
    FUEL_BURN_RATE: 1.2, // kg per frame at full throttle

    // Grid Fins
    GRID_FIN_TORQUE: 0.002,
    GRID_FIN_EFFECTIVENESS_MIN: 0.1,

    // Landing Legs
    LEG_DRAG_INCREASE: 0.3,

    // Landing Criteria
    MAX_LANDING_VERTICAL_SPEED: 3, // Reduced for slower physics
    MAX_LANDING_HORIZONTAL_SPEED: 1.5,
    MAX_LANDING_ANGLE: 10, // degrees

    // Visual
    EXHAUST_PARTICLES: 50,
    GRID_FIN_SIZE: 8,
    LEG_SIZE: 15,

    // Colors
    COLOR_ROCKET: '#CCCCCC',
    COLOR_EXHAUST: '#FF6600',
    COLOR_GROUND: '#654321',
    COLOR_LANDING_ZONE: '#00FF00',
    COLOR_IMPACT_MARKER: '#FF0000',
    COLOR_GRID_FIN: '#888888',
    COLOR_LEG: '#444444'
};

// Level Definitions
const LEVELS = [
    {
        name: "Level 1: The Grasshopper",
        description: "Tutorial - Low altitude hop, no wind",
        startX: 600,
        startY: 200, // ~600m altitude
        landingZoneX: 600,
        landingZoneWidth: 120,
        wind: { x: 0, y: 0 },
        isDroneShip: false
    },
    {
        name: "Level 2: Return to Launch Site (LZ-1)",
        description: "Drop from sub-orbital height with wind",
        startX: 200,
        startY: 150, // ~650m altitude - sub-orbital
        landingZoneX: 700,
        landingZoneWidth: 90,
        wind: { x: 0.02, y: 0 }, // Reduced wind for new physics
        isDroneShip: false
    },
    {
        name: "Level 3: Of Course I Still Love You",
        description: "Drone ship landing - moving target",
        startX: 300,
        startY: 120, // ~680m altitude
        landingZoneX: 800,
        landingZoneWidth: 70,
        wind: { x: 0.03, y: 0 }, // Reduced wind for new physics
        isDroneShip: true
    },
    {
        name: "Level 4: Falcon Heavy Center Core",
        description: "High speed entry - precision required",
        startX: 600,
        startY: 100, // ~700m altitude - highest entry
        landingZoneX: 600,
        landingZoneWidth: 60,
        wind: { x: 0.04, y: 0 }, // Reduced wind for new physics
        isDroneShip: false
    }
];
