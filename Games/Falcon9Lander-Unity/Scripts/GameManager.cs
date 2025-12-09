using UnityEngine;
using UnityEngine.SceneManagement;

public class GameManager : MonoBehaviour
{
    public static GameManager Instance { get; private set; }

    [Header("Game State")]
    public bool gameActive = true;
    public int currentLevel = 0;

    [Header("Level Data")]
    public LevelData[] levels;

    void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
        }
        else
        {
            Destroy(gameObject);
        }
    }

    void Start()
    {
        LoadLevel(currentLevel);
    }

    public void LoadLevel(int levelIndex)
    {
        if (levelIndex < levels.Length)
        {
            currentLevel = levelIndex;
            LevelData level = levels[levelIndex];

            Debug.Log($"Loading Level: {level.levelName}");

            // Apply level settings (you'll need to implement this based on your scene setup)
            ApplyLevelSettings(level);

            gameActive = true;
        }
    }

    void ApplyLevelSettings(LevelData level)
    {
        // Find rocket in scene
        RocketController rocket = FindObjectOfType<RocketController>();
        if (rocket != null)
        {
            rocket.transform.position = level.startPosition;
            rocket.wind = level.windForce;
        }

        // Setup landing zone
        LandingZone landingZone = FindObjectOfType<LandingZone>();
        if (landingZone != null)
        {
            landingZone.transform.position = level.landingZonePosition;
            landingZone.isDroneShip = level.isDroneShip;
        }
    }

    public void OnSuccessfulLanding()
    {
        if (!gameActive) return;

        gameActive = false;
        Debug.Log("SUCCESS! Landing complete!");

        // Wait a moment then load next level
        Invoke("LoadNextLevel", 3f);
    }

    public void OnCrash(string reason)
    {
        if (!gameActive) return;

        gameActive = false;
        Debug.Log($"MISSION FAILED: {reason}");

        // Wait then restart level
        Invoke("RestartLevel", 3f);
    }

    public void LoadNextLevel()
    {
        int nextLevel = currentLevel + 1;
        if (nextLevel < levels.Length)
        {
            LoadLevel(nextLevel);
        }
        else
        {
            Debug.Log("YOU WON! All levels complete!");
        }
    }

    public void RestartLevel()
    {
        SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex);
    }
}

[System.Serializable]
public class LevelData
{
    public string levelName;
    public Vector3 startPosition;
    public Vector3 landingZonePosition;
    public Vector2 windForce;
    public bool isDroneShip;
    public float targetSize = 20f;
}
