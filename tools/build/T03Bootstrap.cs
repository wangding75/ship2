using System;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;

public static class T03Bootstrap
{
    public static string Create()
    {
        const string folder = "Assets/Game/Scenes";
        Directory.CreateDirectory(folder);
        AssetDatabase.Refresh();
        var pipelines = AssetDatabase.FindAssets("t:UniversalRenderPipelineAsset");
        if (pipelines.Length == 0) throw new Exception("No URP pipeline asset found");
        var pipeline = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(AssetDatabase.GUIDToAssetPath(pipelines[0]));
        GraphicsSettings.defaultRenderPipeline = pipeline;
        QualitySettings.renderPipeline = pipeline;
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        scene.name = "T03Foundation";
        RenderSettings.ambientMode = AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(0.45f, 0.51f, 0.6f);
        RenderSettings.fog = false;
        var cameraObject = new GameObject("Main Camera", typeof(Camera), typeof(AudioListener));
        cameraObject.tag = "MainCamera";
        var camera = cameraObject.GetComponent<Camera>();
        camera.transform.position = new Vector3(10, 11, -15);
        camera.transform.LookAt(new Vector3(0, 1, 0));
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = new Color(0.055f, 0.09f, 0.15f);
        camera.fieldOfView = 46;
        camera.nearClipPlane = 0.1f;
        camera.farClipPlane = 200;
        var light = new GameObject("Directional Light", typeof(Light)).GetComponent<Light>();
        light.type = LightType.Directional;
        light.intensity = 1.5f;
        light.transform.rotation = Quaternion.Euler(45, -35, 0);
        MakeBox("PROVISIONAL rendering calibration floor", new Vector3(0,-0.25f,0), new Vector3(14,0.5f,12), new Color(0.14f,0.22f,0.28f));
        MakeBox("Calibration cube 1m", new Vector3(-3,0.5f,0), Vector3.one, new Color(0.12f,0.65f,0.68f));
        MakeBox("Calibration cube 2m", new Vector3(0,1,0), new Vector3(2,2,2), new Color(0.88f,0.62f,0.22f));
        MakeBox("Calibration cube 3m", new Vector3(3,1.5f,0), new Vector3(2,3,2), new Color(0.36f,0.5f,0.78f));
        MakeBox("X axis", new Vector3(0,0.015f,-3), new Vector3(10,0.03f,0.04f), new Color(0.8f,0.3f,0.3f));
        MakeBox("Z axis", new Vector3(-5,0.015f,0), new Vector3(0.04f,0.03f,6), new Color(0.3f,0.7f,0.4f));
        PlayerSettings.companyName = "Ship S1";
        PlayerSettings.productName = "S1 T03 Foundation";
        PlayerSettings.bundleVersion = "0.0.1";
        PlayerSettings.defaultScreenWidth = 1920;
        PlayerSettings.defaultScreenHeight = 1080;
        PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
        PlayerSettings.runInBackground = true;
        PlayerSettings.SetScriptingBackend(UnityEditor.Build.NamedBuildTarget.Standalone, ScriptingImplementation.Mono2x);
        PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, new[] { GraphicsDeviceType.Direct3D11 });
        QualitySettings.vSyncCount = 0;
        EditorSettings.serializationMode = SerializationMode.ForceText;
        EditorSceneManager.SaveScene(scene, folder + "/T03Foundation.unity");
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(folder + "/T03Foundation.unity", true) };
        AssetDatabase.SaveAssets();
        if (GraphicsSettings.defaultRenderPipeline == null) throw new Exception("URP asset missing");
        return "success: T03 foundation saved; URP=" + GraphicsSettings.defaultRenderPipeline.name;
    }

    private static void MakeBox(string name, Vector3 position, Vector3 scale, Color color)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = name;
        go.transform.position = position;
        go.transform.localScale = scale;
        string path = "Assets/Game/Scenes/" + name.Split(' ')[0] + "-" + position.x.ToString(System.Globalization.CultureInfo.InvariantCulture) + "-" + position.z.ToString(System.Globalization.CultureInfo.InvariantCulture) + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (material == null) {
            material = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            AssetDatabase.CreateAsset(material, path);
        }
        material.SetColor("_BaseColor", color);
        EditorUtility.SetDirty(material);
        go.GetComponent<Renderer>().sharedMaterial = material;
    }
}
