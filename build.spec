# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['src'],  # Добавляем путь к src
    binaries=[],
    datas=[src/test.jpg],  # Если есть другие файлы (изображения, конфиги) - добавьте здесь
    hiddenimports=[
        'error_diffusion',
        'ordered_dithering', 
        'palette',
        'randomized',
        'threshold',
        'utils',
        'cv2',  # OpenCV
        'PIL',  # Pillow
        'PIL._imaging',
        'numpy',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ImageDithering',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Для GUI приложений
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)
