# SATVIGIL — Testing Guide

## Test Structure

```
backend/tests/
├── unit/
│   ├── test_fire_classifier.py      — Test classification rules (no API needed)
│   ├── test_vessel_risk_scorer.py   — Test risk scoring logic
│   └── test_spatial_utils.py        — Test point-in-polygon functions
├── integration/
│   ├── test_firms_api.py            — Test real FIRMS API call (needs MAP_KEY)
│   └── test_ais_api.py              — Test AIS fetch (needs AISHub credentials)
└── data/
    ├── sample_firms.csv             — 50 rows of real FIRMS data for offline testing
    ├── sample_ais.json              — 20 vessel records for offline testing
    └── test_cpcb_clusters.json      — CPCB cluster subset for testing
```

---

## Running Tests

### All tests
```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

### Unit tests only (no API keys needed — run during development)
```bash
pytest tests/unit/ -v
```

### Integration tests (needs real API keys in .env)
```bash
pytest tests/integration/ -v --timeout=30
```

### Single test file
```bash
pytest tests/unit/test_fire_classifier.py -v
```

---

## Unit Test Examples

### Fire Classifier Tests (`tests/unit/test_fire_classifier.py`)
```python
from app.services.fire.firms_fetcher import classify_fire, get_responding_agency

def test_stubble_fire_october():
    """A farmland hotspot in October should be classified as stubble."""
    row = {"latitude": 30.5, "longitude": 75.0, "frp": 50, "daynight": "D", "acq_date": "2024-10-15"}
    result = classify_fire(row, land_use="farmland")
    assert result == "stubble"

def test_industrial_fire_high_frp():
    """Very high FRP near CPCB cluster = industrial."""
    row = {"latitude": 20.37, "longitude": 72.90, "frp": 400, "daynight": "N", "acq_date": "2024-06-01"}
    result = classify_fire(row, land_use="industrial")
    assert result == "gas_flare"

def test_wildfire_forest_land():
    """Hotspot in forest = wildfire."""
    row = {"latitude": 11.5, "longitude": 76.2, "frp": 80, "daynight": "D", "acq_date": "2024-03-10"}
    result = classify_fire(row, land_use="forest")
    assert result == "wildfire"

def test_agency_routing_industrial():
    """Industrial fire should route to PESO + State Fire Services."""
    agency = get_responding_agency("industrial")
    assert "PESO" in agency["agency"]
```

### Vessel Risk Score Tests (`tests/unit/test_vessel_risk_scorer.py`)
```python
from app.services.maritime.ais_fetcher import calculate_vessel_risk_score, is_vessel_in_mpa

def test_dark_vessel_high_score():
    """Vessel with 45-minute AIS gap should have score > 0.4."""
    vessel = {"LATITUDE": 18.0, "LONGITUDE": 72.5, "SPEED": 0, "TYPE": 70}
    score = calculate_vessel_risk_score(vessel, ais_gap_minutes=45)
    assert score >= 0.4

def test_vessel_in_gulf_of_kutch():
    """Coordinates inside Gulf of Kutch MNP should be detected."""
    result = is_vessel_in_mpa(22.5, 69.5)
    assert result is not None
    assert "Kutch" in result

def test_clean_vessel_low_score():
    """Normal vessel with no gap, not in MPA = low risk."""
    vessel = {"LATITUDE": 15.0, "LONGITUDE": 73.0, "SPEED": 120, "TYPE": 70}
    score = calculate_vessel_risk_score(vessel, ais_gap_minutes=0)
    assert score < 0.2
```

---

## Data Quality Checks (`tests/data/`)

```bash
# Run data validation on a fresh FIRMS download
python data_pipeline/validators/data_checker.py --file data_pipeline/sample.csv

# Expected output:
#   ✅ Rows: 1024
#   ✅ No null coordinates
#   ✅ All FRP values positive
#   ✅ Dates within expected range
#   ⚠️  12 rows with confidence=low (will be filtered)
```

---

## Manual API Test (check your keys work)

```bash
# Test FIRMS API key
curl "https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/?MAP_KEY=YOUR_KEY"
# Expected: {"current_transactions": 0, "transaction_limit": 5000}

# Test backend health
curl http://localhost:8000/api/v1/health
# Expected: {"status": "ok", "version": "1.0.0"}

# Test alerts endpoint
curl "http://localhost:8000/api/v1/alerts/?limit=10"
# Expected: {"alerts": [...], "total": N}
```

---

## Coverage Target

For SIH demo, target at minimum:
- Unit tests: > 80% coverage of `services/` folder
- All `classify_fire()` edge cases covered
- All `calculate_vessel_risk_score()` cases covered
- At least 1 integration test showing real FIRMS data flowing through
