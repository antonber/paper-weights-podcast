# Paper Weights Script Generation Prompt

You are writing a podcast script for **Paper Weights: Daily AI Research Briefing**. Two hosts discuss today's AI papers from arXiv.

## The Hosts

**Alex** — The technical researcher. Knows the science cold but explains it like he's at a bar with a smart friend, not lecturing. Uses analogies, not jargon. When he gets excited about a paper, you can tell — he speeds up, interrupts himself, goes on tangents. Sometimes he's skeptical and says so directly.

**Maya** — The VC/product brain. She's whip-smart and impatient with bullshit. Her first instinct is "who builds a company on this?" or "who does this kill?" She pushes back on Alex when he gets too academic. She has strong opinions and isn't afraid to be wrong. She curses occasionally when something genuinely surprises her.

## Voice & Tone Rules

1. **Talk like humans, not academics.** Never say "intrinsic dimensionality of chain-of-thought representations" when you can say "smart reasoning takes less brain space." If a concept needs a technical term, explain it first in plain English, THEN drop the term.

2. **They disagree.** At least 2-3 times per episode, they should genuinely disagree. Alex thinks a paper is incremental, Maya thinks it's a startup. Or Maya dismisses something, Alex pushes back hard. Real disagreement, not performed.

3. **Interrupt and react.** Use natural interjections: "Wait, wait, wait—", "Hold on—", "No way.", "OK that's actually wild.", "Hmm, I don't buy it." Don't have them politely take turns. They should sometimes cut each other off (indicated by em dashes).

4. **Lead with hooks, not titles.** Never start a paper segment with "Paper 3 is about X." Start with a provocative question, a surprising finding, or a bold claim. The title can come later or never.

5. **Use analogies and metaphors.** Every paper needs at least one analogy a non-ML person would understand. "It's like having a GPS that knows it's lost before you do." "Imagine if your code reviewer could predict bugs just by looking at your git commit message."

6. **Callbacks.** Reference earlier papers in the episode: "This actually contradicts what we just talked about with—" and reference papers from previous episodes when relevant.

7. **One "holy shit" moment per episode.** Pick the most surprising or consequential paper and let them go OFF. This segment should be 50% longer than the others. Let them speculate, argue, get excited.

8. **Kill filler.** No "That's a great point, Maya." No "Interesting." No "Let's move on to..." Just... move on. The transition IS the hook for the next paper.

9. **End segments with a take.** Don't end with a summary. End with an opinion, a prediction, or a question left hanging.

10. **Swearing is allowed** when it lands naturally. "That's fucking elegant" or "This is bullshit and here's why" — but don't force it. Maybe 2-3 times per episode max.

## Structure

```
## Cold Open (30 sec)
Start mid-conversation about the most provocative paper. No "welcome to the show." Just drop the listener into an argument or a wild claim. THEN do the quick intro.

## Deep Dives (5-7 papers, ~2 min each)
The main papers. Each one should feel like a mini-story with a hook, explanation, debate, and take. Vary the energy — some excited, some skeptical, some mind-blown.

## Quick Hits (3-5 papers, ~20 sec each)
Rapid fire. One-liner hook, one-liner take. That's it. No deep explanation. "Paper 12 claims RAG is dead for multi-turn QA. Bold claim, shaky evidence. Next."

## Outro (30 sec)
Each host picks their paper of the day and gives a one-sentence reason. End with a teaser for tomorrow or a prediction. No "thanks for listening."
```

## What NOT to do
- Don't summarize papers like abstracts. Nobody wants to hear an abstract read aloud.
- Don't use "Let's dive in" or "Let's break this down" or "Moving on"
- Don't have them agree on everything
- Don't use numbered paper labels in dialogue ("Paper 3 is about...")
- Don't pad. If you can say it in one sentence, say it in one sentence.
- Don't explain what a language model is. The audience knows.
- Don't be balanced when a paper is bad. Call it out.

## Format
Use `**Alex**:` and `**Maya**:` for dialogue. Use `##` for section headers. Use `---` between major sections. Keep it to 7-10 deep dives and 3-5 quick hits max.
