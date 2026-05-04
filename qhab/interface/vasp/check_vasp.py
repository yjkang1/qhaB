#!/usr/bin/env python3
"""Strict check: VASP calculation finished without error.

Module API:
    has_error, error_type = check_vasp(path)
        has_error : bool
        error_type: str  ("" if no error, else semicolon-joined error tags)

CLI:
    python check_vasp.py PATH                              # single, prints report
    python check_vasp.py PATH --json                       # single, JSON
    python check_vasp.py PATH1 PATH2 ... --csv out.csv     # batch CSV
    find . -name OUTCAR -printf '%h\\n' | python check_vasp.py - --csv out.csv
"""
from __future__ import annotations
import sys, re, json, csv, argparse
from pathlib import Path
from dataclasses import dataclass, asdict, field

ERROR_PATTERNS: dict[str, str] = {
    # tag : regex
    "ZBRENT":          r"ZBRENT",
    "ZPOTRF":          r"ZPOTRF",
    "ZHEGV":           r"ZHEGV",
    "VERY_BAD_NEWS":   r"VERY BAD NEWS",
    "FEXCP":           r"FEXCP",
    "SGRCON":          r"SGRCON",
    "INVGRP":          r"INVGRP",
    "BRMIX":           r"BRMIX:\s+very serious problems",
    "NON_HERMITIAN":   r"Sub-Space-Matrix is not hermitian",
    "INTERNAL_ERROR":  r"internal error in subroutine",
    "PRICEL":          r"PRICEL: internal error",
    "PSMAXN":          r"PSMAXN for non-local",
    "FORRTL_SEVERE":   r"forrtl: severe",
    "EDWAV":           r"EDWAV: internal error",
    "TETIRR_MEM":      r"Routine TETIRR needs more memory",
}

SUCCESS_MARKERS = [
    "General timing and accumulation information",
    "Total CPU time used",
]


@dataclass
class CheckResult:
    path: str
    index: int | None = None
    name: str = ""
    symm: str = ""
    ok: bool = False
    finished: bool = False
    electronic_converged: bool = False
    ionic_converged: bool = False
    nsw: int = 0
    nelm_max: int = 0
    last_ionic_step: int = 0
    last_scf_steps: int = 0
    final_energy: float | None = None
    max_force: float | None = None
    error_tags: list[str] = field(default_factory=list)

    @property
    def error_type(self) -> str:
        return ";".join(self.error_tags)


def scan_outcar_errors(text: str) -> list[str]:
    return [tag for tag, pat in ERROR_PATTERNS.items() if re.search(pat, text)]


def parse_label_from_path(path: Path) -> tuple[int | None, str, str]:
    """Extract (index, name, symm) from first ancestor matching `<digits>_<name>_<symm>`.

    Walks deepest-to-shallowest. Splits on `_`; first part must be digits.
    Index returned as int (leading zeros stripped). Last part is symm,
    middle (joined by `_`) is name.
    """
    for part in reversed(path.resolve().parts):
        chunks = part.split("_")
        if len(chunks) >= 3 and chunks[0].isdigit():
            return int(chunks[0]), "_".join(chunks[1:-1]), chunks[-1]
    return None, "", ""


def check_vasp_run(run_dir: Path) -> CheckResult:
    res = CheckResult(path=str(run_dir))
    res.index, res.name, res.symm = parse_label_from_path(run_dir)

    outcar = run_dir / "OUTCAR"
    vrun_path = run_dir / "vasprun.xml"
    contcar = run_dir / "CONTCAR"

    if not outcar.exists():
        res.error_tags.append("MISSING_OUTCAR")
        return res

    text = outcar.read_text(errors="replace")
    res.finished = any(m in text for m in SUCCESS_MARKERS)
    if not res.finished:
        res.error_tags.append("NOT_FINISHED")
    res.error_tags.extend(scan_outcar_errors(text))

    if not vrun_path.exists():
        res.error_tags.append("MISSING_VASPRUN")
        return res

    try:
        from pymatgen.io.vasp.outputs import Vasprun
        import numpy as np

        vrun = Vasprun(
            str(vrun_path),
            parse_dos=False, parse_eigen=False,
            parse_potcar_file=False,
            exception_on_bad_xml=True,
        )
        res.nsw = int(vrun.incar.get("NSW", 0))
        res.nelm_max = int(vrun.incar.get("NELM", 60))
        res.last_ionic_step = len(vrun.ionic_steps)
        res.last_scf_steps = len(vrun.ionic_steps[-1].get("electronic_steps", []))
        res.electronic_converged = bool(vrun.converged_electronic)
        res.ionic_converged = True if res.nsw == 0 else bool(vrun.converged_ionic)
        res.final_energy = float(vrun.final_energy)
        forces = np.array(vrun.ionic_steps[-1]["forces"])
        res.max_force = float(np.abs(forces).max())
    except Exception as e:
        res.error_tags.append(f"VASPRUN_PARSE:{type(e).__name__}")
        return res

    if not res.electronic_converged:
        res.error_tags.append("ELEC_NOT_CONVERGED")
    if not res.ionic_converged:
        res.error_tags.append("IONIC_NOT_CONVERGED")
    if res.nelm_max > 0 and res.last_scf_steps >= res.nelm_max:
        res.error_tags.append("NELM_EXHAUSTED")
    if res.nsw > 0 and res.last_ionic_step >= res.nsw and not res.ionic_converged:
        res.error_tags.append("NSW_EXHAUSTED")
    if res.nsw > 0 and (not contcar.exists() or contcar.stat().st_size == 0):
        res.error_tags.append("MISSING_CONTCAR")

    res.ok = (
        res.finished
        and res.electronic_converged
        and res.ionic_converged
        and not res.error_tags
    )
    return res


def check_vasp(path: str | Path) -> tuple[bool, str]:
    """Simple API.

    Returns
    -------
    (has_error, error_type)
        has_error  : True if any problem found, False if clean.
        error_type : semicolon-joined tag string ("" if no error).
    """
    res = check_vasp_run(Path(path))
    has_error = not res.ok
    return has_error, res.error_type


def is_done(path: str | Path) -> tuple[bool, str]:
    """Check one VASP run directory.

    Returns
    -------
    (done, problem)
        done    : True if finished cleanly (electronic + ionic converged, no error patterns).
        problem : "" if done, else semicolon-joined error tags
                  (e.g. "ZBRENT;IONIC_NOT_CONVERGED").
    """
    res = check_vasp_run(Path(path))
    return res.ok, res.error_type


def write_csv(results: list[CheckResult], out_path: Path) -> None:
    cols = [
        "path", "index", "name", "symm",
        "ok", "has_error", "error_type",
        "finished", "electronic_converged", "ionic_converged",
        "nsw", "nelm_max", "last_ionic_step", "last_scf_steps",
        "final_energy", "max_force",
    ]
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in results:
            d = asdict(r)
            d["has_error"] = not r.ok
            d["error_type"] = r.error_type
            w.writerow({k: d.get(k, "") for k in cols})


def _print_report(res: CheckResult) -> None:
    tag = "OK" if res.ok else "FAIL"
    print(f"[{tag}] {res.path}")
    if res.index is not None or res.name or res.symm:
        print(f"  label:                index={res.index} name={res.name} symm={res.symm}")
    print(f"  finished:             {res.finished}")
    print(f"  electronic converged: {res.electronic_converged}")
    print(f"  ionic converged:      {res.ionic_converged}")
    print(f"  ionic steps:          {res.last_ionic_step}/{res.nsw}")
    print(f"  last SCF cycles:      {res.last_scf_steps}/{res.nelm_max}")
    if res.final_energy is not None:
        print(f"  final energy [eV]:    {res.final_energy:.6f}")
    if res.max_force is not None:
        print(f"  max |F| [eV/Å]:       {res.max_force:.6f}")
    if res.error_tags:
        print(f"  error_type:           {res.error_type}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", type=Path,
                    help="Run directories. Use '-' to read paths from stdin.")
    ap.add_argument("--csv", type=Path, help="Write batch results to CSV.")
    ap.add_argument("--json", action="store_true",
                    help="JSON output (single path).")
    args = ap.parse_args()

    if args.paths == [Path("-")]:
        paths = [Path(line.strip()) for line in sys.stdin if line.strip()]
    else:
        paths = args.paths

    results = [check_vasp_run(p.resolve()) for p in paths]

    if args.csv:
        write_csv(results, args.csv)
        n_fail = sum(1 for r in results if not r.ok)
        print(f"Wrote {args.csv}: {len(results)} runs, {n_fail} failed.")
    elif args.json and len(results) == 1:
        out = asdict(results[0]) | {
            "has_error": not results[0].ok,
            "error_type": results[0].error_type,
        }
        print(json.dumps(out, indent=2))
    else:
        for r in results:
            _print_report(r)
            print()

    sys.exit(0 if all(r.ok for r in results) else 1)


if __name__ == "__main__":
    main()
