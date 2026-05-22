# VRP GA Solver Application

This folder contains the Python desktop application source.

## Features

- Built-in VRP datasets for Europe, Vietnam, and Ho Chi Minh City.
- Genetic Algorithm flow: population initialization, selection, OX crossover, mutation, and elitism.
- CSO comparison mode for algorithm experiments.
- PyQt6 interface with Folium map view, Matplotlib convergence chart, dashboard, and export tools.

## Run Locally

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Build Locally

From the repository root:

```powershell
python -m pip install -r VRP_GA_2_APP/requirements.txt -r requirements-dev.txt
pyinstaller --noconfirm --clean packaging/VRP-GA-Solver.spec
```

The executable folder will be generated under `dist/VRP-GA-Solver/`.

## Report Build

```powershell
cd Latex
latexmk -pdf -shell-escape Phuc2.tex
```

Report build outputs are generated under `Latex/build/` and are not committed.
