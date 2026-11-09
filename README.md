# S1 Unity foundation

T03 work in progress. Unity 6000.6.6f1, URP 17.6.0, Pipeline 0.8.0-exp.1. Open `client/UnityProject`.

The foundation scene is a rendering calibration fixture, not the island world or navigation implementation. Settings remain PROVISIONAL. Final quality, memory, performance and 20:9 acceptance remain owner-deferred.

Build on Windows with `powershell -NoProfile -File tools/build/Build-Windows.ps1`; no other Editor may hold this project. Run `tools/build/Test-WindowsLaunch.ps1` for a hidden, real GPU launch, 90 advancing frames and camera capture. The smoke fixture is inert unless `-t03-smoke <evidence-directory>` is passed.

Development evidence is under `releases/t03-recovery`. Gate implementation, protected reviewer provenance, shared resource broker, clean checkout validation and independent A04/A13 acceptance remain outstanding. This repository is not yet an accepted T03 candidate.
