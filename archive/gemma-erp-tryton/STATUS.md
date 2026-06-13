# Gemma-controls-ERP experiment — STATUS

**Goal:** test whether a vision LLM (Gemma) can control a legacy/retro, menu-driven
desktop ERP from screenshots. Test target = **Tryton desktop client** (native GTK,
SQLite backend) plus, as a simpler fallback, **GnuCash**. Both must run in **English**
even though macOS is set to German.

Last updated: 2026-06-13. Paused mid data-generation (see "Where we stopped").

---

## What works right now

### Apps installed & forced to English (system stays German)
- **GnuCash 5.15** — `/Applications/Gnucash.app` (installed via `brew install --cask gnucash`).
  Forced to English per-app: `defaults write org.gnucash.Gnucash AppleLanguages '("en-US","en")'`.
  Verified (startup language list begins `en:en_US`). **Still needs** the one-time
  `File → Save As → SQLite3` step to create a SQLite book (no headless way) — intended
  location: `../gemma-erp-gnucash/`. GnuCash is the low-friction fallback target.
- **Tryton 8.0 desktop client** — `/Applications/Tryton.app` (from `tryton-client.dmg`).
  Forced to English by editing its own config: `~/.config/tryton/8.0/tryton.conf`
  → `[client] lang = en_US` (the macOS AppleLanguages trick does NOT work for it).
  NOTE: its saved login profile still points at the public demo `demo8.0.tryton.org`.
  For our data, connect to the **local** server instead (see below).

### Tryton local server (SQLite)
- Server: `./venv/bin/trytond -c trytond.conf -d tryton` → serves `http://localhost:8000`.
- DB: SQLite at `data/tryton.sqlite` (config `trytond.conf`: `uri = sqlite://`, `path = data`).
- Admin password lives in `.adminpass`; admin email set to `admin@curavani.local`.
- 14 business modules activated: company, party, product, account, account_invoice,
  account_invoice_stock, account_product, sale, purchase, stock (+ deps country, currency, ir, res).

### Synthetic data already in the DB (as of pause)
| thing | count |
|---|---|
| customers | 80 |
| suppliers | 20 |
| products | 40 |
| sales orders | 2,418 |
| customer shipments | 2,418 |
| customer invoices (posted) | 2,418 |
| account moves | 2,418 |
| **purchases** | **0** (not started) |
| fiscal years | 2021–2025 (true calendar years, 12 periods each) |

So: **Sales + Invoicing + Accounting + outbound Stock are fully populated for 5 years.**
Purchases (supplier side) and inbound stock are **not yet generated**.

---

## Where we stopped

The full generation run (`generate_data.py`) completed **all sales** but **crashed at the
very start of the purchase phase** — actually it crashed on the *last* sale iteration
(~#2419) when `inv.click('post')` was called on an invoice that was already `posted`
(state ≠ draft), raising `AccessButtonError`. Root cause not 100% pinned (a single
anomalous already-posted invoice resurfaced via `sale.invoices`; grouping is OFF and that
invoice maps to only one sale, so it's a rare edge case, not systemic).

**Fix already applied to `generate_data.py` (committed in the file, NOT yet re-run):**
both the sales loop and the purchase loop now (a) wrap each document in `try/except`
(log "skipped" + continue, so one bad doc can't abort the whole run) and (b) `reload()`
each invoice and only post when `state in ('draft','validated')`.

---

## How to resume (next session)

The script is **config-driven (env vars)** and **re-runnable**: master-data setup is
idempotent; transactional docs are always appended. So to finish the dataset:

```bash
cd ~/Documents/Curavani/Hackathons/gemma-erp-tryton
pkill -f "trytond -c trytond.conf"          # free the SQLite file (no live server during load)
DYLD_LIBRARY_PATH=/opt/homebrew/lib \
  N_CUSTOMERS=80 N_SUPPLIERS=20 N_PRODUCTS=40 \
  START_YEAR=2021 END_YEAR=2025 \
  N_SALES=0 N_PURCHASES=1300 \              # sales already done → add only purchases
  ./venv/bin/python generate_data.py > gen_resume.log 2>&1 &
tail -f gen_resume.log
```
(Use `N_SALES=200` instead of 0 if you want to top sales up toward ~2,600.)
Rate is ~1–1.5 docs/sec on SQLite, so 1,300 purchases ≈ 20–30 min.

Then restart the server for the GUI:
```bash
./venv/bin/trytond -c trytond.conf -d tryton >> server.log 2>&1 &
open -a Tryton    # connect to localhost:8000, db "tryton", admin pw in .adminpass
```

### If you ever need a clean DB from scratch
```bash
pkill -f "trytond -c trytond.conf"
rm -f data/tryton.sqlite && : > data/tryton.sqlite
TRYTONPASSFILE=.adminpass ./venv/bin/trytond-admin -c trytond.conf -d tryton \
  --email admin@curavani.local --activate-dependencies \
  -u company party product account account_invoice account_invoice_stock \
     account_product sale purchase stock
# then run generate_data.py with full N_SALES / N_PURCHASES
```

---

## Hard-won gotchas (don't re-learn these)

1. **trytond strips `_`-prefixed context keys over RPC** (rpc.py `convert`), so the
   `_skip_warnings` flag can't be passed. proteus runs trytond **in-process**, so the
   script neutralises the warning gate directly in the pool:
   `Pool(DB).get('res.user.warning').check = classmethod(lambda cls, name: False)`.
   Needed because every historical invoice trips the "payment date in the past" warning.
2. **Invoice numbering is strictly date-ordered** for customer (`out`) invoices: you cannot
   post an invoice dated earlier than one already posted in the same sequence. → the script
   pre-sorts sale/purchase dates ascending so posting is always non-decreasing.
3. **Test-tool fiscal years are July–June**, not calendar years. The script overrides
   `start_date`/`end_date` to Jan 1–Dec 31 before `create_period`.
4. **Invoice accounting date defaults to *today*** (2026, outside our fiscal years) → the
   script stamps each invoice with the document's historical date before posting.
5. **trytond SQLite won't create the DB file itself** → `: > data/tryton.sqlite` first.
6. **trytond-admin email prompt** blocks non-interactive init → always pass `--email`.
7. **`libmagic`** is an optional dep for invoice-report image handling; installed via
   `brew install libmagic`, pass `DYLD_LIBRARY_PATH=/opt/homebrew/lib` when running.
8. Workflow button names (8.0): customer shipment `wait→assign_force→pick→pack→ship→do`;
   supplier shipment `receive→do`; sale/purchase `quote→confirm` (auto-processes).

## Key files here
- `generate_data.py` — the data generator (resilience fix applied, not yet re-run).
- `trytond.conf`, `.adminpass`, `data/tryton.sqlite` — local Tryton server + DB.
- `venv/` — Python env with trytond 8.0.4 + proteus + business modules.
- `gen_full.log` — log of the run that crashed (sales complete, purchases not started).
