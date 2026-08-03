"""Isolated game worktree creation and pre-verification patch enforcement."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

from .repair_experiment import PatchEvidence, RepairExperimentPlan


class RepairWorktreeError(RuntimeError):
    """Raised when isolation or a locked patch boundary is violated."""


PROTECTED_REPAIR_PATHS = ("scripts/tools/ValidateEconomyRules.gd",)


def create_repair_worktree(
    *,
    source_repository: str | Path,
    destination: str | Path,
    baseline_commit: str,
    branch: str,
) -> Path:
    """Create a new branch/worktree at the exact locked baseline commit."""

    source = Path(source_repository).resolve()
    target = Path(destination).resolve()
    if target.exists():
        raise RepairWorktreeError("repair worktree destination already exists")
    if _git_optional(source, "rev-parse", "--is-inside-work-tree") != "true":
        raise RepairWorktreeError("source game repository is not a Git worktree")
    resolved = _git(source, "rev-parse", f"{baseline_commit}^{{commit}}")
    if resolved != baseline_commit:
        raise RepairWorktreeError("baseline commit does not resolve exactly")
    if _git_optional(source, "show-ref", "--verify", f"refs/heads/{branch}"):
        raise RepairWorktreeError("repair branch already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    _run_git(source, "worktree", "add", "-b", branch, str(target), baseline_commit)
    if _git(target, "rev-parse", "HEAD") != baseline_commit:
        raise RepairWorktreeError("created worktree is not at the locked baseline")
    if _git(target, "status", "--porcelain", "--untracked-files=all"):
        raise RepairWorktreeError("created repair worktree is not clean")
    return target


def validate_and_save_patch(
    *,
    worktree: str | Path,
    plan: RepairExperimentPlan,
    patch_path: str | Path,
    project_root: str | Path,
    protected_paths: tuple[str, ...] = (),
) -> PatchEvidence:
    """Validate a committed candidate and save its diff before outcome tests."""

    worktree_path = Path(worktree).resolve()
    project = Path(project_root).resolve()
    if _git(worktree_path, "status", "--porcelain", "--untracked-files=all"):
        raise RepairWorktreeError("candidate worktree must be committed and clean")
    head = _git(worktree_path, "rev-parse", "HEAD")
    if head == plan.baseline_game_commit:
        raise RepairWorktreeError("candidate patch has no commit")
    if not _is_ancestor(worktree_path, plan.baseline_game_commit, head):
        raise RepairWorktreeError("candidate patch does not descend from locked baseline")
    if (
        _git(worktree_path, "rev-parse", f"{plan.baseline_game_commit}^{{tree}}")
        != plan.baseline_game_tree
    ):
        raise RepairWorktreeError("candidate baseline tree differs from locked plan")
    names = _git_lines(
        worktree_path,
        "diff",
        "--name-only",
        "--diff-filter=ACDMRTUXB",
        f"{plan.baseline_game_commit}..{head}",
    )
    if not names:
        raise RepairWorktreeError("candidate patch has no changed paths")
    deleted = _git_lines(
        worktree_path,
        "diff",
        "--name-only",
        "--diff-filter=D",
        f"{plan.baseline_game_commit}..{head}",
    )
    if deleted:
        raise RepairWorktreeError("candidate patch may not delete game files")
    if len(names) > plan.maximum_changed_files:
        raise RepairWorktreeError("candidate patch exceeds changed-file budget")
    allowed = set(plan.allowlist)
    for name in names:
        if name in protected_paths:
            raise RepairWorktreeError(f"candidate changes protected validator: {name}")
        _safe_relative(name)
        if name not in allowed:
            raise RepairWorktreeError(f"candidate path is outside allowlist: {name}")
        candidate = worktree_path / name
        if candidate.is_symlink():
            raise RepairWorktreeError(f"candidate path is a symbolic link: {name}")
    added, deleted_lines = _numstat(worktree_path, plan.baseline_game_commit, head)
    if added + deleted_lines > plan.maximum_changed_lines:
        raise RepairWorktreeError("candidate patch exceeds changed-line budget")
    patch = _git_bytes(
        worktree_path,
        "diff",
        "--binary",
        "--full-index",
        plan.baseline_game_commit,
        head,
        "--",
        *names,
    )
    if b"GIT binary patch" in patch or b"Binary files " in patch:
        raise RepairWorktreeError("binary repair patches are forbidden")
    text = patch.decode("utf-8", errors="strict")
    if _contains_seed_special_case(text, (*plan.fixed_seeds, *plan.holdout_seeds)):
        raise RepairWorktreeError("candidate patch contains a seed-specific branch")
    destination = Path(patch_path)
    if not destination.is_absolute():
        destination = project / destination
    destination = destination.resolve()
    try:
        relative = destination.relative_to(project).as_posix()
    except ValueError as exc:
        raise RepairWorktreeError("patch evidence must live under project root") from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(destination, patch)
    return PatchEvidence(
        baseline_commit=plan.baseline_game_commit,
        patched_commit=head,
        patched_tree=_git(worktree_path, "rev-parse", "HEAD^{tree}"),
        patch_path=relative,
        patch_sha256=hashlib.sha256(patch).hexdigest(),
        mechanism_class=plan.mechanism_class,
        modified_paths=tuple(names),
        changed_files=len(names),
        added_lines=added,
        deleted_lines=deleted_lines,
    )


def validate_verification_worktrees(
    *,
    baseline_game: str | Path,
    patched_game: str | Path,
    plan: RepairExperimentPlan,
    patch: PatchEvidence,
    project_root: str | Path,
    protected_paths: tuple[str, ...] = PROTECTED_REPAIR_PATHS,
) -> None:
    """Bind caller paths, Git identities, and patch bytes before any outcome run."""

    baseline = Path(baseline_game).resolve()
    patched = Path(patched_game).resolve()
    project = Path(project_root).resolve()
    if baseline == patched:
        raise RepairWorktreeError("baseline and patched worktrees must be distinct")
    for label, worktree in (("baseline", baseline), ("patched", patched)):
        if _git_optional(worktree, "rev-parse", "--is-inside-work-tree") != "true":
            raise RepairWorktreeError(f"{label} game is not a Git worktree")
        if _git(worktree, "status", "--porcelain", "--untracked-files=all"):
            raise RepairWorktreeError(f"{label} game worktree is not clean")
    if _git(baseline, "rev-parse", "HEAD") != plan.baseline_game_commit:
        raise RepairWorktreeError("baseline worktree HEAD differs from locked plan")
    if _git(baseline, "rev-parse", "HEAD^{tree}") != plan.baseline_game_tree:
        raise RepairWorktreeError("baseline worktree tree differs from locked plan")
    if patch.baseline_commit != plan.baseline_game_commit:
        raise RepairWorktreeError("patch baseline differs from locked plan")
    if _git(patched, "rev-parse", "HEAD") != patch.patched_commit:
        raise RepairWorktreeError("patched worktree HEAD differs from patch evidence")
    if _git(patched, "rev-parse", "HEAD^{tree}") != patch.patched_tree:
        raise RepairWorktreeError("patched worktree tree differs from patch evidence")
    if not _is_ancestor(patched, plan.baseline_game_commit, patch.patched_commit):
        raise RepairWorktreeError("patched worktree does not descend from locked baseline")
    names = tuple(
        _git_lines(
            patched,
            "diff",
            "--name-only",
            "--diff-filter=ACDMRTUXB",
            f"{plan.baseline_game_commit}..{patch.patched_commit}",
        )
    )
    if names != patch.modified_paths:
        raise RepairWorktreeError("actual patched paths differ from patch evidence")
    protected = sorted(set(names) & set(protected_paths))
    if protected:
        raise RepairWorktreeError(f"candidate changes protected validator: {protected[0]}")
    added, deleted = _numstat(patched, plan.baseline_game_commit, patch.patched_commit)
    if (added, deleted) != (patch.added_lines, patch.deleted_lines):
        raise RepairWorktreeError("actual line counts differ from patch evidence")
    diff = _git_bytes(
        patched,
        "diff",
        "--binary",
        "--full-index",
        plan.baseline_game_commit,
        patch.patched_commit,
        "--",
        *names,
    )
    evidence_path = (project / patch.patch_path).resolve()
    try:
        evidence_path.relative_to(project)
    except ValueError as exc:
        raise RepairWorktreeError("patch evidence must live under project root") from exc
    if not evidence_path.is_file():
        raise RepairWorktreeError("patch evidence file is unavailable")
    evidence = evidence_path.read_bytes()
    if evidence != diff or hashlib.sha256(evidence).hexdigest() != patch.patch_sha256:
        raise RepairWorktreeError("patch bytes or hash differ from verified worktree diff")


def _numstat(worktree: Path, baseline: str, head: str) -> tuple[int, int]:
    added = deleted = 0
    for line in _git_lines(worktree, "diff", "--numstat", baseline, head):
        parts = line.split("\t", 2)
        if len(parts) != 3 or parts[0] == "-" or parts[1] == "-":
            raise RepairWorktreeError("candidate patch contains non-text numstat")
        added += int(parts[0])
        deleted += int(parts[1])
    return added, deleted


def _contains_seed_special_case(text: str, seeds: tuple[int, ...]) -> bool:
    additions = "\n".join(
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for seed in seeds:
        value = re.escape(str(seed))
        if re.search(rf"(?i)seed[^\n]{{0,80}}\b{value}\b|\b{value}\b[^\n]{{0,80}}seed", additions):
            return True
    return False


def _safe_relative(value: str) -> None:
    path = PurePosixPath(value.replace("\\", "/"))
    if not value or path.is_absolute() or ".." in path.parts:
        raise RepairWorktreeError("candidate patch contains an unsafe path")


def _atomic_write(path: Path, content: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary).replace(path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def _is_ancestor(repository: Path, baseline: str, head: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", baseline, head],
            cwd=repository,
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _run_git(repository: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(["git", *args], cwd=repository, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.decode("utf-8", errors="replace")[-300:]
        raise RepairWorktreeError(f"git command failed: {message}") from exc


def _git(repository: Path, *args: str) -> str:
    return _run_git(repository, *args).stdout.decode().strip()


def _git_optional(repository: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repository, check=False, capture_output=True, text=True
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _git_lines(repository: Path, *args: str) -> list[str]:
    output = _git(repository, *args)
    return [line for line in output.splitlines() if line]


def _git_bytes(repository: Path, *args: str) -> bytes:
    return _run_git(repository, *args).stdout


__all__ = [
    "PROTECTED_REPAIR_PATHS",
    "RepairWorktreeError",
    "create_repair_worktree",
    "validate_and_save_patch",
    "validate_verification_worktrees",
]
