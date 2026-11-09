# S1 Unity foundation

T03 work in progress. Unity 6000.6.6f1, URP 17.6.0, Pipeline 0.8.0-exp.1. Open `client/UnityProject`.

The foundation scene is a rendering calibration fixture, not the island world or navigation implementation. Settings remain PROVISIONAL. Final quality, memory, performance and 20:9 acceptance remain owner-deferred.

Build on Windows with `powershell -NoProfile -File tools/build/Build-Windows.ps1`; no other Editor may hold this project. Run `tools/build/Test-WindowsLaunch.ps1` for a hidden, real GPU launch, 90 advancing frames and camera capture. The smoke fixture is inert unless `-t03-smoke <evidence-directory>` is passed.

The effective delivery scope is `T03-contract-v2-bootstrap-slice`, SHA256 `10d8e06582d550a6c488efdb5a590d259c9ee4374ba349100709d50a222b44d0`, with the independent A02 G14 record archived in `docs/decisions/t03-inputs`.

Production Gate deployment, protected reviewer trust storage, cross-credential lease isolation, remote CI execution, and platform binary upload recovery are DEFERRED_OWNER / NOT_RUN, not passed. Existing gate/lease tests are development fixtures only. Keep one author and exclusive Unity/GPU access; no concurrent project writers. Independent A04/A13 acceptance must bind the exact candidate and actually obtain its Windows package.

Use a short checkout path on Windows (for example `C:/t03` or a temporary drive mapping). Deep runtime paths can exceed Unity package-import path limits. Do not claim a build is error-free from its exit code alone; inspect the BuildReport and raw log. Preserve earlier failed evidence.
