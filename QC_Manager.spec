from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH)

datas = [
    (str(ROOT / "app.py"), "."),
    (str(ROOT / "pages"), "pages"),
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "services"), "services"),
    (str(ROOT / "calculations"), "calculations"),
]

hiddenimports = []
binaries = []

for package in ["streamlit", "st_aggrid"]:
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h

for package in ["objc", "Cocoa", "WebKit", "PyObjCTools"]:
    hiddenimports += collect_submodules(package)

for package in ["openpyxl", "PIL"]:
    hiddenimports += collect_submodules(package)

a = Analysis(
    ["mac_launcher.py"],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["watchdog"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Portable Radiography QC Manager V2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Portable Radiography QC Manager V2",
)

app = BUNDLE(
    coll,
    name="Portable Radiography QC Manager V2.app",
    icon=None,
    bundle_identifier="com.imran.portableradiographyqcmanager",
    info_plist={
        "NSHighResolutionCapable": True,
    },
)
