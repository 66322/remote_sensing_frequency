# Start Here

This is the authoritative entry point for a new conversation or a new computer.

Read in this order:

1. `docs/current/PROJECT_STATUS.md`
2. `docs/current/DO_NOT_REPEAT.md`
3. `docs/current/NEXT_EXPERIMENT.md`
4. `docs/experiments/rebuild_v1/INDEX.md`
5. `records/rebuild_v1_experiment_registry.json`
6. `docs/protocols/NAMING_CONVENTION.md`

The files under `docs/archive/` are historical evidence only. They must not be
used to determine current status or the next experiment.

Before proposing any experiment, search the registry by experiment ID and
fingerprint. Do not repeat a completed or closed experiment unless the new run
changes seed, dataset, split, protocol, model, budget, or an explicitly stated
independent variable.

After each formal experiment:

1. verify completion and TEST6 isolation;
2. analyze CSV/JSON results;
3. write an experiment report;
4. update the registry, status, do-not-repeat list, index, and next experiment;
5. generate an artifact SHA256 manifest;
6. commit code, configuration, results, analysis and documentation together;
7. push and verify that local and remote commits match.
