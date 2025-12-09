using UnityEngine;

public class LandingZone : MonoBehaviour
{
    [Header("Landing Zone Settings")]
    public float maxSafeLandingSpeed = 5f; // m/s vertical
    public float maxSafeTiltAngle = 10f; // degrees
    public float maxSafeHorizontalSpeed = 2f; // m/s

    [Header("Drone Ship Settings")]
    public bool isDroneShip = false;
    public float bobAmplitude = 0.5f;
    public float bobFrequency = 0.3f;
    private Vector3 originalPosition;

    void Start()
    {
        originalPosition = transform.position;
    }

    void Update()
    {
        if (isDroneShip)
        {
            // Simulate ocean wave bobbing
            float newY = originalPosition.y + Mathf.Sin(Time.time * bobFrequency * 2f * Mathf.PI) * bobAmplitude;
            transform.position = new Vector3(transform.position.x, newY, transform.position.z);
        }
    }

    void OnTriggerEnter2D(Collider2D other)
    {
        RocketController rocket = other.GetComponent<RocketController>();
        if (rocket != null)
        {
            CheckLanding(rocket);
        }
    }

    void CheckLanding(RocketController rocket)
    {
        float vertSpeed = Mathf.Abs(rocket.verticalVelocity);
        float horizSpeed = Mathf.Abs(rocket.horizontalVelocity);
        float tilt = Mathf.Abs(rocket.transform.eulerAngles.z);

        // Normalize angle to 0-180 range
        if (tilt > 180) tilt = 360 - tilt;

        bool speedOk = vertSpeed <= maxSafeLandingSpeed;
        bool horizOk = horizSpeed <= maxSafeHorizontalSpeed;
        bool angleOk = tilt <= maxSafeTiltAngle;
        bool legsOk = rocket.legsDeployed;

        if (speedOk && horizOk && angleOk && legsOk)
        {
            Debug.Log("SUCCESSFUL LANDING!");
            GameManager.Instance?.OnSuccessfulLanding();
        }
        else
        {
            string reason = "";
            if (!speedOk) reason += "Vertical speed too high! ";
            if (!horizOk) reason += "Horizontal speed too high! ";
            if (!angleOk) reason += "Tilt angle too steep! ";
            if (!legsOk) reason += "Landing legs not deployed! ";

            Debug.Log("CRASH: " + reason);
            GameManager.Instance?.OnCrash(reason);
        }
    }
}
