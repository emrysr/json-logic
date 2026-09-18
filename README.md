# json-logic booking demo

A standalone Django proof-of-concept exploring **json-logic as a single source of
truth for business rules shared between Python (server-side) and JavaScript
(client-side)**, built around a golf club booking scenario.

## What this demonstrates

- **A schema-driven admin form.** `ClubRules` (`admin_demo/models.py`) stores a
  club's booking configuration as a single JSON field. Rather than a raw JSON
  textarea, `admin_demo/formkit_widget.py` renders it as a proper form (radios,
  selects, checkboxes) using [FormKit](https://formkit.com/) loaded via CDN -
  the schema is a plain Python data structure, so adding a field is a Python
  change, not a template change.
- **Shared json-logic rules.** `admin_demo/logic.py` defines booking-eligibility
  rules (which player categories can book a given fairway at a given day/time;
  whether a player's category is eligible; whether a player's handicap meets a
  club's configured minimum) as [json-logic](http://jsonlogic.com/) rule trees.
  Each rule is evaluated identically by Python (`json-logic-qubit`) and by the
  browser (`json-logic-js`) - the same rule, not a reimplementation.
- **A DRF endpoint serving pure logic.** `/api/logic/booking` returns the rule
  trees (plus a `description` and `message` for each) as JSON, so any client
  can fetch and evaluate them without duplicating the business logic.
- **Server-rendered first paint, client-side re-evaluation after that.** The
  `/logic-demo` page computes its initial state entirely server-side (calling
  the same `admin_demo.logic` functions a real view would), then re-runs the
  same rules in the browser via `json-logic-js` whenever you change the
  teetime - fetching `/api/logic/booking` once on page load, not per click.

## Requirements

- Python 3.12+ (tested with the pinned versions in `requirements.txt`)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

Standard Django workflow:

```bash
./manage.py migrate
./manage.py seed_demo_data   # creates admin/admin superuser + club_1/club_2 ClubRules
./manage.py runserver
```

- **Admin:** http://localhost:8000/admin/ (login `admin` / `admin`) -
  `Club ruless` shows the FormKit-rendered booking rules for each club.
- **Logic demo:** http://localhost:8000/ (or http://localhost:8000/logic-demo/)
  - pick a teetime (from the mocked teesheet's actual bookable slots) and see
  which players are eligible to book, broken down by category rule and by
  minimum-handicap rule independently, plus the raw input data and rule trees
  used to compute it.
- **API:** http://localhost:8000/api/logic/booking - the raw json-logic rule
  trees, as fetched by the demo page's JS.

## Mock data

`admin_demo/fixtures/example_teesheet.json` and
`admin_demo/fixtures/example_players.json` stand in for two real API responses
(a teesheet lookup and a player search) - shaped to match their real
counterparts' JSON structure, but hand-edited to make the rule filtering
visibly do something (e.g. the `Guest` category is restricted to afternoon
bookings, `Colt` to before-noon bookings). Edit these files directly to try
different scenarios; the page re-reads them on every request, no restart
needed. `./manage.py runserver` auto-reloads on Python/template changes like
any standard Django project.
