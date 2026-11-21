# Design notes

## North star
Stripe's homepage hero (a ribbon of coloured light bleeding off the right edge, quiet white canvas, one big
statement) crossed with Cursor's hero (the real product window sitting on a backdrop). Taken from refs in
`~/.claude/skills/premium-web/refs/stripe.jpg` and `cursor.jpg`.

What I took, and nothing more:
- Stripe: one coloured ribbon as the only bold element, everything else white and disciplined.
- Cursor: the product itself is the hero image, in a window frame, not a mock dashboard.

## Subject-specific twist
The ribbon is a bundle of fibre strands in the TIA-598 fibre colour code (blue, orange, green, brown, slate,
violet, rose, aqua) that every fibre tech knows. Inside the product window the same strands connect the
phrase in the technician's note to the field it filled. Each field keeps one fibre colour everywhere on the
page (hero, eval explorer, data spec), so colour carries meaning.

## Tokens
- Canvas #FFFFFF, ink #1D1B18, secondary ink #5E5A54, hairline #E7E4DF
- Ask / needs input: #FF4C24 (a nod to Zinier's own accent, used only for "the agent asks")
- Field colours (fibre code): outcome blue #2F6BD8, fault green #2E9D5B, parts brown #8A5A3B,
  light level violet #7D4CC8, sign-off aqua #138F98, revisit rose #D9557E
- Type: Cabinet Grotesk 800 (display, tight -0.03em), Switzer 400/500 (body), JetBrains Mono (code and
  event names only). No Inter.

## Rules kept
No eyebrow labels in caps, no middle-dot meta strings, no card grid, one orchestrated motion (the hero
close-out replay), reduced motion respected, 390px with no horizontal scroll.
