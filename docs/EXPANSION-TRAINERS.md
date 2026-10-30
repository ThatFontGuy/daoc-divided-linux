# Expansion class trainers — Eve of Darkness import

The modern test world receives 94 trainer NPCs from Eve of Darkness snapshot e0e6ed280f6239d2c40d4d0a57b244dafdc2056e. This imports trainer placements only; class availability, spell/style definitions, inventories, saves, Sovereign trainers and other existing NPCs are unchanged.

| Class | Trainer spawns |
|---|---:|
| Bainshee Trainer | 14 |
| Heretic Trainer | 12 |
| Mauler Trainer | 28 |
| Valkyrie Trainer | 13 |
| Vampiir Trainer | 14 |
| Warlock Trainer | 13 |

The temporary `local-valkyrie-test-trainer` beside Saeunn in Mularn is removed. The original Viking trainer remains. The old Valkyrie progression seed recognizes the imported Valkyrie trainers and does not recreate that temporary NPC.

Jordheim now has Valkyrie trainers **Brienda** and **Sunhilda**, and Warlock trainers **Runda** and **Thidar**. Camelot has Heretic trainers **A'nolasa** and **Tinelas**. Tir na Nog has **Rheoran** (Bainshee) and **Megh** (Vampiir). Mauler trainers are placed in each realm as listed below.

## Data and validation

- Source names, coordinates, headings, levels, models, sizes, realms and equipment are preserved. Generic tutorial scripts and an unsupported Mauler script name are mapped to this server's actual class/realm trainer scripts. Nine minotaur mauler trainees found by the earlier broad search are monsters, not trainers, and are excluded.
- Imported NPCs have private `eod-trainer-*` identities and package `OfflineDAoC.ExpansionTrainers.EoD.v1`. They are standalone Mob records (`NPCTemplateID=0`) to avoid shared/template collisions. They are nonaggressive and do not roam or inherit foreign paths/merchant lists. No shared NPC template is changed.
- All 94 models and equipment object models exist in the installed modern client. All 35 required equipment templates already exist. All placements fall inside known local region/zone bounds. Trainer script declarations exist in the server source. Terrain placement and interaction still require in-game acceptance.
- The import is idempotent, skips equivalent nearby existing trainers, and rejects occupied/edited identities, missing equipment and out-of-bounds coordinates.

`source/tools/install_expansion_trainers.py <modern-test-folder>` previews; `--apply` backs up the database and installs the checked migration only while launcher/client/server are closed. All 37 saved-progress table hashes must remain unchanged. `--rollback <backup-folder>` refuses if the database has changed after installation. No server build or client patch is needed. No game processes are started by the installer.

Source: https://github.com/Eve-of-Darkness/db-public/tree/e0e6ed280f6239d2c40d4d0a57b244dafdc2056e

## Locations

| Name | Trainer | Region | X | Y | Z |
|---|---|---|---:|---:|---:|
| D'arine | Heretic Trainer | Albion (1) | 473097 | 628180 | 2383 |
| L'uar | Heretic Trainer | Albion (1) | 522025 | 616080 | 1795 |
| Tarzras | Heretic Trainer | Albion (1) | 510152 | 381320 | 8288 |
| Tathlaunim | Heretic Trainer | Albion (1) | 560587 | 513716 | 2408 |
| A'nolasa | Heretic Trainer | Camelot City (10) | 32960 | 26705 | 7830 |
| Tinelas | Heretic Trainer | Camelot City (10) | 38915 | 28797 | 8009 |
| Myrand | Heretic Trainer | Tutorial (27) | 98287 | 89491 | 5715 |
| Belamir | Heretic Trainer | Avalon (51) | 532500 | 549657 | 4800 |
| Kimbrisa | Heretic Trainer | Inconnu Crypt (65) | 31295 | 37113 | 16401 |
| Kadak | Heretic Trainer | Ruins of Atlantis (70) | 568841 | 538946 | 6104 |
| J'auatas | Heretic Trainer | New Frontiers (163) | 566872 | 670031 | 8088 |
| Voralia | Heretic Trainer | New Frontiers (163) | 676556 | 568937 | 8088 |
| Consul Pylos | Mauler Trainer | Albion (1) | 561829 | 509798 | 2430 |
| Consul Aieleen | Mauler Trainer | Camelot City (10) | 34449 | 26869 | 8448 |
| Consul Galirs | Mauler Trainer | Camelot City (10) | 31673 | 29749 | 8191 |
| Consul Morgimor | Mauler Trainer | Camelot City (10) | 30907 | 31589 | 8216 |
| Consul Harbuses | Mauler Trainer | Tutorial (27) | 98041 | 91115 | 5696 |
| Consul Truy | Mauler Trainer | Inconnu Crypt (65) | 34346 | 34353 | 16413 |
| Consul Kailot | Mauler Trainer | New Frontiers (163) | 676410 | 568856 | 8088 |
| Consul Lucauy | Mauler Trainer | New Frontiers (163) | 567385 | 670026 | 8088 |
| Consul Latam | Mauler Trainer | Tutorial (27) | 227281 | 219183 | 5881 |
| Consul Bergaghar | Mauler Trainer | Midgard (100) | 703486 | 740108 | 6535 |
| Consul Ciarion | Mauler Trainer | Midgard (100) | 805448 | 726903 | 4717 |
| Consul Nalonim | Mauler Trainer | Midgard (100) | 797251 | 893787 | 4744 |
| Consul Soldorl | Mauler Trainer | Midgard (100) | 747752 | 814854 | 4464 |
| Consul Krenimar | Mauler Trainer | Jordheim (101) | 28961 | 34938 | 8021 |
| Consul Omard | Mauler Trainer | Jordheim (101) | 29544 | 35924 | 8005 |
| Consul Bhinlin | Mauler Trainer | New Frontiers (163) | 700648 | 416657 | 8088 |
| Consul Lesdorl | Mauler Trainer | New Frontiers (163) | 597855 | 303493 | 8088 |
| Consul Geltran | Mauler Trainer | Kobold Undercity (243) | 34919 | 31392 | 18421 |
| Freja | Valkyrie Trainer | Tutorial (27) | 227195 | 219219 | 5710 |
| Aenida | Valkyrie Trainer | Ruinrar Atlantis (71) | 562224 | 574201 | 6008 |
| Aera | Valkyrie Trainer | Midgard (100) | 787031 | 904699 | 4972 |
| Njanna | Valkyrie Trainer | Midgard (100) | 749797 | 815084 | 4408 |
| Roskerla | Valkyrie Trainer | Midgard (100) | 802806 | 725178 | 4688 |
| Sonda | Valkyrie Trainer | Midgard (100) | 705157 | 739969 | 6536 |
| Brienda | Valkyrie Trainer | Jordheim (101) | 30219 | 35620 | 8001 |
| Sunhilda | Valkyrie Trainer | Jordheim (101) | 28282 | 35198 | 8021 |
| Ainda | Valkyrie Trainer | Aegir (151) | 288869 | 355554 | 3866 |
| Benna | Valkyrie Trainer | Aegir (151) | 286565 | 302500 | 4162 |
| Sudya | Valkyrie Trainer | New Frontiers (163) | 700227 | 416695 | 8097 |
| Vura | Valkyrie Trainer | New Frontiers (163) | 598158 | 303422 | 8098 |
| Lasynn | Valkyrie Trainer | Kobold Undercity (243) | 35448 | 31676 | 18421 |
| Basla | Warlock Trainer | Tutorial (27) | 229525 | 221328 | 5696 |
| Brurd | Warlock Trainer | Ruinrar Atlantis (71) | 562257 | 573333 | 6008 |
| Idotan | Warlock Trainer | Midgard (100) | 748615 | 816110 | 4408 |
| Rieki | Warlock Trainer | Midgard (100) | 705640 | 740026 | 6536 |
| Skynna | Warlock Trainer | Midgard (100) | 798195 | 892258 | 4744 |
| Thonnir | Warlock Trainer | Midgard (100) | 805073 | 726866 | 4688 |
| Runda | Warlock Trainer | Jordheim (101) | 34017 | 35603 | 8022 |
| Thidar | Warlock Trainer | Jordheim (101) | 34141 | 35956 | 8234 |
| Sieglira | Warlock Trainer | Aegir (151) | 289086 | 304207 | 4248 |
| Veitan | Warlock Trainer | Aegir (151) | 291086 | 354099 | 3866 |
| Ledar | Warlock Trainer | New Frontiers (163) | 699202 | 418012 | 8088 |
| Odeya | Warlock Trainer | New Frontiers (163) | 597933 | 305516 | 8088 |
| Solgi | Warlock Trainer | Kobold Undercity (243) | 34095 | 28115 | 18397 |
| Agriea | Bainshee Trainer | Tutorial (27) | 360396 | 354178 | 5716 |
| Morynne | Bainshee Trainer | Scrios de Atlantis (72) | 556910 | 571883 | 6096 |
| Tellyn | Bainshee Trainer | Shar Labyrinth (93) | 27127 | 26700 | 17634 |
| Aethegh | Bainshee Trainer | New Frontiers (163) | 373159 | 574592 | 8057 |
| Carinan | Bainshee Trainer | New Frontiers (163) | 482675 | 666980 | 7857 |
| Daegda | Bainshee Trainer | HyBrasil (181) | 430608 | 317637 | 3465 |
| Lenvanu | Bainshee Trainer | HyBrasil (181) | 308734 | 350931 | 3503 |
| Terraene | Bainshee Trainer | HyBrasil (181) | 422540 | 445202 | 5952 |
| Beland | Bainshee Trainer | Hibernia (200) | 342857 | 591978 | 5456 |
| Bleollyn | Bainshee Trainer | Hibernia (200) | 420358 | 487389 | 2656 |
| Leena | Bainshee Trainer | Hibernia (200) | 348769 | 492363 | 5199 |
| Maedri | Bainshee Trainer | Hibernia (200) | 297101 | 641117 | 4848 |
| Siddyn | Bainshee Trainer | Hibernia (200) | 352661 | 553442 | 5131 |
| Rheoran | Bainshee Trainer | Tir na Nog (201) | 23538 | 28680 | 7187 |
| Consul Crauchant | Mauler Trainer | Tutorial (27) | 359717 | 350842 | 5747 |
| Consul Lorraent | Mauler Trainer | Shar Labyrinth (93) | 27281 | 28748 | 17610 |
| Consul Addreoc | Mauler Trainer | New Frontiers (163) | 372534 | 572936 | 8040 |
| Consul Gyryn | Mauler Trainer | New Frontiers (163) | 482369 | 669416 | 7857 |
| Consul Teorraent | Mauler Trainer | HyBrasil (181) | 423607 | 443695 | 5952 |
| Consul Caromyr | Mauler Trainer | Hibernia (200) | 421255 | 487362 | 2656 |
| Consul Maedyg | Mauler Trainer | Hibernia (200) | 349709 | 491510 | 5441 |
| Consul Vyn | Mauler Trainer | Hibernia (200) | 296225 | 641482 | 4848 |
| Consul Daegit | Mauler Trainer | Tir na Nog (201) | 26929 | 36195 | 7450 |
| Consul Krakish | Mauler Trainer | Tir na Nog (201) | 31330 | 31071 | 7942 |
| Meaghan | Vampiir Trainer | Tutorial (27) | 360158 | 354108 | 5723 |
| Ceollyna | Vampiir Trainer | Scrios de Atlantis (72) | 557046 | 571764 | 6096 |
| Rhenze | Vampiir Trainer | Shar Labyrinth (93) | 27149 | 26818 | 17634 |
| Rygda | Vampiir Trainer | New Frontiers (163) | 372158 | 572910 | 8057 |
| Vertyn | Vampiir Trainer | New Frontiers (163) | 482761 | 667172 | 7857 |
| Glaer | Vampiir Trainer | HyBrasil (181) | 424011 | 444902 | 5952 |
| Lynny | Vampiir Trainer | HyBrasil (181) | 430805 | 318074 | 3479 |
| Morcen | Vampiir Trainer | HyBrasil (181) | 308601 | 350510 | 3507 |
| Bleryne | Vampiir Trainer | Hibernia (200) | 294634 | 641412 | 4848 |
| Kyrlora | Vampiir Trainer | Hibernia (200) | 348926 | 489274 | 5284 |
| Shyna | Vampiir Trainer | Hibernia (200) | 340910 | 591954 | 5464 |
| Sywn | Vampiir Trainer | Hibernia (200) | 419839 | 487455 | 2656 |
| Veown | Vampiir Trainer | Hibernia (200) | 351930 | 552728 | 5105 |
| Megh | Vampiir Trainer | Tir na Nog (201) | 26734 | 35155 | 7493 |
