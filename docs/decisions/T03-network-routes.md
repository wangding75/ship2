T03 network route comparison, 2026-11-09 (development evidence, not independent acceptance).

Explicit HTTP proxy 127.0.0.1:33210: Git smart HTTP and Pipeline metadata returned 200. Pipeline 0.8.0-exp.1 tarball downloaded completely (4,667,717 bytes), SHA1 62c08c808737255821f3449466689a527a2eea50 matches the official registry metadata.

No application proxy: Git and metadata returned 200, but the tarball timed out after 20 seconds with 225,357 bytes. A Unity UPM run with proxy variables removed reported EACCES; its owned Editor was deliberately stopped. This is not a successful build. GitHub resolved to 198.19.x.x, so disabling application proxy does not prove the absence of transparent/TUN routing.

China registry packages.unity.cn: Input System metadata returned 200 and includes 1.20.0; Pipeline metadata returned 404. Therefore it cannot replace the project's entire registry. No manifest or global registry settings were changed.

The subsequent UPM run with the existing proxy environment registered all 33 packages and proceeded into the clean checkout build. Raw results are delivered separately in the issue evidence attachment. Earlier ECONNRESET results remain historical failures; current success does not identify their precise transient cause.

Official network configuration reference: https://docs.unity.cn/cn/tuanjiemanual/1.2/Manual/upm-config-network.html (China endpoints and proxy environment variables; endpoint listing does not guarantee package parity).
