#!/usr/bin/env python3
"""QClaw Soul Sync — 同步 Agent 定义、知识库和技能到 GitHub"""
import argparse, json, os, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path

DATA_ROOT = r"D:\wujm\QClaw\data"
SKILLS_ROOT = r"C:\Users\adigle\.qclaw\skills"
REPO = "dpdp2020/QClaw_Soul"
SIZE_LIMIT = 50 * 1024 * 1024  # 50MB

AGENT_MAP = {
    "main": {
        "src_dir": "workspace",
        "files": ["SOUL.md", "AGENTS.md", "IDENTITY.md", "USER.md", "TOOLS.md"],
        "dst_dir": "agents/main"
    },
    "finance-learner": {
        "src_dir": "workspace-finance-learner",
        "files": ["SOUL.md", "IDENTITY.md", "TOOLS.md", "USER.md"],
        "dst_dir": "agents/finance-learner",
        "kb_src": "knowledge-base",
        "kb_dst": "knowledge-base"
    },
    "market-news": {
        "src_dir": "workspace-market-news",
        "files": ["SOUL.md", "IDENTITY.md", "RULES.md", "TOOLS.md", "USER.md"],
        "dst_dir": "agents/market-news"
    },
    "strategy-analyst": {
        "src_dir": "workspace-strategy-analyst",
        "files": ["SOUL.md", "IDENTITY.md", "STRATEGY.md", "TOOLS.md", "USER.md"],
        "dst_dir": "agents/strategy-analyst"
    },
    "trader": {
        "src_dir": "workspace-trader",
        "files": ["SOUL.md", "IDENTITY.md", "RULES.md", "API.md", "TOOLS.md", "USER.md"],
        "dst_dir": "agents/trader"
    },
    "media-operator": {
        "src_dir": "workspace-media-operator",
        "files": ["SOUL.md", "IDENTITY.md", "CAST.md", "PRODUCTION.md", "SCENE.md", "TOOLS.md", "USER.md"],
        "dst_dir": "agents/media-operator"
    },
    "media-producer": {
        "src_dir": "workspace-media-producer",
        "files": ["SOUL.md", "IDENTITY.md", "TOOLS.md", "USER.md"],
        "dst_dir": "agents/media-producer"
    },
    "media-publisher": {
        "src_dir": "workspace-media-publisher",
        "files": ["SOUL.md", "IDENTITY.md", "TOOLS.md", "USER.md"],
        "dst_dir": "agents/media-publisher"
    },
}

def run_git(args, cwd=None):
    r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r

def fmt_size(size):
    if size > 1024*1024: return f"{size/1024/1024:.1f}MB"
    if size > 1024: return f"{size/1024:.1f}KB"
    return f"{size}B"


def _cleanup_workdir(work_dir):
    """清理临时目录，忽略 Windows 文件锁导致的失败"""
    for _ in range(3):
        try:
            if os.path.exists(work_dir):
                shutil.rmtree(work_dir, onerror=_remove_readonly)
            return
        except Exception:
            time.sleep(1)

def _remove_readonly(func, path, _exc):
    """Windows 下处理只读文件"""
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)


def sync_skills(token, dry_run=False):
    """将本地 skills/ 目录同步到仓库的 skills/ 目录"""
    work_dir = os.path.join(DATA_ROOT, "workspace", "_soul_sync_tmp")

    report = {"added": [], "modified": [], "skipped": [], "errors": []}

    # 获取所有本地技能目录
    skills_src_root = SKILLS_ROOT

    if dry_run:
        # 预览模式：只扫描本地，不克隆远程仓库
        print("[DRY RUN] Preview mode — listing local skill files only")
        for skill_name in sorted(os.listdir(skills_src_root)):
            if not os.path.isdir(os.path.join(skills_src_root, skill_name)):
                continue
            if skill_name.startswith("."):
                continue
            src_dir = os.path.join(skills_src_root, skill_name)
            for root, dirs, files in os.walk(src_dir):
                for fname in files:
                    src_file = os.path.join(root, fname)
                    rel_path = os.path.relpath(src_file, src_dir)
                    file_size = os.path.getsize(src_file)
                    if file_size > SIZE_LIMIT:
                        report["skipped"].append(f"skills/{skill_name}/{rel_path} ({fmt_size(file_size)})")
                    else:
                        report["added"].append(f"skills/{skill_name}/{rel_path}")
        return report, [f for f in report["added"] + report["skipped"]]

    # 正式同步：克隆 → 复制 → 推送 → 清理
    _cleanup_workdir(work_dir)
    print(f"[INFO] Cloning {REPO}...")
    r = run_git(["clone", f"https://x-access-token:{token}@github.com/{REPO}.git", work_dir])
    if r.returncode != 0 and "Cloning into" not in (r.stderr + r.stdout):
        print(f"[ERROR] Clone failed: {r.stderr}")
        sys.exit(1)

    skills_dst_root = os.path.join(work_dir, "skills")
    os.makedirs(skills_dst_root, exist_ok=True)

    for skill_name in sorted(os.listdir(skills_src_root)):
        if not os.path.isdir(os.path.join(skills_src_root, skill_name)):
            continue
        if skill_name.startswith("."):
            continue

        src_dir = os.path.join(skills_src_root, skill_name)
        dst_dir = os.path.join(skills_dst_root, skill_name)

        print(f"  Syncing skill: {skill_name} ...")
        os.makedirs(dst_dir, exist_ok=True)

        for root, dirs, files in os.walk(src_dir):
            for fname in files:
                # 跳过敏感文件
                if fname in ("config.json", "_meta.json") or fname.endswith(".pyc"):
                    continue
                src_file = os.path.join(root, fname)
                rel_path = os.path.relpath(src_file, src_dir)
                dst_file = os.path.join(dst_dir, rel_path)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)

                file_size = os.path.getsize(src_file)
                if file_size > SIZE_LIMIT:
                    report["skipped"].append(f"skills/{skill_name}/{rel_path} ({fmt_size(file_size)})")
                    continue
                shutil.copy2(src_file, dst_file)
                report["added"].append(f"skills/{skill_name}/{rel_path}")

    # Git commit & push
    run_git(["add", "-A"], cwd=work_dir)
    r = run_git(["status", "--porcelain"], cwd=work_dir)
    changed = [l[3:].strip() for l in r.stdout.strip().split("\n") if l.strip() and l[0] in "MADRC"]

    if not changed:
        print("[OK] No skill changes to sync")
        _cleanup_workdir(work_dir)
        return report, changed

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = f"sync: update skills from local qclaw-soul-sync - {ts}"
    run_git(["config", "user.name", "dpdp2020"], cwd=work_dir)
    run_git(["config", "user.email", "dpdp2020@users.noreply.github.com"], cwd=work_dir)
    r = run_git(["commit", "-m", msg], cwd=work_dir)
    if r.returncode != 0:
        print(f"[ERROR] Commit failed: {r.stderr}")
    r = run_git(["push", "origin", "main"], cwd=work_dir)
    if r.returncode != 0 and "Everything up-to-date" not in (r.stderr + r.stdout):
        print(f"[ERROR] Push failed: {r.stderr}")
        sys.exit(1)
    print(f"[OK] Pushed: {msg}")
    print(f"[OK] Repo: https://github.com/{REPO}")

    _cleanup_workdir(work_dir)
    return report, changed


def sync(agent_filter, skill_filter, token, dry_run=False):
    work_dir = os.path.join(DATA_ROOT, "workspace", "_soul_sync_tmp")

    # Clone
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    print(f"[INFO] Cloning {REPO}...")
    r = run_git(["clone", f"https://x-access-token:{token}@github.com/{REPO}.git", work_dir])
    if r.returncode != 0 and "Cloning into" not in (r.stderr + r.stdout):
        print(f"[ERROR] Clone failed: {r.stderr}")
        sys.exit(1)

    report = {"added": [], "modified": [], "skipped": [], "errors": []}

    agents = {agent_filter: AGENT_MAP[agent_filter]} if agent_filter and agent_filter in AGENT_MAP else AGENT_MAP

    # Also handle knowledge-base only mode
    if agent_filter == "knowledge-base":
        agents = {"finance-learner": AGENT_MAP["finance-learner"]}

    for name, cfg in agents.items():
        src_base = os.path.join(DATA_ROOT, cfg["src_dir"])

        # Sync agent definition files
        for fname in cfg["files"]:
            src = os.path.join(src_base, fname)
            dst = os.path.join(work_dir, cfg["dst_dir"], fname)
            if not os.path.exists(src):
                report["errors"].append(f"Missing: {name}/{fname}")
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.getsize(src) > SIZE_LIMIT:
                report["skipped"].append(f"{cfg['dst_dir']}/{fname} ({fmt_size(os.path.getsize(src))})")
                continue
            shutil.copy2(src, dst)
            report["added"].append(f"{cfg['dst_dir']}/{fname}")

        # Sync knowledge-base if defined
        if "kb_src" in cfg:
            kb_src = os.path.join(src_base, cfg["kb_src"])
            kb_dst = os.path.join(work_dir, cfg["kb_dst"])
            if os.path.exists(kb_src):
                os.makedirs(kb_dst, exist_ok=True)
                for f in os.listdir(kb_src):
                    src_f = os.path.join(kb_src, f)
                    dst_f = os.path.join(kb_dst, f)
                    if os.path.isdir(src_f):
                        continue
                    if os.path.getsize(src_f) > SIZE_LIMIT:
                        report["skipped"].append(f"{cfg['kb_dst']}/{f} ({fmt_size(os.path.getsize(src_f))})")
                        continue
                    shutil.copy2(src_f, dst_f)
                    report["added"].append(f"{cfg['kb_dst']}/{f}")

    # Git commit & push
    run_git(["add", "-A"], cwd=work_dir)
    r = run_git(["status", "--porcelain"], cwd=work_dir)
    changed = [l[3:].strip() for l in r.stdout.strip().split("\n") if l.strip() and l[0] in "MADRC"]

    if not changed:
        print("[OK] No changes to sync")
        shutil.rmtree(work_dir)
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = f"sync: update agent definitions & knowledge base - {ts}"
    if dry_run:
        print(f"[DRY RUN] Would commit: {msg}")
        print(f"[DRY RUN] Changed files: {len(changed)}")
        for f in changed:
            print(f"  - {f}")
    else:
        run_git(["config", "user.name", "dpdp2020"], cwd=work_dir)
        run_git(["config", "user.email", "dpdp2020@users.noreply.github.com"], cwd=work_dir)
        r = run_git(["commit", "-m", msg], cwd=work_dir)
        r = run_git(["push", "origin", "main"], cwd=work_dir)
        if r.returncode != 0 and "Everything up-to-date" not in (r.stderr + r.stdout):
            print(f"[ERROR] Push failed: {r.stderr}")

    # Report
    print(f"\n=== QClaw Soul Sync Report ===")
    print(f"Changed: {len(changed)} files")
    for f in changed:
        print(f"  - {f}")
    if report["skipped"]:
        print(f"Skipped (>50MB): {len(report['skipped'])} files")
        for s in report["skipped"]:
            print(f"  - {s}")
    if report["errors"]:
        print(f"Errors: {len(report['errors'])}")
        for e in report["errors"]:
            print(f"  - {e}")
    if not dry_run:
        print(f"commit: {msg}")
        print(f"repo: https://github.com/{REPO}")

    # Cleanup
    shutil.rmtree(work_dir)

def main():
    parser = argparse.ArgumentParser(description="QClaw Soul Sync")
    parser.add_argument("--agent", help="Only sync specific agent (e.g. main, finance-learner, knowledge-base)")
    parser.add_argument("--skill", action="store_true", help="Sync all managed skills from ~/.qclaw/skills/ to GitHub")
    parser.add_argument("--token", required=True, help="GitHub PAT token")
    parser.add_argument("--dry-run", action="store_true", help="Preview without pushing")
    args = parser.parse_args()

    if args.skill:
        report, changed = sync_skills(args.token, args.dry_run)
        print(f"\n=== QClaw Soul Sync — Skills Report ===")
        print(f"Changed: {len(changed)} files")
        for f in changed:
            print(f"  - {f}")
        if report["skipped"]:
            print(f"Skipped (>50MB): {len(report['skipped'])} files")
            for s in report["skipped"]:
                print(f"  - {s}")
        if report["errors"]:
            print(f"Errors: {len(report['errors'])}")
            for e in report["errors"]:
                print(f"  - {e}")
        print(f"commit: sync: update skills - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"repo: https://github.com/{REPO}")
        return

    sync(args.agent, None, args.token, args.dry_run)

if __name__ == "__main__":
    main()
