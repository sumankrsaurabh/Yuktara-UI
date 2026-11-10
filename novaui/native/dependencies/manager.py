"""First-run dependency provisioning for the Yuktara UI native runtime.

The manager intentionally uses the active interpreter for Python packages and
stores native libraries in a per-user cache. No files are written into the
package installation directory. Downloads are verified before extraction.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import importlib
import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

SDL3_VERSION = "3.4.20"
SKIA_PYTHON_VERSION = "144.1"
PYTEST_VERSION = "9.2.0"

SDL3_WINDOWS_ASSETS = {
    "AMD64": (
        "https://www.libsdl.org/release/SDL3-3.4.20-win32-x64.zip",
        "368bed8b24e44ad9ea372990814f2343fcfb9e468abb7f8f4a3bc146c7304752",
    ),
    "ARM64": (
        "https://www.libsdl.org/release/SDL3-3.4.20-win32-arm64.zip",
        "51c292eafc114ea3c63519fa2f5413a486979769d5444a636296f8a61c737267",
    ),
    "X86": (
        "https://www.libsdl.org/release/SDL3-3.4.20-win32-x86.zip",
        "f6fbf5afa42195a01b1da8adf25567377d0e212f4b2b6770923903eb3feea254",
    ),
}
SDL3_MACOS_ASSET = (
    "https://www.libsdl.org/release/SDL3-3.4.20.dmg",
    "36b7e4cefcf7d55d227b3df5e686f8f33ab34193173a976445d1b57c80009e44",
)
SDL3_LINUX_SOURCE = (
    "https://www.libsdl.org/release/SDL3-3.4.20.tar.gz",
    "f3bb06f55bed9557227a700af2ea62e49497ebdf58037732a731a5fb3ef8581f",
)


class DependencyError(RuntimeError):
    """Raised when a required dependency cannot be provisioned."""


def auto_install_enabled() -> bool:
    return os.environ.get("YUKTARA_UI_NO_AUTO_INSTALL", "0").strip().lower() not in {
        "1", "true", "yes", "on"
    }


def cache_root() -> Path:
    """Return a writable per-user cache root, with an explicit override."""
    override = os.environ.get("YUKTARA_UI_CACHE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        return base / "Yuktara" / "UI" / "cache"
    if system == "Darwin":
        return Path.home() / "Library" / "Caches" / "Yuktara-UI"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "yuktara-ui"


def _run(command: list[str], *, cwd: Path | None = None) -> None:
    try:
        subprocess.run(command, cwd=str(cwd) if cwd else None, check=True)
    except FileNotFoundError as exc:
        raise DependencyError(f"Required setup command was not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise DependencyError(
            f"Dependency setup command failed ({exc.returncode}): {' '.join(command)}"
        ) from exc


def _pip_install(requirement: str) -> None:
    """Install or upgrade a Python distribution with the running interpreter."""
    command = [sys.executable, "-m", "pip", "install", "--upgrade", requirement]
    try:
        _run(command)
    except DependencyError as first_error:
        # Some Python installations omit pip until ensurepip is run.
        try:
            _run([sys.executable, "-m", "ensurepip", "--upgrade"])
            _run(command)
        except DependencyError:
            raise first_error


def ensure_python_distribution(
    distribution: str,
    version: str,
    *,
    import_name: str | None = None,
    installer: Callable[[str], None] = _pip_install,
) -> None:
    """Ensure an exact tested Python distribution is available."""
    try:
        installed = importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        installed = None
    if installed != version:
        if not auto_install_enabled():
            raise DependencyError(
                f"{distribution}=={version} is required. Automatic installation is disabled."
            )
        installer(f"{distribution}=={version}")
        importlib.invalidate_caches()
    if import_name:
        try:
            importlib.import_module(import_name)
        except ImportError as exc:
            raise DependencyError(
                f"{distribution}=={version} was installed but '{import_name}' cannot be imported."
            ) from exc


def ensure_skia_python() -> None:
    """Install the pinned current Skia Python wheel on first render."""
    ensure_python_distribution(
        "skia-python", SKIA_PYTHON_VERSION, import_name="skia"
    )


def _architecture() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64", "x64"}:
        return "AMD64"
    if machine in {"aarch64", "arm64"}:
        return "ARM64"
    if machine in {"i386", "i486", "i586", "i686", "x86"}:
        return "X86"
    raise DependencyError(f"Unsupported CPU architecture for SDL3: {platform.machine()}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download_verified(url: str, expected_sha256: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".download", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Yuktara-UI-dependency-manager/1.0"},
        )
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as out:
            shutil.copyfileobj(response, out, length=1024 * 1024)
        actual = _sha256(temporary)
        if actual.lower() != expected_sha256.lower():
            raise DependencyError(
                f"SHA-256 verification failed for {destination.name}: expected "
                f"{expected_sha256}, received {actual}."
            )
        os.replace(temporary, destination)
        return destination
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _safe_zip_member(archive: zipfile.ZipFile, filename: str) -> zipfile.ZipInfo:
    for member in archive.infolist():
        if Path(member.filename).name.lower() == filename.lower():
            # Do not extract archive paths; read only the selected DLL member.
            if member.is_dir():
                continue
            return member
    raise DependencyError(f"The SDL3 package does not contain {filename}.")


def _install_windows_sdl3(target_dir: Path) -> Path:
    arch = _architecture()
    try:
        url, checksum = SDL3_WINDOWS_ASSETS[arch]
    except KeyError as exc:
        raise DependencyError(f"SDL3 Windows binaries are unavailable for {arch}.") from exc
    archive_path = _download_verified(url, checksum, target_dir / "download.zip")
    dll_path = target_dir / "SDL3.dll"
    if not dll_path.is_file():
        with zipfile.ZipFile(archive_path) as archive:
            member = _safe_zip_member(archive, "SDL3.dll")
            with archive.open(member) as source, dll_path.open("wb") as destination:
                shutil.copyfileobj(source, destination)
    return dll_path


def _install_macos_sdl3(target_dir: Path) -> Path:
    if not shutil.which("hdiutil"):
        raise DependencyError("macOS SDL3 setup requires the hdiutil utility.")
    url, checksum = SDL3_MACOS_ASSET
    dmg = _download_verified(url, checksum, target_dir / "SDL3.dmg")
    mount_dir = target_dir / "mounted-dmg"
    mount_dir.mkdir(parents=True, exist_ok=True)
    attached = False
    try:
        result = subprocess.run(
            ["hdiutil", "attach", "-readonly", "-nobrowse", "-noautoopen", "-mountpoint", str(mount_dir), str(dmg)],
            check=True, capture_output=True, text=True,
        )
        attached = True
        framework = next(mount_dir.rglob("SDL3.framework"), None)
        if framework is not None and framework.is_dir():
            destination = target_dir / "SDL3.framework"
            shutil.copytree(framework, destination, dirs_exist_ok=True, symlinks=True)
            candidates = [
                destination / "Versions" / "Current" / "SDL3",
                destination / "SDL3",
                destination / "Versions" / "A" / "SDL3",
            ]
            for candidate in candidates:
                if candidate.exists():
                    return candidate
        dylib = next(mount_dir.rglob("libSDL3.dylib"), None)
        if dylib is not None:
            destination = target_dir / "libSDL3.dylib"
            shutil.copy2(dylib, destination)
            return destination
        raise DependencyError("The official SDL3 macOS disk image contained no SDL3 framework or dylib.")
    finally:
        if attached:
            subprocess.run(
                ["hdiutil", "detach", str(mount_dir), "-quiet"],
                check=False, capture_output=True,
            )


def _extract_tar_safely(archive_path: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            resolved = (destination / member.name).resolve()
            if resolved != root and root not in resolved.parents:
                raise DependencyError("Rejected unsafe path in SDL3 source archive.")
            if member.issym() or member.islnk() or member.isdev():
                raise DependencyError("Rejected links or device files in SDL3 source archive.")
        archive.extractall(destination, members=members)
    directories = [p for p in destination.iterdir() if p.is_dir()]
    if not directories:
        raise DependencyError("SDL3 source archive did not contain a source directory.")
    return directories[0]


def _cmake_executable() -> str:
    found = shutil.which("cmake")
    if found:
        return found
    if not auto_install_enabled():
        raise DependencyError("CMake is missing and automatic dependency installation is disabled.")
    _pip_install("cmake")
    scripts = Path(sysconfig.get_path("scripts"))
    names = ("cmake.exe", "cmake") if os.name == "nt" else ("cmake",)
    for name in names:
        candidate = scripts / name
        if candidate.exists():
            return str(candidate)
    found = shutil.which("cmake")
    if found:
        return found
    raise DependencyError("CMake was installed, but its executable could not be located.")


def _linux_display_deps_available() -> bool:
    """Return true when at least one common desktop window backend can build."""
    pkg_config = shutil.which("pkg-config")
    if not pkg_config:
        return False
    for package in ("x11", "wayland-client"):
        result = subprocess.run(
            [pkg_config, "--exists", package],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            return True
    return False


def _try_install_linux_build_tools() -> bool:
    """Bootstrap compiler and common SDL video/audio development libraries.

    Package-manager authorization is requested only from an interactive
    terminal. A GUI-launched app without a terminal fails fast with a useful
    message rather than hanging on an invisible sudo password prompt.
    """
    package_managers = [
        (
            "apt-get", ["apt-get", "update"],
            ["apt-get", "install", "-y", "build-essential", "pkg-config", "cmake",
             "libasound2-dev", "libpulse-dev", "libwayland-dev", "libx11-dev",
             "libxext-dev", "libxrandr-dev", "libxcursor-dev", "libxfixes-dev",
             "libxi-dev", "libxss-dev", "libxkbcommon-dev", "libdrm-dev", "libgbm-dev",
             "libegl1-mesa-dev", "libgl1-mesa-dev", "libibus-1.0-dev", "libudev-dev",
             "libdbus-1-dev"],
        ),
        (
            "dnf", [],
            ["dnf", "install", "-y", "gcc", "gcc-c++", "make", "pkgconf-pkg-config", "cmake",
             "alsa-lib-devel", "pulseaudio-libs-devel", "wayland-devel", "libX11-devel",
             "libXext-devel", "libXrandr-devel", "libXcursor-devel", "libXfixes-devel",
             "libXi-devel", "libXScrnSaver-devel", "libxkbcommon-devel", "libdrm-devel",
             "mesa-libgbm-devel", "mesa-libEGL-devel", "mesa-libGL-devel", "ibus-devel",
             "systemd-devel", "dbus-devel"],
        ),
        (
            "pacman", [],
            ["pacman", "-Sy", "--noconfirm", "base-devel", "pkgconf", "cmake", "alsa-lib",
             "libpulse", "wayland", "libx11", "libxext", "libxrandr", "libxcursor",
             "libxfixes", "libxi", "libxss", "libxkbcommon", "libdrm", "mesa", "libglvnd",
             "ibus", "systemd-libs", "dbus"],
        ),
        (
            "zypper", [],
            ["zypper", "--non-interactive", "install", "gcc", "gcc-c++", "make", "pkg-config",
             "cmake", "alsa-devel", "libpulse-devel", "wayland-devel", "libX11-devel",
             "libXext-devel", "libXrandr-devel", "libXcursor-devel", "libXfixes-devel",
             "libXi-devel", "libXScrnSaver-devel", "libxkbcommon-devel", "libdrm-devel",
             "Mesa-libEGL-devel", "Mesa-libGL-devel", "ibus-devel", "systemd-devel", "dbus-1-devel"],
        ),
        (
            "apk", [],
            ["apk", "add", "build-base", "pkgconf", "cmake", "alsa-lib-dev", "pulseaudio-dev",
             "wayland-dev", "libx11-dev", "libxext-dev", "libxrandr-dev", "libxcursor-dev",
             "libxfixes-dev", "libxi-dev", "libxss-dev", "libxkbcommon-dev", "libdrm-dev",
             "mesa-dev", "mesa-egl-dev", "mesa-gl-dev", "ibus-dev", "eudev-dev", "dbus-dev"],
        ),
    ]
    for executable, update, install in package_managers:
        if not shutil.which(executable):
            continue
        prefix: list[str] = []
        if hasattr(os, "geteuid") and os.geteuid() != 0:
            if not shutil.which("sudo"):
                return False
            if not (sys.stdin.isatty() and sys.stdout.isatty()):
                return False
            prefix = ["sudo"]
        try:
            for command in ([update] if update else []) + [install]:
                _run(prefix + command)
            return True
        except DependencyError:
            return False
    return False


def _install_linux_sdl3(target_dir: Path) -> Path:
    compiler = next((shutil.which(name) for name in ("cc", "gcc", "clang") if shutil.which(name)), None)
    if not compiler or not _linux_display_deps_available():
        _try_install_linux_build_tools()
        compiler = next((shutil.which(name) for name in ("cc", "gcc", "clang") if shutil.which(name)), None)
    if not compiler:
        raise DependencyError(
            "SDL3 3.4.20 must be built from its official source on Linux. "
            "Yuktara UI attempted to bootstrap a compiler and the SDL video/audio "
            "development libraries. Run `python -m novaui setup` from an interactive "
            "terminal so your package manager can request administrator authorization, "
            "then retry."
        )
    if not _linux_display_deps_available():
        raise DependencyError(
            "SDL3 cannot provide a desktop video backend because neither X11 nor "
            "Wayland development files are available. Run `python -m novaui setup` "
            "from an interactive terminal to install the system build dependencies, "
            "or install your distribution's X11/Wayland development packages."
        )
    cmake = _cmake_executable()
    url, checksum = SDL3_LINUX_SOURCE
    source_archive = _download_verified(url, checksum, target_dir / "SDL3-source.tar.gz")
    source_dir = _extract_tar_safely(source_archive, target_dir / "source")
    build_dir = target_dir / "build"
    install_dir = target_dir / "install"
    configure = [
        cmake, "-S", str(source_dir), "-B", str(build_dir),
        "-DCMAKE_BUILD_TYPE=Release",
        f"-DCMAKE_INSTALL_PREFIX={install_dir}",
        "-DSDL_SHARED=ON", "-DSDL_STATIC=OFF",
        "-DSDL_TESTS=OFF", "-DSDL_TEST_LIBRARY=OFF",
        "-DSDL_EXAMPLES=OFF", "-DSDL_INSTALL_TESTS=OFF",
    ]
    _run(configure)
    _run([cmake, "--build", str(build_dir), "--parallel"])
    _run([cmake, "--install", str(build_dir)])
    candidates = list(install_dir.rglob("libSDL3.so")) + list(install_dir.rglob("libSDL3.so.*"))
    if not candidates:
        raise DependencyError("SDL3 3.4.20 built successfully, but libSDL3.so was not found after installation.")
    # Prefer the unversioned linker/runtime entry when present.
    return next((p for p in candidates if p.name == "libSDL3.so"), candidates[0])


def _version_code(version: tuple[int, int, int]) -> int:
    major, minor, patch = version
    return major * 1_000_000 + minor * 1_000 + patch


def _read_sdl_version(library: ctypes.CDLL) -> int | None:
    try:
        function = library.SDL_GetVersion
        function.restype = ctypes.c_int
        function.argtypes = []
        return int(function())
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def system_sdl3_library() -> str | None:
    candidates: list[str] = []
    override = os.environ.get("YUKTARA_UI_SDL3_LIBRARY")
    if override:
        candidates.append(override)
    found = ctypes.util.find_library("SDL3")
    if found:
        candidates.append(found)
    candidates.extend(("SDL3.dll", "libSDL3.so", "libSDL3.dylib"))
    minimum = _version_code(tuple(map(int, SDL3_VERSION.split("."))))
    for candidate in candidates:
        try:
            library = ctypes.CDLL(candidate)
            version = _read_sdl_version(library)
            if version is not None and version >= minimum:
                return candidate
        except OSError:
            continue
    return None


def ensure_sdl3_runtime() -> str:
    """Return a path to SDL3 3.4.20, provisioning it if necessary.

    Windows and macOS use official prebuilt SDL3 3.4.20 releases. Linux uses
    the official 3.4.20 source and automatically configures/builds a shared
    library, because the SDL project does not publish a Linux runtime binary
    asset in its official release.
    """
    system_library = system_sdl3_library()
    if system_library:
        return system_library
    if not auto_install_enabled():
        raise DependencyError(
            f"SDL3 {SDL3_VERSION} is required and automatic installation is disabled."
        )
    target_dir = cache_root() / "native" / "SDL3" / SDL3_VERSION / platform.system().lower() / _architecture().lower()
    target_dir.mkdir(parents=True, exist_ok=True)
    system = platform.system()
    if system == "Windows":
        path = _install_windows_sdl3(target_dir)
    elif system == "Darwin":
        path = _install_macos_sdl3(target_dir)
    elif system == "Linux":
        path = _install_linux_sdl3(target_dir)
    else:
        raise DependencyError(f"Automatic SDL3 setup is not supported on {system}.")
    try:
        library = ctypes.CDLL(str(path))
    except OSError as exc:
        raise DependencyError(f"Downloaded SDL3 library could not be loaded: {path}") from exc
    version = _read_sdl_version(library)
    expected = _version_code(tuple(map(int, SDL3_VERSION.split("."))))
    if version is None or version < expected:
        raise DependencyError(
            f"SDL3 library at {path} does not report the required version {SDL3_VERSION}."
        )
    return str(path)


def setup_all(*, include_dev: bool = False) -> dict[str, str]:
    """Install/verify Python dependencies and provision SDL3 ahead of launch."""
    ensure_skia_python()
    sdl_path = ensure_sdl3_runtime()
    result = {
        "skia-python": SKIA_PYTHON_VERSION,
        "SDL3": SDL3_VERSION,
        "SDL3 library": sdl_path,
    }
    if include_dev:
        ensure_python_distribution("pytest", PYTEST_VERSION, import_name="pytest")
        result["pytest"] = PYTEST_VERSION
    return result


__all__ = [
    "DependencyError", "SDL3_VERSION", "SKIA_PYTHON_VERSION", "PYTEST_VERSION",
    "auto_install_enabled", "cache_root", "ensure_python_distribution",
    "ensure_skia_python", "ensure_sdl3_runtime", "setup_all", "system_sdl3_library",
]
