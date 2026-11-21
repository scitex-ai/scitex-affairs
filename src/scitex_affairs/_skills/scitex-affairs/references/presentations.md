# Business presentations and revision evidence

Establish audience, decision, language, duration, and delivery format from the
request. Obtain company facts, current financial sources, brand assets, template,
and operator preferences from private records. A startup presentation does not
by itself imply equity fundraising.

Reuse the chosen native PowerPoint framework and retain editable content,
masters, layouts, aspect ratio, links, notes, and any required VBA. Copy source
files before editing. Keep implemented capabilities, plans, forecasts, actuals,
and customer evidence distinct. Use real product media for product claims.

Plan each slide around its message, evidence, and visual. Render the resulting
PPTX and inspect legibility, clipping, density, navigation, and links. Code/XML
checks do not substitute for visual review. Do not claim VBA execution was
tested from metadata inspection alone.

The standard-library [deck_feedback.py](../scripts/deck_feedback.py) snapshots
PPTX/PPTM semantics without rewriting the deck:

```bash
python /path/to/scitex-affairs/scripts/deck_feedback.py snapshot delivered.pptx --output baseline.json
python /path/to/scitex-affairs/scripts/deck_feedback.py compare baseline.json edited.pptx --output diff.json
```

Keep the immutable baseline and revision diff in the private workspace: slide
text, notes, and links can disclose confidential information. Match slide IDs
first, inspect uncertain identities after re-export, and compare rendered slides
for visual changes. A semantic diff identifies edits, not the operator's motive.
Record explicit feedback separately from interpretations and apply lessons only
at the scope supported by the evidence.
