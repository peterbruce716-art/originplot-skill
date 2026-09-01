# Capability Tests v6.1

This directory validates that declared OriginPlot capabilities match actual support levels.

## Capability levels

- planning: a semantic plan can be produced
- compile: a valid OperationPlan can be generated
- live: verified execution evidence exists

A higher level must not be inferred from a lower level.

## Test goals

- detect capability drift
- prevent unsupported feature claims
- preserve fail-closed behavior
