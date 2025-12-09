using UnityEngine;

public class RocketController : MonoBehaviour
{
    [Header("Physics Settings")]
    public float gravity = 9.8f;
    public float dragCoefficient = 0.5f;
    public float mass = 25000f; // kg (empty)
    public float fuelMass = 15000f; // kg
    public float maxFuel = 15000f;

    [Header("Engine Settings")]
    public float maxThrust = 845000f; // Newtons (~190,000 lbf)
    public float minThrottle = 0.4f; // 40% minimum
    public float maxThrottle = 1.0f;
    public float currentThrottle = 0f;
    public bool engineOn = false;
    public float fuelBurnRate = 250f; // kg/s at full throttle

    [Header("Grid Fins")]
    public float gridFinTorque = 50000f;
    public float gridFinEffectivenessMin = 0.1f;

    [Header("Landing Legs")]
    public bool legsDeployed = false;
    public float legDragIncrease = 0.3f;
    public float legSpringConstant = 100000f;
    public float legDamping = 5000f;

    [Header("Wind")]
    public Vector2 wind = Vector2.zero;

    // Internal state
    private Rigidbody2D rb;
    private Vector2 velocity;
    private float currentRotation = 0f;
    private float angularVelocity = 0f;
    private float momentOfInertia;

    // Telemetry
    public float altitude;
    public float verticalVelocity;
    public float horizontalVelocity;
    public Vector2 impactPoint;

    void Start()
    {
        rb = GetComponent<Rigidbody2D>();
        if (rb == null)
        {
            rb = gameObject.AddComponent<Rigidbody2D>();
        }

        rb.gravityScale = 0; // We'll handle gravity manually
        CalculateMomentOfInertia();
    }

    void FixedUpdate()
    {
        float dt = Time.fixedDeltaTime;

        // Calculate current mass (rocket + remaining fuel)
        float currentMass = mass + fuelMass;

        // Get current velocity
        velocity = rb.velocity;

        // Calculate telemetry
        CalculateTelemetry();

        // Apply forces
        Vector2 totalForce = Vector2.zero;

        // 1. Gravity
        totalForce += Vector2.down * gravity * currentMass;

        // 2. Atmospheric Drag
        float dragMult = legsDeployed ? (1f + legDragIncrease) : 1f;
        Vector2 dragForce = -velocity * velocity.magnitude * dragCoefficient * dragMult;
        totalForce += dragForce;

        // 3. Wind (stronger at higher altitudes)
        float windFactor = Mathf.Clamp01(altitude / 1000f);
        totalForce += wind * windFactor * currentMass;

        // 4. Engine Thrust
        if (engineOn && fuelMass > 0)
        {
            float actualThrottle = Mathf.Clamp(currentThrottle, minThrottle, maxThrottle);
            Vector2 thrustDirection = transform.up;
            Vector2 thrustForce = thrustDirection * maxThrust * actualThrottle;
            totalForce += thrustForce;

            // Burn fuel
            float fuelUsed = fuelBurnRate * actualThrottle * dt;
            fuelMass = Mathf.Max(0, fuelMass - fuelUsed);

            if (fuelMass <= 0)
            {
                engineOn = false;
            }
        }

        // Apply forces to velocity
        Vector2 acceleration = totalForce / currentMass;
        velocity += acceleration * dt;
        rb.velocity = velocity;

        // Update telemetry
        CalculateTelemetry();
    }

    void CalculateMomentOfInertia()
    {
        // Approximation for a cylinder: I = (1/12) * m * h^2
        float height = 70f; // Falcon 9 first stage is ~42m, scaled
        momentOfInertia = (1f / 12f) * (mass + fuelMass) * height * height;
    }

    void CalculateTelemetry()
    {
        // Altitude (distance from ground, assuming ground is at y=0)
        altitude = transform.position.y;

        // Vertical and horizontal velocity
        verticalVelocity = velocity.y;
        horizontalVelocity = velocity.x;

        // Calculate impact point (simple ballistic prediction)
        if (verticalVelocity < 0)
        {
            float timeToGround = altitude / Mathf.Abs(verticalVelocity);
            impactPoint = new Vector2(
                transform.position.x + horizontalVelocity * timeToGround,
                0
            );
        }
    }

    // Control methods
    public void ThrottleUp(float amount)
    {
        currentThrottle = Mathf.Clamp(currentThrottle + amount, 0f, maxThrottle);
    }

    public void ThrottleDown(float amount)
    {
        currentThrottle = Mathf.Clamp(currentThrottle - amount, 0f, maxThrottle);
    }

    public void ToggleEngine()
    {
        if (fuelMass > 0)
        {
            engineOn = !engineOn;
        }
    }

    public void ApplyGridFinControl(float input)
    {
        // Grid fins are more effective at higher speeds
        float effectiveness = Mathf.Lerp(
            gridFinEffectivenessMin,
            1f,
            Mathf.Abs(verticalVelocity) / 100f
        );

        float torque = input * gridFinTorque * effectiveness;
        rb.AddTorque(torque);
    }

    public void DeployLandingLegs()
    {
        if (!legsDeployed)
        {
            legsDeployed = true;
            Debug.Log("Landing legs deployed");
        }
    }

    public float GetThrustToWeightRatio()
    {
        if (!engineOn) return 0f;
        float currentMass = mass + fuelMass;
        float weight = currentMass * gravity;
        float thrust = maxThrust * currentThrottle;
        return thrust / weight;
    }

    public float GetFuelPercentage()
    {
        return (fuelMass / maxFuel) * 100f;
    }
}
