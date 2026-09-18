# Reflection

## What manual work did the automation remove? (Part 1)

Before this, someone had to open every incoming document, read it, decide what
kind of document it was, work out who it concerned and what they needed to do,
copy that into a spreadsheet by hand, and remember to tell the right person.
That's 2–5 minutes of reading-and-typing per document, done by a person who
adds no real judgement to the *first pass* — they're transcribing, not
deciding. The automation now does that first pass in 15–30 seconds: it reads
the file, extracts the same seven fields a human would have written down, logs
the row, and emails the right kind of notice depending on urgency. The Google
Drive folder structure (`Incoming` → `Processed`) also removes the "did I
already deal with this file?" bookkeeping — a document processed once moves
itself out of the way.

## What the application adds that n8n alone could not (Part 2)

n8n has no front door. Before Part 2, "using" the system meant opening the
n8n editor, or the raw spreadsheet, or waiting for an email — none of which
an office employee should have to do, and none of which let them *send* a
document on demand rather than wait for the Drive-folder poll. The app adds:
a place to drop a file and watch it happen; a dashboard with search and
filters over data n8n already produced; a detail view that turns a
spreadsheet row into something readable, including an AI-written plain-
language briefing on request; and a "mark as reviewed" action that writes
back through the same webhook contract. None of that is business logic — it's
presentation and input-collection in front of logic that still lives
entirely in n8n, which is the one rule the whole project is built around.

## What still requires a human

Everything the sheet marks `Needs Review` — two or more missing fields means
the AI didn't have enough to work with, and a person should look at the
source file, not trust the row. Beyond that: anything the AI's confidence
can't be checked on structurally — is this complaint actually from that
sender, is this invoice amount plausible for this vendor, should this
"quote valid 7 days" actually be acted on before it lapses. `requested_action`
naming a payment or a legal reply is a suggestion, not an authorization; a
person still approves the pay-run or signs the reply. And every AI judgement
here is a single model call with no second opinion — for anything with real
money or legal exposure attached, that call should be the *first* read, not
the only one.

## What would break first at a thousand documents a day

1. **The Gemini free tier.** Five requests a minute is nowhere near a
   thousand documents a day arriving in bursts — we hit this limit ourselves
   testing with four documents dropped at once. A production version needs a
   paid tier and a real queue with backoff, not the `retryOnFail` band-aid
   this build uses.
2. **The Google Sheet as the datastore.** No concurrent-write safety (two
   near-simultaneous appends can race), reads get slower as the sheet grows,
   and every write is coupled to exact column-name strings. It's fine for a
   few hundred rows; it is not the shape of a system meant to hold years of
   documents.
3. **Single-poll batching.** The Drive trigger can hand a whole batch of
   files to one execution — building that correctly (see PROMPTS.md item 9)
   is what surfaced how easy it is to write per-item logic that quietly only
   handles the first item of a batch. At real volume, bursts are the normal
   case, not the edge case.
4. **No content-level deduplication on the Drive path.** The email-intake
   add-on tags a processed message so it's never re-imported; a file dropped
   twice into `Incoming Documents`, or the same invoice arriving from two
   channels, has nothing stopping a duplicate row today.

## One thing that would be built differently next time

Two honest candidates, and it's worth naming both since Part 2 §4 explicitly
asks for this trade-off when the shared-sub-workflow architecture isn't used:

- **The sheet would start as a real database**, with the Sheet kept only as an
  export/view for the office team — this is the change everything above
  points back to.
- **The Drive-trigger and webhook pipelines were built as two workflows with
  the same shared steps duplicated**, not as one sub-workflow called from
  both entry points (the architecture Part 2 recommends). That was a
  deliberate choice under time pressure — refactoring the already-tested
  webhook flow to pass binary data through n8n's Execute Workflow node
  carried real risk of breaking something that worked, for a benefit
  (avoiding duplication) that doesn't change what the system does. The
  maintenance cost is real, though: the email templates, the AI prompt, and
  the OCR fallback all had to be updated in two places in this session, and
  will again next time any of them changes. A second pass on this project
  would spend the time to build the sub-workflow properly rather than accept
  that cost twice.
