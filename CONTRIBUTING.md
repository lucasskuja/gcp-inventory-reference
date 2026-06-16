# Contributing

This repository is maintained as a reusable reference implementation for GCP inventory documentation. Contributions should improve practical usefulness, extension potential, and documentation quality without overstating the scope of the current codebase.

## Contribution Priorities

The best contributions usually fall into one of these areas:

- add coverage for additional GCP services
- improve consistency of Markdown output across collectors
- harden behavior for missing permissions, empty services, and CLI edge cases
- simplify maintenance without introducing unnecessary framework complexity
- improve documentation accuracy so it matches the current implementation

## Contribution Principles

Please keep changes aligned with the current positioning of the repository.

- Prefer reusable implementation patterns over one-off project-specific logic.
- Keep the script read-only with respect to cloud resources.
- Do not introduce claims in the documentation that the code does not support.
- Preserve predictable output structure whenever new collectors are added.
- Favor incremental extensibility over broad rewrites.

## Collector Changes

When adding or changing a collector in [`gcp_inventory.py`](./gcp_inventory.py):

- follow the existing section and table conventions
- return useful output even when a service is disabled or inaccessible
- avoid failing the entire inventory because one service cannot be listed
- keep field choices practical for architecture review and operational discovery

## Documentation Changes

Documentation should present the repository as:

- a reference implementation
- a reusable pattern
- a practical baseline for extension

Avoid tutorial-first, lab-style, or study-project language unless the repository itself changes direction.

## Pull Request Standard

A good contribution should make it easy to answer these questions:

- What real capability or reliability improvement does this add?
- Does the README still reflect the actual state of the repository?
- Is the change reusable beyond a single environment?
- Does the output remain clear for human review?
