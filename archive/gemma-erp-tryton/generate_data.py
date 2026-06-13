#!/usr/bin/env python
"""Generate synthetic, internally-consistent ERP history into the local Tryton DB.

Everything is routed through proteus (Tryton's official scripting layer) so that
every invoice, account move and stock move respects the same business logic the
GUI enforces. The script is config-driven (env vars) and re-runnable: master
data setup is idempotent; transactional documents are always appended.

Env config (all optional, sensible "medium" defaults):
  TRYTON_DB         database name              (default: tryton)
  TRYTON_CONFIG     trytond config file        (default: trytond.conf)
  N_CUSTOMERS       customer parties to ensure (default: 80)
  N_SUPPLIERS       supplier parties to ensure (default: 20)
  N_PRODUCTS        products to ensure         (default: 40)
  START_YEAR        first fiscal year          (default: 2021)
  END_YEAR          last fiscal year           (default: 2025)
  N_SALES           sale orders to create      (default: 2600)
  N_PURCHASES       purchase orders to create  (default: 1300)
  SEED              RNG seed for reproducibility (default: 42)
"""
import os
import sys
import random
import datetime as dt
from decimal import Decimal

from proteus import config as pconfig, Model
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.modules.account.tests.tools import (
    create_fiscalyear, create_chart, get_accounts)
from trytond.modules.account_invoice.tests.tools import (
    set_fiscalyear_invoice_sequences)

# ----------------------------------------------------------------------------- config
DB = os.environ.get('TRYTON_DB', 'tryton')
CONFIG_FILE = os.environ.get('TRYTON_CONFIG', 'trytond.conf')
N_CUSTOMERS = int(os.environ.get('N_CUSTOMERS', 80))
N_SUPPLIERS = int(os.environ.get('N_SUPPLIERS', 20))
N_PRODUCTS = int(os.environ.get('N_PRODUCTS', 40))
START_YEAR = int(os.environ.get('START_YEAR', 2021))
END_YEAR = int(os.environ.get('END_YEAR', 2025))
N_SALES = int(os.environ.get('N_SALES', 2600))
N_PURCHASES = int(os.environ.get('N_PURCHASES', 1300))
SEED = int(os.environ.get('SEED', 42))

random.seed(SEED)


def log(msg):
    print(msg, flush=True)


def random_business_date():
    """Uniform random weekday in [START_YEAR-01-01, END_YEAR-12-31]."""
    start = dt.date(START_YEAR, 1, 1)
    end = dt.date(END_YEAR, 12, 31)
    span = (end - start).days
    while True:
        d = start + dt.timedelta(days=random.randint(0, span))
        if d.weekday() < 5:  # Mon-Fri
            return d


def advance(doc, transitions):
    """Click workflow buttons until terminal state, guided by a state->button map."""
    for _ in range(12):
        doc.reload()
        btn = transitions.get(doc.state)
        if not btn:
            break
        doc.click(btn)
    return doc.state


# ----------------------------------------------------------------------------- connect
log("Connecting to Tryton DB '%s' ..." % DB)
cfg = pconfig.set_trytond(DB, config_file=CONFIG_FILE)

# ----------------------------------------------------------------------------- company
Company = Model.get('company.company')
if not Company.find():
    log("Creating company (EUR) ...")
    try:
        from trytond.modules.currency.tests.tools import get_currency
        eur = get_currency('EUR')
    except Exception as e:
        log("  (could not preset EUR currency: %s)" % e)
        eur = None
    create_company(currency=eur)
company = get_company()
log("Company: %s (id=%s)" % (company.party.name, company.id))
User = Model.get('res.user')
cfg.set_context(User.get_preferences(True, cfg.context))

# Bulk load: auto-acknowledge all confirm-warnings (e.g. "payment date in the
# past" on historical invoices). The GUI handles these by having the user click
# "ignore"; the `_skip_warnings` context flag can't be used because trytond's RPC
# layer strips every "_"-prefixed context key. proteus runs trytond in-process,
# so we neutralise the warning gate directly in the pool for this run.
from trytond.pool import Pool
Pool(DB).get('res.user.warning').check = classmethod(lambda cls, name: False)

# ----------------------------------------------------------------------------- chart of accounts
Account = Model.get('account.account')
existing_accounts = Account.find([('company', '=', company.id)])
if not existing_accounts:
    log("Creating chart of accounts ...")
    create_chart(company)
accounts = get_accounts(company)
revenue = accounts['revenue']
expense = accounts['expense']
log("Accounts ready (receivable=%s payable=%s revenue=%s expense=%s)"
    % (accounts['receivable'].code, accounts['payable'].code,
       revenue.code, expense.code))

# ----------------------------------------------------------------------------- fiscal years
FiscalYear = Model.get('account.fiscalyear')
have_years = {fy.name for fy in FiscalYear.find([('company', '=', company.id)])}
for year in range(START_YEAR, END_YEAR + 1):
    if str(year) in have_years:
        continue
    log("Creating fiscal year %s ..." % year)
    # create_fiscalyear's default span is July-June; force a real calendar year
    fy = create_fiscalyear(company, dt.date(year, 1, 1))
    fy.name = str(year)
    fy.start_date = dt.date(year, 1, 1)
    fy.end_date = dt.date(year, 12, 31)
    fy = set_fiscalyear_invoice_sequences(fy)
    fy.click('create_period')

# ----------------------------------------------------------------------------- payment terms
PaymentTerm = Model.get('account.invoice.payment_term')
terms = PaymentTerm.find([('name', '=', 'Net 30')])
if terms:
    payment_term = terms[0]
else:
    log("Creating payment term 'Net 30' ...")
    payment_term = PaymentTerm(name='Net 30')
    line = payment_term.lines.new(type='remainder')
    line.relativedeltas.new(days=30)
    payment_term.save()

# ----------------------------------------------------------------------------- product category (links accounts)
ProductCategory = Model.get('product.category')
cats = ProductCategory.find([('name', '=', 'Goods (accounting)')])
if cats:
    account_category = cats[0]
else:
    log("Creating accounting product category ...")
    account_category = ProductCategory(name='Goods (accounting)')
    account_category.accounting = True
    account_category.account_revenue = revenue
    account_category.account_expense = expense
    account_category.save()

# ----------------------------------------------------------------------------- units
ProductUom = Model.get('product.uom')
unit, = ProductUom.find([('name', '=', 'Unit')])

# ----------------------------------------------------------------------------- products
ProductTemplate = Model.get('product.template')
Product = Model.get('product.product')
ADJ = ['Premium', 'Standard', 'Eco', 'Pro', 'Compact', 'Heavy-Duty', 'Smart',
       'Classic', 'Industrial', 'Mini']
NOUN = ['Pump', 'Valve', 'Boiler', 'Sensor', 'Thermostat', 'Filter', 'Pipe',
        'Heater', 'Controller', 'Manifold', 'Gauge', 'Compressor']
products = Product.find([('template.salable', '=', True)])
existing_n = len(products)
for i in range(existing_n, N_PRODUCTS):
    name = "%s %s %04d" % (random.choice(ADJ), random.choice(NOUN), i + 1)
    list_price = Decimal(random.randint(20, 2000))
    tmpl = ProductTemplate()
    tmpl.name = name
    tmpl.default_uom = unit
    tmpl.type = 'goods'
    tmpl.salable = True
    tmpl.purchasable = True
    tmpl.list_price = list_price
    tmpl.sale_uom = unit
    tmpl.purchase_uom = unit
    tmpl.account_category = account_category
    tmpl.save()
    prod = tmpl.products[0]
    prod.cost_price = (list_price * Decimal('0.6')).quantize(Decimal('0.01'))
    prod.save()
products = Product.find([('template.salable', '=', True)])
log("Products available: %d" % len(products))

# ----------------------------------------------------------------------------- parties
Party = Model.get('party.party')
CITIES = ['Aachen', 'Köln', 'Düsseldorf', 'Berlin', 'München', 'Hamburg',
          'Frankfurt', 'Stuttgart', 'Dresden', 'Leipzig']
FORMS = ['GmbH', 'AG', 'KG', 'e.K.', 'GmbH & Co. KG', 'OHG']


def ensure_parties(prefix, target, is_customer):
    existing = Party.find([('name', 'like', prefix + ' %')])
    for i in range(len(existing), target):
        p = Party(name="%s %s %s %04d"
                  % (prefix, random.choice(CITIES), random.choice(FORMS), i + 1))
        if is_customer:
            p.customer_payment_term = payment_term
        else:
            p.supplier_payment_term = payment_term
        p.save()
    return Party.find([('name', 'like', prefix + ' %')])


log("Ensuring parties ...")
customers = ensure_parties('Customer', N_CUSTOMERS, True)
suppliers = ensure_parties('Supplier', N_SUPPLIERS, False)
log("Customers: %d  Suppliers: %d" % (len(customers), len(suppliers)))

# ----------------------------------------------------------------------------- sales
Sale = Model.get('sale.sale')
SALE_FLOW = {'draft': 'quote', 'quotation': 'confirm'}
OUT_FLOW = {'draft': 'wait', 'waiting': 'assign_force', 'assigned': 'pick',
            'picked': 'pack', 'packed': 'ship', 'shipped': 'do'}

log("Creating %d sale orders ..." % N_SALES)
# Post in non-decreasing date order: customer-invoice numbering enforces that
# no already-posted invoice in the sequence has a later date.
sale_dates = sorted(random_business_date() for _ in range(N_SALES))
for n in range(N_SALES):
    try:
        sale = Sale()
        sale.party = random.choice(customers)
        sale.sale_date = sale_dates[n]
        for _ in range(random.randint(1, 4)):
            line = sale.lines.new()
            line.product = random.choice(products)
            line.quantity = random.randint(1, 10)
        sale.save()
        advance(sale, SALE_FLOW)            # -> confirmed (auto-processes)
        sale.reload()
        for inv in sale.invoices:
            inv.reload()
            if inv.state in ('draft', 'validated'):
                if not inv.invoice_date:
                    inv.invoice_date = sale.sale_date  # inside a fiscal period
                    inv.save()
                inv.click('post')
        for shp in sale.shipments:
            advance(shp, OUT_FLOW)
    except Exception as e:
        log("  ! sale %d skipped: %s" % (n + 1, str(e)[:90]))
    if (n + 1) % 50 == 0:
        log("  sales %d/%d" % (n + 1, N_SALES))
log("Sales done.")

# ----------------------------------------------------------------------------- purchases
Purchase = Model.get('purchase.purchase')
PURCHASE_FLOW = {'draft': 'quote', 'quotation': 'confirm'}
IN_FLOW = {'draft': 'receive', 'received': 'do'}

log("Creating %d purchase orders ..." % N_PURCHASES)
purchase_dates = sorted(random_business_date() for _ in range(N_PURCHASES))
for n in range(N_PURCHASES):
    try:
        purchase = Purchase()
        purchase.party = random.choice(suppliers)
        purchase.purchase_date = purchase_dates[n]
        for _ in range(random.randint(1, 3)):
            line = purchase.lines.new()
            line.product = random.choice(products)
            line.quantity = random.randint(1, 20)
            if not line.unit_price:
                line.unit_price = (line.product.cost_price or Decimal('1.0'))
        purchase.save()
        advance(purchase, PURCHASE_FLOW)    # -> confirmed (auto-processes)
        purchase.reload()
        for shp in purchase.shipments:
            advance(shp, IN_FLOW)
        purchase.reload()
        for inv in purchase.invoices:
            inv.reload()
            if inv.state in ('draft', 'validated'):
                if not inv.invoice_date:
                    inv.invoice_date = purchase.purchase_date  # fiscal period
                    inv.save()
                inv.click('post')
    except Exception as e:
        log("  ! purchase %d skipped: %s" % (n + 1, str(e)[:90]))
    if (n + 1) % 50 == 0:
        log("  purchases %d/%d" % (n + 1, N_PURCHASES))
log("Purchases done.")

# ----------------------------------------------------------------------------- summary
Invoice = Model.get('account.invoice')
Move = Model.get('account.move')
log("=" * 50)
log("DONE. Current totals in DB '%s':" % DB)
log("  parties:        %d" % len(Party.find([])))
log("  products:       %d" % len(Product.find([])))
log("  sales:          %d" % len(Sale.find([])))
log("  purchases:      %d" % len(Purchase.find([])))
log("  invoices:       %d" % len(Invoice.find([])))
log("  account moves:  %d" % len(Move.find([])))
