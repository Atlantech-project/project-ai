<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/logo-dark.png">
    <img src=".github/assets/logo-light.png" alt="ATLANTECH, Intelligent Port Operations" width="340">
  </picture>
</p>

<p align="center"><b>AI Engine</b> &nbsp;|&nbsp; reading the sea, planning the quay</p>
<p align="center"><i>Smarter coordination. Stronger ports.</i></p>

<p align="center">
  <img src="https://img.shields.io/badge/status-in_development-A58D66?style=flat-square&labelColor=083A4F" alt="status">
  <img src="https://img.shields.io/badge/part_of-ATLANTECH-407E8C?style=flat-square&labelColor=083A4F" alt="part of ATLANTECH">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-workers-407E8C?style=flat-square&logo=python&logoColor=E5E1DD&labelColor=083A4F" alt="Python">
  <img src="https://img.shields.io/badge/OR--Tools-CP--SAT-407E8C?style=flat-square&logo=google&logoColor=E5E1DD&labelColor=083A4F" alt="OR-Tools">
  <img src="https://img.shields.io/badge/LightGBM-forecasting-407E8C?style=flat-square&logo=microsoft&logoColor=E5E1DD&labelColor=083A4F" alt="LightGBM">
  <img src="https://img.shields.io/badge/pyTMD-tide_model-407E8C?style=flat-square&labelColor=083A4F" alt="pyTMD">
  <img src="https://img.shields.io/badge/Redis-queues-407E8C?style=flat-square&logo=redis&logoColor=E5E1DD&labelColor=083A4F" alt="Redis">
  <img src="https://img.shields.io/badge/MySQL-storage-407E8C?style=flat-square&logo=mysql&logoColor=E5E1DD&labelColor=083A4F" alt="MySQL">
  <img src="https://img.shields.io/badge/EDIFACT-BAPLIE_D.17A-407E8C?style=flat-square&labelColor=083A4F" alt="BAPLIE">
</p>

<img src=".github/assets/wave.svg" width="100%" alt="">

## What lives here

This repository holds the thinking part of ATLANTECH: a small group of **Python workers** that run on the port's own server, right next to the database.

The flow is simple. A staff member does something in the dashboard, and Laravel drops a job on a Redis queue. The right worker picks it up, reads the state of the port from MySQL, does its work and writes the answer back. Laravel then pushes the result to the screen over SSE.

```
dashboard -> Laravel -> Redis (queue:part1 | queue:part2 | queue:edi) -> Python worker
          -> MySQL -> SSE -> dashboard
```

All learning happens locally. No model, weight or update ever leaves the port's server, and no port ever learns from another port's data.

## The three parts

### Part 1: Predictive and environmental

Before anyone talks about berths, we need to know when a ship can safely come in at all. Part 1 answers that question and nothing else. **It never allocates a resource.**

| Piece | How it works |
|---|---|
| Data ingestion | Weather, waves and currents every 6 hours and on demand, from a primary and a backup provider |
| Astronomical tide | A harmonic model built on pyTMD, computed in-house every day |
| Surge | `Surge(t) = SeaLevel(t) - Tide(t)`, a definition rather than a guess |
| Feasibility | Wind, gusts, visibility, waves, tide and surge checked against operating limits |
| Under-keel clearance | UKC including Barrass squat |
| Safety margin | Statistical margin or provider ensemble spread |
| Demand forecast (M3) | Simple aggregates today, a LightGBM regressor in phase 2 |

It returns `feasible_windows`, `blocked_periods`, a `peak_congestion_score` and the `data_versions` it used.

### Part 2: The allocation engine

Once a person has confirmed the entry window, Part 2 decides who gets which **berth, tugs and pilot**. It looks at the whole port in a single solve, and it also suggests yard placement for the Container Terminal. It is the only component allowed to allocate.

| Piece | How it works |
|---|---|
| Constraint filter | Length, draft, terminal type, the safety officer's rules and the Part 1 windows |
| Service time (M2) | A formula for now, LightGBM quantile regression (P50 / P90) later |
| Delay risk (M4) | A rule-based score until there is enough history, then a LightGBM classifier |
| Solver | Google OR-Tools **CP-SAT**, a joint berth allocation problem that includes tugs and pilots |
| Fallback | A plain FIFO plan, used only if the solver itself fails |
| Rationale | Fixed, versioned templates that explain each choice. No language model involved. |
| Re-planning | A rolling-horizon re-solve when a ship is late or a plan is cancelled |

There are three possible outcomes: ranked options, a FIFO fallback that is clearly labelled as one, or `NO_FEASIBLE_PLAN` together with the constraints that made it impossible.

### Part 3: The feedback loop

After the ship leaves, Part 3 compares the plan with what really happened.

| Piece | How it works |
|---|---|
| Evaluation | MAE, override rate, waiting time and accuracy of the entry windows |
| Drift watch | PSI and rolling MAE on M2, M3 and M4 |
| Retraining | A time-based split with a champion and a challenger, under guard |
| Bias correction | Regression or quantile mapping on forecast error, fed back to Part 1 |

A new model replaces the old one **only if it is no worse** on MAE and override rate. The old one is always kept for rollback. Hard safety limits are never adjusted automatically.

### EDI parser

A strict, deterministic reader for **UN/EDIFACT BAPLIE D.17A** (SMDG 2019) files. It runs on `queue:edi` and extracts the vessel, the containers and the stowage, committing all of it or none of it. There is no AI here, just careful parsing.

## Stack

| Area | Technology |
|---|---|
| Language | Python |
| Optimisation | Google OR-Tools (CP-SAT) |
| Machine learning | LightGBM |
| Tides | pyTMD |
| Messaging | Redis queues |
| Storage | MySQL, shared with the backend |

## Getting started

```bash
git clone https://github.com/Atlantech-project/project-ai.git
cd project-ai
```

Setup steps will be added here as each worker takes shape.

## Neighbours

[PortHub](https://github.com/Atlantech-project/PortHub) &middot;
[project-backend](https://github.com/Atlantech-project/project-backend) &middot;
[project-frontend](https://github.com/Atlantech-project/project-frontend) &middot;
[project-mobile](https://github.com/Atlantech-project/project-mobile)

## Crew

**Mostafa Mohamed Ragab Rashwan**, AI Engineer and Team Lead<br>
**Menna-Allah Gamal Mohamed Nasr**, AI Engineer

<img src=".github/assets/wave.svg" width="100%" alt="">

<p align="center">
  <sub>ATLANTECH, Intelligent Port Operations &middot; Mansoura University &middot; Graduation Project 2026</sub>
</p>
