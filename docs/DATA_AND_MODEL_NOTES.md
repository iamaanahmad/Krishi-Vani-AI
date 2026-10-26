# Data and model notes

## Included evidence

`data/knowledge.json` contains five short, manually curated and translated demonstration records (expanded from two in this improvement round; excerpts are curated demonstration summaries, not verbatim publisher text, and each record links to its publisher page):

- ICAR's *Kharif Agro-Advisories for Farmers 2025*, used for brown-spot appearance and broad non-chemical crop-management context.
- IRRI's Rice Knowledge Bank page on leaf blast, used to distinguish blast-like pointed lesions from rounder brown-spot cues.
- IRRI's Rice Knowledge Bank brown-spot page, used for brown-spot identification (lesion shape, size, centre colour).
- IRRI's Rice Knowledge Bank brown-spot page, used for non-chemical field care (soil fertility monitoring, resistant varieties, clean fields) — no product or dose is included.
- IRRI's Rice Knowledge Bank narrow-brown-spot page, used to distinguish linear, vein-parallel lesions from rounder brown-spot lesions.

The application links to the publisher page for every record and shows the citation ID in the answer. The Odia text is a demonstration translation, not publisher-authored Odia material.

## Not included

- No external image dataset or corpus files are bundled.
- No real speech-recognition or vision model/API is connected.
- No Llama weights are bundled or downloaded automatically.
- No diagnostic accuracy claim is made from the synthetic fixtures.

## Fixture purpose

The supported SVG makes the expected visual cues obvious and carries an in-image synthetic-fixture label. The uncertain SVG is intentionally low-detail. The generated WAV tones exercise media validation and the speech-adapter contract without pretending to be Odia speech.

## Evaluation needed before field use

A field pilot requires consented Odia recordings across dialects, held-out rice-leaf images from Odisha, agronomist adjudication, calibration curves, per-condition sensitivity/specificity, KVK escalation usability, and monitoring for unsafe or uncited advice. Until then, the application remains a challenge demonstration.
