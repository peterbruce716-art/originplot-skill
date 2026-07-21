# Release Profile

Use Release for AA2195 benchmarks, regression acceptance, package release, or a full live-validation claim. This profile is the compatibility home of the retained p18 strict workflow distributed in release 5.9.0.

Require `template_policy=strict`, `evidence_level=full`, `reopen_check=strict`, and `visual_qa=benchmark`. Reject lighter overrides.

Keep the full administrator privilege envelope where the existing release contract requires it. Use a new or empty run root; validate source lineage; inspect official templates in compatible Origin; build; export before save; save; detach; reopen; perform full object/style/binding readback; export again; calculate benchmark metrics; materialize hashes and provenance; run release and batch audits; and fail closed on any missing gate.

Do not rewrite historical evidence identities. `release_version`, `contract_version`, and `evidence_version` remain sourced from `version.json`.

For AA2195, load benchmark configuration only after the route is identified as Fig3, Fig12, Fig14, Fig15, or Fig16. Use the existing legacy worker as the strict execution backend until each specialized builder has an equivalent plugin hook and live regression evidence.
