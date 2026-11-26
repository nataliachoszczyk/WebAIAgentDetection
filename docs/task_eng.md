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

---

# Rules of the research project (general course information)

Each team gets one open research topic about AI security. The team examines the topic and writes a report. The main part of the report has a maximum of two pages (LaTeX, two-column CVPR template). An appendix of any length can follow. The main criterion is the quality of the communication of the results.

**Deadline: 11 January 2027, 16:00.** The team submits the report (PDF) and a link to the repository. The method of submission comes later.

## Aim

The project has no leaderboard and no metric to maximize. The aim is a small, independent study with limited time and limited compute, and a clear presentation of its results.

The topics are exploratory and have no single correct answer. A negative result is a valid result. A negative result is a reliable, documented statement that the effect does not occur.

## Success criterion

The reader of the report must learn more, and more clearly, than from a language model that gets the topic text as a prompt.

## Grading criteria

- **Quality of communication.** The report must clearly show what we did and what we conclude. A numerical result or a plot must support each claim.
- **Quality and simplicity of plots.** Each plot must have axis labels, units and a caption that states the conclusion.
- **Correctness and choice of experiments.** The experiments must answer the research question. They must have a baseline and control runs. The conclusions must follow from the experiments.
- **Reliability.** The report must clearly state the doubts about the results and the limits of the experiments.
- The literature review is not graded.

## Report requirements

- **Main part:** a maximum of two pages in the two-column CVPR template (author kit), in LaTeX. Overleaf is recommended. The limit includes plots and tables. The references are not in the limit. All important information must be in the main part.
- **The team must write the text of the main part without AI tools.** If the text looks generated by AI, the grade gets lower, down to zero. This rule applies only to the text of the report. AI help for the code is recommended.
- **Appendix of any length:** full result tables, prompts, examples of model answers, training details.
- **Link to the Git repository** with the code that reproduces the results. The README must give step-by-step instructions to reproduce the results of the report.

Suggested layout of the main part (not mandatory):

1. The most important plot at the top of the first page, with a caption that states the conclusion.
2. Main results: two to four points. Each point starts with a highlighted claim and has numerical results.
3. A short description of the study: the object of the study (model, data, metric) and the results of each step, with references to the appendix.
4. Limits and future work: what to do with more time.

## Rules of the work

- Each topic has steps. The most important thing is the first own result (usually steps 1 and 2). The next steps show possible directions. They are not mandatory, and their order is free.
- For the research (experiments, code, analysis), the team can use language models, repositories of other people and any materials. The report must give their sources. This does not apply to the text of the main part.
- The topics are possible with the free version of Google Colab and with models through an API. The lecturers give the API access after the topic assignment. If a model of the topic is too large for the resources, a smaller variant is permitted.
- Topics about jailbreak and backdoor attacks use standard test sets and own, controlled models. The report and the repository show only aggregate results, not harmful model outputs.

## Schedule

| Date | Stage |
|---|---|
| until Wednesday 25.11.2026, 24:00 | topic choice (vote) |
| directly after the vote | assignment of the topics |
| until 11.01.2027, 16:00 | submission of the report (PDF) and the link to the repository |
