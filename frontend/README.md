# Fieldwork WSN observatory

```bash
npm ci
npm run dev
```

Open `http://127.0.0.1:5173/`. Vite proxies `/api`, `/docs` and `/openapi.json` to the local FastAPI server on port 8001. Set `WSN_API_URL` before starting Vite to use another local port.

`npm run build` produces `dist/`; `scripts/start_project.sh` serves that build with FastAPI. Use `npm run dev` for hot reload during development.

The UI provides six overview cards, temperature trends, per-sensor selection, observed RPL parent links, node/history tables, packet/energy analysis, experiment selection, raw CSV download and persistent light/dark themes. Polling uses cancellation and schedules the next refresh only after the previous fetch completes. Connection failures retain the last successful values and visibly mark them stale.

There are no hardcoded measurement values. Color assignments and visual styling are constants; experiment values come exclusively from the API. The chart uses five-second display buckets, with full raw samples retained in CSV. Its x-axis uses simulation seconds for Cooja. ISO timestamps in the table are the run's UTC epoch plus simulation receipt time and can run ahead of wall time in accelerated simulations.

All temperatures are simulated in sensor firmware until the hardware adapter is implemented for a specific board. Energy and lifetime are explicitly labeled estimates. Completed-run node status is evaluated at the end of its simulation, not at the current wall clock.
