# Demo Video Script (Proof of Execution)

A two to three minute screen recording covers the deliverable's video proof. Run
`python seed.py` then `python run.py` first, and record at 1280x800 or larger.

1. **Start (0:00).** Show the terminal running `python run.py`, then open
   http://127.0.0.1:5000. The sign-in page loads.

2. **Traveler (0:15).** Sign in as `aisha@example.com` / `Traveler#2026`. Open
   "New declaration", pick a flight, add two items (for example a laptop at 1200
   and a camera at 2200), and submit. Show the new reference and that the status is
   pending. Open "My declarations" to show the list. Sign out.

3. **Inspector (1:00).** Sign in as `patrick@entebbe.go.ug` / `Inspector#2026`.
   In the audit queue, apply a filter (status = pending, risk = high) and show the
   list narrowing. Open the declaration you just filed, choose "Clear declaration",
   add a note, and save. Show the audit trail updating. Sign out.

4. **Supervisor (1:45).** Sign in as `supervisor@entebbe.go.ug` /
   `Supervisor#2026`. Show the dashboard charts loading: the trend line, status
   and risk doughnuts, busiest flights, and value by category. Open "Users" and
   show creating or deactivating a staff account. Open "Flights" and add a flight.

5. **Security note (2:30).** Briefly show that opening `/admin/` while signed in as
   a traveler returns a 403 page, demonstrating role-based access control.

6. **Close.** Mention the GitHub repository and that the technical report and user
   manual are in `docs/`.
