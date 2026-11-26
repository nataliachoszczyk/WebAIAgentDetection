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

---

# Zasady projektu badawczego (informacje ogólne kursu)

**Streszczenie.** Każdy zespół otrzymuje jeden otwarty temat badawczy z zakresu bezpieczeństwa sztucznej inteligencji, samodzielnie go bada i przedstawia wyniki w raporcie o objętości najwyżej dwóch stron (LaTeX, dwukolumnowy szablon CVPR), uzupełnionym dodatkiem bez ograniczenia objętości. Podstawowym kryterium oceny jest jakość komunikacji wyników. Wyboru tematu dokonują Państwo w głosowaniu trwającym do środy 25 listopada 2026 r., godz. 24:00. Termin oddania raportu upływa 11 stycznia 2027 r. o godz. 16:00.

## Cel projektu

Projekt badawczy różni się od dotychczasowych zadań laboratoryjnych: nie ma w nim tablicy wyników ani metryki, którą należy zmaksymalizować. Celem jest przeprowadzenie niewielkiego, samodzielnego badania przy ograniczonym czasie i ograniczonych zasobach obliczeniowych oraz jasne przedstawienie jego wyników.

Tematy mają charakter eksploracyjny i nie mają jednej poprawnej odpowiedzi. Wynik negatywny, czyli rzetelnie udokumentowane stwierdzenie, że badany efekt nie występuje, jest pełnoprawnym wynikiem projektu.

## Kryterium sukcesu

Czytelnik raportu powinien dowiedzieć się więcej i jaśniej, niż gdyby treść tematu wprowadził jako zapytanie do modelu językowego.

## Kryteria oceny

- **Jakość komunikacji.** Z raportu powinno jasno wynikać, co zostało zrobione i jakie płyną z tego wnioski. Każde twierdzenie powinno być poparte wynikiem liczbowym lub wykresem.
- **Jakość i prostota wykresów.** Wymagane są opisane osie, jednostki oraz podpis wskazujący wniosek płynący z wykresu. Zob. wskazówki dotyczące prezentacji wyników.
- **Poprawność i dobór eksperymentów.** Eksperymenty powinny odpowiadać na postawione pytanie, zawierać punkt odniesienia i próby kontrolne, a wnioski powinny z nich rzeczywiście wynikać.
- **Rzetelność.** Wątpliwości co do wyników oraz ograniczenia przeprowadzonych eksperymentów należy wyraźnie wskazać w raporcie.
- Przegląd literatury nie podlega ocenie.

## Wymagania dotyczące raportu

- **Część główna:** najwyżej dwie strony w dwukolumnowym szablonie CVPR (author kit), przygotowana w systemie LaTeX. Do pracy nad raportem polecamy Overleaf. Limit obejmuje wykresy i tabele; bibliografia nie wlicza się do limitu. Wszystkie najważniejsze informacje muszą znaleźć się w tej części.
- **Tekst części głównej musi być napisany samodzielnie, bez użycia narzędzi sztucznej inteligencji.** Uznanie tekstu części głównej za wygenerowany przez AI skutkuje odjęciem punktów, aż do wyzerowania oceny za projekt. Zakaz dotyczy wyłącznie tekstu raportu, a nie kodu: korzystanie ze wsparcia AI przy pisaniu kodu jest wskazane.
- **Dodatek bez ograniczenia objętości:** pełne tabele wyników, treść zapytań, przykłady odpowiedzi modeli, szczegóły treningu.
- **Odnośnik do repozytorium Git** z kodem umożliwiającym odtworzenie wyników. Repozytorium musi zawierać plik README opisujący krok po kroku, jak odtworzyć wyniki przedstawione w raporcie.

Układ części głównej pozostawiamy Państwa decyzji. Jako sugestię proponujemy następujący:

1. Najważniejszy wykres u góry pierwszej strony, z podpisem formułującym wniosek.
2. Główne wyniki: od dwóch do czterech punktów; każdy rozpoczyna się wyróżnionym twierdzeniem i zawiera wyniki liczbowe.
3. Zwięzły opis badania: przedmiot badania (model, dane, miara) oraz wyniki kolejnych kroków, z odesłaniami do dodatku.
4. Ograniczenia i dalsze kierunki: co należałoby zrobić, dysponując większą ilością czasu.

## Zasady realizacji

- Opis każdego tematu zawiera kolejne kroki. Najważniejsze jest uzyskanie pierwszego własnego wyniku (zazwyczaj kroki 1 i 2). Dalsze kroki wskazują możliwe kierunki pracy; nie stanowią listy obowiązkowej i nie muszą być realizowane po kolei.
- W pracy badawczej (eksperymenty, kod, analiza) dopuszcza się korzystanie z modeli językowych, cudzych repozytoriów i dowolnych materiałów, pod warunkiem wskazania w raporcie ich źródeł. Nie dotyczy to redagowania części głównej raportu, którą należy napisać samodzielnie.
- Tematy dobrano tak, aby ich realizacja była możliwa z użyciem bezpłatnej wersji Google Colab oraz modeli dostępnych przez API. Dostęp do API zapewniają prowadzący; szczegóły zostaną podane po przydziale tematów. Jeżeli model wskazany w opisie tematu przekracza dostępne zasoby, dopuszcza się użycie mniejszego wariantu.
- W tematach dotyczących ataków typu jailbreak oraz backdoorów stosuje się standardowe zbiory testowe i własne, kontrolowane modele. W raporcie i repozytorium nie zamieszcza się szkodliwych treści wygenerowanych przez modele, a jedynie wyniki zbiorcze.

## Harmonogram

| Termin | Etap |
|---|---|
| do środy 25.11.2026, godz. 24:00 | wybór tematu (głosowanie) |
| bezpośrednio po zamknięciu głosowania | ogłoszenie przydziału tematów |
| do 11.01.2027, godz. 16:00 | oddanie raportu (PDF) wraz z odnośnikiem do repozytorium; sposób przekazania zostanie podany odrębnie |
