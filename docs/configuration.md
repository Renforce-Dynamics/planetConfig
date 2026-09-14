# Configuration files and composition

Packages contain code only. Keep authored configuration in the repository's root
`configs/` tree and pass its path explicitly. The included example is
`configs/entry/entry_example.yaml`, which inherits `configs/example.yaml`.

```bash
./scripts/run.sh resolve configs/entry/entry_example.yaml --output runs/example
./scripts/doctor.sh configs/entry/entry_example.yaml
```

`extends` files apply in listed order. `compose` applies layers in the fixed order
`robot`, `backend`, `task`, `site`, `experiment`, followed by the current file.
Mappings merge recursively; lists and scalar values replace. Duplicate keys,
missing files and inheritance cycles are errors. Each consuming service validates
its own fields after composition.

The entry path is relative to the caller's working directory. Relative inheritance
references resolve beside their declaring file. `ResolvedConfig.path(key)` resolves
a resource relative to that field's original declaration, even after inheritance.
The loader never searches another directory when a file is missing. It does not
interpret every string as a path; device names, network endpoints and output
directories retain the consuming service's rules.

`freeze(directory)` saves merged values, declaration provenance, explicit overrides
and a content digest. The configuration CLI supports `resolve`, `validate`, `diff`
and explicit `--set` overrides for configuration inspection.

The generic `resolve_resource` API retains explicit `pkg://` and checksum-checked
`artifact://` compatibility for external callers. No production example or default
profile is embedded in these packages.
