# Rural Postman Problem (RPP) Solver Prototype

A Python-based tool to solve the Rural Postman Problem (RPP) on OpenStreetMap (OSM) data. 
It identifies a set of required edges (e.g., residential streets) and calculates an Eulerian circuit that covers all of them with minimum total cost, exporting the result as a GPX file.

### Features
- **Graph Loading**: Imports OSM data using `osmnx` and `networkx`.
- **Route Optimization**: Solves the RPP by connecting required components and matching odd-degree nodes.
- **GPX Export**: Generates a GPX route including geometry for navigation.

### Usage
Run the main script to process the sample data:
```bash
python main.py
```

### Sample
https://github.com/user-attachments/assets/3958631c-9b01-4edf-b342-266f00c53466

