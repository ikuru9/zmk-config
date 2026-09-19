#!/usr/bin/env python3
"""Shared build runner for local Docker and GitHub Actions."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import random
import shlex
import shutil
import subprocess
import sys
import uuid
from typing import Any

import yaml

from build_profiles import get_profile


REPO_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(shlex.quote(part) for part in cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def resolve_path(raw_path: str, *, base_dir: Path = REPO_ROOT) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    return (base_dir / path).resolve()


def read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_path, path)


def load_matrix_data(build_matrix_path: Path | None, build_matrix_json: str) -> list[dict[str, Any]]:
    if build_matrix_json.strip():
        data = json.loads(build_matrix_json)
    else:
        if build_matrix_path is None:
            raise ValueError("build_matrix_path is required when build_matrix_json is empty.")
        data = yaml.safe_load(build_matrix_path.read_text(encoding="utf-8")) or {}

    include = data.get("include", [])
    if not isinstance(include, list):
        source = str(build_matrix_path) if build_matrix_path else "<build_matrix_json>"
        raise ValueError(f"`include` must be a list in {source}")
    return [normalize_entry(entry) for entry in include if isinstance(entry, dict)]


def default_artifact_name(entry: dict[str, Any]) -> str:
    shield = str(entry.get("shield", "")).strip()
    board = str(entry.get("board", "")).strip().replace("/", "_")
    if shield:
        return f"{shield.replace(' ', '-')}-{board}-zmk"
    return f"{board}-zmk"


def artifact_name(entry: dict[str, Any]) -> str:
    name = str(entry.get("artifact-name") or entry.get("artifact_name") or "").strip()
    return name if name else default_artifact_name(entry)


def normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(entry)
    normalized_name = artifact_name(normalized)
    normalized["artifact-name"] = normalized_name
    normalized["artifact_name"] = normalized_name

    cmake_args = str(normalized.get("cmake-args") or normalized.get("cmake_args") or "").strip()
    normalized["cmake-args"] = cmake_args
    normalized["cmake_args"] = cmake_args
    return normalized


def filter_matrix(entries: list[dict[str, Any]], patterns: list[str]) -> list[dict[str, Any]]:
    if not patterns:
        return entries

    names = [artifact_name(entry) for entry in entries]
    unmatched_patterns = [
        pattern for pattern in patterns if not any(fnmatch.fnmatchcase(name, pattern) for name in names)
    ]
    if unmatched_patterns:
        raise ValueError(
            "artifact-name pattern(s) matched nothing: "
            + ", ".join(unmatched_patterns)
            + ". Use --list to see valid names."
        )

    return [
        entry
        for entry in entries
        if any(fnmatch.fnmatchcase(artifact_name(entry), pattern) for pattern in patterns)
    ]


def select_entries(
    *,
    build_matrix_path: Path | None,
    build_matrix_json: str,
    artifact_names: str,
    sample_count: int,
) -> list[dict[str, Any]]:
    entries = load_matrix_data(build_matrix_path, build_matrix_json)
    if not entries:
        source = build_matrix_path if build_matrix_path else "<build_matrix_json>"
        raise ValueError(f"No matrix entries found in {source}")

    patterns = [part.strip() for part in artifact_names.split(",") if part.strip()]
    selected = filter_matrix(entries, patterns)

    if sample_count:
        if sample_count < 1:
            raise ValueError("--sample-count must be >= 1")
        if sample_count > len(selected):
            raise ValueError(
                f"--sample-count {sample_count} exceeds selected entries ({len(selected)})."
            )
        selected = random.SystemRandom().sample(selected, sample_count)

    return selected


def write_github_outputs(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def ensure_config_copy(src_config: Path, dst_base: Path, config_name: str) -> Path:
    dst_config = dst_base / config_name
    if dst_config.exists():
        shutil.rmtree(dst_config)
    dst_config.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_config, dst_config)
    return dst_config


def stage_extra_modules_from_git(repo_root: Path, dst_base: Path) -> Path:
    staged_root = dst_base / "_extra_modules" / "workspace-module"
    if staged_root.exists():
        shutil.rmtree(staged_root)
    staged_root.mkdir(parents=True, exist_ok=True)

    try:
        listed = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return repo_root

    rel_paths = [p for p in listed.stdout.decode("utf-8", errors="surrogateescape").split("\0") if p]
    if not rel_paths:
        return repo_root

    for rel in rel_paths:
        src = repo_root / rel
        if not src.exists() or src.is_dir():
            continue
        dst = staged_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    return staged_root


def override_zmk_revision(config_dir: Path, revision: str) -> None:
    west_manifest = config_dir / "west.yml"
    if not west_manifest.exists():
        raise FileNotFoundError(f"Cannot override ZMK revision, missing: {west_manifest}")

    data = yaml.safe_load(west_manifest.read_text(encoding="utf-8")) or {}
    manifest = data.get("manifest")
    if not isinstance(manifest, dict):
        raise ValueError(f"Invalid west manifest format: {west_manifest}")

    projects = manifest.get("projects")
    if not isinstance(projects, list):
        raise ValueError(f"Invalid west projects list: {west_manifest}")

    updated = False
    for project in projects:
        if isinstance(project, dict) and project.get("name") == "zmk":
            project["revision"] = revision
            updated = True
            break

    if not updated:
        raise ValueError(f"No 'zmk' project entry found in {west_manifest}")

    west_manifest.write_text(
        yaml.safe_dump(data, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def remove_stale_git_locks(base_dir: Path) -> list[Path]:
    removed: list[Path] = []

    for git_dir in base_dir.rglob(".git"):
        if not git_dir.is_dir():
            continue
        for lock_file in git_dir.rglob("*.lock"):
            if not lock_file.is_file():
                continue
            lock_file.unlink(missing_ok=True)
            removed.append(lock_file)

    return removed


def ensure_west_ready(
    base_dir: Path,
    config_dir: Path,
    *,
    force_update: bool,
) -> str:
    west_manifest = config_dir / "west.yml"
    if not west_manifest.is_file():
        raise FileNotFoundError(f"West manifest not found: {west_manifest}")

    manifest_sha256 = hashlib.sha256(west_manifest.read_bytes()).hexdigest()
    west_dir = base_dir / ".west"
    workspace_marker = west_dir / "zmk-config-workspace.json"
    marker_data = read_json_object(workspace_marker)
    marker_valid = (
        marker_data is not None
        and marker_data.get("schema") == 1
        and marker_data.get("manifest_sha256") == manifest_sha256
        and isinstance(marker_data.get("generation"), str)
        and bool(marker_data["generation"])
    )
    needs_update = force_update or not west_dir.is_dir() or not marker_valid

    if not west_dir.is_dir():
        run(["west", "init", "-l", str(config_dir)], cwd=base_dir)
    else:
        run(["west", "config", "manifest.path", config_dir.name], cwd=base_dir)

    if not needs_update:
        run(["west", "zephyr-export"], cwd=base_dir)
        return marker_data["generation"]

    workspace_marker.unlink(missing_ok=True)
    try:
        run(["west", "update", "--fetch-opt=--filter=tree:0"], cwd=base_dir)
    except subprocess.CalledProcessError:
        removed = remove_stale_git_locks(base_dir)
        if not removed:
            raise
        print(
            f"Detected stale git lock files. Removed {len(removed)} lock file(s) and retrying west update.",
            flush=True,
        )
        run(["west", "update", "--fetch-opt=--filter=tree:0"], cwd=base_dir)

    run(["west", "zephyr-export"], cwd=base_dir)
    workspace_state = {
        "schema": 1,
        "manifest_sha256": manifest_sha256,
        "generation": uuid.uuid4().hex,
    }
    write_json_atomic(workspace_marker, workspace_state)
    return workspace_state["generation"]


def detect_physical_cores() -> int | None:
    try:
        lscpu = subprocess.run(
            ["lscpu", "-p=CORE,SOCKET"],
            check=True,
            capture_output=True,
            text=True,
        )
        core_pairs: set[tuple[int, int]] = set()
        for line in lscpu.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 2:
                continue
            if parts[0].isdigit() and parts[1].isdigit():
                core_pairs.add((int(parts[0]), int(parts[1])))
        if core_pairs:
            return len(core_pairs)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        try:
            core_pairs: set[tuple[int, int]] = set()
            physical_id = 0
            core_id = None
            for raw_line in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw_line.strip()
                if not line:
                    if core_id is not None:
                        core_pairs.add((physical_id, core_id))
                    physical_id = 0
                    core_id = None
                    continue
                if ":" not in line:
                    continue
                key, value = [part.strip() for part in line.split(":", 1)]
                if key == "physical id" and value.isdigit():
                    physical_id = int(value)
                elif key == "core id" and value.isdigit():
                    core_id = int(value)
            if core_id is not None:
                core_pairs.add((physical_id, core_id))
            if core_pairs:
                return len(core_pairs)
        except OSError:
            pass

    return None


def prepare_workspace(
    *,
    profile_name: str,
    config_path: Path,
    base_dir: Path | None,
    force_update: bool,
    zmk_revision_override: str,
) -> tuple[Path, Path, Path | None, str]:
    profile = get_profile(profile_name)
    src_config_path = config_path
    if not src_config_path.exists():
        raise FileNotFoundError(f"Config path not found: {src_config_path}")

    effective_base_dir = base_dir if base_dir is not None else Path(profile["base_dir"]).resolve()

    if (REPO_ROOT / "zephyr" / "module.yml").exists():
        config_dir = ensure_config_copy(src_config_path, effective_base_dir, src_config_path.name)
        extra_modules_dir: Path | None = stage_extra_modules_from_git(REPO_ROOT, effective_base_dir)
    else:
        effective_base_dir = REPO_ROOT
        config_dir = src_config_path
        extra_modules_dir = None

    revision = zmk_revision_override.strip() or profile["zmk_revision"]
    if revision:
        override_zmk_revision(config_dir, revision)

    workspace_generation = ensure_west_ready(
        effective_base_dir,
        config_dir,
        force_update=force_update,
    )
    return effective_base_dir, config_dir, extra_modules_dir, workspace_generation


def build_signature(
    entry: dict[str, Any],
    *,
    profile_name: str,
    workspace_generation: str,
    base_dir: Path,
    config_dir: Path,
    extra_modules_dir: Path | None,
) -> dict[str, Any]:
    profile = get_profile(profile_name)
    snippet = str(entry.get("snippet", "")).strip()
    cmake_args = str(entry.get("cmake-args") or entry.get("cmake_args") or "").strip()

    return {
        "schema": 1,
        "profile_name": profile["profile"],
        "profile_cache_key": profile["cache_key"],
        "container_image": profile["container_image"],
        "workspace_generation": workspace_generation,
        "artifact_name": artifact_name(entry),
        "board": str(entry.get("board", "")).strip(),
        "shield": str(entry.get("shield", "")).strip(),
        "snippets": shlex.split(snippet),
        "cmake_args": shlex.split(cmake_args),
        "source_dir": str((base_dir / "zmk" / "app").resolve()),
        "config_dir": str(config_dir.resolve()),
        "extra_modules_dir": (
            str(extra_modules_dir.resolve()) if extra_modules_dir is not None else None
        ),
    }


def build_entry(
    *,
    entry: dict[str, Any],
    profile_name: str,
    workspace_generation: str,
    base_dir: Path,
    build_root: Path,
    output_dir: Path,
    config_dir: Path,
    fallback_binary: str,
    extra_modules_dir: Path | None,
    pristine: bool,
    build_jobs: int,
) -> Path:
    signature = build_signature(
        entry,
        profile_name=profile_name,
        workspace_generation=workspace_generation,
        base_dir=base_dir,
        config_dir=config_dir,
        extra_modules_dir=extra_modules_dir,
    )
    board = signature["board"]
    if not board:
        raise ValueError(f"Missing board in matrix entry: {entry}")
    if build_jobs < 1:
        raise ValueError("build_jobs must be >= 1")

    artifact = signature["artifact_name"]
    build_dir = build_root / artifact
    signature_path = build_dir / ".zmk-build-entry.json"
    build_root.mkdir(parents=True, exist_ok=True)

    reuse_build = (
        not pristine
        and (build_dir / "CMakeCache.txt").is_file()
        and (build_dir / "build.ninja").is_file()
        and read_json_object(signature_path) == signature
    )

    if reuse_build:
        cmd = ["west", "build", "-d", str(build_dir), f"-o=-j{build_jobs}"]
    else:
        cmd = [
            "west",
            "build",
            "-p=always",
            "-s",
            "zmk/app",
            "-d",
            str(build_dir),
            "-b",
            board,
            f"-o=-j{build_jobs}",
        ]
        for snippet_name in signature["snippets"]:
            cmd.extend(["-S", snippet_name])
        cmd.append("--")
        cmd.append(f"-DZMK_CONFIG={config_dir}")
        if signature["shield"]:
            cmd.append(f"-DSHIELD={signature['shield']}")
        if extra_modules_dir is not None:
            cmd.append(f"-DZMK_EXTRA_MODULES={extra_modules_dir}")
        cmd.extend(signature["cmake_args"])

    run(cmd, cwd=base_dir)
    if not reuse_build:
        write_json_atomic(signature_path, signature)

    zephyr_out = build_dir / "zephyr"
    uf2 = zephyr_out / "zmk.uf2"
    fallback = zephyr_out / f"zmk.{fallback_binary}"

    output_dir.mkdir(parents=True, exist_ok=True)
    if uf2.exists():
        dst = output_dir / f"{artifact}.uf2"
        shutil.copy2(uf2, dst)
        return dst
    if fallback.exists():
        dst = output_dir / f"{artifact}.{fallback_binary}"
        shutil.copy2(fallback, dst)
        return dst

    raise FileNotFoundError(
        f"No build artifact found for {artifact} (expected zmk.uf2 or zmk.{fallback_binary})."
    )


def build_entries(
    *,
    entries: list[dict[str, Any]],
    profile_name: str,
    workspace_generation: str,
    base_dir: Path,
    build_root: Path,
    output_dir: Path,
    config_dir: Path,
    fallback_binary: str,
    extra_modules_dir: Path | None,
    pristine: bool,
    jobs: int | None,
) -> int:
    logical_cores = max(1, os.cpu_count() or 1)
    detected_physical_cores = detect_physical_cores()
    physical_cores = logical_cores if detected_physical_cores is None else detected_physical_cores
    physical_cores = max(1, min(physical_cores, logical_cores))
    physical_core_cap = physical_cores
    default_auto_cap = max(1, physical_cores // 2)

    if jobs is None:
        max_workers = min(len(entries), default_auto_cap)
        print(
            f"Auto-selected parallel jobs: {max_workers} "
            f"(entries={len(entries)}, logical_cores={logical_cores}, "
            f"physical_cores={physical_cores}, default_cap={default_auto_cap}).",
            flush=True,
        )
    else:
        if jobs < 1:
            raise ValueError("--jobs must be >= 1")
        max_workers = min(jobs, len(entries))
        if max_workers > physical_core_cap:
            print(
                f"--jobs {jobs} exceeds physical core count ({physical_core_cap}); "
                f"capping to {physical_core_cap}.",
                flush=True,
            )
            max_workers = physical_core_cap

    build_jobs = max(1, physical_core_cap // max_workers)
    print(
        "Build concurrency: "
        f"matrix_workers={max_workers}, "
        f"ninja_jobs_per_target={build_jobs}, "
        f"total_job_cap={max_workers * build_jobs}, "
        f"physical_cores={physical_core_cap}.",
        flush=True,
    )

    produced: list[Path] = []
    if max_workers == 1:
        for entry in entries:
            name = artifact_name(entry)
            print(f"\n=== Building {name} ===", flush=True)
            out = build_entry(
                entry=entry,
                profile_name=profile_name,
                workspace_generation=workspace_generation,
                base_dir=base_dir,
                build_root=build_root,
                output_dir=output_dir,
                config_dir=config_dir,
                fallback_binary=fallback_binary,
                extra_modules_dir=extra_modules_dir,
                pristine=pristine,
                build_jobs=build_jobs,
            )
            produced.append(out)
            print(f"Built artifact: {out}", flush=True)
    else:
        print(
            f"Running {len(entries)} build(s) with up to {max_workers} parallel job(s).",
            flush=True,
        )
        build_failures: list[tuple[str, Exception]] = []
        future_to_name: dict[Any, str] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for entry in entries:
                name = artifact_name(entry)
                print(f"\n=== Queueing {name} ===", flush=True)
                future = executor.submit(
                    build_entry,
                    entry=entry,
                    profile_name=profile_name,
                    workspace_generation=workspace_generation,
                    base_dir=base_dir,
                    build_root=build_root,
                    output_dir=output_dir,
                    config_dir=config_dir,
                    fallback_binary=fallback_binary,
                    extra_modules_dir=extra_modules_dir,
                    pristine=pristine,
                    build_jobs=build_jobs,
                )
                future_to_name[future] = name

            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    out = future.result()
                except Exception as exc:  # noqa: BLE001
                    build_failures.append((name, exc))
                    print(f"Build failed for {name}: {exc}", file=sys.stderr, flush=True)
                else:
                    produced.append(out)
                    print(f"Built artifact: {out}", flush=True)

        if build_failures:
            print("\nBuild completed with failures:", file=sys.stderr, flush=True)
            for name, exc in build_failures:
                print(f"- {name}: {exc}", file=sys.stderr, flush=True)
            return 1

    print("\nBuild complete.", flush=True)
    for out in produced:
        print(f"- {out}")
    return 0


def add_common_matrix_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--build-matrix-path", default="build.yaml")
    parser.add_argument("--build-matrix-json", default="")
    parser.add_argument(
        "--artifact-names",
        default="",
        help=(
            "Comma-separated artifact-name values or wildcard patterns "
            "(e.g. 'totem_*', '*_reset')."
        ),
    )


def add_common_build_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", default="stable", help="Build profile: stable.")
    parser.add_argument("--config-path", default="config")
    parser.add_argument("--fallback-binary", default="bin")
    parser.add_argument("--output-dir", default="firmware")
    parser.add_argument("--build-root", default=".build/local/build")
    parser.add_argument("--base-dir", default="")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Refresh west projects even when the staged manifest is unchanged.",
    )
    parser.add_argument(
        "--pristine",
        action="store_true",
        help="Discard the selected targets' build state before compiling.",
    )
    parser.add_argument(
        "--zmk-revision-override",
        default="",
        help="Optional override for the zmk project revision in config/west.yml.",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    select = subparsers.add_parser("select-matrix", help="Filter and normalize build matrix entries.")
    add_common_matrix_args(select)
    select.add_argument("--sample-count", type=int, default=0)
    select.add_argument("--list", action="store_true")
    select.add_argument("--github-output", default="")

    build_many = subparsers.add_parser("build-many", help="Build a filtered matrix of firmware targets.")
    add_common_matrix_args(build_many)
    add_common_build_args(build_many)
    build_many.add_argument(
        "--all",
        action="store_true",
        help="Build every matrix entry. Cannot be combined with --artifact-names.",
    )
    build_many.add_argument(
        "--jobs",
        type=int,
        default=None,
        help=(
            "Number of matrix entries to build in parallel. "
            "Default: auto (min(selected entries, max(1, physical core count // 2)))."
        ),
    )
    build_many.add_argument("--list", action="store_true")

    build_one = subparsers.add_parser("build-one", help="Build exactly one matrix entry from JSON.")
    add_common_build_args(build_one)
    build_one.add_argument("--entry-json", required=True)

    return parser.parse_args(argv)


def command_select_matrix(args: argparse.Namespace) -> int:
    build_matrix_path = resolve_path(args.build_matrix_path)
    if not args.build_matrix_json and not build_matrix_path.exists():
        raise FileNotFoundError(f"Build matrix path not found: {build_matrix_path}")

    entries = select_entries(
        build_matrix_path=build_matrix_path if not args.build_matrix_json else None,
        build_matrix_json=args.build_matrix_json,
        artifact_names=args.artifact_names,
        sample_count=args.sample_count,
    )

    if args.list:
        print("Selected artifact-name values:")
        for entry in entries:
            print(f"- {artifact_name(entry)}")

    matrix_json = json.dumps({"include": entries}, separators=(",", ":"))
    if args.github_output:
        write_github_outputs(
            Path(args.github_output),
            {
                "build_matrix": matrix_json,
                "selected_count": str(len(entries)),
            },
        )
    print(matrix_json)
    return 0


def command_build_many(args: argparse.Namespace) -> int:
    has_artifact_names = bool(args.artifact_names.strip())
    if args.all and has_artifact_names:
        raise ValueError("--all cannot be combined with --artifact-names")
    if not args.list and not args.all and not has_artifact_names:
        raise ValueError("Specify --artifact-names PATTERN or --all.")

    build_matrix_path = resolve_path(args.build_matrix_path)
    if not args.build_matrix_json and not build_matrix_path.exists():
        raise FileNotFoundError(f"Build matrix path not found: {build_matrix_path}")

    entries = select_entries(
        build_matrix_path=build_matrix_path if not args.build_matrix_json else None,
        build_matrix_json=args.build_matrix_json,
        artifact_names=args.artifact_names,
        sample_count=0,
    )

    if args.list:
        print("Available artifact-name values:")
        for entry in entries:
            print(f"- {artifact_name(entry)}")
        return 0

    config_path = resolve_path(args.config_path)
    build_root = resolve_path(args.build_root)
    output_dir = resolve_path(args.output_dir)
    base_dir = Path(args.base_dir).resolve() if args.base_dir else None

    effective_base_dir, config_dir, extra_modules_dir, workspace_generation = prepare_workspace(
        profile_name=args.profile,
        config_path=config_path,
        base_dir=base_dir,
        force_update=args.update,
        zmk_revision_override=args.zmk_revision_override,
    )
    return build_entries(
        entries=entries,
        profile_name=args.profile,
        workspace_generation=workspace_generation,
        base_dir=effective_base_dir,
        build_root=build_root,
        output_dir=output_dir,
        config_dir=config_dir,
        fallback_binary=args.fallback_binary,
        extra_modules_dir=extra_modules_dir,
        pristine=args.pristine,
        jobs=args.jobs,
    )


def command_build_one(args: argparse.Namespace) -> int:
    entry = normalize_entry(json.loads(args.entry_json))
    config_path = resolve_path(args.config_path)
    build_root = resolve_path(args.build_root)
    output_dir = resolve_path(args.output_dir)
    base_dir = Path(args.base_dir).resolve() if args.base_dir else None

    effective_base_dir, config_dir, extra_modules_dir, workspace_generation = prepare_workspace(
        profile_name=args.profile,
        config_path=config_path,
        base_dir=base_dir,
        force_update=args.update,
        zmk_revision_override=args.zmk_revision_override,
    )

    logical_cores = max(1, os.cpu_count() or 1)
    detected_physical_cores = detect_physical_cores()
    physical_cores = logical_cores if detected_physical_cores is None else detected_physical_cores
    build_jobs = max(1, min(physical_cores, logical_cores))

    print(f"\n=== Building {artifact_name(entry)} ===", flush=True)
    out = build_entry(
        entry=entry,
        profile_name=args.profile,
        workspace_generation=workspace_generation,
        base_dir=effective_base_dir,
        build_root=build_root,
        output_dir=output_dir,
        config_dir=config_dir,
        fallback_binary=args.fallback_binary,
        extra_modules_dir=extra_modules_dir,
        pristine=args.pristine,
        build_jobs=build_jobs,
    )
    print(f"Built artifact: {out}", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "select-matrix":
        return command_select_matrix(args)
    if args.command == "build-many":
        return command_build_many(args)
    if args.command == "build-one":
        return command_build_one(args)
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}", file=sys.stderr)
        raise
