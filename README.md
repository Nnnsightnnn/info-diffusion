# 📡 Info Diffusion Simulator

A toy model for exploring how information from a video spreads through a population — like a zeitgeist ripple moving outward from the first viewers.

## Concept

Uses a SIR-style epidemiological model adapted for information spread:

- **S (Susceptible):** People who haven't heard the information yet
- **I (Informed):** People who know and are actively sharing it
- **R (Recovered/Silent):** People who know but have stopped talking about it

## Versions

| Version | Feature |
|---------|---------|
| v0.1 | Core SIR math model, CSV output |
| v0.2 | Stochastic Monte Carlo simulation, variance analysis |
| v0.3 | Visualizations: S-curves, comparisons, sensitivity plots |
| v0.4 | Interactive CLI scenario explorer with presets |

## Quick Start

```bash
pip install -r requirements.txt

# Run the deterministic model
python sir_model.py

# Run Monte Carlo simulations
python monte_carlo.py

# Generate visualizations
python visualize.py

# Interactive explorer
python explore.py
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `seed_viewers` | Initial informed population | 10 |
| `population_size` | Total population | 1,000,000 |
| `conversation_rate` | People told per day per informed person | 3 |
| `spread_probability` | Chance listener cares/shares | 0.15 |
| `recovery_rate` | Rate at which informed become silent | 0.1 |
| `days_to_simulate` | Simulation duration | 60 |

## The Viral Coefficient

The **viral coefficient** `k = conversation_rate × spread_probability` determines growth:
- `k > recovery_rate`: Information spreads exponentially (viral!)
- `k < recovery_rate`: Information fizzles out
- `k ≈ recovery_rate`: Slow, steady diffusion
