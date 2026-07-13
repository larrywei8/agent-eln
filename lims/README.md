# lims/ — Laboratory Information Management (stub)

Planned. Not yet implemented.

## Scope

LIMS will own **resource state**: physical location, quantity on hand, chain of custody,
QC records, expiry, and check-in/check-out events.

The ELN's `resources/` folder currently doubles as both a resource **catalog** (metadata,
provenance, source paper) and a partial resource **inventory** (location, storage unit).
As LIMS grows, inventory concerns move here, leaving `eln/resources/` as pure catalog.

## Boundary

| Concern | Owner |
| --- | --- |
| A plasmid exists, its map, its source | `eln/resources/` |
| The plasmid tube sits at box 4 shelf 2 with 15 μL left | `lims/` (planned) |
| An experiment used the plasmid on 2026-06-01 | `eln/experiments/` |

Contributions welcome — open an issue with a proposed schema before writing code.
