"""coord/queue.py: a merge queue for patches."""
import subprocess


def git(repo, *args, patch=None):
    return subprocess.run(["git", "-C", str(repo), *args], input=patch, capture_output=True, text=patch is None)


def drain(repo, patches, verify):
    """(merged, rejected), with main reset after a red patch."""
    merged, rejected = [], []
    for name, patch in patches:
        if git(repo, "apply", "--3way", "-", patch=patch.encode()).returncode:   # bytes: no newline rewriting
            git(repo, "reset", "--hard", "-q")
            rejected.append((name, "text conflict"))                     # the same lines edited twice
            continue
        report = verify(repo, rings=(1, 2, 3, 4))
        if report.ok:
            git(repo, "commit", "-qam", f"{name}: rings 1 to 4 pass on main")
            merged.append(name)
        else:
            git(repo, "reset", "--hard", "-q")                            # main stays green
            rejected.append((name, f"ring {report.ring}: {report.why}"))
    return merged, rejected
