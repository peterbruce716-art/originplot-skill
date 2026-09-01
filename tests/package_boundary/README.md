# Package Boundary Tests v6.1

## Purpose

Protect the separation between production code and development-only assets.

## Checks

- `originplot` runtime modules remain importable without benchmark helpers.
- Development scripts do not become runtime dependencies.
- Benchmark examples remain isolated from the core package.
- Adapter/runtime boundaries remain explicit.

## Principle

A clean package boundary prevents scientific plotting workflows from becoming coupled to local development tooling.
