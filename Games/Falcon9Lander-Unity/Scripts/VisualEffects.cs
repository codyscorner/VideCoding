using UnityEngine;

public class VisualEffects : MonoBehaviour
{
    [Header("References")]
    public RocketController rocket;
    public ParticleSystem engineExhaust;
    public SpriteRenderer rocketSprite;
    public GameObject gridFinLeft;
    public GameObject gridFinRight;
    public GameObject[] landingLegs;

    [Header("Engine Exhaust Settings")]
    public float exhaustScaleMin = 0.5f;
    public float exhaustScaleMax = 2.0f;

    [Header("Soot Settings")]
    public Color cleanColor = Color.white;
    public Color sootColor = new Color(0.3f, 0.3f, 0.3f);
    private float sootAccumulation = 0f;

    void Update()
    {
        if (rocket == null) return;

        UpdateEngineExhaust();
        UpdateGridFins();
        UpdateLandingLegs();
        UpdateSoot();
    }

    void UpdateEngineExhaust()
    {
        if (engineExhaust != null)
        {
            if (rocket.engineOn && rocket.fuelMass > 0)
            {
                if (!engineExhaust.isPlaying)
                    engineExhaust.Play();

                // Scale exhaust based on throttle
                var main = engineExhaust.main;
                float scale = Mathf.Lerp(exhaustScaleMin, exhaustScaleMax, rocket.currentThrottle);
                main.startSize = scale;

                // Adjust based on altitude (wide plume at high altitude, tight at low)
                float altitudeFactor = Mathf.Clamp01(rocket.altitude / 1000f);
                main.startSpeed = Mathf.Lerp(10f, 5f, altitudeFactor);
            }
            else
            {
                if (engineExhaust.isPlaying)
                    engineExhaust.Stop();
            }
        }
    }

    void UpdateGridFins()
    {
        // Grid fins can rotate slightly to show control input
        float finAngle = 0f;

        if (Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.LeftArrow))
            finAngle = -15f;
        else if (Input.GetKey(KeyCode.D) || Input.GetKey(KeyCode.RightArrow))
            finAngle = 15f;

        if (gridFinLeft != null)
            gridFinLeft.transform.localRotation = Quaternion.Euler(0, 0, finAngle);

        if (gridFinRight != null)
            gridFinRight.transform.localRotation = Quaternion.Euler(0, 0, finAngle);
    }

    void UpdateLandingLegs()
    {
        if (landingLegs != null && landingLegs.Length > 0)
        {
            float targetAngle = rocket.legsDeployed ? 45f : 0f;

            foreach (GameObject leg in landingLegs)
            {
                if (leg != null)
                {
                    // Smooth rotation
                    Quaternion targetRotation = Quaternion.Euler(0, 0, targetAngle);
                    leg.transform.localRotation = Quaternion.Lerp(
                        leg.transform.localRotation,
                        targetRotation,
                        Time.deltaTime * 5f
                    );
                }
            }
        }
    }

    void UpdateSoot()
    {
        // Accumulate soot when engine is firing
        if (rocket.engineOn)
        {
            sootAccumulation += Time.deltaTime * 0.1f;
            sootAccumulation = Mathf.Clamp01(sootAccumulation);
        }

        // Apply soot color to rocket sprite
        if (rocketSprite != null)
        {
            rocketSprite.color = Color.Lerp(cleanColor, sootColor, sootAccumulation);
        }
    }

    public void TriggerExplosion()
    {
        // Create explosion effect
        Debug.Log("RUD - Rapid Unscheduled Disassembly!");
        // You can add particle effects, sound, etc. here
    }
}
