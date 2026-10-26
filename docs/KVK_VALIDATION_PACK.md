# KVK / agronomist validation pack — DRAFT, NOT SENT

Purpose: get one honest, external check before the Grand Finale, without
inventing farmer results. A short review from a KVK officer, extension
officer, or agronomist is worth more than any invented pilot number.

## What to send (draft message — fill the brackets, do not send as-is)

> Subject: 10-minute review request — Krishi-Vani AI rice triage prototype
>
> Hello [Name],
>
> I am [Your name], [Team name], a Top Finalist in the UNLEASH LLM
> Innovation Challenge (Edition 2). We built Krishi-Vani AI, an
> Odia-first rice-leaf triage prototype that gives one cited,
> non-chemical next step, or escalates to a KVK/extension officer when
> confidence is low.
>
> Could you spare 10 minutes to try the demo and answer the five
> questions below? We are not claiming a diagnosis or a field pilot —
> we want an expert check on whether the next step, the citations, and
> the escalation are safe and understandable.
>
> Demo: [localhost link for a live call, or static phone preview link]
> Code: https://github.com/iamaanahmad/Krishi-Vani-AI
>
> Thank you,
> [Your name, contact]

## Five questions for the reviewer

1. Is the one next step — inspect five affected leaves for round or
   oval spots with grey centres — safe and understandable for an
   Odia-speaking rice farmer?
2. Do the ICAR/IRRI citations match the pattern described, and is
   anything misleading?
3. Is the uncertain case handled correctly — should it escalate, or
   is there a safe step it could give instead?
4. Is the unknown-upload behaviour (no advice, confidence 0.0)
   the right behaviour for a real farmer upload?
5. What is the single biggest change you would require before a
   small, consented KVK pilot?

## What to record, and what NOT to claim

Record, with permission: reviewer name, role, organisation, date, and
their answers in their own words. If they give a written line you may
quote, keep the quote exact and attribute it.

Do NOT claim, from this review alone: a pilot, field accuracy,
farmer adoption, or a KVK partnership. A review is a review. A pilot
needs consented field data, agronomist adjudication, and a written
pilot agreement — all still in the roadmap, not in the demo.

## Demo checklist to run with the reviewer

- [ ] Supported scenario: cited step, 5 records, confidence 0.88
- [ ] Uncertain scenario: escalation, confidence 0.41, no citations
- [ ] Unknown upload: escalation, confidence 0.0, no advice
- [ ] Chemical-prescription guard: no product or dose in any answer
- [ ] Odia readability: farmer-facing text is understandable in Odia

If any box fails, fix the demo first and say so in the pitch. A
reviewer who finds a flaw and sees it fixed is stronger evidence
than a reviewer who finds nothing.
