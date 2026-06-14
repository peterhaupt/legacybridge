# DEMO_SCRIPT.md — LegacyBridge stage demo

The on-stage plan for the LegacyBridge hackathon demo: taglines, the spoken
pitch, the sped-up video storyboard, and judge Q&A prep. Honest by design —
matches the tone of `WORKFLOW.md` and `README.md`. Nothing is oversold; the
capability split is stated plainly because the judges will ask.

## Table of contents

1. [Tagline options](#1-tagline-options)
2. [The 60–90 second pitch script](#2-the-6090-second-pitch-script)
3. [Video storyboard (sped-up recording)](#3-video-storyboard-sped-up-recording)
4. [Judge Q&A prep](#4-judge-qa-prep)
5. [Pre-flight checklist](#5-pre-flight-checklist)

---

## 1. Tagline options

Pick one for the slide, keep one in the back pocket as the closer.

1. **"An API for the apps that don't have one."**
2. **"The integration layer for software that was never meant to be integrated."**
3. **"If it has a screen, it has an API now."**
4. **"We don't ask the legacy system for an API. We just use it — like a human, on-device."**

Primary recommendation: **#1** on the title slide, **#3** as the spoken closer.

---

## 2. The 60–90 second pitch script

Exact words to say on stage. Five beats, lead with the pain, end with the
vision. Bracketed `[...]` are stage directions, not spoken. Target ~80 seconds.

### Beat 0 — The pain (0:00–0:12)

> "Every B2B startup eventually hits the same wall. You build something modern,
> a customer loves it, and then they say: *great, now make it work with our
> ERP.* And their ERP is a 15-year-old desktop app with no API. Deal stalls.
> We've all been there."

### Beat 1 — Billflow + the request (0:12–0:25)

> "So here's Billflow — a modern billing app we built. I type the invoice I want
> in plain language."

[Type into the Billflow chat: *"Invoice Angela Martin for one ream of A4 paper."*
Gemini parses it.]

> "Gemini reads that."

### Beat 2 — Web search (0:25–0:32)

> "It does a quick web lookup on the product with Tavily —"

[Tavily result flashes in.]

### Beat 3 — Structure to JSON (0:32–0:40)

> "— and Pioneer, from Fastino, turns the whole thing into a clean structured
> invoice request. JSON, ready to send."

[Clean JSON invoice request appears on screen.]

### Beat 4 — The wall (0:40–0:52)

> "Now Billflow tries to push it into the customer's ERP — Tryton. And…"

[Click *Send to ERP*. Big red **INTEGRATION BLOCKED — no API** state.]

> "…there's no API. This is the dead end. Everything upstream was easy. *This* is
> where every integration project goes to die."

### Beat 5 — LegacyBridge (0:52–1:15)

> "So we flip on **LegacyBridge**."

[Flip the LegacyBridge toggle ON. Cut to the sped-up video.]

> "LegacyBridge doesn't need an API. It drives the ERP's screen the way a person
> would — it takes a screenshot, a local vision model finds the field, and it
> clicks and types. Fully on-device. No cloud, no data leaving the machine. It
> creates the invoice *and* posts it, right inside the real Tryton."

[Video ends on the posted invoice — state **Posted**, total visible.]

> "That invoice is real. It's posted. No API existed — and it just worked."

### Closer — Vision / ask (1:15–1:25)

> "Tryton today, but it's OS-level — the same approach drives SAP and any legacy
> GUI where the data has to stay in-house. If it has a screen, it has an API now.
> That's LegacyBridge."

**Timing note:** the recorded video carries beat 5; you narrate it live. If you
run long, cut the Tavily line (beat 2) — it's the most droppable.

---

## 3. Video storyboard (sped-up recording)

A live LegacyBridge run is **~9 minutes** (six vision clicks at ~32 s each
dominate; keyboard and fixed-fraction steps are instant). That is far too slow to
watch on stage. So the LegacyBridge portion is a **sped-up recorded video,
narrated live**. The upstream Billflow pipeline (Gemini → Tavily → Pioneer →
wall) can be **live** (it's fast) or folded into the same recording — recommended
to record the whole thing so nothing fails on stage.

### Shot list

| # | On screen | Source | Speed | Narration lands here |
|---|-----------|--------|-------|----------------------|
| A | Billflow chat, typing the request, Gemini parsing | live screen-record of Billflow | 1× (or light 1.5×) | Beats 1–3 |
| B | Tavily result + Pioneer JSON appears | same | 1× | Beats 2–3 |
| C | *Send to ERP* → **INTEGRATION BLOCKED, no API** | same | 1× — hold 1.5 s on the red state | Beat 4 (let the wall land) |
| D | Toggle LegacyBridge **ON** | same | 1× | Beat 5 open |
| E | **The 17-step Tryton run**: screenshots, mouse moving, fields filling, line added, Post, Yes | screen-record of the real run **OR** `runs/step_NN.png` montage | **compress 9 min → ~10–15 s** (~40–55× on the recorded run; or a 17-frame montage at ~0.7 s/frame) | "takes a screenshot, finds the field, clicks and types… on-device…" |
| F | Final posted invoice — state **Posted**, total shown | screenshot / end of run | hold 2 s, 1× | "That invoice is real. It's posted." |

### What is sped up vs not

- **Sped up:** only segment **E**, the LegacyBridge run. The ~32 s vision
  inferences are dead air — compress hard. The mouse movement and field-fill
  reads great at high speed (you *see* it working).
- **Not sped up:** the wall (**C**) and the final posted state (**F**). Those are
  the two emotional beats — hold them at 1× so the audience registers them.

### Two ways to make segment E (pick one)

1. **Sped-up screen recording (preferred — most convincing).** Screen-record an
   actual `--workflow` run, then time-lapse it ~40–55× to land at 10–15 s. Shows
   real mouse motion and live screen changes; clearly not faked.
2. **Screenshot montage (fallback if a real screen-record is too slow/flaky to
   capture cleanly).** The run already writes `runs/step_01.png … step_17.png`
   (all 17 exist). Stitch them into a ~12 s video, ~0.7 s/frame, with a small
   "step N/17" counter. Less cinematic but bulletproof — no live capture risk.

A hybrid also works: montage with two or three short real-motion clips spliced in
(e.g. the field actually filling, the Post click) to prove it's not a slideshow.

### Practical recording setup

- **Built-in display only.** `pyautogui` sees and clicks the built-in display, so
  Tryton must run there for the real run. Record that display.
- **Tryton maximized, clean start.** Start from a clean Tryton — no tabs, just the
  left nav tree (the workflow assumes this; the four fixed-fraction buttons assume
  the window is maximized).
- **Capture the trace too.** `runs/trace.log` + `runs/step_NN.png` are your
  montage source *and* your proof for Q&A — keep that run's `runs/` folder.
- **Record once, well, before the event.** Don't gamble on a live 9-minute run on
  stage. Capture a clean green run, speed it, done.
- **Caption overlay (optional):** a tiny "local vision model • on-device • no API"
  watermark during segment E reinforces the message while you talk.

---

## 4. Judge Q&A prep

Honest answers. The engineering docs already state the limits plainly — lean into
that; it reads as credibility, not weakness.

**Q1 — "Isn't this just hardcoded coordinates?"**
> No — and we're precise about the split. The 17-step invoice has exactly **4
> pinned clicks**, and they're all *static chrome*: the label-less "+" icon, two
> near-identical "Add" buttons, the "Post" button, and the "Yes" confirm. Those
> never move and the model mislocates them deterministically, so pinning them as
> resolution-independent screen fractions is the honest, robust choice. The **6
> understanding clicks** — find the Customer Invoices menu, the *Angela Martin*
> row, the *A4 Paper* row, the Product/Quantity/Price fields — are all done by the
> vision model reading the live screen. Those are the data-dependent ones that
> actually need understanding. The split is documented step-by-step in
> `WORKFLOW.md` §7. (The remaining 7 steps are deterministic keyboard shortcuts —
> Ctrl+N, F2, Enter — which need no screen reading at all.)

**Q2 — "Why not just use the ERP's API?"**
> Because there isn't one. That's the entire point. The wall you saw in the demo
> is real — Tryton (and a huge amount of legacy enterprise software) has no usable
> API to integrate against. If there were an API, you wouldn't need us. We're for
> exactly the case where the API doesn't exist.

**Q3 — "Why a local model instead of Gemini for the driving?"**
> Privacy and offline operation. The whole point is sensitive enterprise systems
> where the screen data — customer records, invoices, financials — must never
> leave the machine. The driving model never sees the cloud; screenshots, model,
> and control all run on-device. We *do* use Gemini upstream in Billflow for
> parsing the user's request — that's fine, it's not the customer's confidential
> ERP screen. The moment we're looking at the legacy system itself, it's local.

**Q4 — "How is this different from RPA tools like UiPath?"**
> Classic RPA binds to UI selectors and screen coordinates — it's brittle and
> breaks when the layout shifts, and it needs a per-screen script someone hand-
> builds. We're **vision-model-driven**: the model looks at the actual screen and
> finds the target by what it *is* ("the Angela Martin row", "the Quantity
> field"), not by a fixed selector. It adapts to where things actually are in the
> live list. And it's on-device — no RPA cloud orchestrator in the loop.

**Q5 — "Does it really work end-to-end, or is this a mock?"**
> Real, end-to-end. It creates the invoice **and posts it** inside the actual
> Tryton ERP — the posted state you see is genuine. Every single step is traced:
> a screenshot per step (`runs/step_01..17.png`) plus `runs/trace.log` with the
> input image, the located coordinates, and the exact click performed. The full
> workflow is documented in `WORKFLOW.md`. Happy to show the trace.

**Q6 (if pressed) — "It's slow — 9 minutes. Is that usable?"**
> Today, yes — for back-office work that's async anyway (an invoice doesn't need
> to post in two seconds). The ~32 s is the local vision inference; that's a model
> we run unoptimized on a laptop. It gets faster with a better/quantized model or
> a real machine, and the architecture doesn't change. The video is sped up
> because watching 9 minutes on stage is boring, not because anything's faked.

---

## 5. Pre-flight checklist

- [ ] Recorded + sped-up video rendered and on the presenting machine (not
      streamed). Test playback fullscreen.
- [ ] Billflow app open and warmed up (Gemini / Tavily / Pioneer keys live) if any
      part is shown live.
- [ ] `runs/` from a clean green run kept on disk — montage source + Q&A proof.
- [ ] Title slide with tagline #1; closer line #3 memorized.
- [ ] Know the capability split cold (6 vision / 4 pinned / 7 keyboard) — Q1 is
      almost guaranteed.
- [ ] Fallback ready: if the live Billflow part fails, the full recording covers
      the whole pipeline — switch to it and keep talking.
