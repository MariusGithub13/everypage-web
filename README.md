# EveryPage

Ask a PDF a question. EveryPage names the page, proves each quote is really there, and tells you when a page could not be read instead of telling you "no".

**Live demo:** https://everypage.devaland.com (two invented sample documents are built in; you can also upload your own PDF)

## The problem

I once told a friend that a number was not in her document. It was on page 6, on a scanned page lying on its side. The text extraction returned four pages of text and no warning, the model answered from what it was given, and the answer was confident and wrong.

Most "chat with your PDF" tools have the same blind spot. A scanned page has no text layer, so it is silently skipped. A page OCR'd sideways turns into noise that still looks like text. The model never learns that part of the document was missing, so "it is not in the document" can mean "it is not in the part I was shown".

## Three verdicts, never two

| Verdict | When | Who says it |
|---|---|---|
| **FOUND** | At least one quote was found and verified to be literally on the page it names | the model proposes, the code verifies |
| **NOT FOUND** | Every page was read and every page was examined, and nothing answers the question | the code, from the page count |
| **CANNOT SAY** | Nothing was found, but some page could not be read, or a model call for a page failed | the code |

The model is never allowed to say "it is not in the document". Only the code can, and only when it has counted that every page was read and examined.

## How it works

1. **Read every page and measure it.** Each page is read from its text layer, or by OCR when there is none. The app scores how legible the result is (the share of everyday words, English and Romanian), tries other rotations when a page reads as noise, and marks a page as unreadable when nothing works. The coverage table is shown before any question is asked.
2. **Examine every readable page.** There is no retrieval step that decides what the model may skip. Each page goes to the model with the question, and the model must return verbatim quotes as JSON.
3. **Verify every quote in code.** A quote that is not literally on the page it names is thrown away, whatever the model says about it.
4. **Write the answer only from verified quotes**, each with its page number, next to a preview of that page.
5. **Decide the verdict in code**, from the evidence and the page count.

Text inside a page is treated as untrusted data: the prompt tells the model not to follow instructions found in it, and an injected instruction cannot produce a quote that passes verification.

## NVIDIA Nemotron on Nebius Token Factory

Every model call is a runtime call to the Token Factory inference API (`https://api.tokenfactory.nebius.com/v1`, OpenAI-compatible) with **`nvidia/nemotron-3-super-120b-a12b`**. See `app/llm.py`.

What that made possible, measured on the built-in sample:

- The first version of this idea ran a small open model on a CPU and took 77 to 185 seconds per question. On Token Factory the same question takes about 4 to 6 seconds, with every page examined in parallel.
- A question over the 6-page sample costs about 0.001 USD (7 model calls), and the app shows the cost of each answer.
- Nemotron 3 Super returned quotes that were exact enough to pass a literal, character-level check. Two smaller models tried with the same prompt missed the page that mattered, which this design reports as a failed check rather than a wrong answer.

The app keeps a daily budget and per-visitor limits so a public demo cannot run up a bill, and it waits and retries when the API rate-limits it. A page whose call still fails counts as "not examined", which makes the verdict CANNOT SAY rather than NOT FOUND.

## Run it yourself

You need Docker and a Nebius Token Factory API key.

```
git clone https://github.com/MariusGithub13/everypage-web
cd everypage-web
cp .env.example .env      # put your NEBIUS_API_KEY in .env
docker compose up --build
```

Then open http://127.0.0.1:8092. The image installs Poppler and Tesseract (English and Romanian).

Settings, all optional, as environment variables: `EVERYPAGE_MODEL`, `EVERYPAGE_MAX_MB` (8), `EVERYPAGE_MAX_PAGES` (25), `EVERYPAGE_TTL_MIN` (30), `EVERYPAGE_DAY_BUDGET_USD` (1.50), `EVERYPAGE_IP_UPLOADS` (6), `EVERYPAGE_IP_QUESTIONS` (40).

## Tests

```
python3 -m pytest -q tests
```

The tests need no model and no network. They cover the rules that decide a verdict: an invented quote is discarded, a negative needs every page read, a failed or unparsable model reply is not a "no".

## Privacy and limits

- An uploaded file is kept in memory-backed temporary storage and deleted after 30 minutes. Page text is sent to the model to answer your question and is not stored by this app.
- PDFs only, up to 8 MB and 25 pages in the demo.
- The legibility check knows English and Romanian. Pages in other languages may be marked unreadable, which is the safe way to be wrong.
- A verified quote proves the words are on the page, not that the model understood them. Read the quote. This is a reading aid, not legal advice.
- The sample documents are invented. Every name, place and amount in them is made up.

## Where it came from

The page-reading and verdict rules were first written as a small local command-line tool, [everypage](https://github.com/MariusGithub13/everypage), on 2 October 2026. This repository is the hosted application built on those rules during the Nebius x NVIDIA Global AI Hackathon: the web interface, the upload flow with live page-by-page coverage, page previews, parallel examination, the Token Factory client with usage accounting, budgets and limits, and the container.

## Licence

MIT. Built by [Devaland](https://devaland.com/ai-development).
