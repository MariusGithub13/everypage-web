"""Read a PDF page by page and record, for each page, HOW it was read and whether it worked.

A page with no text layer is a scan, not an empty page. A scan that was OCR'd sideways is
garbage that looks like text. Both are measured here, so nothing downstream has to guess.
"""
import os
import re
import subprocess
import tempfile

MIN_TEXT_CHARS = 40      # below this a page's text layer is treated as absent
MIN_LEGIBILITY = 0.18    # share of tokens that are everyday words of the language
OCR_DPI = int(os.environ.get("EVERYPAGE_OCR_DPI", "300"))
OCR_LANG = os.environ.get("EVERYPAGE_OCR_LANG", "eng+ron")   # the default, "en": English or Romanian
THUMB_DPI = 60

# Nonsense like "pebueyoun" is full of vowels, so a vowel test passes OCR garbage. Real prose is
# recognisable by its small everyday words, so those are counted instead. English and Romanian.
COMMON = set("""a about after all also an and any are as at be been before but by can could day did do each
for from had has have he her his if in into is it its may more most must no not of on one only or other our
out over shall she should so such than that the their them then there these they this to under up upon was
we were what when which who will with within would year you your said between agreement date amount paid pay
total page section party parties property price seller buyer signed name number address
si în in la de pe cu din care ca sa să se un o este sunt nu au fost prin pentru sau al ale ai lui ei lor
acest aceasta această aceste cel cea cele mai dar după dupa până pana fi va vor are fără fara către catre
între intre privind conform art nr lei data anul lege legea hotărârea hotararea consiliul local primar
primarul comuna oraș oras județ judet contract valoare suma total pagina articol alin anexa""".split())

# 23.10.2026: a scan in another language. The visitor picks the document's language, and ONLY that language
# is OCR'd, so the default (English or Romanian) stays exactly as fast and as accurate as before. Each language
# brings its own everyday words, plus English ones, because documents mix them (names, terms, headings).
LANG_WORDS = {
    "de": set("""der die das den dem des ein eine einer eines einem und oder nicht ist sind war wird werden wurde
hat haben sein mit von zu zum zur im in an auf aus bei nach vor über unter für durch gegen ohne als wie auch nur
noch so dass sich sie er es wir ihr ihre sein seine dieser diese dieses jahr datum betrag summe vertrag seite
käufer verkäufer kaufpreis preis euro zahlung gemäß nach abs artikel vereinbarung unterschrift name anschrift""".split()),
    "fr": set("""le la les un une des du de et ou ne pas est sont était sera ont a avec pour par dans sur sous
en au aux ce cette ces qui que dont il elle ils elles nous vous leur leurs son sa ses plus selon entre après avant
date montant somme total prix contrat page article acheteur vendeur paiement euros signé nom adresse année""".split()),
    "es": set("""el la los las un una unos unas de del y o no es son era será han ha con para por en sobre bajo
al lo que cual se su sus este esta estos estas entre después antes según fecha importe suma total precio contrato
página artículo comprador vendedor pago euros firmado nombre dirección año partes""".split()),
    "it": set("""il lo la i gli le un una uno di del della dei delle e o non è sono era sarà hanno ha con per da
in su sotto al alla ai che cui si suo sua suoi questo questa questi tra dopo prima secondo data importo somma
totale prezzo contratto pagina articolo acquirente venditore pagamento euro firmato nome indirizzo anno parti""".split()),
}
_ENGLISH = set("""a about after all also an and any are as at be been before but by can could do each for from had has have
if in into is it its may more must no not of on one only or other our out over shall should so such than that the
their them then there these they this to under up upon was we were what when which who will with would you your
agreement date amount paid pay total page section party parties property price seller buyer signed name number address""".split())
LANGS = {"en": "eng+ron", "de": "deu", "fr": "fra", "es": "spa", "it": "ita"}


def words_for(lang):
    return COMMON if lang not in LANG_WORDS else LANG_WORDS[lang] | _ENGLISH


_TOKEN = re.compile(r"[A-Za-zÀ-ÿĂăÂâÎîȘșȚțŞşŢţ]+")


def legibility(text, lang="en"):
    """Share of alphabetic tokens that are everyday words. Real prose sits near 0.3-0.5; noise near 0."""
    tokens = [t.lower() for t in _TOKEN.findall(text)]
    if len(tokens) < 8:
        return 0.0
    words = words_for(lang)
    return sum(1 for t in tokens if t in words) / len(tokens)


def _run(cmd, timeout=120):
    p = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError("%s failed (rc=%d): %s" % (cmd[0], p.returncode, p.stderr.decode("utf-8", "replace")[:300]))
    return p.stdout


def page_count(pdf):
    out = _run(["pdfinfo", pdf]).decode("utf-8", "replace")
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    if not m:
        raise RuntimeError("pdfinfo gave no page count")
    return int(m.group(1))


def _text_layer(pdf, n):
    return _run(["pdftotext", "-layout", "-f", str(n), "-l", str(n), pdf, "-"]).decode("utf-8", "replace")


def _ocr(png, rotate, lang="en"):
    src = png
    if rotate:
        from PIL import Image
        src = png + ".r%d.png" % rotate
        Image.open(png).rotate(-rotate, expand=True).save(src)
    return _run(["tesseract", src, "-", "-l", OCR_LANG if lang == "en" else LANGS[lang], "--psm", "3"], timeout=180).decode("utf-8", "replace")


def _ocr_page(pdf, n, tmp, lang="en"):
    base = os.path.join(tmp, "p%d" % n)
    _run(["pdftoppm", "-r", str(OCR_DPI), "-png", "-f", str(n), "-l", str(n), "-singlefile", pdf, base])
    png = base + ".png"
    best = (-1.0, "", 0)
    for rot in (0, 90, 270, 180):
        text = _ocr(png, rot, lang)
        score = legibility(text, lang)
        if score > best[0]:
            best = (score, text, rot)
        if score >= 0.30:      # clearly upright prose: stop rotating, each try costs CPU
            break
    return best


def thumbnail(pdf, n, out_png):
    """A small image of the page, so a person can look at the page a quote came from."""
    base = out_png[:-4]
    _run(["pdftoppm", "-r", str(THUMB_DPI), "-png", "-f", str(n), "-l", str(n), "-singlefile", pdf, base])


def read_page(pdf, n, tmp, lang="en"):
    page = {"n": n, "method": None, "rotation": 0, "legibility": 0.0, "chars": 0,
            "status": "unreadable", "text": "", "error": None}
    try:
        text = _text_layer(pdf, n)
        if len(text.strip()) >= MIN_TEXT_CHARS:
            page.update(method="text-layer", text=text, legibility=round(legibility(text, lang), 2))
        else:
            score, text, rot = _ocr_page(pdf, n, tmp, lang)
            page.update(method="ocr", text=text, rotation=rot, legibility=round(score, 2))
        page["chars"] = len(page["text"].strip())
        if page["chars"] >= MIN_TEXT_CHARS and page["legibility"] >= MIN_LEGIBILITY:
            page["status"] = "ok"
    except Exception as e:  # a page that failed is reported, never silently dropped
        page["error"] = str(e)[:300]
    return page


def read_pdf(pdf, on_page=None, thumbs_dir=None, lang="en"):
    """Return {'pages': [...], 'total', 'readable', 'unreadable': [n, ...]}. on_page(page, total) per page."""
    if lang not in LANGS:
        raise ValueError("Unknown document language.")
    total = page_count(pdf)
    pages = []
    with tempfile.TemporaryDirectory() as tmp:
        for n in range(1, total + 1):
            page = read_page(pdf, n, tmp, lang)
            if thumbs_dir:
                try:
                    thumbnail(pdf, n, os.path.join(thumbs_dir, "p%d.png" % n))
                except Exception:
                    pass   # a missing preview never changes a verdict
            pages.append(page)
            if on_page:
                on_page(page, total)
    bad = [p["n"] for p in pages if p["status"] != "ok"]
    return {"pages": pages, "total": total, "readable": total - len(bad), "unreadable": bad}
