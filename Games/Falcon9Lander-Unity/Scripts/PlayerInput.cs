using UnityEngine;

public class PlayerInput : MonoBehaviour
{
    private RocketController rocket;

    [Header("Input Settings")]
    public float throttleChangeRate = 0.5f; // Per second

    void Start()
    {
        rocket = GetComponent<RocketController>();
    }

    void Update()
    {
        // Throttle control
        if (Input.GetKey(KeyCode.W) || Input.GetKey(KeyCode.UpArrow))
        {
            rocket.ThrottleUp(throttleChangeRate * Time.deltaTime);
            if (!rocket.engineOn)
            {
                rocket.ToggleEngine();
            }
        }

        if (Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.DownArrow))
        {
            rocket.ThrottleDown(throttleChangeRate * Time.deltaTime);
        }

        // Engine toggle
        if (Input.GetKeyDown(KeyCode.Space))
        {
            rocket.ToggleEngine();
        }

        // Grid fin control (rotation)
        float gridFinInput = 0f;
        if (Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.LeftArrow))
        {
            gridFinInput = 1f;
        }
        else if (Input.GetKey(KeyCode.D) || Input.GetKey(KeyCode.RightArrow))
        {
            gridFinInput = -1f;
        }

        if (gridFinInput != 0f)
        {
            rocket.ApplyGridFinControl(gridFinInput);
        }

        // Deploy landing legs
        if (Input.GetKeyDown(KeyCode.L))
        {
            rocket.DeployLandingLegs();
        }
    }
}
