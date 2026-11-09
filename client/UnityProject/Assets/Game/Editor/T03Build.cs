using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

public static class T03Build
{
    public static void Windows()
    {
        string root = Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        string output = Path.Combine(root, "releases/windows/S1T03.exe");
        Directory.CreateDirectory(Path.GetDirectoryName(output));
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
            scenes = new[] { "Assets/Game/Scenes/T03Foundation.unity" },
            locationPathName = output,
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.Development | BuildOptions.DetailedBuildReport
        });
        var s = report.summary;
        File.WriteAllText(Path.Combine(root, "releases/t03-recovery/windows-build.json"), JsonUtility.ToJson(new Record {
            utc=DateTime.UtcNow.ToString("o"), result=s.result.ToString(), errors=s.totalErrors,
            warnings=s.totalWarnings, bytes=s.totalSize, seconds=s.totalTime.TotalSeconds, output=output
        }, true));
        if (s.result != BuildResult.Succeeded) throw new Exception("Windows build failed: " + s.result);
    }
    [Serializable] private class Record {
        public string utc, result, output;
        public int errors, warnings;
        public ulong bytes;
        public double seconds;
    }
}
