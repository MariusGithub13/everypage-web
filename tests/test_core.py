"""Tests that need no model and no network: the rules that decide a verdict."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import ask as ask_mod
from app.ingest import legibility
from app.verdict import CANNOT_SAY, FOUND, NOT_FOUND, quote_on_page


def doc(pages, unreadable=()):
    ps = [{"n": i + 1, "status": "unreadable" if i + 1 in unreadable else "ok", "text": t, "method": "text-layer"}
          for i, t in enumerate(pages)]
    return {"pages": ps, "total": len(ps), "readable": len(ps) - len(unreadable), "unreadable": list(unreadable)}


def fake(reply_by_page):
    def generate(prompt, as_json=False, counter=None, **kw):
        if not as_json:
            return "written answer"
        for n, reply in reply_by_page.items():
            if "PAGE %d TEXT" % n in prompt:
                if isinstance(reply, Exception):
                    raise reply
                return reply if isinstance(reply, str) else json.dumps(reply)
        return json.dumps({"relevant": False, "quotes": []})
    return generate


TAX = "Property taxes for 2022 remain unpaid in the total amount of $18,450."


def test_found_needs_a_quote_that_is_on_the_page():
    d = doc(["Nothing here about it at all, only a preamble.", "Some terms. " + TAX])
    r = ask_mod.ask(d, "unpaid taxes?", generate=fake({2: {"relevant": True, "quotes": [TAX]}}))
    assert r["verdict"] == FOUND and r["evidence"] == [{"page": 2, "quote": TAX, "method": "text-layer"}]


def test_invented_quote_is_discarded_and_cannot_make_a_found():
    d = doc(["A page about something else entirely, with enough words."])
    r = ask_mod.ask(d, "unpaid taxes?", generate=fake({1: {"relevant": True, "quotes": ["Taxes of $5 are unpaid."]}}))
    assert r["verdict"] == NOT_FOUND and r["rejected"] and not r["evidence"]


def test_negative_only_when_every_page_was_read():
    d = doc(["A page about something else entirely, with enough words.", ""], unreadable=(2,))
    assert ask_mod.ask(d, "unpaid taxes?", generate=fake({}))["verdict"] == CANNOT_SAY


def test_model_failure_on_a_page_is_not_a_no():
    d = doc(["First page text with enough words in it.", "Second page text with enough words in it."])
    r = ask_mod.ask(d, "unpaid taxes?", generate=fake({2: RuntimeError("down")}))
    assert r["verdict"] == CANNOT_SAY and r["model_failed"] == [2]


def test_unparsable_model_reply_is_not_a_no():
    d = doc(["First page text with enough words in it."])
    r = ask_mod.ask(d, "unpaid taxes?", generate=fake({1: "not json at all"}))
    assert r["verdict"] == CANNOT_SAY and r["model_failed"] == [1]


def test_quote_check_ignores_case_and_spacing_but_not_words():
    assert quote_on_page("the  seller SHALL pay", "…The Seller shall pay this amount…")
    assert not quote_on_page("the buyer shall pay", "The Seller shall pay this amount")


def test_legibility_separates_prose_from_ocr_noise():
    assert legibility("The seller shall pay the amount in full before the date of closing of this agreement.") > 0.3
    assert legibility("pebueyoun ee me oe xqzt vrrk lmno ptuv wxyz abce dfgh ijkl") < 0.18
    assert legibility("Consiliul local al comunei aprobă suma de 5.000 lei pentru anul 2026, conform legii.") > 0.3


def test_baseline_names_what_a_text_layer_tool_would_miss():
    d = doc(["Intro text about the sale of the house.", TAX, "Signatures of both parties."])
    d["pages"][1]["method"] = "ocr"          # the answer sits on a scanned page
    r = ask_mod.ask(d, "unpaid taxes?", generate=fake({2: {"relevant": True, "quotes": [TAX]}}))
    assert r["verdict"] == FOUND
    assert r["baseline"] == {"text_layer_pages": 2, "total": 3, "answer_on_pages_without_text_layer": [2]}


def test_no_baseline_when_every_page_has_a_text_layer():
    d = doc(["Intro text about the sale of the house.", TAX])
    assert ask_mod.ask(d, "unpaid taxes?", generate=fake({}))["baseline"] is None


def test_progress_counts_every_examined_page():
    d = doc(["Intro text about the sale of the house.", TAX, "Signatures of both parties."])
    seen = []
    ask_mod.ask(d, "unpaid taxes?", generate=fake({}), on_progress=lambda done, total: seen.append((done, total)))
    assert seen[0] == (0, 3) and seen[-1] == (3, 3) and len(seen) == 4


def test_legibility_in_the_chosen_language():
    from app.ingest import LANGS, legibility
    de = "Der Käufer zahlt den Kaufpreis von 20.000 Euro bis zum Datum der Unterschrift an den Verkäufer."
    fr = "Le vendeur et l'acheteur ont signé le contrat de vente avec le prix total de la maison en euros."
    assert legibility(de, "de") > 0.3 and legibility(de) < 0.18      # read as German it is prose; as English, noise
    assert legibility(fr, "fr") > 0.3
    assert legibility("pebueyoun ee me oe xqzt vrrk lmno ptuv wxyz abce dfgh ijkl", "de") < 0.18
    assert LANGS["en"] == "eng+ron"                                  # the default reads exactly as before


def test_unknown_language_is_refused_not_guessed():
    import pytest
    from app.ingest import read_pdf
    with pytest.raises(ValueError):
        read_pdf("/nonexistent.pdf", lang="xx")
