"""A group's report as a PDF: balances, who pays whom, expense history and settlements."""
from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from .money import rupees, who_owes_whom
from .services import calculate_balances

styles = getSampleStyleSheet()
PAGE_WIDTH = A4[0] - 2 * inch  # SimpleDocTemplate leaves a 1 inch margin on each side


def money(paise):
    """120050 -> "Rs 1200.50", -40000 -> "-Rs 400.00". The built-in PDF fonts have no ₹ sign."""
    return f"-Rs {rupees(-paise)}" if paise < 0 else f"Rs {rupees(paise)}"


def people(rows):
    """Payers or shares as "Mohit 600.00, Ankit 300.00"."""
    return ", ".join(f"{row.user.name} {rupees(row.amount_paise)}" for row in rows)


def text(value, style="BodyText"):
    return Paragraph(escape(str(value)), styles[style])  # escape: "Tax & charges" is text, not markup


def table(header, rows, widths=None):
    """A grid with a grey header row. Long text wraps inside its cell."""
    widths = widths or [PAGE_WIDTH / len(header)] * len(header)
    grid = Table([header] + [[text(cell) for cell in row] for row in rows], colWidths=widths, repeatRows=1)
    grid.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return grid


def expense_row(expense):
    payers = expense.payments.all()
    paid_by = payers[0].user.name if len(payers) == 1 else people(payers)
    title = expense.description
    if expense.split_type == "itemized":
        title += " (" + ", ".join(item.name for item in expense.items.all()) + ")"
    return [expense.created_at.strftime("%d %b %Y"), title, money(expense.amount_paise), paid_by, people(expense.splits.all())]


def group_pdf(group):
    """Builds the report in memory and returns the PDF file as bytes."""
    balances = calculate_balances(group).values()
    payments = who_owes_whom({balance["name"]: balance["net"] for balance in balances})
    expenses = group.expenses.prefetch_related("payments__user", "splits__user", "items")
    settlements = group.settlements.select_related("from_user", "to_user")

    page = [
        text(group.name, "Title"),
        text("Members: " + ", ".join(balance["name"] for balance in balances)),
        text(f"Exported on {timezone.now():%d %b %Y}"),

        text("Balances", "Heading2"),
        table(["Name", "Paid", "Share", "Net"],
              [[b["name"], money(b["paid"]), money(b["share"]), money(b["net"])] for b in balances]),

        text("Who pays whom to settle up", "Heading2"),
        table(["From", "To", "Amount"], [[debtor, creditor, money(amount)] for debtor, creditor, amount in payments])
        if payments else text("Everyone is settled up."),

        text("Expense history (newest first)", "Heading2"),
        table(["Date", "Expense", "Amount", "Paid by", "Each person's share"],
              [expense_row(expense) for expense in expenses],
              widths=[0.16 * PAGE_WIDTH, 0.24 * PAGE_WIDTH, 0.15 * PAGE_WIDTH, 0.18 * PAGE_WIDTH, 0.27 * PAGE_WIDTH])
        if expenses else text("No expenses yet."),

        text("Settlements", "Heading2"),
        table(["Date", "From", "To", "Amount"],
              [[s.created_at.strftime("%d %b %Y"), s.from_user.name, s.to_user.name, money(s.amount_paise)] for s in settlements])
        if settlements else text("No settlements yet."),
    ]

    buffer = BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4, title=f"{group.name} expenses").build(page)
    return buffer.getvalue()
