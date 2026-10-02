"""The three states. There are never two.

FOUND      evidence exists, with its page.
NOT_FOUND  nothing was found AND every page was read. Only then is a negative allowed.
CANNOT_SAY nothing was found, but at least one page could not be read. Not a negative.
"""
import re

FOUND, NOT_FOUND, CANNOT_SAY = "FOUND", "NOT_FOUND", "CANNOT_SAY"


def norm(s):
    """Lowercase, straighten quotes, collapse whitespace. Used to compare a quote to a page."""
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def digits(s):
    """A number with its separators removed: '$2,100,000.00' and '2100000' compare equal."""
    s = re.sub(r"[^\d.,]", "", s).rstrip(".,")
    s = re.sub(r"[.,]\d{2}$", "", s)          # drop cents
    return re.sub(r"\D", "", s)


def quote_on_page(quote, page_text):
    """True only if the quote is literally on the page (after whitespace and case normalisation)."""
    q = norm(quote)
    return len(q) >= 6 and q in norm(page_text)


def decide(evidence, doc):
    if evidence:
        return FOUND
    return CANNOT_SAY if doc["unreadable"] else NOT_FOUND


def coverage_line(doc):
    line = "read %d of %d pages" % (doc["readable"], doc["total"])
    if doc["unreadable"]:
        line += "; could NOT read page(s) %s" % ", ".join(str(n) for n in doc["unreadable"])
    return line
