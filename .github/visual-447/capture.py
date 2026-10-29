"""Capture the exact #447 offset change on a real NSH backend."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

# Windows runners can default their redirected console to a legacy code page.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "crates/nsh-base/src/text_view/view.rs"
ANCHOR = b"                    .text_decoration_thickness(px(1.0))\n                    .role(AccessibilityRole::Link)"
BASELINE = ANCHOR.replace(b"                    .role", b"                    .underline_offset(px(3.0))\n                    .role")
CASES = {
    "reported": {"label": "Reported: 11pt / 15pt", "fontSize": 11, "lineHeight": 15},
    "default": {"label": "Default: 15pt / 25.5pt"},
    "explicit": {"label": "Link offset: 1.5pt", "fontSize": 11, "lineHeight": 15, "linkOffset": 1.5},
    "inherited": {"label": "Root offset: 1.5pt", "fontSize": 11, "lineHeight": 15, "rootOffset": 1.5},
    "override": {"label": "Root: 2pt; Link: 1.5pt", "fontSize": 11, "lineHeight": 15, "rootOffset": 2, "linkOffset": 1.5},
}


def run(command, log, env=None):
    print("Running: " + " ".join(map(str, command)), flush=True)
    with log.open("w", encoding="utf-8") as output:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT)
    print(log.read_text(encoding="utf-8", errors="replace"), flush=True)
    if result.returncode:
        raise RuntimeError(f"Command exited {result.returncode}; see {log.name}")


def capture(target, variant, out, cli):
    work = ROOT / ".nsh/visual-447"
    work.mkdir(parents=True, exist_ok=True)
    (work / "nsh.json").write_text(json.dumps({"name": "Link underline #447", "id": "com.example.nsh447", "appearance": "light"}))
    tests = ['import { expect, open, test } from "nsh/test";']
    for name, props in CASES.items():
        entry = work / f"{name}.tsx"
        component = (ROOT / ".github/visual-447/App.tsx").as_posix()
        entry.write_text(
            'import { mount } from "nsh";\n'
            f'import {{ Sample }} from {json.dumps(component)};\n'
            f'mount(() => <Sample {{...{json.dumps(props)}}} />);\n', encoding="utf-8"
        )
        tests.append(f'''
test({json.dumps(variant + ": " + name)}, async () => {{
  const app = await open({json.dumps(entry.as_posix())}, {{ width: 760, height: 810, colorScheme: "light" }});
  await app.waitFor("id:sample-document >> text:Final-line link");
  expect(app.spanStyle("id:sample-document >> text:Final-line link").fontSize).toBe({props.get("fontSize", 15)});
  expect(app.spanStyle("id:sample-document >> text:Final-line link").underline).toBe(true);
  await app.wait(350);
  await app.screenshot({json.dumps((out / (variant + "-" + name + ".png")).as_posix())});
}});
''')
    test = work / f"{variant}.test.ts"
    test.write_text("\n".join(tests), encoding="utf-8")
    shutil.copyfile(work / "reported.tsx", work / "App.tsx")
    env = os.environ.copy()
    if target == "android":
        run(["cargo", "xtask", "android", "--dev", "--abi", "x86_64"], out / f"{variant}-android-build.log")
        runtime = work / "runtime"
        shutil.copytree(ROOT / "target/android/debug-dev", runtime / "android/dev", dirs_exist_ok=True)
        env["NSH_RUNTIME"] = str(runtime)
    run([str(cli), "test", str(test), "--target", target], out / f"{variant}-capture.log", env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=["linux", "macos", "windows", "ios", "android", "web", "gpui"])
    parser.add_argument("--only", choices=["before", "after"], help="For a local harness smoke check")
    parser.add_argument("--cli", type=Path)
    args = parser.parse_args()
    cli = args.cli or ROOT / "target/debug" / ("nsh.exe" if os.name == "nt" else "nsh")
    out = ROOT / "out/visual-447" / args.target
    out.mkdir(parents=True, exist_ok=True)
    (out / "failures.txt").unlink(missing_ok=True)
    fixed = SOURCE.read_bytes()
    if fixed.count(ANCHOR) != 1:
        raise RuntimeError("Expected the reviewed one-line fix exactly once; refusing to change the source")
    baseline = fixed.replace(ANCHOR, BASELINE, 1)
    metadata = {"target": args.target, "host": platform.platform(), "cases": CASES,
                "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "source_sha256": {v: hashlib.sha256(data).hexdigest() for v, data in [("before", baseline), ("after", fixed)]},
                "note": "Captures and semantic assertions require visual review; they do not assert underline visibility."}
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    failures = []
    try:
        for variant in [args.only] if args.only else ["before", "after"]:
            SOURCE.write_bytes(baseline if variant == "before" else fixed)
            try:
                capture(args.target, variant, out, cli.resolve())
            except Exception as error:
                failures.append(f"{variant}: {error}")
                print(failures[-1], file=sys.stderr, flush=True)
    finally:
        SOURCE.write_bytes(fixed)
    if not args.only:
        try:
            run([sys.executable, str(Path(__file__).with_name("compare.py")), str(out)], out / "comparison.log")
        except Exception as error:
            failures.append(str(error))
    if failures:
        (out / "failures.txt").write_text("\n".join(failures), encoding="utf-8")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
