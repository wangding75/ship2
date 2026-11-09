using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public static class T07Import
{
    static readonly string[] Islands = { "ISL-S", "ISL-M", "ISL-L" };
    static readonly Dictionary<string, float> Diameters = new Dictionary<string, float>
    {
        { "ISL-S", 48f }, { "ISL-M", 110f }, { "ISL-L", 200f }, { "PORT", 36f }
    };

    public static void Run()
    {
        var reportPath = @"C:\t07isl\unity_import_report.json";
        try
        {
            var paths = JsonUtility.FromJson<PathFile>(File.ReadAllText(@"C:\t07isl\t07-paths.json"));
            reportPath = paths.report;
            Directory.CreateDirectory(Path.GetDirectoryName(paths.unityEvidence));
            var metrics = MiniJson.Parse(File.ReadAllText(paths.metrics)) as Dictionary<string, object>;
            Debug.Log("T07 stage refresh");
            AssetDatabase.Refresh();
            Debug.Log("T07 stage textures");
            ConfigureTextures();
            Debug.Log("T07 stage models");
            var meshes = ConfigureModels();
            Debug.Log("T07 stage materials");
            var materials = CreateMaterials();
            Debug.Log("T07 stage rotations");
            var rotations = ChooseRotations(meshes, metrics);
            Debug.Log("T07 stage slots");
            var ordered = OrderSlots(meshes);
            MakeUnreadable(meshes.Keys);
            Debug.Log("T07 stage prefabs");
            WritePrefabs(ordered, materials, rotations, metrics);
            Debug.Log("T07 stage render");
            var shots = Render(paths.unityEvidence, metrics);
            Debug.Log("T07 stage done");
            var report = new Dictionary<string, object>
            {
                { "utc", DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ") },
                { "unity", Application.unityVersion },
                { "status", "DEVELOPMENT_OK" },
                { "acceptance", "NOT_RUN" },
                { "rotations_rx_deg", RotationReport(rotations) },
                { "triangles", TriangleReport(ordered) },
                { "shots", shots },
                { "lod_note", "screenRelativeHeight uses suggested heights 50 m and 140 m with an assumed 60 degree vertical FOV. It is not a new threshold." }
            };
            File.WriteAllText(paths.report, MiniJson.Serialize(report));
            AssetDatabase.SaveAssets();
            EditorApplication.Exit(0);
        }
        catch (Exception error)
        {
            File.WriteAllText(reportPath, error.ToString());
            Debug.LogError(error);
            EditorApplication.Exit(1);
        }
    }

    static void ConfigureTextures()
    {
        SetTexture("Assets/Game/Art/Islands/Textures/island_atlas_1024.png", 1024);
        SetTexture("Assets/Game/Art/Islands/Textures/island_atlas_512.png", 512);
        SetTexture("Assets/Game/Art/Islands/Textures/port_atlas_1024.png", 1024);
        SetTexture("Assets/Game/Art/Islands/Textures/port_atlas_512.png", 512);
    }

    static void SetTexture(string path, int size)
    {
        var importer = (TextureImporter)AssetImporter.GetAtPath(path);
        importer.textureType = TextureImporterType.Default;
        importer.sRGBTexture = true;
        importer.mipmapEnabled = true;
        importer.maxTextureSize = size;
        importer.SaveAndReimport();
    }

    static Dictionary<string, Mesh> ConfigureModels()
    {
        var result = new Dictionary<string, Mesh>();
        foreach (var path in ModelPaths())
        {
            var importer = (ModelImporter)AssetImporter.GetAtPath(path);
            importer.globalScale = 1f;
            importer.useFileScale = true;
            importer.bakeAxisConversion = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.None;
            importer.isReadable = true;
            importer.importAnimation = false;
            importer.animationType = ModelImporterAnimationType.None;
            importer.SaveAndReimport();
            result[path] = LoadMesh(path);
        }
        return result;
    }

    static Dictionary<string, Mesh> LoadMeshes()
    {
        var result = new Dictionary<string, Mesh>();
        foreach (var path in ModelPaths()) result[path] = LoadMesh(path);
        return result;
    }

    static Mesh LoadMesh(string path)
    {
        Mesh best = null;
        foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(path))
        {
            if (asset is Mesh mesh && (best == null || mesh.vertexCount > best.vertexCount)) best = mesh;
        }
        if (best == null) throw new InvalidOperationException("No mesh in " + path);
        return best;
    }

    static Dictionary<string, Mesh> OrderSlots(Dictionary<string, Mesh> sources)
    {
        var ordered = new Dictionary<string, Mesh>();
        foreach (var pair in sources)
        {
            var file = Path.GetFileNameWithoutExtension(pair.Key);
            var slots = file.StartsWith("PORT") ? new[] { "wood", "wall" } : new[] { "sand", "grass", "rock" };
            var mesh = Reorder(pair.Value, slots);
            var path = Path.ChangeExtension(pair.Key, null) + "_slots.asset";
            if (AssetDatabase.LoadAssetAtPath<Mesh>(path) != null) AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(mesh, path);
            ordered[pair.Key] = mesh;
        }
        return ordered;
    }

    static Mesh Reorder(Mesh source, string[] slots)
    {
        if (source.subMeshCount != slots.Length) throw new InvalidOperationException(source.name + " submeshes " + source.subMeshCount);
        var uvs = source.uv;
        var map = new int[slots.Length];
        var used = new bool[source.subMeshCount];
        for (var slot = 0; slot < slots.Length; slot++)
        {
            var found = -1;
            for (var sub = 0; sub < source.subMeshCount; sub++)
            {
                if (used[sub]) continue;
                var tris = source.GetTriangles(sub);
                if (tris.Length == 0 || !Matches(uvs[tris[0]], slots[slot])) continue;
                found = sub;
                break;
            }
            if (found < 0) throw new InvalidOperationException(source.name + " missing slot " + slots[slot]);
            used[found] = true;
            map[slot] = found;
        }
        var mesh = UnityEngine.Object.Instantiate(source);
        mesh.name = source.name + "_slots";
        for (var slot = 0; slot < slots.Length; slot++) mesh.SetTriangles(source.GetTriangles(map[slot]), slot, true);
        return mesh;
    }

    static bool Matches(Vector2 uv, string slot)
    {
        if (slot == "sand") return uv.y < 0.5f && uv.x < 0.5f;
        if (slot == "grass") return uv.y < 0.5f && uv.x >= 0.5f;
        if (slot == "rock" || slot == "wall") return uv.y >= 0.5f;
        if (slot == "wood") return uv.y < 0.5f;
        return false;
    }

    static void MakeUnreadable(IEnumerable<string> paths)
    {
        foreach (var path in paths)
        {
            var importer = (ModelImporter)AssetImporter.GetAtPath(path);
            importer.isReadable = false;
            importer.SaveAndReimport();
        }
    }

    static Dictionary<string, AxisFix> ChooseRotations(Dictionary<string, Mesh> meshes, Dictionary<string, object> metrics)
    {
        var meshMetrics = (Dictionary<string, object>)metrics["meshes"];
        var chosen = new Dictionary<string, AxisFix>();
        foreach (var asset in Islands.Concat(new[] { "PORT" }))
        {
            var lods = (Dictionary<string, object>)((Dictionary<string, object>)meshMetrics[asset])["lods"];
            var expected = (Dictionary<string, object>)((Dictionary<string, object>)lods["0"])["bounds_unity_m"];
            var min = Numbers(expected["min"]);
            var max = Numbers(expected["max"]);
            var path = ModelPath(asset, 0);
            var best = new AxisFix();
            float bestError = float.MaxValue;
            foreach (var rx in new[] { 0f, -90f, 90f, 180f })
            {
                foreach (var sx in new[] { 1f, -1f })
                {
                    var error = BoundsError(meshes[path], rx, sx, min, max);
                    if (error < bestError)
                    {
                        bestError = error;
                        best = new AxisFix { rx = rx, sx = sx };
                    }
                }
            }
            if (bestError > 0.25f) throw new InvalidOperationException(asset + " axis error " + bestError + " rx " + best.rx + " sx " + best.sx);
            best.error = bestError;
            chosen[asset] = best;
        }
        return chosen;
    }

    static float BoundsError(Mesh mesh, float rx, float sx, List<double> min, List<double> max)
    {
        var rotation = Quaternion.Euler(rx, 0f, 0f);
        var scale = new Vector3(sx, 1f, 1f);
        var first = rotation * Vector3.Scale(scale, mesh.vertices[0]);
        var lo = first;
        var hi = first;
        foreach (var vertex in mesh.vertices)
        {
            var point = rotation * Vector3.Scale(scale, vertex);
            lo = Vector3.Min(lo, point);
            hi = Vector3.Max(hi, point);
        }
        return Mathf.Abs(lo.x - (float)min[0]) + Mathf.Abs(lo.y - (float)min[1]) + Mathf.Abs(lo.z - (float)min[2])
            + Mathf.Abs(hi.x - (float)max[0]) + Mathf.Abs(hi.y - (float)max[1]) + Mathf.Abs(hi.z - (float)max[2]);
    }

    static Dictionary<string, Material> CreateMaterials()
    {
        var shader = Shader.Find("Universal Render Pipeline/Lit");
        if (shader == null)
        {
            var hull = AssetDatabase.LoadAssetAtPath<Material>("Assets/Game/Art/Ships/Materials/M_Ship_Hull.mat");
            if (hull != null) shader = hull.shader;
        }
        if (shader == null) throw new InvalidOperationException("URP Lit missing");
        EnsureFolder("Assets/Game/Art/Islands/Materials");
        var map = new Dictionary<string, Material>();
        map["sand"] = Material(shader, "M_Isl_Sand", "Assets/Game/Art/Islands/Textures/island_atlas_1024.png");
        map["grass"] = Material(shader, "M_Isl_Grass", "Assets/Game/Art/Islands/Textures/island_atlas_1024.png");
        map["rock"] = Material(shader, "M_Isl_Rock", "Assets/Game/Art/Islands/Textures/island_atlas_1024.png");
        map["sand2"] = Material(shader, "M_Isl_Sand_LOD2", "Assets/Game/Art/Islands/Textures/island_atlas_512.png");
        map["grass2"] = Material(shader, "M_Isl_Grass_LOD2", "Assets/Game/Art/Islands/Textures/island_atlas_512.png");
        map["rock2"] = Material(shader, "M_Isl_Rock_LOD2", "Assets/Game/Art/Islands/Textures/island_atlas_512.png");
        map["wood"] = Material(shader, "M_Port_Wood", "Assets/Game/Art/Islands/Textures/port_atlas_1024.png");
        map["wall"] = Material(shader, "M_Port_Wall", "Assets/Game/Art/Islands/Textures/port_atlas_1024.png");
        map["wood2"] = Material(shader, "M_Port_Wood_LOD2", "Assets/Game/Art/Islands/Textures/port_atlas_512.png");
        map["wall2"] = Material(shader, "M_Port_Wall_LOD2", "Assets/Game/Art/Islands/Textures/port_atlas_512.png");
        return map;
    }

    static Material Material(Shader shader, string name, string texturePath)
    {
        var material = new Material(shader) { name = name };
        material.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath));
        material.SetColor("_BaseColor", Color.white);
        var path = "Assets/Game/Art/Islands/Materials/" + name + ".mat";
        if (AssetDatabase.LoadAssetAtPath<Material>(path) != null) AssetDatabase.DeleteAsset(path);
        AssetDatabase.CreateAsset(material, path);
        return material;
    }

    static void WritePrefabs(Dictionary<string, Mesh> meshes, Dictionary<string, Material> materials, Dictionary<string, AxisFix> rotations, Dictionary<string, object> metrics)
    {
        EnsureFolder("Assets/Game/Art/Islands/Prefabs");
        foreach (var asset in Islands) SaveIsland(asset, meshes, materials, rotations[asset]);
        SavePort(meshes, materials, rotations["PORT"], metrics);
    }

    static void SaveIsland(string asset, Dictionary<string, Mesh> meshes, Dictionary<string, Material> materials, AxisFix fix)
    {
        var root = new GameObject(asset);
        var visual = Child(root, "VisualRoot");
        var group = visual.AddComponent<LODGroup>();
        var lods = new LOD[3];
        var renderers = new Renderer[3];
        for (var lod = 0; lod < 3; lod++)
        {
            var go = Child(visual, asset + "_LOD" + lod);
            go.transform.localRotation = Quaternion.Euler(fix.rx, 0f, 0f);
            go.transform.localScale = new Vector3(fix.sx, 1f, 1f);
            var filter = go.AddComponent<MeshFilter>();
            filter.sharedMesh = meshes[ModelPath(asset, lod)];
            var renderer = go.AddComponent<MeshRenderer>();
            renderer.sharedMaterials = lod == 2
                ? new[] { materials["sand2"], materials["grass2"], materials["rock2"] }
                : new[] { materials["sand"], materials["grass"], materials["rock"] };
            renderers[lod] = renderer;
        }
        var height0 = Suggested(Diameters[asset], 50f);
        var height1 = Suggested(Diameters[asset], 140f);
        if (height1 >= height0) height1 = height0 * 0.45f;
        lods[0] = new LOD(height0, new[] { renderers[0] });
        lods[1] = new LOD(height1, new[] { renderers[1] });
        lods[2] = new LOD(0.01f, new[] { renderers[2] });
        group.SetLODs(lods);
        group.RecalculateBounds();
        var prefabPath = "Assets/Game/Art/Islands/Prefabs/" + asset + ".prefab";
        if (AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath) != null) AssetDatabase.DeleteAsset(prefabPath);
        PrefabUtility.SaveAsPrefabAsset(root, prefabPath);
        UnityEngine.Object.DestroyImmediate(root);
    }

    static void SavePort(Dictionary<string, Mesh> meshes, Dictionary<string, Material> materials, AxisFix fix, Dictionary<string, object> metrics)
    {
        var port = (Dictionary<string, object>)metrics["port_local_m"];
        var landmark = Numbers(port["landmark_xz"]);
        var anchor = Numbers(port["anchor_xz"]);
        var root = new GameObject("PORT");
        var visual = Child(root, "VisualRoot");
        var group = visual.AddComponent<LODGroup>();
        var renderers = new Renderer[3];
        for (var lod = 0; lod < 3; lod++)
        {
            var go = Child(visual, "PORT_LOD" + lod);
            go.transform.localRotation = Quaternion.Euler(fix.rx, 0f, 0f);
            go.transform.localScale = new Vector3(fix.sx, 1f, 1f);
            go.AddComponent<MeshFilter>().sharedMesh = meshes[ModelPath("PORT", lod)];
            var renderer = go.AddComponent<MeshRenderer>();
            renderer.sharedMaterials = lod == 2
                ? new[] { materials["wood2"], materials["wall2"] }
                : new[] { materials["wood"], materials["wall"] };
            renderers[lod] = renderer;
        }
        var height0 = Suggested(Diameters["PORT"], 50f);
        var height1 = Suggested(Diameters["PORT"], 140f);
        if (height1 >= height0) height1 = height0 * 0.45f;
        group.SetLODs(new[]
        {
            new LOD(height0, new[] { renderers[0] }),
            new LOD(height1, new[] { renderers[1] }),
            new LOD(0.01f, new[] { renderers[2] })
        });
        group.RecalculateBounds();
        var prefabPath = "Assets/Game/Art/Islands/Prefabs/PORT.prefab";
        if (AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath) != null) AssetDatabase.DeleteAsset(prefabPath);
        var mark = Child(root, "LM-PORT-01");
        mark.transform.localPosition = new Vector3((float)landmark[0], 0f, (float)landmark[1]);
        var berth = Child(root, "ANCHOR-PORT-01");
        berth.transform.localPosition = new Vector3((float)anchor[0], 0f, (float)anchor[1]);
        PrefabUtility.SaveAsPrefabAsset(root, prefabPath);
        UnityEngine.Object.DestroyImmediate(root);
    }

    static void EnsureFolder(string path)
    {
        path = path.Replace("\\", "/");
        if (AssetDatabase.IsValidFolder(path)) return;
        var parent = Path.GetDirectoryName(path).Replace("\\", "/");
        if (!AssetDatabase.IsValidFolder(parent)) EnsureFolder(parent);
        AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
    }

    static List<string> Render(string directory, Dictionary<string, object> metrics)
    {
        Directory.CreateDirectory(directory);
        var sun = new GameObject("Sun");
        var light = sun.AddComponent<Light>();
        light.type = LightType.Directional;
        light.intensity = 1.25f;
        sun.transform.rotation = Quaternion.Euler(55f, -35f, 0f);
        var cameraObject = new GameObject("Shot");
        var camera = cameraObject.AddComponent<Camera>();
        if (cameraObject.GetComponent<UniversalAdditionalCameraData>() == null)
            cameraObject.AddComponent<UniversalAdditionalCameraData>();
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = new Color(0.23f, 0.48f, 0.62f);
        camera.fieldOfView = 50f;
        camera.nearClipPlane = 0.2f;
        camera.farClipPlane = 8000f;
        camera.allowHDR = false;
        camera.allowMSAA = false;
        var texture = new RenderTexture(960, 540, 24, RenderTextureFormat.ARGB32);
        camera.targetTexture = texture;
        var shots = new List<string>();
        foreach (var asset in Islands.Concat(new[] { "PORT" }))
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Game/Art/Islands/Prefabs/" + asset + ".prefab");
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            for (var lod = 0; lod < 3; lod++)
            {
                SetLodVisible(instance, asset, lod);
                if (lod == 0)
                {
                    foreach (var yaw in new[] { 0f, 45f, 90f, 135f, 180f, 225f, 270f, 315f })
                    {
                        Aim(camera, asset, instance, yaw, 28f);
                        shots.Add(Shot(camera, texture, directory, asset + "_LOD0_yaw" + yaw.ToString("000")));
                    }
                }
                else
                {
                    Aim(camera, asset, instance, 40f, 28f);
                    shots.Add(Shot(camera, texture, directory, asset + "_LOD" + lod + "_yaw040"));
                }
            }
            UnityEngine.Object.DestroyImmediate(instance);
        }
        var island = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Game/Art/Islands/Prefabs/ISL-L.prefab"));
        var port = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Game/Art/Islands/Prefabs/PORT.prefab"));
        SetLodVisible(island, "ISL-L", 0);
        SetLodVisible(port, "PORT", 0);
        var landmark = Numbers(((Dictionary<string, object>)metrics["port_local_m"])["landmark_xz"]);
        var look = new Vector3((float)landmark[0], 4f, (float)landmark[1]);
        foreach (var item in new[] { new[] { "near", "35" }, new[] { "mid", "85" }, new[] { "far", "220" } })
        {
            var height = float.Parse(item[1], CultureInfo.InvariantCulture);
            var horiz = height / Mathf.Tan(55f * Mathf.Deg2Rad);
            var camX = look.x + horiz;
            if (new Vector2(camX, look.z).magnitude < 206f) camX = 208f;
            camera.transform.position = new Vector3(camX, height, look.z);
            camera.transform.LookAt(look);
            shots.Add(Shot(camera, texture, directory, "ISL-L_PORT_LOD0_" + item[0] + "_h" + item[1]));
        }
        UnityEngine.Object.DestroyImmediate(island);
        UnityEngine.Object.DestroyImmediate(port);
        UnityEngine.Object.DestroyImmediate(texture);
        UnityEngine.Object.DestroyImmediate(cameraObject);
        UnityEngine.Object.DestroyImmediate(sun);
        return shots;
    }

    static void Aim(Camera camera, string asset, GameObject instance, float yaw, float pitch)
    {
        var target = instance.GetComponentInChildren<Renderer>().bounds.center;
        var distance = asset == "PORT" ? 70f : Diameters[asset] * 1.15f;
        var rotation = Quaternion.Euler(pitch, yaw, 0f);
        camera.transform.position = target + rotation * new Vector3(0f, 0f, -distance);
        camera.transform.LookAt(target);
    }

    static void SetLodVisible(GameObject root, string asset, int lod)
    {
        foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
        {
            renderer.enabled = renderer.gameObject.name == asset + "_LOD" + lod;
        }
    }

    static void RenderCamera(Camera camera, RenderTexture texture)
    {
        camera.targetTexture = texture;
        var request = new RenderPipeline.StandardRequest();
        if (RenderPipeline.SupportsRenderRequest(camera, request))
        {
            request.destination = texture;
            RenderPipeline.SubmitRenderRequest(camera, request);
        }
        else camera.Render();
    }

    static string Shot(Camera camera, RenderTexture texture, string directory, string name)
    {
        RenderCamera(camera, texture);
        var previous = RenderTexture.active;
        RenderTexture.active = texture;
        var image = new Texture2D(texture.width, texture.height, TextureFormat.RGB24, false);
        image.ReadPixels(new Rect(0, 0, texture.width, texture.height), 0, 0);
        image.Apply();
        RenderTexture.active = previous;
        var path = Path.Combine(directory, name + ".png");
        File.WriteAllBytes(path, image.EncodeToPNG());
        UnityEngine.Object.DestroyImmediate(image);
        return path;
    }

    static float Suggested(float diameter, float height)
    {
        var distance = height / Mathf.Sin(55f * Mathf.Deg2Rad);
        var value = diameter / (2f * distance * Mathf.Tan(30f * Mathf.Deg2Rad));
        if (value > 0.99f) value = 0.99f;
        if (value < 0.02f) value = 0.02f;
        return value;
    }

    static Dictionary<string, object> RotationReport(Dictionary<string, AxisFix> rotations)
    {
        var report = new Dictionary<string, object>();
        foreach (var pair in rotations)
        {
            report[pair.Key] = new Dictionary<string, object>
            {
                { "rx", pair.Value.rx },
                { "sx", pair.Value.sx },
                { "bounds_error_m", pair.Value.error }
            };
        }
        return report;
    }

    static Dictionary<string, object> TriangleReport(Dictionary<string, Mesh> meshes)
    {
        var report = new Dictionary<string, object>();
        foreach (var pair in meshes)
        {
            var mesh = pair.Value;
            var counts = new int[mesh.subMeshCount];
            for (var index = 0; index < mesh.subMeshCount; index++) counts[index] = (int)mesh.GetIndexCount(index) / 3;
            report[pair.Key] = counts;
        }
        return report;
    }

    static IEnumerable<string> ModelPaths()
    {
        foreach (var asset in Islands.Concat(new[] { "PORT" }))
            for (var lod = 0; lod < 3; lod++) yield return ModelPath(asset, lod);
    }

    static string ModelPath(string asset, int lod)
    {
        return "Assets/Game/Art/Islands/Models/" + asset + "_LOD" + lod + ".fbx";
    }

    static GameObject Child(GameObject parent, string name)
    {
        var child = new GameObject(name);
        child.transform.SetParent(parent.transform, false);
        return child;
    }

    static List<double> Numbers(object value)
    {
        var list = new List<double>();
        foreach (var item in (List<object>)value) list.Add(Convert.ToDouble(item));
        return list;
    }

    [Serializable]
    class PathFile
    {
        public string metrics;
        public string report;
        public string unityEvidence;
    }

    class AxisFix
    {
        public float rx;
        public float sx = 1f;
        public float error;
    }
}

static class MiniJson
{
    public static object Parse(string json)
    {
        return new Parser(json).ParseValue();
    }

    public static string Serialize(object value)
    {
        var writer = new StringWriter();
        Write(writer, value);
        return writer.ToString();
    }

    static void Write(StringWriter writer, object value)
    {
        if (value == null) writer.Write("null");
        else if (value is string text) writer.Write("\"" + text.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"");
        else if (value is bool flag) writer.Write(flag ? "true" : "false");
        else if (value is int || value is float || value is double) writer.Write(Convert.ToString(value, System.Globalization.CultureInfo.InvariantCulture));
        else if (value is Dictionary<string, object> map)
        {
            writer.Write("{");
            var first = true;
            foreach (var pair in map)
            {
                if (!first) writer.Write(",");
                first = false;
                Write(writer, pair.Key);
                writer.Write(":");
                Write(writer, pair.Value);
            }
            writer.Write("}");
        }
        else if (value is Dictionary<string, float> floats)
        {
            writer.Write("{");
            var first = true;
            foreach (var pair in floats)
            {
                if (!first) writer.Write(",");
                first = false;
                Write(writer, pair.Key);
                writer.Write(":");
                writer.Write(pair.Value.ToString(System.Globalization.CultureInfo.InvariantCulture));
            }
            writer.Write("}");
        }
        else if (value is List<string> strings)
        {
            writer.Write("[");
            for (var i = 0; i < strings.Count; i++)
            {
                if (i > 0) writer.Write(",");
                Write(writer, strings[i]);
            }
            writer.Write("]");
        }
        else if (value is Dictionary<string, int[]> tables)
        {
            writer.Write("{");
            var first = true;
            foreach (var pair in tables)
            {
                if (!first) writer.Write(",");
                first = false;
                Write(writer, pair.Key);
                writer.Write(":[");
                for (var i = 0; i < pair.Value.Length; i++)
                {
                    if (i > 0) writer.Write(",");
                    writer.Write(pair.Value[i].ToString(System.Globalization.CultureInfo.InvariantCulture));
                }
                writer.Write("]");
            }
            writer.Write("}");
        }
        else if (value is int[] numbers)
        {
            writer.Write("[");
            for (var i = 0; i < numbers.Length; i++)
            {
                if (i > 0) writer.Write(",");
                writer.Write(numbers[i]);
            }
            writer.Write("]");
        }
        else throw new InvalidOperationException("Cannot serialize " + value.GetType());
    }

    sealed class Parser
    {
        readonly string text;
        int index;
        public Parser(string text) { this.text = text; }
        public object ParseValue()
        {
            Skip();
            if (text[index] == '{') return ParseObject();
            if (text[index] == '[') return ParseArray();
            if (text[index] == '"') return ParseString();
            var start = index;
            while (index < text.Length && "}],".IndexOf(text[index]) < 0) index++;
            var token = text.Substring(start, index - start).Trim();
            if (token == "true") return true;
            if (token == "false") return false;
            if (token == "null") return null;
            if (token.Contains(".") || token.Contains("e") || token.Contains("E")) return double.Parse(token, System.Globalization.CultureInfo.InvariantCulture);
            return long.Parse(token, System.Globalization.CultureInfo.InvariantCulture);
        }
        Dictionary<string, object> ParseObject()
        {
            var map = new Dictionary<string, object>();
            index++;
            Skip();
            if (text[index] == '}') { index++; return map; }
            while (true)
            {
                var key = ParseString();
                Skip();
                index++;
                map[key] = ParseValue();
                Skip();
                if (text[index] == '}') { index++; break; }
                index++;
                Skip();
            }
            return map;
        }
        List<object> ParseArray()
        {
            var list = new List<object>();
            index++;
            Skip();
            if (text[index] == ']') { index++; return list; }
            while (true)
            {
                list.Add(ParseValue());
                Skip();
                if (text[index] == ']') { index++; break; }
                index++;
                Skip();
            }
            return list;
        }
        string ParseString()
        {
            index++;
            var start = index;
            var value = "";
            while (text[index] != '"')
            {
                if (text[index] == '\\')
                {
                    value += text.Substring(start, index - start);
                    index++;
                    value += text[index] == 'n' ? "\n" : text[index].ToString();
                    index++;
                    start = index;
                }
                else index++;
            }
            value += text.Substring(start, index - start);
            index++;
            return value;
        }
        void Skip()
        {
            while (index < text.Length && char.IsWhiteSpace(text[index])) index++;
        }
    }
}
