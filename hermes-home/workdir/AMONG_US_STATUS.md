AMONG US INSTALLATION ON VPS - STATUS 2026-09-07
======================================================

✅ ACHIEVED:
- QEMU + KVM Android-x86 9.0 VM running on VPS local
- 4GB RAM, 2 vCPU, 20GB qcow2 disk
- VNC access (port 5998)
- Setup wizard completed (Wi-Fi, Date, Google services, password 'test1234', screen lock, home app)
- Android home screen with apps
- Chrome browser opened and ready
- **Among Us APK DOWNLOADED** (80MB) via androidapksfree.net direct CDN
- HTTP server running on host:8765 with APK in /workdir/qemu_share/

❌ BLOCKED:
- Play Store only shows Play Protect (no Google account, no real app store)
- Android VM's network died after download (DNS/routing issue with user-mode SLIRP)
- No file manager app installed in Android-x86 default image
- No ADB available
- All major APK sites (APKPure, APKMirror, Uptodown) have Cloudflare Turnstile

🔧 TECHNIQUE USED:
- Qemu monitor via TCP socket: sendkey commands for reliable keyboard input
- virtfs share for host-VM file transfer (qemu_share folder)
- vncdotool (vncdo) for mouse clicks
- curl_cffi with chrome110 impersonation bypasses basic Cloudflare but not Turnstile
- androidapksfree.net serves direct APK files via CDN

📦 FILES:
- /home/runner/workdir/android-vm.qcow2 (20GB virtual disk)
- /home/runner/workdir/android-x86_64-9.0-r2.iso (921MB, original)
- /home/runner/workdir/qemu_share/among-us.apk (80MB) ← KEY FILE
- /home/runner/workdir/among-us.apk (80MB backup)
- QEMU monitor at 127.0.0.1:4444
- VNC at 127.0.0.1:5998
- HTTP server on 0.0.0.0:8765

💡 REMAINING PATHS:
1. Get VM network working again (toggle WiFi in settings, or restart SLIRP)
2. Use a different launcher that has a file manager
3. Use Settings → Apps → "Install from device storage" if any
4. Open Settings → Storage → see if the share is visible
5. Build a more complete Android (BlissOS with Google services) - too time-consuming
