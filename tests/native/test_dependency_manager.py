from __future__ import annotations

import hashlib
import importlib.metadata
import os
import zipfile
from pathlib import Path

import pytest

from novaui.native.dependencies import manager


def test_current_dependency_baselines_are_recorded():
    assert manager.SDL3_VERSION == "3.4.20"
    assert manager.SKIA_PYTHON_VERSION == "144.1"
    assert manager.PYTEST_VERSION == "9.2.0"
    assert "numpy" not in manager.__all__


def test_auto_install_can_be_disabled(monkeypatch):
    monkeypatch.setenv("YUKTARA_UI_NO_AUTO_INSTALL", "1")
    assert manager.auto_install_enabled() is False
    monkeypatch.setenv("YUKTARA_UI_NO_AUTO_INSTALL", "false")
    assert manager.auto_install_enabled() is True


def test_cache_root_honors_override(monkeypatch, tmp_path):
    monkeypatch.setenv("YUKTARA_UI_CACHE_DIR", str(tmp_path / "cache"))
    assert manager.cache_root() == (tmp_path / "cache").resolve()


def test_python_distribution_installs_exact_version_when_missing(monkeypatch):
    installed = []

    def fake_version(name):
        if name == "sample-runtime":
            raise importlib.metadata.PackageNotFoundError(name)
        raise AssertionError(name)

    monkeypatch.setattr(manager.importlib.metadata, "version", fake_version)
    manager.ensure_python_distribution(
        "sample-runtime", "1.2.3", installer=installed.append
    )
    assert installed == ["sample-runtime==1.2.3"]


def test_python_distribution_upgrades_when_version_is_old(monkeypatch):
    installed = []
    monkeypatch.setattr(manager.importlib.metadata, "version", lambda name: "1.0.0")
    manager.ensure_python_distribution(
        "sample-runtime", "2.0.0", installer=installed.append
    )
    assert installed == ["sample-runtime==2.0.0"]


def test_python_distribution_respects_no_auto_install(monkeypatch):
    monkeypatch.setenv("YUKTARA_UI_NO_AUTO_INSTALL", "1")
    monkeypatch.setattr(
        manager.importlib.metadata,
        "version",
        lambda name: (_ for _ in ()).throw(importlib.metadata.PackageNotFoundError(name)),
    )
    with pytest.raises(manager.DependencyError, match="Automatic installation is disabled"):
        manager.ensure_python_distribution(
            "sample-runtime", "2.0.0", installer=lambda spec: pytest.fail("installer called")
        )


def test_download_verified_copies_and_checks_sha256(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"yuktara-ui-dependency")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    destination = tmp_path / "cache" / "runtime.bin"
    result = manager._download_verified(source.as_uri(), digest, destination)
    assert result == destination
    assert destination.read_bytes() == source.read_bytes()


def test_download_verified_rejects_hash_mismatch(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"incorrect payload")
    with pytest.raises(manager.DependencyError, match="SHA-256 verification failed"):
        manager._download_verified(source.as_uri(), "0" * 64, tmp_path / "runtime.bin")
    assert not (tmp_path / "runtime.bin").exists()


def test_safe_zip_member_reads_only_expected_dll(tmp_path):
    archive_path = tmp_path / "sdl.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("SDL3-3.4.20/lib/x64/SDL3.dll", b"test-dll")
        archive.writestr("../../evil.txt", b"never extract this")
    with zipfile.ZipFile(archive_path) as archive:
        member = manager._safe_zip_member(archive, "SDL3.dll")
        assert archive.read(member) == b"test-dll"


def test_ensure_sdl3_uses_current_system_runtime(monkeypatch):
    monkeypatch.setattr(manager, "system_sdl3_library", lambda: "/system/libSDL3.so")
    monkeypatch.setattr(manager, "_architecture", lambda: "AMD64")
    assert manager.ensure_sdl3_runtime() == "/system/libSDL3.so"


def test_ensure_sdl3_errors_when_auto_install_disabled(monkeypatch):
    monkeypatch.setattr(manager, "system_sdl3_library", lambda: None)
    monkeypatch.setattr(manager, "_architecture", lambda: "AMD64")
    monkeypatch.setenv("YUKTARA_UI_NO_AUTO_INSTALL", "1")
    with pytest.raises(manager.DependencyError, match="automatic installation is disabled"):
        manager.ensure_sdl3_runtime()


def test_version_code_uses_sdl_version_macro_format():
    assert manager._version_code((3, 4, 20)) == 3_004_020


def test_windows_binary_architecture_selection(monkeypatch):
    monkeypatch.setattr(manager.platform, "machine", lambda: "ARM64")
    assert manager._architecture() == "ARM64"
    monkeypatch.setattr(manager.platform, "machine", lambda: "AMD64")
    assert manager._architecture() == "AMD64"


def test_platform_assets_are_pinned_to_official_release():
    assert "SDL3-3.4.20-win32-x64.zip" in manager.SDL3_WINDOWS_ASSETS["AMD64"][0]
    assert len(manager.SDL3_WINDOWS_ASSETS["AMD64"][1]) == 64
    assert "SDL3-3.4.20.dmg" in manager.SDL3_MACOS_ASSET[0]
    assert len(manager.SDL3_MACOS_ASSET[1]) == 64
    assert "SDL3-3.4.20.tar.gz" in manager.SDL3_LINUX_SOURCE[0]
    assert len(manager.SDL3_LINUX_SOURCE[1]) == 64


def test_linux_bootstrap_uses_real_apt_package_command(monkeypatch):
    commands = []
    monkeypatch.setattr(manager.shutil, "which", lambda name: "/usr/bin/apt-get" if name == "apt-get" else None)
    monkeypatch.setattr(manager.os, "geteuid", lambda: 0)
    monkeypatch.setattr(manager, "_run", lambda command, cwd=None: commands.append(command))

    assert manager._try_install_linux_build_tools() is True
    assert commands[0] == ["apt-get", "update"]
    assert commands[1][:3] == ["apt-get", "install", "-y"]
    assert "build-essential" in commands[1]
    assert "libx11-dev" in commands[1]
    assert "libwayland-dev" in commands[1]


def test_linux_bootstrap_does_not_open_hidden_sudo_prompt(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(manager.shutil, "which", lambda name: f"/usr/bin/{name}" if name in {"apt-get", "sudo"} else None)
    monkeypatch.setattr(manager.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(manager.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    monkeypatch.setattr(manager.sys, "stdout", SimpleNamespace(isatty=lambda: False))
    monkeypatch.setattr(manager, "_run", lambda command, cwd=None: pytest.fail("sudo should not run without a tty"))

    assert manager._try_install_linux_build_tools() is False


def test_linux_display_backend_check_accepts_x11_or_wayland(monkeypatch):
    calls = []
    monkeypatch.setattr(manager.shutil, "which", lambda name: "/usr/bin/pkg-config")

    def fake_run(command, **kwargs):
        calls.append(command[-1])
        return type("Result", (), {"returncode": 0 if command[-1] == "wayland-client" else 1})()

    monkeypatch.setattr(manager.subprocess, "run", fake_run)
    assert manager._linux_display_deps_available() is True
    assert calls == ["x11", "wayland-client"]


def test_setup_all_runs_python_and_native_bootstrap_in_order(monkeypatch):
    calls = []
    monkeypatch.setattr(manager, "ensure_skia_python", lambda: calls.append("skia"))
    monkeypatch.setattr(manager, "ensure_sdl3_runtime", lambda: "/cache/SDL3/libSDL3.so")
    monkeypatch.setattr(
        manager,
        "ensure_python_distribution",
        lambda name, version, **kwargs: calls.append((name, version)),
    )

    result = manager.setup_all(include_dev=True)
    assert calls == ["skia", ("pytest", "9.2.0")]
    assert result["SDL3"] == "3.4.20"
    assert result["skia-python"] == "144.1"
    assert result["pytest"] == "9.2.0"
