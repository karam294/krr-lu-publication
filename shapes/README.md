# shapes/

YOUR TEAM: your Session 4 work, on your own data.

- `shapes.ttl`: replace the example with the shapes for your constraint
  inventory (Session 1). Cover every constraint you found, with
  `sh:message` text a person can act on and a severity that says what the
  pipeline does: a Violation stops the load.
- For each constraint, decide and write down why it is a SHACL shape and not
  an OWL axiom (or the reverse).
- Triage every failure on your real data: a data defect, or a wrong
  constraint. Keep the triage in `shapes/triage.md`; a constraint you found
  false in the data is reported in the technical report, not dropped.
- The gate runs in CI (`.github/workflows/shacl-gate.yml`). Keep one red run
  it blocked, for the report; a branch with one deliberately broken row does
  it.

Run it locally: `python pipeline/run.py --no-load` stops at the gate and
prints the report.
