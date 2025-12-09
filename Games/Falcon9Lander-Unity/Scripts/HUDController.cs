using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class HUDController : MonoBehaviour
{
    [Header("References")]
    public RocketController rocket;

    [Header("UI Text Elements")]
    public TextMeshProUGUI altitudeText;
    public TextMeshProUGUI verticalVelocityText;
    public TextMeshProUGUI horizontalVelocityText;
    public TextMeshProUGUI fuelText;
    public TextMeshProUGUI throttleText;
    public TextMeshProUGUI twrText;
    public TextMeshProUGUI legsStatusText;
    public TextMeshProUGUI engineStatusText;

    [Header("UI Images")]
    public Image fuelGauge;
    public GameObject impactMarker;

    [Header("Colors")]
    public Color safeColor = Color.green;
    public Color warningColor = Color.yellow;
    public Color dangerColor = Color.red;

    void Update()
    {
        if (rocket == null) return;

        UpdateTelemetry();
        UpdateImpactPredictor();
    }

    void UpdateTelemetry()
    {
        // Altitude
        if (altitudeText != null)
        {
            altitudeText.text = $"ALT: {rocket.altitude:F1} m";
        }

        // Vertical Velocity with color coding
        if (verticalVelocityText != null)
        {
            float vertSpeed = rocket.verticalVelocity;
            verticalVelocityText.text = $"V/S: {vertSpeed:F1} m/s";

            // Color code based on safety
            if (Mathf.Abs(vertSpeed) < 5f)
                verticalVelocityText.color = safeColor;
            else if (Mathf.Abs(vertSpeed) < 15f)
                verticalVelocityText.color = warningColor;
            else
                verticalVelocityText.color = dangerColor;
        }

        // Horizontal Velocity
        if (horizontalVelocityText != null)
        {
            float horizSpeed = rocket.horizontalVelocity;
            horizontalVelocityText.text = $"H/S: {horizSpeed:F1} m/s";

            if (Mathf.Abs(horizSpeed) < 2f)
                horizontalVelocityText.color = safeColor;
            else if (Mathf.Abs(horizSpeed) < 5f)
                horizontalVelocityText.color = warningColor;
            else
                horizontalVelocityText.color = dangerColor;
        }

        // Fuel Gauge
        if (fuelText != null)
        {
            float fuelPercent = rocket.GetFuelPercentage();
            fuelText.text = $"FUEL: {fuelPercent:F0}%";

            if (fuelGauge != null)
            {
                fuelGauge.fillAmount = fuelPercent / 100f;

                if (fuelPercent > 30f)
                    fuelGauge.color = safeColor;
                else if (fuelPercent > 10f)
                    fuelGauge.color = warningColor;
                else
                    fuelGauge.color = dangerColor;
            }
        }

        // Throttle
        if (throttleText != null)
        {
            throttleText.text = $"THROTTLE: {(rocket.currentThrottle * 100f):F0}%";
        }

        // Thrust to Weight Ratio
        if (twrText != null)
        {
            float twr = rocket.GetThrustToWeightRatio();
            twrText.text = $"TWR: {twr:F2}";

            if (twr > 1.0f)
                twrText.color = safeColor;
            else if (twr > 0.5f)
                twrText.color = warningColor;
            else
                twrText.color = Color.white;
        }

        // Landing Legs Status
        if (legsStatusText != null)
        {
            legsStatusText.text = rocket.legsDeployed ? "LEGS: DEPLOYED" : "LEGS: RETRACTED";
            legsStatusText.color = rocket.legsDeployed ? safeColor : warningColor;
        }

        // Engine Status
        if (engineStatusText != null)
        {
            if (rocket.fuelMass <= 0)
            {
                engineStatusText.text = "ENGINE: NO FUEL";
                engineStatusText.color = dangerColor;
            }
            else
            {
                engineStatusText.text = rocket.engineOn ? "ENGINE: ON" : "ENGINE: OFF";
                engineStatusText.color = rocket.engineOn ? safeColor : Color.white;
            }
        }
    }

    void UpdateImpactPredictor()
    {
        if (impactMarker != null && rocket != null)
        {
            // Show impact marker on ground
            Vector3 impactPos = new Vector3(rocket.impactPoint.x, rocket.impactPoint.y, 0);
            impactMarker.transform.position = impactPos;

            // Only show when descending
            impactMarker.SetActive(rocket.verticalVelocity < -1f);
        }
    }
}
