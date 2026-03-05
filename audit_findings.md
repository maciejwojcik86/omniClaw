Audit of the repository for weak points, inconsistencies, and scalability/developer-experience improvements with concrete file-level fixes. 

## Review agent report 
Here are the key findings and concrete fixes:

1. High: Runtime command injection risk in gateway start
    - Risk: gateway_host is interpolated into shell command construction.
    - References: schemas.py (line 14), service.py (line 379), service.py (line 415), service.py (line 468)
    - Specific solution: replace shell-string launch with subprocess.Popen([...], shell=False) argv composition; validate gateway_host strictly (ipaddress + hostname validation).
    - Verification: add test with gateway_host="127.0.0.1;touch /tmp/pwned" and assert rejection + no side effects.
2. High: IPC auto-scan has scaling/event-loop blocking behavior
    - Risk: scanner keeps traversing after limit; sync scan work runs inside async loop.
    - References: ipc/service.py (line 63), ipc/service.py (line 64), app.py (line 39), app.py (line 43)
    - Specific solution: break traversal once scanned == limit; run scan via asyncio.to_thread(...) or move to dedicated worker.
    - Verification: load test with large pending dir + limit=10, assert bounded runtime and low /healthz latency.
3. High: Form transition sequencing is race-prone
    - Risk: read-check-write plus max(sequence)+1 can conflict under concurrency.
    - References: repository.py (line 528), repository.py (line 543), repository.py (line 556), models.py (line 158)
    - Specific solution: add optimistic locking/version column or transactional lock + retry on IntegrityError; make sequence allocation atomic.
    - Verification: concurrent transition test on same form should produce deterministic conflict handling and unique sequence.
4. Medium: Startup bypasses migration contract via create_all
    - Risk: schema drift from Alembic history.
    - References: app.py (line 29), session.py (line 43)
    - Specific solution: remove runtime create_all; require alembic upgrade head or fail fast if DB revision is behind.
    - Verification: startup fails on un-migrated DB; passes after migration.
5. Medium: Undelivered IPC files not dead-lettered
    - Risk: repeated retries/noise; same bad file reprocessed every scan.
    - References: config.py (line 24), ipc/service.py (line 923), test_ipc_actions.py (line 401)
    - Specific solution: move undelivered files to dead-letter dir; persist dead-letter metadata; skip unless explicitly requeued.
    - Verification: malformed file dead-lettered once, not reprocessed on next scan.
6. Medium: Tests out of sync with current validation behavior
    - Risk: CI instability; currently failing.
    - References: forms/service.py (line 1083), test_forms_actions.py (line 670), test_ipc_actions.py (line 288), test_ipc_actions.py (line 719)
    - Specific solution: update fixtures to include required skills or assert validation errors intentionally.
    - Verification: uv run pytest -q green; include explicit missing-skill negative test.

7. Low: Duplicate logic likely to drift
    - Risk: inconsistent behavior over time.
    - References: repository.py (line 104), repository.py (line 133), ipc/service.py (line 815), forms/service.py (line 1211)
    - Specific solution: extract shared resolver/helper and consolidate manager-link code paths.
    - Verification: unit tests around shared helper edge cases.

