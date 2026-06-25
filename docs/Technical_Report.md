# Technical Report: Entebbe Flight Tracker

**Customs declarations application with inspector audit filters**

Course 81213 FST, Advanced Application Design and Development, Coursework 2.
Project scenario 35.

---

## 1. Problem statement

Customs clearance at a busy international airport is a queue problem under time
pressure. Arriving passengers must declare goods, and a limited number of customs
inspectors must decide, quickly, which declarations to clear and which to examine
more closely. Doing this on paper is slow, hard to audit, and gives supervisors no
real-time view of throughput or risk.

The Entebbe Flight Tracker addresses this for Entebbe International Airport. It lets
travelers file a structured customs declaration against the flight they are
arriving on, before they reach the arrivals hall. It gives inspectors a single
audit queue with filters so they can triage by risk, flight, status, and date, and
record a decision with a reason. It gives a supervisor a live dashboard of volume,
risk distribution, and inspector activity, so staffing and attention can follow the
load. Every decision is written to an immutable audit trail.

## 2. Requirements

### 2.1 Functional requirements

| ID | Requirement |
|----|-------------|
| F1 | A traveler can register and sign in. |
| F2 | A traveler can file a declaration against an arriving flight, listing goods with category, quantity, and value. |
| F3 | The system assigns each declaration a unique reference and a computed risk level. |
| F4 | A traveler can view the status and history of their own declarations only. |
| F5 | An inspector can view all declarations in an audit queue. |
| F6 | An inspector can filter the queue by free text, status, risk, flight, and date. |
| F7 | An inspector can clear, flag, or mark a declaration inspected, and add a note. |
| F8 | Every submission and decision is recorded in an audit trail. |
| F9 | A supervisor can view aggregate analytics over all declarations. |
| F10 | A supervisor can manage the flight roster and staff accounts. |

### 2.2 Non-functional requirements

- **Security.** Hashed passwords, role-based access control, CSRF protection,
  input validation, and protection against SQL injection and XSS.
- **Performance.** List and dashboard queries must avoid the N+1 pattern and use
  indexes on filtered columns.
- **Portability.** The same code must run on localhost with SQLite and in the
  cloud with Postgres or MySQL, configured by environment variables.
- **Maintainability.** A clear MVC separation so each concern lives in one place.

### 2.3 Roles

Three roles, in increasing privilege: **traveler**, **customs inspector**, and
**supervisor** (admin). A supervisor can do everything an inspector can, plus
roster and user management.

## 3. System architecture

The application uses the Model, View, Controller pattern on a Flask backend.

```
Browser (HTML, CSS, vanilla JS, Chart.js)
        |  HTTPS, session cookie, CSRF token
        v
Controllers  ->  app/blueprints/{auth, traveler, inspector, admin, api}.py
        |            request handling, access checks, form processing
        v
Domain       ->  app/services.py (risk scoring, references, audit)
                 app/queries.py  (aggregations, N+1-safe reads)
        |
        v
Models (ORM) ->  app/models.py  (SQLAlchemy)
        |
        v
Database     ->  SQLite locally, Postgres or MySQL in the cloud
```

- **Models** define the tables, relationships, and indexes.
- **Views** are Jinja2 templates in `app/templates`, with autoescaping on. The
  browser holds no business logic; it renders server data and, on the dashboard,
  fetches small JSON aggregates to draw charts.
- **Controllers** are Flask blueprints, one per concern. Each protected route is
  guarded by an access decorator before any work runs.

The app is created by a factory (`create_app`) so configuration and extensions
(SQLAlchemy, CSRF) are bound explicitly, which keeps testing and cloud startup
clean.

## 4. Data model (ERD and schema)

### 4.1 Entity relationship diagram

```
        +---------+            +-------------------+           +-----------------+
        |  Flight |            |    Declaration    |           | DeclarationItem |
        +---------+            +-------------------+           +-----------------+
        | id (PK) |1----------*| id (PK)           |1---------*| id (PK)         |
        | flight_ |            | reference (unique)|           | declaration_id  |
        | number  |            | traveler_id  (FK) |           |  (FK)           |
        | airline |            | flight_id    (FK) |           | description     |
        | origin  |            | reviewed_by_ (FK) |           | category        |
        | sched_  |            | status            |           | quantity        |
        | arrival |            | risk_level        |           | unit_value      |
        +---------+            | currency          |           +-----------------+
                               | total_value       |
        +---------+            | created_at        |           +-----------------+
        |  User   |            | reviewed_at       |           |    AuditLog     |
        +---------+            +-------------------+           +-----------------+
        | id (PK) |1----------*| (traveler)        |1---------*| id (PK)         |
        | full_   |            | (reviewer)        |           | declaration_id  |
        | name    |*-----------| reviewed_by_id    |           |  (FK)           |
        | email   |            +-------------------+           | actor_id  (FK)  |
        | (unique)|                                            | action          |
        | passwd_ |1-------------------------------------------*| detail         |
        | hash    |   (actor)                                  | created_at      |
        | role    |                                            +-----------------+
        +---------+
```

Relationships:

- A **Flight** has many **Declarations**.
- A **User** (as traveler) has many **Declarations**; a **User** (as reviewer) may
  be linked to many reviewed declarations. Two distinct foreign keys from
  Declaration to User model these two roles.
- A **Declaration** has many **DeclarationItems** and many **AuditLog** entries.
- A **User** (as actor) writes many **AuditLog** entries.

### 4.2 Schema and indexes

| Table | Key columns | Indexes |
|-------|-------------|---------|
| `users` | id, email (unique), role, password_hash | `email`, `role` |
| `flights` | id, flight_number (unique), scheduled_arrival | `flight_number`, `scheduled_arrival` |
| `declarations` | id, reference (unique), traveler_id, flight_id, reviewed_by_id, status, risk_level, total_value, created_at | `reference`, `traveler_id`, `flight_id`, `reviewed_by_id`, `status`, `risk_level`, `created_at`, composite `(flight_id, status)`, composite `(status, created_at)` |
| `declaration_items` | id, declaration_id, category | `declaration_id`, `category` |
| `audit_logs` | id, declaration_id, actor_id, action, created_at | `declaration_id`, `actor_id`, `created_at` |

Indexing strategy: every foreign key is indexed because they are the join keys.
The inspector audit filters and the analytics aggregations both filter and group
on `status`, `risk_level`, `flight_id`, and `created_at`, so those carry single
and composite indexes. The composite `(flight_id, status)` index serves the common
"declarations on this flight still pending" query directly.

## 5. ORM transactions

All database work goes through the SQLAlchemy ORM. No raw SQL strings are built
from user input, which removes the SQL injection surface. Representative
transactions:

**Create (declaration with nested items, one unit of work).** The controller
builds the parent `Declaration` and its `DeclarationItem` children in memory,
computes the risk level, flushes to obtain the primary key, writes the audit row,
then commits once. Because the items are assigned to `declaration.items`,
SQLAlchemy inserts the parent and children in a single flush:

```python
declaration = Declaration(reference=generate_reference(), traveler_id=user.id,
                          flight_id=..., total_value=total, items=items, ...)
declaration.risk_level = score_risk(total, currency, items)
db.session.add(declaration)
db.session.flush()                 # parent + children inserted, PK available
record_audit(declaration, user, "submitted", ...)
db.session.commit()                # atomic
```

**Read without N+1 (queue and dashboard lists).** List views eager-load related
rows with `joinedload`, so one page of declarations is one SELECT with joins
rather than one query per row:

```python
Declaration.query.options(
    joinedload(Declaration.traveler),
    joinedload(Declaration.flight),
    joinedload(Declaration.reviewer),
).filter(...).order_by(Declaration.created_at.desc())
```

**Update (inspector decision).** The inspector review writes the new status, risk,
note, reviewer, and timestamp, appends an audit row, and commits as one
transaction, so a declaration and its audit trail never drift apart.

**Aggregate reads.** Dashboard figures are computed by the database with grouped
queries (see section 7), not by loading rows and counting in Python.

## 6. Security and RBAC architecture

Security is layered so that no single mistake is fatal.

- **Authentication.** Passwords are hashed with PBKDF2-SHA256 and a per-user salt
  through Werkzeug's `generate_password_hash`. Plaintext is never stored or logged.
  The session holds only the user id; the user record is reloaded each request, so
  a deactivated account loses access immediately.
- **Role-based access control.** Decorators in `app/security.py`
  (`login_required`, `role_required`, `admin_required`, `inspector_required`)
  guard every protected route. The check runs before any view logic, returns 403
  on a role mismatch, and is enforced on the JSON API as well as the pages. Server
  side enforcement means hiding a link in the UI is never the only control.
- **Row-level access.** A traveler can only read or act on declarations whose
  `traveler_id` matches their session user; any other id returns 403.
- **Privilege escalation prevention.** Public registration is hard-wired to the
  traveler role. Staff roles can only be granted by a supervisor.
- **CSRF.** Flask-WTF issues and validates a CSRF token on every state-changing
  form, including logout and the account toggle.
- **Input validation.** WTForms validates type, length, range, and required state
  on the server for every field before it reaches the database.
- **Injection defences.** The ORM parameterises all queries (no SQL injection).
  Jinja2 autoescaping encodes all rendered values (no stored or reflected XSS).
- **Cookie hardening.** Session cookies are HttpOnly and SameSite=Lax, and are
  marked Secure when `SESSION_COOKIE_SECURE=1` behind HTTPS.

The three roles map to permissions as follows:

| Capability | Traveler | Inspector | Supervisor |
|------------|:--------:|:---------:|:----------:|
| File and view own declarations | yes | yes (all) | yes (all) |
| View any declaration | no | yes | yes |
| Decide on a declaration | no | yes | yes |
| View analytics dashboard | no | no | yes |
| Manage flights | no | no | yes |
| Manage users | no | no | yes |

## 7. Visualization pipeline

The visualization is a thin client over a server that does the aggregation.

1. **Aggregate in SQL.** Functions in `app/queries.py` issue grouped queries, for
   example declarations grouped by status, by risk band, by day over the last 14
   days, the busiest flights by declaration count, and total declared value per
   goods category. Each is a single `GROUP BY` executed by the database.
2. **Serve small JSON.** Read-only endpoints under `app/blueprints/api.py`
   (`/api/analytics/...`) return only labels and values, restricted to inspector
   and supervisor roles. A page of charts transfers a few hundred bytes, not the
   underlying rows.
3. **Draw in the browser.** `app/static/js/dashboard.js` fetches the endpoints in
   parallel and renders them with Chart.js: a filled line for the daily trend,
   doughnuts for status and risk, and horizontal bars for flights and categories.
   The browser performs no aggregation.

The same pattern drives the geographic view. `/api/geo/origins` returns each
flight origin with its declaration and flagged counts (a grouped query joining
flights and declarations), and the arrivals map (Leaflet with OpenStreetMap
tiles) draws a weighted route from each origin to Entebbe.

This separation keeps the payload small, keeps business logic on the server, and
means the same aggregates could feed any other client.

## 8. Cloud deployment steps

The application is configured entirely through environment variables
(`config.py`), so deployment needs no code changes.

1. Push the repository to GitHub.
2. On the host (for example Render), create a web service from the repo with build
   command `pip install -r requirements.txt`.
3. Provision a managed Postgres database. Add `psycopg2-binary` to requirements.
4. Set environment variables: `SECRET_KEY` (long random), `DATABASE_URL` (the
   Postgres URL), and `SESSION_COOKIE_SECURE=1`.
5. Initialise the schema once, either by running `python seed.py` as a one-off job
   or by running your own migration step.
6. Set the start command to a production WSGI server:
   `gunicorn "app:create_app()"`.
7. Point the platform health check at `/healthz`.

## 9. Testing and verification

The application was verified end to end with Flask's test client and by driving
the running app in a browser. Confirmed behaviours: successful and rejected
logins, traveler declaration submission, the RBAC decorators returning 403 to a
traveler reaching inspector or admin routes, the JSON analytics endpoints
returning correct grouped values, the inspector filters narrowing the queue, and
all dashboards rendering. Screenshots of each role are in `docs/screenshots`.

## 10. Conclusion

The Entebbe Flight Tracker delivers the scenario in full: a data-driven MVC web
application with three roles, a risk-scored inspector audit queue with filters,
a supervisor analytics dashboard built on database aggregations, and a defensive
security posture covering hashing, RBAC, CSRF, validation, and injection
protection. The schema is normalised and indexed for the queries the application
actually runs, and the configuration is portable from localhost to the cloud.
