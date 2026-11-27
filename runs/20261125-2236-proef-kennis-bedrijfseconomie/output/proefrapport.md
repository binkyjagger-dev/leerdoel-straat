# Proefrapport kennisgestuurde toets (bedrijfseconomie 5 VWO periode 2, 2026-11-27)

1. **Lat gehaald.** Blinde vergelijking: nieuw 16 van 17 *goed*, 1 *aanpassen*, 0 *weg* (lat: ≥ 10 van 16). Run 0943 kreeg 10 *goed*, 2 *aanpassen* en 5 *weg*, waarvan 3 keer omdat de vraag te makkelijk was.
2. **Aanpassen bij nieuw:** O2-V7 (btw-aangifte). De docent wil de inkoopwaarde van de omzet bij de gegevens en geen "inclusief btw" in de bron. Nog niet gerepareerd.
3. **Mechanismen bij de *goed*-vragen:** het vaakst *veranderde voorwaarde doorrekenen* (3×), *grondslag kiezen* (3×), *terugredeneren vanuit een uitkomst* (2×; ook bij O2-V7), *twee tegengestelde effecten afwegen* (2×) en *tijdsafbakening* (2×). De andere mechanismen kwamen elk één keer voor. Geen enkel mechanisme viel af.
4. **Misconcepten:** elke vraag had een goedgekeurd misconcept. De misconceptie-oplosser vond bij 11 vragen dat het misconcept gevangen wordt en bij 6 vragen deels. Bij *deels* komt de conclusie vaak toevallig gelijk uit (bijvoorbeeld O3-V10). Het cv vangt die gevallen nu met regels: een misconcept kost een scorepunt.
5. **Verifier:** drie rondes. Twee reparatieronden (O3 twee keer, O4 één keer); eindstand 17/17 *pass*. Op toetsniveau bleven afwijkingen over die je met itemreparatie niet oplost: stappen, noise, B01 en de Bloom-mix/P16. De docent heeft ze alle vier geaccepteerd.
6. **Kosten:** ongeveer 55 agent-calls. Dit is een schatting uit de bestanden in de run, omdat het gesprek tussendoor is gewist. Ze bestaan uit kennisopbouw (8), planner (3), varianten A/B en schrijvers (≈ 12), solver (6), labellers A/B/R (15), misconceptie-oplosser (6), verifier (3) en reparatie (3).
7. **Wat niet ging zonder codewijziging:**
   - De misconceptiecheck en de blinde vergelijking zijn met de hand of met losse scripts gemaakt (`34_misconcept_check.json`, `output/blind-vergelijking.md`); er is geen straatscript voor.
   - Een wijziging die alleen het cv raakt, laat T4 toch helemaal opnieuw lopen.
   - Planner en verifier hebben een regel nodig voor P01 met een open richting (bedrijfsecon-080).
8. **Open besluiten:** bedrijfsecon-078 (noise per vraag), 079 en 080. Voor 079 staat het besluit "term verplicht" (2026-11-26) wel in `35_teacher_acceptances.json`, maar nog niet in `decisions.json`.
9. **Advies:** doorgaan met specs/38. Neem daarin misconceptiekaartjes, mechanismen en de misconceptie-oplosser op als vaste straatstappen, met scripts in plaats van handwerk.
