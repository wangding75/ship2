using System;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;

// T03 build/launch fixture only. Inert unless the explicit command-line flag is present.
public sealed class T03SmokeProbe : MonoBehaviour
{
    private string evidence;
    private int frames;
    private float started;
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    private static void Install()
    {
        var args = Environment.GetCommandLineArgs();
        for (int i = 0; i < args.Length - 1; i++)
            if (args[i] == "-t03-smoke")
            {
                var probe = new GameObject("T03 launch verification fixture").AddComponent<T03SmokeProbe>();
                probe.evidence = Path.GetFullPath(args[i + 1]);
                probe.started = Time.realtimeSinceStartup;
                Application.runInBackground = true;
                Application.targetFrameRate = 60;
                return;
            }
    }
    private void Update()
    {
        frames++;
        if (frames != 90) return;
        try
        {
            Directory.CreateDirectory(evidence);
            int width = Screen.width, height = Screen.height;
            var camera = Camera.main;
            if (camera == null || SystemInfo.graphicsDeviceType == GraphicsDeviceType.Null) throw new Exception("Real graphics camera required");
            var target = RenderTexture.GetTemporary(width, height, 24);
            var previous = RenderTexture.active;
            camera.targetTexture = target;
            camera.Render();
            RenderTexture.active = target;
            var pixels = new Texture2D(width, height, TextureFormat.RGB24, false);
            pixels.ReadPixels(new Rect(0, 0, width, height), 0, 0);
            pixels.Apply();
            File.WriteAllBytes(Path.Combine(evidence, "launch.png"), pixels.EncodeToPNG());
            camera.targetTexture = null;
            RenderTexture.active = previous;
            RenderTexture.ReleaseTemporary(target);
            Destroy(pixels);
            var record = new Record { utc=DateTime.UtcNow.ToString("o"), frames=frames, seconds=Time.realtimeSinceStartup-started, width=width, height=height, graphicsDevice=SystemInfo.graphicsDeviceName, graphicsApi=SystemInfo.graphicsDeviceType.ToString(), unity=Application.unityVersion, scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene().path, success=true };
            File.WriteAllText(Path.Combine(evidence, "launch.json"), JsonUtility.ToJson(record, true));
            Debug.Log("T03_SMOKE_PASS: 90 advancing frames and GPU camera capture");
            Application.Quit(0);
        }
        catch (Exception ex) { Debug.LogException(ex); Application.Quit(1); }
    }
    [Serializable] private sealed class Record
    {
        public string utc, graphicsDevice, graphicsApi, unity, scene;
        public int frames, width, height;
        public float seconds;
        public bool success;
    }
}
