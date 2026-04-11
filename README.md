## Domarkalender

This repo scrapes Fogis assignments and publishes a public ICS file on a schedule.

### How it works
- GitHub Actions runs the scraper every 6 hours.
- It generates `uppdrag.csv` and exports `calendar.ics`.
- GitHub Pages serves the ICS file for calendar subscriptions.

### Setup
1) Add GitHub Actions secrets:
   - `FOGIS_USERNAME`
   - `FOGIS_PASSWORD`

2) Enable GitHub Pages:
   - Settings → Pages → Deploy from branch
   - Branch: `main` (or default)
   - Folder: `/ (root)`

3) Run the workflow once:
   - Actions → “Update calendar” → Run workflow

### Calendar URL
Once Pages is enabled, your calendar will be available at:

```
https://<username>.github.io/<repo>/calendar.ics
```

### Local usage
```
python -c "from client import get_schedule; print(get_schedule())"
python export_ics.py --csv uppdrag.csv --out calendar.ics
```
