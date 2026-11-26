# Detection of an LLM agent on a web page

Browser agents are language models that click and fill in forms on web pages. They operate more and more on sites that expect a human. CAPTCHA and similar protections were made against simple bots. The first studies show that some agents pass them. The task: examine, from the side of the defender, how a site can know that an agent operates on the page and not a human.

## Context

Browser agents (Claude in Chrome, Operator, browser-use, agents on Playwright) click, fill in forms and read pages for the user. Classic protections were made against simple bots. Examples: reCAPTCHA, browser fingerprinting and analysis of mouse movement. An LLM agent is different from these bots. It looks at screenshots or at the accessibility tree. It often operates in the usual browser of the user.

The first studies show that agents are distinguishable. But the signals are not always where the classic tools look for them. FP-Agent reports that behavioral signals work better than the browser fingerprint. The browser fingerprint does not distinguish agents well. The study "On the Internet, Nobody Knows You're an LLM Bot" sent six agents to trap servers. Some agents passed all tested protections. But each agent was distinguishable from a human and from the other agents.

The detection has three layers:

- Behavioral and timing signals: the rhythm of actions, clicks at coordinates, delays from model inference.
- Semantic traps: elements that a human cannot see, but that are in the DOM or in the accessibility tree. Examples: honeypots, hidden instructions, canary links. Only a model reacts to them.
- "Reverse CAPTCHA": tasks that are easy for an LLM, but not natural for a human.

The study is about defense: the site operator wants to know who operates on the page. The study does not include the bypass of protections.

## Research question

Which signals let a site distinguish an LLM agent from a human? What is the cost of each signal in false alarms?

## Steps

**Step 1. Test bench.** Make a simple test page. Run at least one agent on it. Collect the traces of humans who do the same tasks.

**Step 2. Detection.** Implement one method from each of at least two layers. Measure the detection rate and the false alarm rate of each method.

**Step 3. Comparison.** Extend the study to more agents or more models. Measure the cost for users of assistive technology: screen readers also read the accessibility tree.

## Practical notes

Models through an API and open tools for browser automation are sufficient. Run experiments only on our own test page.

## References

- Fayolle et al., On the Internet, Nobody Knows You're an LLM Bot: Unmasking Web Agents with Multi-Layer Fingerprinting, arXiv:2606.30119.
- Wang et al., FP-Agent: Fingerprinting AI Browsing Agents, arXiv:2605.01247.
- Known By Their Actions: Fingerprinting LLM Browser Agents via UI Traces, arXiv:2605.14786.
- Whose Agent Are You? Multi-Layer Fingerprinting and Attribution of Autonomous Web Agents, arXiv:2606.20910.
