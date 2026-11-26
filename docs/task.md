# Wykrywanie agenta LLM działającego na stronie WWW

Agenci przeglądarkowi, czyli modele językowe, które same klikają i wypełniają formularze na stronach WWW, coraz częściej działają tam, gdzie serwis spodziewa się człowieka. Zabezpieczenia takie jak CAPTCHA projektowano przeciw prostym botom, a pierwsze badania pokazują, że część agentów je przechodzi. Zadanie: zbadać od strony obrońcy, po czym serwis może poznać, że na stronie działa agent, a nie człowiek.

## Kontekst

Agenci przeglądarkowi (Claude in Chrome, Operator, browser-use, agenci na Playwright) klikają, wypełniają formularze i czytają strony za użytkownika. Klasyczne mechanizmy obronne, takie jak reCAPTCHA, fingerprinting przeglądarki czy analiza ruchów myszy, powstały z myślą o prostych botach. Agent LLM różni się od nich: ogląda zrzuty ekranu albo drzewo dostępności i często działa w zwykłej przeglądarce użytkownika.

Pierwsze prace sugerują, że agenci są rozróżnialni, ale nie zawsze tam, gdzie szukają klasyczne narzędzia. Według FP-Agent sygnały behawioralne działają lepiej niż fingerprint przeglądarki, który słabo rozróżnia agentów. Praca On the Internet, Nobody Knows You're an LLM Bot wysłała sześciu agentów na serwery-pułapki: część przeszła wszystkie testowane zabezpieczenia, a mimo to każdy dawał się odróżnić od człowieka i od pozostałych.

Można wyróżnić trzy warstwy detekcji:

- sygnały behawioralne i czasowe: rytm akcji, klikanie po współrzędnych, opóźnienia wynikające z wnioskowania modelu;
- pułapki semantyczne: elementy niewidoczne dla człowieka, ale obecne w DOM albo drzewie dostępności (honeypoty, ukryte instrukcje, linki-kanarki), na które reaguje tylko model;
- „odwrócona CAPTCHA”: zadania łatwe dla LLM, a nienaturalne dla człowieka.

Badanie dotyczy strony obronnej: dostawca serwisu chce wiedzieć, kto działa na stronie. Nie obejmuje omijania zabezpieczeń.

## Pytanie badawcze

Które sygnały pozwalają serwisowi odróżnić agenta LLM od człowieka i ile kosztują w fałszywych alarmach?

## Co trzeba zrobić

**Krok 1. Stanowisko.** Zbudować prostą stronę testową i uruchomić na niej co najmniej jednego agenta oraz zebrać ślady ludzi wykonujących te same zadania.

**Krok 2. Detekcja.** Zaimplementować po jednej metodzie z co najmniej dwóch warstw i zmierzyć ich skuteczność oraz odsetek fałszywych alarmów.

**Krok 3. Porównanie.** Rozszerzyć na kilku agentów lub kilka modeli i ocenić koszt dla osób korzystających z technologii asystujących: czytniki ekranu też czytają drzewo dostępności.

## Uwagi praktyczne

Wystarczą modele przez API i otwarte narzędzia do automatyzacji przeglądarki. Eksperymenty prowadzimy wyłącznie na własnej stronie testowej.

## Literatura

- Fayolle i in., On the Internet, Nobody Knows You're an LLM Bot: Unmasking Web Agents with Multi-Layer Fingerprinting, arXiv:2606.30119.
- Wang i in., FP-Agent: Fingerprinting AI Browsing Agents, arXiv:2605.01247.
- Known By Their Actions: Fingerprinting LLM Browser Agents via UI Traces, arXiv:2605.14786.
- Whose Agent Are You? Multi-Layer Fingerprinting and Attribution of Autonomous Web Agents, arXiv:2606.20910.
