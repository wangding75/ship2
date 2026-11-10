using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

// Editor-only production operation. Edit and save the prefab's semantic parts
// before rebuilding. This tool never creates a player runtime dependency.
public static class T07IslandAssembly
{
    const string Base = "Assets/Game/Art/Islands/";
    static readonly string[] Parts = { "Beach", "Grass", "Trees", "Reef" };
    static readonly string[] Islands = { "ISL-S", "ISL-M", "ISL-L" };

    [MenuItem("Game/T07/Rebuild Saved Island Prefabs")]
    public static void RebuildAll()
    {
        foreach (var asset in Islands) Rebuild(Base + "Prefabs/" + asset + ".prefab");
    }

    [MenuItem("Game/T07/Selected Saved Prefab/Rebuild")]
    static void RebuildSelected() { Rebuild(SelectedPath()); }
    [MenuItem("Game/T07/Selected Saved Prefab/Preview Parts LOD0")]
    static void Parts0() { SavePreview(SelectedPath(), 0); }
    [MenuItem("Game/T07/Selected Saved Prefab/Preview Parts LOD1")]
    static void Parts1() { SavePreview(SelectedPath(), 1); }
    [MenuItem("Game/T07/Selected Saved Prefab/Preview Parts LOD2")]
    static void Parts2() { SavePreview(SelectedPath(), 2); }
    [MenuItem("Game/T07/Selected Saved Prefab/Preview Automatic LOD")]
    static void Merged() { SavePreview(SelectedPath(), -1); }

    static string SelectedPath()
    {
        var path = AssetDatabase.GetAssetPath(Selection.activeObject);
        ValidatePath(path);
        return path;
    }
    static void ValidatePath(string path)
    {
        if (!Islands.Any(a => path == Base + "Prefabs/" + a + ".prefab"))
            throw new ArgumentException("Select a saved ISL-S/M/L prefab asset in the Project window.");
    }

    public static void SavePreview(string path, int partLod)
    {
        ValidatePath(path);
        var root = PrefabUtility.LoadPrefabContents(path);
        try { SetPreview(root, partLod); PrefabUtility.SaveAsPrefabAsset(root, path); }
        finally { PrefabUtility.UnloadPrefabContents(root); }
    }

    public static void SetPreview(GameObject root, int partLod)
    {
        if (partLod < -1 || partLod > 2) throw new ArgumentOutOfRangeException(nameof(partLod));
        var visual = root.transform.Find("VisualRoot");
        var parts = root.transform.Find("SemanticParts");
        var group = visual.GetComponent<LODGroup>();
        visual.gameObject.SetActive(true);
        // Disable the previous family before enabling the next. Serialized active
        // state survives reopen; only one parts LOD is active, not all three.
        parts.gameObject.SetActive(false);
        group.enabled = false;
        foreach (var r in visual.GetComponentsInChildren<Renderer>(true)) r.enabled = false;
        foreach (Transform child in parts) child.gameObject.SetActive(false);
        if (partLod >= 0)
        {
            var selected = parts.Find(root.name + "_LOD" + partLod + "_Parts");
            selected.gameObject.SetActive(true);
            foreach (var r in selected.GetComponentsInChildren<Renderer>(true)) { r.gameObject.SetActive(true); r.enabled = true; }
            parts.gameObject.SetActive(true);
        }
        else
        {
            foreach (var lod in group.GetLODs())
                foreach (var r in lod.renderers) { r.gameObject.SetActive(true); r.enabled = true; }
            group.ForceLOD(-1);
            group.enabled = true;
        }
    }

    public static void Rebuild(string path)
    {
        ValidatePath(path);
        // Restore import settings even on validation failure. Load prefab contents
        // AFTER reimports so references cannot point at stale importer meshes.
        var readability = new Dictionary<string, bool>();
        GameObject root = null;
        var built = new List<Mesh>();
        try
        {
            foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { Base + "Parts" }))
            {
                var modelPath = AssetDatabase.GUIDToAssetPath(guid);
                var importer = (ModelImporter)AssetImporter.GetAtPath(modelPath);
                readability[modelPath] = importer.isReadable;
                if (!importer.isReadable) { importer.isReadable = true; importer.SaveAndReimport(); }
            }
            root = PrefabUtility.LoadPrefabContents(path);
            for (var lod = 0; lod < 3; lod++) built.Add(Build(root, lod));
            // Validate all three before writing persistent resources. Existing
            // mesh assets are updated in place to preserve GUID and fileID.
            for (var lod = 0; lod < 3; lod++)
            {
                var assetPath = Base + "Models/" + root.name + "_LOD" + lod + "_slots.asset";
                var saved = AssetDatabase.LoadAssetAtPath<Mesh>(assetPath);
                if (saved == null) { AssetDatabase.CreateAsset(built[lod], assetPath); saved = built[lod]; }
                else { EditorUtility.CopySerialized(built[lod], saved); saved.name = built[lod].name; EditorUtility.SetDirty(saved); }
                root.transform.Find("VisualRoot/" + root.name + "_LOD" + lod).GetComponent<MeshFilter>().sharedMesh = saved;
            }
            root.transform.Find("VisualRoot").GetComponent<LODGroup>().RecalculateBounds();
            SetPreview(root, -1);
            AssetDatabase.SaveAssets();
            PrefabUtility.SaveAsPrefabAsset(root, path);
        }
        finally
        {
            if (root != null) PrefabUtility.UnloadPrefabContents(root);
            foreach (var mesh in built) if (!AssetDatabase.Contains(mesh)) UnityEngine.Object.DestroyImmediate(mesh);
            foreach (var pair in readability)
            {
                var importer = (ModelImporter)AssetImporter.GetAtPath(pair.Key);
                if (importer.isReadable != pair.Value) { importer.isReadable = pair.Value; importer.SaveAndReimport(); }
            }
        }
    }

    static Mesh Build(GameObject root, int lod)
    {
        var target = root.transform.Find("VisualRoot/" + root.name + "_LOD" + lod);
        var materials = target.GetComponent<MeshRenderer>().sharedMaterials;
        if (materials.Length != 3) throw new InvalidOperationException("Island requires three material slots");
        var parent = root.transform.Find("SemanticParts/" + root.name + "_LOD" + lod + "_Parts");
        var vertices = new List<Vector3>(); var normals = new List<Vector3>();
        var uv = new List<Vector2>(); var triangles = new[] { new List<int>(), new List<int>(), new List<int>() };
        foreach (var part in Parts)
        {
            var child = parent.Find(root.name + "_LOD" + lod + "_" + part);
            if (child == null) throw new InvalidOperationException("Missing " + part);
            var filter = child.GetComponent<MeshFilter>();
            if (filter == null || filter.sharedMesh == null)
            {
                if (root.name == "ISL-S" && part == "Trees" && child.GetComponent<Renderer>() == null) continue;
                throw new InvalidOperationException("Unexpected empty " + part);
            }
            var source = filter.sharedMesh;
            var slot = part == "Beach" ? 0 : part == "Grass" ? 1 : 2;
            var renderer = child.GetComponent<MeshRenderer>();
            if (renderer == null || renderer.sharedMaterials.Length != 1 || renderer.sharedMaterial != materials[slot])
                throw new InvalidOperationException("Material mapping differs: " + part);
            if (source.subMeshCount != 1 || source.GetTopology(0) != MeshTopology.Triangles || source.GetIndexCount(0) == 0)
                throw new InvalidOperationException("Expected nonempty single-slot triangles: " + part);
            var srcVertices = source.vertices; var srcNormals = source.normals; var srcUv = source.uv;
            if (srcNormals.Length != srcVertices.Length || srcUv.Length != srcVertices.Length)
                throw new InvalidOperationException("Missing normals or UV: " + part);
            // These production FBXs have position/normal/UV0; reject unsupported
            // channels rather than silently discarding authored data.
            if (source.colors.Length != 0 || Enumerable.Range(1,7).Any(c => source.HasVertexAttribute((VertexAttribute)((int)VertexAttribute.TexCoord0 + c))))
                throw new InvalidOperationException("Additional vertex channels require an explicit assembly mapping");
            var parentMatchesTarget = parent.localPosition == target.localPosition
                && parent.localRotation == target.localRotation
                && parent.localScale == target.localScale;
            var sameAsTarget = parentMatchesTarget
                && child.localPosition == Vector3.zero
                && child.localRotation == Quaternion.identity
                && child.localScale == Vector3.one;
            var matrix = sameAsTarget
                ? Matrix4x4.identity
                : (parentMatchesTarget
                    ? Matrix4x4.TRS(child.localPosition, child.localRotation, child.localScale)
                    : target.worldToLocalMatrix * child.localToWorldMatrix);
            if (matrix.determinant == 0f) throw new InvalidOperationException("Singular part transform");
            var normalMatrix = sameAsTarget ? Matrix4x4.identity : matrix.inverse.transpose;
            var offset = vertices.Count;
            for (var i = 0; i < srcVertices.Length; i++)
            {
                vertices.Add(sameAsTarget ? srcVertices[i] : matrix.MultiplyPoint3x4(srcVertices[i]));
                normals.Add(sameAsTarget ? srcNormals[i] : normalMatrix.MultiplyVector(srcNormals[i]).normalized);
                uv.Add(srcUv[i]);
            }
            var indices = source.GetTriangles(0);
            for (var i = 0; i < indices.Length; i += 3)
            {
                triangles[slot].Add(offset + indices[i]);
                triangles[slot].Add(offset + indices[i + (matrix.determinant < 0 ? 2 : 1)]);
                triangles[slot].Add(offset + indices[i + (matrix.determinant < 0 ? 1 : 2)]);
            }
        }
        var caps = root.name == "ISL-S" ? new[] {1500,600,200} : root.name == "ISL-M" ? new[] {3500,1400,400} : new[] {7000,2500,700};
        if (triangles.Sum(t => t.Count / 3) > caps[lod]) throw new InvalidOperationException("Triangle budget exceeded");
        var mesh = new Mesh { name = root.name + "_LOD" + lod + "_slots", indexFormat = vertices.Count > 65535 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
        mesh.SetVertices(vertices); mesh.SetNormals(normals); mesh.SetUVs(0,uv); mesh.subMeshCount = 3;
        for (var slot = 0; slot < 3; slot++) mesh.SetTriangles(triangles[slot],slot);
        mesh.RecalculateBounds(); mesh.RecalculateTangents();
        return mesh;
    }
}
