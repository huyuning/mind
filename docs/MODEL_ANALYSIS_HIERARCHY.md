# Model Analysis Hierarchy

This document organizes the current CSDE prototype into a layered analysis model.
It maps theoretical viewpoints such as point, line, face, volume, field, spectral,
state-space, and information layers onto the current codebase.

## Purpose

The current repository contains both:

- a viewer-oriented projection layer
- an emerging lower-level triad dynamics layer with an explicit connector/apex state

These layers are not the same thing. This document clarifies:

- what each analysis layer studies
- which structures belong to which layer
- where each layer currently lives in code
- which layers are mature and which are still partial

## Layer Diagram

```text
                           Model Analysis Hierarchy

┌──────────────────────────────────────────────────────────────┐
│ 7. Hierarchy / Ontology View                                │
│ What: cell -> triad -> connector/apex -> projection         │
│ Code: TriadCoreState / TriadRecord / projection_cell        │
│ Entry: schema + triad construction + composite render mode  │
└──────────────────────────────────────────────────────────────┘
                              ▲
┌──────────────────────────────────────────────────────────────┐
│ 6. Information View                                         │
│ What: 0-1 bit streams, duty cycles, phase layout, edge      │
│       complex values, information transfer                  │
│ Code: TriadCoreState already provides the right state base  │
│ Entry: triad_core_step + future bitstream / MI / TE layer   │
└──────────────────────────────────────────────────────────────┘
                              ▲
┌──────────────────────────────────────────────────────────────┐
│ 5. State-Space / Dynamics View                              │
│ What: trajectories, locking, attractors, closure evolution  │
│ Code: triad_core_step                                       │
│ Entry: TriadCoreState -> triad_core_step -> diagnostics     │
└──────────────────────────────────────────────────────────────┘
                              ▲
┌──────────────────────────────────────────────────────────────┐
│ 4. Spectral / Relational View                               │
│ What: edge coupling spectrum, phase relations, modal        │
│       organization, coherence                               │
│ Code: edge_state_real/imag, coherence_score                 │
│ Entry: TriadCoreState + build_triad_unit                    │
└──────────────────────────────────────────────────────────────┘
                              ▲
┌──────────────────────────────────────────────────────────────┐
│ 3. Field View                                               │
│ What: point cloud field, slices, phase field, strain field, │
│       wavefront propagation                                 │
│ Code: XYZ Point Cloud / XY-XZ-YZ slices / shell trails      │
│ Entry: Viewer3D.update_frame                                │
└──────────────────────────────────────────────────────────────┘
                              ▲
┌──────────────────────────────────────────────────────────────┐
│ 2. Geometry View                                            │
│ Point: centers, connector candidates, closure centers       │
│ Line: edges, axes, shell network                            │
│ Face: closure sphere, future triad faces, slices            │
│ Volume: closure envelope, future pyramid body               │
│ Code: Viewer3D + geometry builders                          │
└──────────────────────────────────────────────────────────────┘
                              ▲
┌──────────────────────────────────────────────────────────────┐
│ 1. Core State View                                          │
│ What: node duty, node frequency, node phase, edge complex   │
│       state, position, velocity, axis                       │
│ Code: TriadCoreState                                        │
└──────────────────────────────────────────────────────────────┘
```

## Layer Definitions

### 1. Core State View

This is the lowest explicit layer in the current prototype.

It studies the raw coupled state:

- node duty cycle
- node frequency
- node phase
- node position
- node velocity
- node axis
- edge complex state

Current code anchor:

- `TriadCoreState` in `csde_data_schema.py`
- `triad_core_step()` in `csde_experiment_viewer_prototype.py`
- connector/apex state is now part of the explicit core state rather than only a
  later geometric interpretation

This is the correct entry point if the model is interpreted as a triad-level coupled
system instead of independent geometric cells.

### 2. Geometry View

This layer studies explicit geometric projections.

It currently includes:

- points:
  - cell centers
  - triad center
  - closure center
- lines:
  - shell network
  - local frame axes
  - projected structural edges
- faces:
  - closure sphere rings
  - slices
  - future explicit triad or pyramid faces
- volumes:
  - closure envelope
  - future pyramid volume and compactness

Current code anchor:

- `Viewer3D`
- shell and slice geometry helpers
- closure sphere rendering

### 3. Field View

This layer studies how the local structure projects into surrounding space.

Current field-level objects:

- XYZ point cloud field
- XY/XZ/YZ dynamic slices
- multi-layer shells
- shell trails and slice trails

This is the strongest current layer in the viewer.

Current code anchor:

- `Viewer3D.update_frame()`
- `build_space_point_cloud()`
- slice grid builders
- shell distortion builders

### 4. Spectral / Relational View

This layer studies relationships instead of only geometry.

Typical questions:

- which edge is strongest
- which phase relation dominates
- whether the triad is locking
- what the dominant coupling mode is

Current code already provides partial inputs:

- `edge_state_real`
- `edge_state_imag`
- `coherence_score`
- `phase_coherence`
- `direction_coherence`

What is missing is a dedicated spectral analysis API or panel.

### 5. State-Space / Dynamics View

This layer studies the full system as a time-evolving state vector.

Typical questions:

- does the system lock
- does it oscillate around a stable orbit
- does it drift
- does closure grow or collapse
- is there a stable attractor or a limit cycle

Current code anchor:

- `triad_core_step()`
- diagnostics returned from one integration step

This layer exists computationally, but not yet as a dedicated visualization mode.

### 6. Information View

This is the natural high-level view if the true substrate is 0-1 bit activity.

Typical questions:

- what information each node carries
- whether the triad contains redundancy or synergy
- which node or edge drives causal transfer
- how bitstream organization changes over time

Current code status:

- the data structure is close to ready
- the analysis layer is not implemented yet

Likely next additions:

- bitstream generation from `TriadCoreState`
- mutual information
- transfer entropy
- phase-coded information summaries

### 7. Hierarchy / Ontology View

This is the layer that organizes what is fundamental and what is projected.

The current code is moving toward:

```text
TriadCoreState -> TriadRecord -> projection_cell -> viewer geometry
```

This layer answers questions like:

- what is the true dynamical substrate
- what is a structural unit
- what is only a geometric projection
- how lower-level states become higher-level observables

Current code anchors:

- `TriadCoreState`
- `TriadRecord`
- `build_triad_unit()`
- `build_composite_cell()`
- `Composite Wave Only`

## Code Mapping

### `csde_data_schema.py`

Role:

- ontology layer
- state layer
- structural record layer

Main objects:

- `CellRecord`
- `TriadRecord`
- `TriadCoreState`
- `FrameState`

### `csde_experiment_viewer_prototype.py`

Role:

- dynamics layer
- geometry projection layer
- field layer
- viewer and analysis entry layer

Main components:

- `triad_core_step()`
- `build_triad_unit()`
- `build_composite_cell()`
- `resolve_frame_triads()`
- `Viewer3D`
- `StructureTree`
- `MainWindow`

## Current Maturity by Layer

### Relatively mature

- geometry point/line layer
- field layer
- viewer projection layer
- basic hierarchy semantics

### Partially implemented

- face layer
- volume layer
- spectral / relational interpretation
- state-space diagnostics

### Mostly not yet implemented

- information-theoretic analysis
- topology layer
- explicit pyramid / connector ontology beyond the current triad-based landing

## Recommended Development Order

If the model keeps moving toward a deeper structural interpretation, the most sensible
order is:

1. Promote the current triad landing into a fuller pyramid-like structural core
2. Add explicit face and volume observables
3. Generate 0-1 bitstreams from `TriadCoreState`
4. Add information and spectral analysis
5. Add dedicated state-space and attractor views

## Practical Reading Guide

When inspecting the current codebase, use the following interpretation:

- if you want to know what the system *is*: read the state and ontology layers
- if you want to know what the system *looks like*: read the geometry and field layers
- if you want to know how the system *evolves*: read the dynamics layer
- if you want to know how the system *organizes or communicates*: read the future
  spectral and information layers

## Summary

The current repository is no longer just a viewer for animated cells.

It already contains the beginnings of a layered model:

- raw coupled state
- structural triad abstraction
- geometric projection
- field rendering
- future spectral, information, and topological analysis

This layered view should be used as the reference map for future refactors.
