import os
import sys
import time
import socket
import signal
import subprocess
import threading
import urllib.request
from pathlib import Path

PORT = 3000
URL = f"http://127.0.0.1:{PORT}"
HEALTH = URL + "/_stcore/health"

FROZEN = getattr(sys, "frozen", False)
ROOT = Path(sys._MEIPASS) if FROZEN else Path(__file__).resolve().parent
APP = ROOT / "app.py"

LOG_DIR = Path.home() / "Library" / "Logs" / "Portable Radiography QC Manager V2"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "launcher.log"


def log(message):
    print(message, flush=True)
    with LOG_FILE.open("a") as f:
        f.write(message + "\n")


def serve():
    import streamlit.web.cli as cli

    sys.argv = [
        "streamlit", "run", str(APP),
        "--server.address=127.0.0.1",
        "--server.port=3000",
        "--global.developmentMode=false",
        "--server.headless=true",
        "--server.fileWatcherType=none",
    ]
    cli.main()


def server_ready():
    try:
        with urllib.request.urlopen(HEALTH, timeout=1) as response:
            return response.status == 200 and response.read().strip() == b"ok"
    except Exception:
        return False


def main():
    import objc
    from Cocoa import (
        NSApplication, NSWindow, NSMakeRect, NSURL, NSURLRequest,
        NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
        NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
        NSBackingStoreBuffered, NSObject
    )
    from WebKit import WKWebView, WKNavigationResponsePolicyDownload

    class DownloadDelegate(NSObject):
        def download_decideDestinationUsingResponse_suggestedFilename_completionHandler_(
            self, download, response, filename, completion
        ):
            destination = Path.home() / "Downloads"
            destination.mkdir(parents=True, exist_ok=True)

            name = Path(str(filename)).name or "QC_Report.xlsx"
            target = destination / name

            if target.exists():
                stem = target.stem
                suffix = target.suffix
                counter = 1
                while target.exists():
                    target = destination / f"{stem}-{counter}{suffix}"
                    counter += 1

            log(f"Saving Excel report to: {target}")
            completion(NSURL.fileURLWithPath_(str(target)))

        def downloadDidFinish_(self, download):
            log("SUCCESS: WebKit download completed")

        def download_didFailWithError_resumeData_(self, download, error, data):
            log(f"ERROR: WebKit download failed: {error}")

    class NavigationDelegate(NSObject):
        def webView_navigationResponse_decisionHandler_(
            self, webview, response, decision
        ):
            if not response.canShowMIMEType():
                decision(WKNavigationResponsePolicyDownload)
            else:
                decision(1)

        def webView_navigationResponse_didBecomeDownload_(
            self, webview, response, download
        ):
            download.setDelegate_(download_delegate)

        def webView_navigationAction_didBecomeDownload_(
            self, webview, action, download
        ):
            download.setDelegate_(download_delegate)


    log("Starting native QC Manager")

    if not APP.is_file():
        log(f"ERROR: Missing app.py: {APP}")
        return 1

    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", PORT)) == 0:
            log("ERROR: Port 3000 is already occupied.")
            return 1

    os.chdir(ROOT)

    command = (
        [sys.executable, "--serve"]
        if FROZEN else
        [sys.executable, str(Path(__file__).resolve()), "--serve"]
    )

    with LOG_FILE.open("a") as output:
        process = subprocess.Popen(
            command,
            cwd=str(ROOT),
            stdout=output,
            stderr=subprocess.STDOUT,
        )

    application = NSApplication.sharedApplication()
    application.setActivationPolicy_(0)

    class WindowDelegate(NSObject):
        def windowWillClose_(self, notification):
            log("Native window closed")
            application.stop_(None)

    delegate = WindowDelegate.alloc().init()

    window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(200, 150, 1200, 800),
        NSWindowStyleMaskTitled |
        NSWindowStyleMaskClosable |
        NSWindowStyleMaskMiniaturizable |
        NSWindowStyleMaskResizable,
        NSBackingStoreBuffered,
        False,
    )

    window.setTitle_("Portable Radiography QC Manager V2")
    window.setDelegate_(delegate)

    webview = WKWebView.alloc().initWithFrame_(window.contentView().bounds())
    download_delegate = DownloadDelegate.alloc().init()
    navigation_delegate = NavigationDelegate.alloc().init()

    webview.setNavigationDelegate_(navigation_delegate)
    window.setContentView_(webview)

    def load_when_ready():
        for _ in range(90):
            if process.poll() is not None:
                log("ERROR: Streamlit exited during startup")
                return

            if server_ready():
                log("SUCCESS: Streamlit server ready")
                webview_url = NSURL.URLWithString_(URL)

                # Schedule WebKit loading on the macOS main thread.
                from PyObjCTools import AppHelper
                AppHelper.callAfter(
                    lambda: webview.loadRequest_(
                        NSURLRequest.requestWithURL_(webview_url)
                    )
                )
                return

            time.sleep(1)

        log("ERROR: Streamlit startup timed out")

    threading.Thread(target=load_when_ready, daemon=True).start()

    def stop_application(signum, frame):
        application.stop_(None)

    previous_handler = signal.signal(signal.SIGTERM, stop_application)

    try:
        window.makeKeyAndOrderFront_(None)
        application.activateIgnoringOtherApps_(True)
        application.run()
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
        log("Stopping Streamlit server")

        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        log("QC Manager stopped")

    return 0


if __name__ == "__main__":
    if "--serve" in sys.argv:
        serve()
    else:
        sys.exit(main())
