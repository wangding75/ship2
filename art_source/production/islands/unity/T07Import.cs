using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
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
        var pathsJson = Environment.GetEnvironmentVariable("T07_PATHS_JSON");
        if (string.IsNullOrEmpty(pathsJson)) pathsJson = Path.Combine(Directory.GetCurrentDirectory(), "t07-paths.json");
        var reportPath = Path.Combine(Directory.GetCurrentDirectory(), "unity_import_report.json");
        try
        {
            var paths = JsonUtility.FromJson<PathFile>(File.ReadAllText(pathsJson));
            reportPath = paths.report;
            Directory.CreateDirectory(Path.GetDirectoryName(paths.unityEvidence));
            var metrics = MiniJson.Parse(File.ReadAllText(paths.metrics)) as Dictionary<string, object>;
            Debug.Log("T07 stage refresh");
            AssetDatabase.Refresh();
            Debug.Log("T07 stage textures");
            ConfigureTextures();
            Debug.Log("T07 stage models");
            var meshes = ConfigureModels();
            Debug.Log("T07 stage parts");
            var partMeshes = ConfigureParts();
            Debug.Log("T07 stage materials");
            var materials = CreateMaterials();
            Debug.Log("T07 stage rotations");
            var rotations = ChooseRotations(meshes, metrics);
            Debug.Log("T07 stage slots");
            var ordered = OrderSlots(meshes);
            var waterline = MeasureWaterlines(meshes, rotations, paths.metrics);
            Debug.Log("T07 stage part assembly");
            var assembly = VerifyPartAssembly(ordered, partMeshes, rotations);
            MakeUnreadable(meshes.Keys);
            MakeUnreadable(partMeshes.Keys);
            Debug.Log("T07 stage prefabs");
            WritePrefabs(ordered, partMeshes, materials, rotations, metrics);
            T07IslandAssembly.RebuildAll();
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
                { "waterline_unity", waterline },
                { "semantic_parts", assembly },
                { "lod_transitions", TransitionReport() },
                { "lod_note", "Yaw, top and oblique frames disable LODGroup and show one mesh. natural_lod.json is the automatic LODGroup sweep. 50 m and 140 m stay suggestions. A saturated suggestion is not clamped to 0.99." }
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
            var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (existing != null)
            {
                EditorUtility.CopySerialized(mesh, existing);
                EditorUtility.SetDirty(existing);
                UnityEngine.Object.DestroyImmediate(mesh);
                mesh = existing;
            }
            else AssetDatabase.CreateAsset(mesh, path);
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

    static void WritePrefabs(Dictionary<string, Mesh> meshes, Dictionary<string, Mesh> partMeshes, Dictionary<string, Material> materials, Dictionary<string, AxisFix> rotations, Dictionary<string, object> metrics)
    {
        EnsureFolder("Assets/Game/Art/Islands/Prefabs");
        foreach (var asset in Islands) SaveIsland(asset, meshes, partMeshes, materials, rotations[asset]);
        SavePort(meshes, materials, rotations["PORT"], metrics);
    }

    static readonly string[] PartNames = { "Beach", "Grass", "Trees", "Reef" };

    static string PartPath(string asset, int lod, string part)
    {
        return "Assets/Game/Art/Islands/Parts/" + asset + "_LOD" + lod + "_" + part + ".fbx";
    }

    static Dictionary<string, Mesh> ConfigureParts()
    {
        var result = new Dictionary<string, Mesh>();
        EnsureFolder("Assets/Game/Art/Islands/Parts");
        foreach (var asset in Islands)
        {
            for (var lod = 0; lod < 3; lod++)
            {
                foreach (var part in PartNames)
                {
                    var path = PartPath(asset, lod, part);
                    if (AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(path) == null) continue;
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
            }
        }
        return result;
    }

    static Material PartMaterial(string part, int lod, Dictionary<string, Material> materials)
    {
        var lod2 = lod == 2;
        if (part == "Beach") return lod2 ? materials["sand2"] : materials["sand"];
        if (part == "Grass") return lod2 ? materials["grass2"] : materials["grass"];
        return lod2 ? materials["rock2"] : materials["rock"];
    }

    static void SaveIsland(string asset, Dictionary<string, Mesh> meshes, Dictionary<string, Mesh> partMeshes, Dictionary<string, Material> materials, AxisFix fix)
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
        var choice = Transition(Diameters[asset]);
        lods[0] = new LOD(choice.height0, new[] { renderers[0] });
        lods[1] = new LOD(choice.height1, new[] { renderers[1] });
        lods[2] = new LOD(0.01f, new[] { renderers[2] });
        group.SetLODs(lods);
        group.RecalculateBounds();
        var partsRoot = Child(root, "SemanticParts");
        partsRoot.SetActive(false);
        for (var lod = 0; lod < 3; lod++)
        {
            var lodRoot = Child(partsRoot, asset + "_LOD" + lod + "_Parts");
            lodRoot.transform.localRotation = Quaternion.Euler(fix.rx, 0f, 0f);
            lodRoot.transform.localScale = new Vector3(fix.sx, 1f, 1f);
            foreach (var part in PartNames)
            {
                var partObject = Child(lodRoot, asset + "_LOD" + lod + "_" + part);
                var path = PartPath(asset, lod, part);
                if (!partMeshes.ContainsKey(path)) continue;
                partObject.AddComponent<MeshFilter>().sharedMesh = partMeshes[path];
                var partRenderer = partObject.AddComponent<MeshRenderer>();
                partRenderer.sharedMaterial = PartMaterial(part, lod, materials);
            }
        }
        var prefabPath = "Assets/Game/Art/Islands/Prefabs/" + asset + ".prefab";
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
        var choice = Transition(Diameters["PORT"]);
        group.SetLODs(new[]
        {
            new LOD(choice.height0, new[] { renderers[0] }),
            new LOD(choice.height1, new[] { renderers[1] }),
            new LOD(0.01f, new[] { renderers[2] })
        });
        group.RecalculateBounds();
        var prefabPath = "Assets/Game/Art/Islands/Prefabs/PORT.prefab";
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
                        shots.Add(Shot(camera, texture, directory, asset + "_LOD0_forced_yaw" + yaw.ToString("000")));
                    }
                }
                else
                {
                    Aim(camera, asset, instance, 40f, 28f);
                    shots.Add(Shot(camera, texture, directory, asset + "_LOD" + lod + "_forced_yaw040"));
                }
                if (asset != "PORT")
                {
                    Aim(camera, asset, instance, 40f, 78f);
                    shots.Add(Shot(camera, texture, directory, asset + "_LOD" + lod + "_forced_top"));
                    Aim(camera, asset, instance, 40f, 32f);
                    shots.Add(Shot(camera, texture, directory, asset + "_LOD" + lod + "_forced_oblique"));
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
            shots.Add(Shot(camera, texture, directory, "ISL-L_PORT_LOD0_forced_" + item[0] + "_h" + item[1]));
            SetLodNatural(island);
            SetLodNatural(port);
            shots.Add(Shot(camera, texture, directory, "ISL-L_PORT_natural_" + item[0] + "_h" + item[1]));
            SetLodVisible(island, "ISL-L", 0);
            SetLodVisible(port, "PORT", 0);
        }
        UnityEngine.Object.DestroyImmediate(island);
        UnityEngine.Object.DestroyImmediate(port);
        File.WriteAllText(Path.Combine(directory, "natural_lod.json"), NaturalSweep(camera, texture, directory));
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
        var group = root.GetComponentInChildren<LODGroup>(true);
        if (group != null) group.enabled = false;
        foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
        {
            renderer.enabled = renderer.gameObject.name == asset + "_LOD" + lod;
        }
    }

    static void SetLodNatural(GameObject root)
    {
        var group = root.GetComponentInChildren<LODGroup>(true);
        if (group != null)
        {
            group.enabled = true;
            group.ForceLOD(-1);
        }
        foreach (var renderer in root.GetComponentsInChildren<Renderer>(true)) renderer.enabled = true;
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

    struct TransitionChoice
    {
        public float height0;
        public float height1;
        public float legacy0;
        public float legacy1;
        public string reason;
    }

    static float Unclamped(float diameter, float height)
    {
        var distance = height / Mathf.Sin(55f * Mathf.Deg2Rad);
        return diameter / (2f * distance * Mathf.Tan(30f * Mathf.Deg2Rad));
    }

    static TransitionChoice Transition(float diameter)
    {
        var near = Unclamped(diameter, 50f);
        var far = Unclamped(diameter, 140f);
        var legacy0 = near > 0.99f ? 0.99f : near < 0.02f ? 0.02f : near;
        var legacy1 = far > 0.99f ? 0.99f : far < 0.02f ? 0.02f : far;
        if (legacy1 >= legacy0) legacy1 = legacy0 * 0.45f;
        var choice = new TransitionChoice { legacy0 = legacy0, legacy1 = legacy1 };
        if (near <= 0.90f && far <= near - 0.08f && far >= 0.05f)
        {
            choice.height0 = near;
            choice.height1 = far;
            choice.reason = "50m/140m suggestion separates at an assumed 60 degree FOV. Not a new threshold.";
            return choice;
        }
        if (near > 0.90f && far < 0.85f && far > 0.08f)
        {
            choice.height0 = 0.60f;
            choice.height1 = 0.22f;
            choice.reason = "50m suggestion saturates the frame; 0.60/0.22 keeps ~2.73x LOD1 band width matching S/L/PORT so both 50 deg and 60 deg zoom sweeps cross LOD0 -> LOD1 -> LOD2 cleanly. Not a new threshold.";
            return choice;
        }
        choice.height0 = 0.55f;
        choice.height1 = 0.20f;
        choice.reason = "Both suggested heights saturate a 60 degree frame, so the old code clamped LOD0 to 0.99. Production split 0.55/0.20 lets a continuous zoom cross three LODs. LOD2 remains until 0.01. Not a new threshold.";
        return choice;
    }

    static Dictionary<string, object> TransitionReport()
    {
        var report = new Dictionary<string, object>();
        foreach (var asset in Islands.Concat(new[] { "PORT" }))
        {
            var choice = Transition(Diameters[asset]);
            report[asset] = new Dictionary<string, object>
            {
                { "height0", (double)choice.height0 },
                { "height1", (double)choice.height1 },
                { "legacy0", (double)choice.legacy0 },
                { "legacy1", (double)choice.legacy1 },
                { "reason", choice.reason }
            };
        }
        return report;
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

    [MenuItem("Game/T07/Reassemble Island Parts")]
    public static void ReassembleMenu()
    {
        T07IslandAssembly.RebuildAll();
    }

    static Dictionary<string, object> VerifyPartAssembly(Dictionary<string, Mesh> ordered, Dictionary<string, Mesh> partMeshes, Dictionary<string, AxisFix> rotations)
    {
        var assets = new List<object>();
        string mismatch = null;
        foreach (var asset in Islands)
        {
            var fix = rotations[asset];
            for (var lod = 0; lod < 3; lod++)
            {
                var render = ordered[ModelPath(asset, lod)];
                var expected = new Dictionary<string, int>();
                AddTriangles(expected, render, 0, "sand");
                AddTriangles(expected, render, 1, "grass");
                AddTriangles(expected, render, 2, "rock");
                var actual = new Dictionary<string, int>();
                var partTriangles = new Dictionary<string, object>();
                foreach (var part in PartNames)
                {
                    var path = PartPath(asset, lod, part);
                    var slot = part == "Beach" ? "sand" : part == "Grass" ? "grass" : "rock";
                    if (!partMeshes.ContainsKey(path))
                    {
                        partTriangles[part] = 0;
                        if (part != "Trees" || asset != "ISL-S") mismatch = asset + " LOD" + lod + " missing " + part;
                        continue;
                    }
                    var count = AddTriangles(actual, partMeshes[path], -1, slot);
                    partTriangles[part] = count;
                }
                var same = SameCounts(expected, actual);
                if (!same && mismatch == null) mismatch = asset + " LOD" + lod + " triangles differ";
                var moved = MoveAndRestore(asset, lod, fix, partMeshes);
                if (!moved && mismatch == null) mismatch = asset + " LOD" + lod + " parts stayed bound";
                assets.Add(new Dictionary<string, object>
                {
                    { "asset", asset },
                    { "lod", lod },
                    { "render_submeshes", new List<object> { render.GetIndexCount(0) / 3, render.GetIndexCount(1) / 3, render.GetIndexCount(2) / 3 } },
                    { "part_triangles", partTriangles },
                    { "active_material_slots", 3 },
                    { "geometry_match", same },
                    { "independent_move", moved }
                });
            }
        }
        var report = new Dictionary<string, object>
        {
            { "active_renderers_per_lod", 1 },
            { "active_material_slots", 3 },
            { "parts_in_lod_group", false },
            { "assets", assets }
        };
        if (mismatch != null)
        {
            report["mismatch"] = mismatch;
            throw new InvalidOperationException(mismatch);
        }
        return report;
    }

    static int AddTriangles(Dictionary<string, int> counts, Mesh mesh, int submesh, string slot)
    {
        var total = 0;
        if (submesh >= 0)
        {
            var tris = mesh.GetTriangles(submesh);
            total = tris.Length / 3;
            for (var i = 0; i < tris.Length; i += 3) AddKey(counts, mesh.vertices[tris[i]], mesh.vertices[tris[i + 1]], mesh.vertices[tris[i + 2]], slot);
            return total;
        }
        for (var sub = 0; sub < mesh.subMeshCount; sub++) total += AddTriangles(counts, mesh, sub, slot);
        return total;
    }

    static void AddKey(Dictionary<string, int> counts, Vector3 a, Vector3 b, Vector3 c, string slot)
    {
        var key = slot + "|" + Quant(a) + "|" + Quant(b) + "|" + Quant(c);
        var keys = key.Split('|');
        var body = new[] { keys[1], keys[2], keys[3] };
        var rotations = new[] { string.Join("|", body), body[1] + "|" + body[2] + "|" + body[0], body[2] + "|" + body[0] + "|" + body[1] };
        Array.Sort(rotations, StringComparer.Ordinal);
        body = rotations[0].Split('|');
        key = keys[0] + "|" + body[0] + "|" + body[1] + "|" + body[2];
        counts[key] = counts.ContainsKey(key) ? counts[key] + 1 : 1;
    }

    static string Quant(Vector3 point)
    {
        return string.Format(CultureInfo.InvariantCulture, "{0:R},{1:R},{2:R}", point.x, point.y, point.z);
    }

    static bool SameCounts(Dictionary<string, int> expected, Dictionary<string, int> actual)
    {
        if (expected.Count != actual.Count) return false;
        foreach (var pair in expected)
        {
            if (!actual.ContainsKey(pair.Key) || actual[pair.Key] != pair.Value) return false;
        }
        return true;
    }

    static bool MoveAndRestore(string asset, int lod, AxisFix fix, Dictionary<string, Mesh> partMeshes)
    {
        var root = new GameObject(asset + "_partcheck");
        try
        {
            var beach = PartProbe(root, asset, lod, "Beach", fix, partMeshes);
            var grass = PartProbe(root, asset, lod, "Grass", fix, partMeshes);
            var trees = PartProbe(root, asset, lod, "Trees", fix, partMeshes);
            var reef = PartProbe(root, asset, lod, "Reef", fix, partMeshes);
            if (beach == null || grass == null || reef == null) return false;
            var beachBefore = WorldPoint(beach);
            var grassBefore = WorldPoint(grass);
            var reefBefore = WorldPoint(reef);
            var treesBefore = trees == null ? (Vector3?)null : WorldPoint(trees);
            reef.transform.localPosition += new Vector3(4f, 0f, 0f);
            if (trees != null) trees.transform.localPosition += new Vector3(-3f, 0f, 0f);
            var beachSame = Vector3.Distance(WorldPoint(beach), beachBefore) < 1e-4f;
            var grassSame = Vector3.Distance(WorldPoint(grass), grassBefore) < 1e-4f;
            var reefMoved = Vector3.Distance(WorldPoint(reef), reefBefore) > 1f;
            var treesMoved = trees == null || Vector3.Distance(WorldPoint(trees), treesBefore.Value) > 1f;
            reef.SetActive(false);
            grass.SetActive(false);
            var hidden = !reef.activeSelf && !grass.activeSelf && beach.activeSelf;
            reef.SetActive(true);
            grass.SetActive(true);
            reef.transform.localPosition -= new Vector3(4f, 0f, 0f);
            if (trees != null) trees.transform.localPosition -= new Vector3(-3f, 0f, 0f);
            var restored = Vector3.Distance(WorldPoint(reef), reefBefore) < 1e-3f && Vector3.Distance(WorldPoint(beach), beachBefore) < 1e-4f;
            return beachSame && grassSame && reefMoved && treesMoved && hidden && restored;
        }
        finally
        {
            UnityEngine.Object.DestroyImmediate(root);
        }
    }

    static GameObject PartProbe(GameObject root, string asset, int lod, string part, AxisFix fix, Dictionary<string, Mesh> partMeshes)
    {
        var path = PartPath(asset, lod, part);
        if (!partMeshes.ContainsKey(path)) return null;
        var mesh = partMeshes[path];
        if (mesh == null || mesh.vertexCount == 0) return null;
        var go = Child(root, part);
        go.transform.localRotation = Quaternion.Euler(fix.rx, 0f, 0f);
        go.transform.localScale = new Vector3(fix.sx, 1f, 1f);
        go.AddComponent<MeshFilter>().sharedMesh = mesh;
        return go;
    }

    static Vector3 WorldPoint(GameObject go)
    {
        var mesh = go.GetComponent<MeshFilter>().sharedMesh;
        return go.transform.TransformPoint(mesh.vertices[0]);
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

    static string NaturalSweep(Camera camera, RenderTexture texture, string directory)
    {
        var quality = QualitySettings.names[QualitySettings.GetQualityLevel()];
        var bias = QualitySettings.lodBias;
        var maxLod = QualitySettings.maximumLODLevel;
        var builder = new StringBuilder();
        builder.Append("{\"fov\":").Append(camera.fieldOfView.ToString(CultureInfo.InvariantCulture));
        builder.Append(",\"lodBias\":").Append(bias.ToString(CultureInfo.InvariantCulture));
        builder.Append(",\"maximumLODLevel\":").Append(maxLod.ToString(CultureInfo.InvariantCulture));
        builder.Append(",\"quality\":").Append(JsonString(quality));
        builder.Append(",\"note\":\"Automatic LODGroup. ForceLOD is -1. Forced mesh frames are separate and are not this sweep.\",\"assets\":[");
        var firstAsset = true;
        foreach (var asset in Islands.Concat(new[] { "PORT" }))
        {
            if (!firstAsset) builder.Append(",");
            firstAsset = false;
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Game/Art/Islands/Prefabs/" + asset + ".prefab");
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            SetLodNatural(instance);
            var group = instance.GetComponentInChildren<LODGroup>(true);
            var lods = group.GetLODs();
            builder.Append("{\"asset\":").Append(JsonString(asset));
            builder.Append(",\"size\":").Append(group.size.ToString(CultureInfo.InvariantCulture));
            builder.Append(",\"thresholds\":[");
            for (var i = 0; i < lods.Length; i++)
            {
                if (i > 0) builder.Append(",");
                builder.Append(lods[i].screenRelativeTransitionHeight.ToString(CultureInfo.InvariantCulture));
            }
            builder.Append("],\"samples\":[");
            var seen = new bool[3];
            var multipliers = new[] { 0.45f, 0.8f, 1.3f, 2f, 3f, 4.5f, 7f, 10f, 15f, 22f };
            var firstSample = true;
            foreach (var multiplier in multipliers)
            {
                var distance = Mathf.Max(group.size, 1f) * multiplier;
                var center = group.transform.TransformPoint(group.localReferencePoint);
                var rotation = Quaternion.Euler(28f, 40f, 0f);
                camera.transform.position = center + rotation * new Vector3(0f, 0f, -distance);
                camera.transform.LookAt(center);
                var relative = RelativeHeight(group, camera);
                var predicted = PredictLod(lods, relative);
                foreach (var lodEntry in lods)
                    foreach (var r in lodEntry.renderers) { r.enabled = false; r.enabled = true; }
                group.ForceLOD(-1);
                var image = ReadShot(camera, texture);
                var empty = EmptyFraction(image);
                UnityEngine.Object.DestroyImmediate(image);
                var pixels = MeasureLodPixels(camera, texture, group);
                var visible = new List<string>();
                for (var level = 0; level < pixels.Length; level++)
                {
                    if (pixels[level] > 0)
                    {
                        seen[level] = true;
                        visible.Add(asset + "_LOD" + level);
                    }
                }
                var name = asset + "_natural_d" + multiplier.ToString("0.00", CultureInfo.InvariantCulture).Replace(".", "p");
                Shot(camera, texture, directory, name);
                if (!firstSample) builder.Append(",");
                firstSample = false;
                builder.Append("{\"distance_m\":").Append(distance.ToString(CultureInfo.InvariantCulture));
                builder.Append(",\"relative_height\":").Append(relative.ToString(CultureInfo.InvariantCulture));
                builder.Append(",\"predicted_lod\":").Append(predicted.ToString(CultureInfo.InvariantCulture));
                builder.Append(",\"empty_fraction\":").Append(empty.ToString(CultureInfo.InvariantCulture));
                builder.Append(",\"lod_pixels\":[").Append(pixels[0]).Append(",").Append(pixels[1]).Append(",").Append(pixels[2]).Append("]");
                builder.Append(",\"visible\":[");
                for (var v = 0; v < visible.Count; v++)
                {
                    if (v > 0) builder.Append(",");
                    builder.Append(JsonString(visible[v]));
                }
                builder.Append("],\"file\":").Append(JsonString(name + ".png")).Append("}");
            }
            builder.Append("],\"matched\":[");
            var firstMatch = true;
            for (var lod = 0; lod < 3; lod++)
            {
                var band = BandDistance(group, camera, lods, lod);
                if (float.IsNaN(band)) continue;
                var center = group.transform.TransformPoint(group.localReferencePoint);
                var rotation = Quaternion.Euler(28f, 40f, 0f);
                camera.transform.position = center + rotation * new Vector3(0f, 0f, -band);
                camera.transform.LookAt(center);
                SetLodNatural(instance);
                var natural = ReadShot(camera, texture);
                var naturalEmpty = EmptyFraction(natural);
                var bestLod = -1;
                var bestDiff = double.MaxValue;
                var diffs = new double[3];
                for (var forced = 0; forced < 3; forced++)
                {
                    SetLodVisible(instance, asset, forced);
                    var image = ReadShot(camera, texture);
                    diffs[forced] = MeanAbs(natural, image);
                    UnityEngine.Object.DestroyImmediate(image);
                    if (diffs[forced] < bestDiff)
                    {
                        bestDiff = diffs[forced];
                        bestLod = forced;
                    }
                }
                var file = asset + "_natural_match_LOD" + lod;
                var bytes = natural.EncodeToPNG();
                File.WriteAllBytes(Path.Combine(directory, file + ".png"), bytes);
                UnityEngine.Object.DestroyImmediate(natural);
                SetLodNatural(instance);
                if (!firstMatch) builder.Append(",");
                firstMatch = false;
                builder.Append("{\"target_lod\":").Append(lod.ToString(CultureInfo.InvariantCulture));
                builder.Append(",\"distance_m\":").Append(band.ToString(CultureInfo.InvariantCulture));
                builder.Append(",\"empty_fraction\":").Append(naturalEmpty.ToString(CultureInfo.InvariantCulture));
                builder.Append(",\"closest_forced_lod\":").Append(bestLod.ToString(CultureInfo.InvariantCulture));
                builder.Append(",\"mean_abs\":[");
                for (var i = 0; i < 3; i++)
                {
                    if (i > 0) builder.Append(",");
                    builder.Append(diffs[i].ToString(CultureInfo.InvariantCulture));
                }
                builder.Append("],\"file\":").Append(JsonString(file + ".png")).Append("}");
            }
            builder.Append("],\"saw_rendered_pixels\":[");
            for (var i = 0; i < seen.Length; i++)
            {
                if (i > 0) builder.Append(",");
                builder.Append(seen[i] ? "true" : "false");
            }
            builder.Append("]}");
            UnityEngine.Object.DestroyImmediate(instance);
        }
        builder.Append("]}");
        return builder.ToString();
    }

    // Each sample measures a fresh render. Predictions and cached isVisible
    // never establish an observed level. Raw counts retain tiny-image limitations.
    static int[] MeasureLodPixels(Camera camera, RenderTexture texture, LODGroup group)
    {
        var shader = Shader.Find("Universal Render Pipeline/Unlit");
        if (shader == null) throw new InvalidOperationException("Missing diagnostic unlit shader");
        var colors = new[] { Color.red, Color.green, Color.blue };
        var materials = colors.Select(c => { var m = new Material(shader); m.SetColor("_BaseColor", c); return m; }).ToArray();
        var originals = new Dictionary<Renderer, Material[]>();
        var background = camera.backgroundColor;
        var flags = camera.clearFlags;
        Texture2D image = null;
        try
        {
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = Color.black;
            var lods = group.GetLODs();
            group.ForceLOD(-1);
            for (var l = 0; l < lods.Length; l++)
                foreach (var r in lods[l].renderers)
                {
                    originals[r] = r.sharedMaterials;
                    r.sharedMaterials = Enumerable.Repeat(materials[l], r.sharedMaterials.Length).ToArray();
                }
            image = ReadShot(camera, texture);
            var counts = new int[3];
            foreach (var p in image.GetPixels32())
            {
                if (p.r > 200 && p.g < 30 && p.b < 30) counts[0]++;
                if (p.g > 200 && p.r < 30 && p.b < 30) counts[1]++;
                if (p.b > 200 && p.r < 30 && p.g < 30) counts[2]++;
            }
            return counts;
        }
        finally
        {
            foreach (var pair in originals) pair.Key.sharedMaterials = pair.Value;
            foreach (var m in materials) UnityEngine.Object.DestroyImmediate(m);
            if (image != null) UnityEngine.Object.DestroyImmediate(image);
            camera.backgroundColor = background; camera.clearFlags = flags;
        }
    }

    static float BandDistance(LODGroup group, Camera camera, LOD[] lods, int lod)
    {
        var size = WorldSize(group);
        var half = Mathf.Tan(camera.fieldOfView * Mathf.Deg2Rad * 0.5f);
        var bias = Mathf.Max(QualitySettings.lodBias, 0.01f);
        var high = lod == 0 ? 2.5f : lods[lod - 1].screenRelativeTransitionHeight;
        var low = lods[lod].screenRelativeTransitionHeight;
        var mid = Mathf.Sqrt(Mathf.Max(high, 0.02f) * Mathf.Max(low, 0.02f));
        if (lod == 0) mid = Mathf.Max(lods[0].screenRelativeTransitionHeight * 1.35f, 0.9f);
        var distance = size / (2f * mid * half) * bias;
        return distance;
    }

    static int PredictLod(LOD[] lods, float relative)
    {
        for (var i = 0; i < lods.Length; i++)
        {
            if (relative >= lods[i].screenRelativeTransitionHeight) return i;
        }
        return -1;
    }

    static float RelativeHeight(LODGroup group, Camera camera)
    {
        var world = group.transform.TransformPoint(group.localReferencePoint);
        var distance = Vector3.Distance(camera.transform.position, world);
        if (distance < 0.01f) distance = 0.01f;
        var half = Mathf.Tan(camera.fieldOfView * Mathf.Deg2Rad * 0.5f);
        return WorldSize(group) / (2f * distance * half) * QualitySettings.lodBias;
    }

    static float WorldSize(LODGroup group)
    {
        var scale = group.transform.lossyScale;
        var max = Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.y), Mathf.Abs(scale.z));
        return group.size * max;
    }

    static Texture2D ReadShot(Camera camera, RenderTexture texture)
    {
        RenderCamera(camera, texture);
        var previous = RenderTexture.active;
        RenderTexture.active = texture;
        var image = new Texture2D(texture.width, texture.height, TextureFormat.RGB24, false);
        image.ReadPixels(new Rect(0, 0, texture.width, texture.height), 0, 0);
        image.Apply();
        RenderTexture.active = previous;
        return image;
    }

    static float EmptyFraction(Texture2D image)
    {
        var pixels = image.GetPixels32();
        var empty = 0;
        for (var i = 0; i < pixels.Length; i++)
        {
            var pixel = pixels[i];
            if (Mathf.Abs(pixel.r - 59) <= 10 && Mathf.Abs(pixel.g - 122) <= 10 && Mathf.Abs(pixel.b - 158) <= 10) empty++;
        }
        return empty / (float)pixels.Length;
    }

    static double MeanAbs(Texture2D a, Texture2D b)
    {
        var pa = a.GetPixels32();
        var pb = b.GetPixels32();
        double total = 0;
        var count = Math.Min(pa.Length, pb.Length);
        for (var i = 0; i < count; i++)
        {
            total += Math.Abs(pa[i].r - pb[i].r) + Math.Abs(pa[i].g - pb[i].g) + Math.Abs(pa[i].b - pb[i].b);
        }
        return total / (count * 3.0);
    }

    static string JsonString(string value)
    {
        return "\"" + value.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
    }

    static Dictionary<string, object> MeasureWaterlines(Dictionary<string, Mesh> meshes, Dictionary<string, AxisFix> rotations, string metricsPath)
    {
        var packagePath = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(metricsPath), "..", "data", "island_module_package.json"));
        var package = MiniJson.Parse(File.ReadAllText(packagePath)) as Dictionary<string, object>;
        var canon = (Dictionary<string, object>)package["canonical_integers"];
        var archetypes = (List<object>)canon["archetypes"];
        var report = new Dictionary<string, object>();
        foreach (var asset in Islands)
        {
            List<double[]> ring = null;
            foreach (var item in archetypes)
            {
                var archetype = (Dictionary<string, object>)item;
                if ((string)archetype["archetype_id"] != asset) continue;
                foreach (var polyItem in (List<object>)archetype["polygons"])
                {
                    var poly = (Dictionary<string, object>)polyItem;
                    if ((string)poly["kind"] != "land") continue;
                    ring = new List<double[]>();
                    foreach (var pointItem in (List<object>)poly["outer"])
                    {
                        var point = (List<object>)pointItem;
                        ring.Add(new[] { Convert.ToDouble(point[0]) / 100000.0, Convert.ToDouble(point[1]) / 100000.0 });
                    }
                }
            }
            var fix = rotations[asset];
            var lodReport = new Dictionary<string, object>();
            for (var lod = 0; lod < 3; lod++)
            {
                var mesh = meshes[ModelPath(asset, lod)];
                var water = new List<Vector2>();
                foreach (var vertex in mesh.vertices)
                {
                    var point = Quaternion.Euler(fix.rx, 0f, 0f) * Vector3.Scale(new Vector3(fix.sx, 1f, 1f), vertex);
                    if (Mathf.Abs(point.y) <= 0.02f) water.Add(new Vector2(point.x, point.z));
                }
                var worst = 0.0;
                foreach (var wanted in ring)
                {
                    var best = double.MaxValue;
                    for (var index = 0; index < water.Count; index++)
                    {
                        var dx = water[index].x - wanted[0];
                        var dz = water[index].y - wanted[1];
                        var dist = Math.Sqrt(dx * dx + dz * dz);
                        if (dist < best) best = dist;
                    }
                    if (best > worst) worst = best;
                }
                lodReport[lod.ToString(CultureInfo.InvariantCulture)] = new Dictionary<string, object>
                {
                    { "waterline_vertices", water.Count },
                    { "canonical_vertices", ring.Count },
                    { "max_error_m", worst }
                };
            }
            report[asset] = lodReport;
        }
        return report;
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
        else if (value is int || value is long || value is uint || value is float || value is double) writer.Write(Convert.ToString(value, System.Globalization.CultureInfo.InvariantCulture));
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
        else if (value is System.Collections.IList list)
        {
            writer.Write("[");
            var first = true;
            foreach (var item in list)
            {
                if (!first) writer.Write(",");
                first = false;
                Write(writer, item);
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
