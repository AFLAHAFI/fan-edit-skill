# Prompt template - copy, fill, send to Claude

Fill only the lines you care about. Leave the rest as `auto`. Attach the files listed at the end.

```text
Use the mass-fan-edit skill.

PROJECT FOLDER : D:\edits\<name>            (raw\ = clips, song\ = song)
HERO / MOVIE   : <e.g. Iron Man, The Amazing Spider-Man, Leo, Vikram>
SONG           : <file name>   | window: auto | start at <m:ss> | the chorus "<hook line>"
LENGTH         : 38 s          (30-60)
FORMAT         : 16:9 landscape | 9:16 reel | 1:1 | 4:5
STYLE PRESET   : mass-hero | phonk-night | cinematic-trailer | emotional | anime-hype | villain-glitch | retro-synthwave
GRADE          : auto | teal-orange | phonk-night | warm-gold | cold-steel | bw-punch | vhs-retro | clean
IMPACT FONT    : auto | anton | bebas-neue | russo-one | oswald-bold | teko-bold | bungee | black-ops-one | orbitron-black
                 | monoton | archivo-black | big-shoulders-black | unbounded-black | bangers | audiowide | rubik-glitch
                 | permanent-marker | rajdhani-bold
LEAD FONT      : auto | playfair-italic | instrument-serif | cormorant-italic | dm-serif-italic
COLOURS        : auto | gold red cyan | red blue white | <your hex colours>
WORDS ON SCREEN: auto (from lyrics/drops) | exactly these: <WORD1>, <lead> <WORD2>, ...
LYRICS         : <paste lyrics, or "none / instrumental">
WORD TIMES     : auto | VEERA 1:12.9, OMKAARA 1:17.9 ...   (song time, by ear - optional)
GRAPHICS LEVEL : minimal | medium | heavy
                 minimal = words only, light shake, no echo grid, no flashes
                 medium  = words + echo grid on 2 words + flashes on drops
                 heavy   = full mass: echo grid, RGB split, strong shake, flash on every bass hit
HUD FRAME      : off | on (title "<TEXT>", corner label "<TEXT>")
SHOTS I WANT   : <e.g. suit-up, helmet eyes, landings, moon swing, free fall, fights>
SHOTS TO AVOID : <e.g. dialogue, daylight, Gwen scenes>
SPEED          : fast cuts every beat | mixed | slow cinematic
OUTPUT         : bat file only (I render) | render for me
```

Attach (only these - they are small):
- `song_report.txt`, `video_report.txt`, and the images in `sheets\` (made by `PREP.bat`)
- or, if Claude can reach your folder, nothing - just the prompt.

---

## Example 1 - Tamil/Malayalam mass hero (lyric sync)

```text
Use the mass-fan-edit skill.
PROJECT FOLDER : D:\aflah\ironman edtis
HERO / MOVIE   : Iron Man 1 + 2
SONG           : Veezha Veera.mp3 | window: the first chorus "Veezha Veera Vaa Vaa Veera"
LENGTH         : 38 s
FORMAT         : 16:9 landscape
STYLE PRESET   : mass-hero
IMPACT FONT    : anton
LEAD FONT      : playfair-italic
COLOURS        : gold red cyan
WORDS ON SCREEN: veezha VEERA, theeyaai ERIYUM, OMKAARA, sigarathil ASURAA, end title VEERA
LYRICS         : <pasted>
GRAPHICS LEVEL : heavy
HUD FRAME      : on (title "VEERA", corner label "126 BPM")
SHOTS I WANT   : suit-up, helmet closing + eyes lighting, repulsor blasts, explosions, landings
OUTPUT         : bat file only
```

## Example 2 - Phonk night edit (no lyrics)

```text
Use the mass-fan-edit skill.
PROJECT FOLDER : D:\aflah\Spider-man
HERO / MOVIE   : The Amazing Spider-Man
SONG           : INTERWORLD - METAMORPHOSIS.mp3 | window: auto (hardest drop)
FORMAT         : 9:16 reel
STYLE PRESET   : phonk-night
IMPACT FONT    : russo-one
LEAD FONT      : instrument-serif
COLOURS        : red blue white
WORDS ON SCREEN: the AMAZING, your friendly SPIDER-MAN, spidey SENSE, with great POWER, METAMORPHOSIS
GRAPHICS LEVEL : heavy
HUD FRAME      : off
SHOTS I WANT   : night web-swings, moon swing, free fall, rooftop eyes, lizard fight
SHOTS TO AVOID : daylight school scenes
SPEED          : fast cuts every beat
OUTPUT         : bat file only
```

## Example 3 - Emotional reel (minimal graphics)

```text
Use the mass-fan-edit skill.
HERO / MOVIE   : Peter + Gwen (TASM)
SONG           : another_love.mp3 | start at 2:05
LENGTH         : 30 s
FORMAT         : 9:16 reel
STYLE PRESET   : emotional
IMPACT FONT    : bebas-neue
LEAD FONT      : cormorant-italic
COLOURS        : white gold
WORDS ON SCREEN: exactly these: "i miss" YOU, "forever" GWEN
GRAPHICS LEVEL : minimal
SPEED          : slow cinematic
OUTPUT         : bat file only
```

## Example 4 - one-line quick prompt

```text
Use the mass-fan-edit skill: 35 s 9:16 phonk edit of the clips in D:\edits\batman with the song in song\, auto words, heavy graphics, bat file only.
```

---

### No Claude at all
Open `templates\AUTO_EDIT.bat`, set `PRESET`, `ASPECT`, `WORDS` (e.g. `the/AMAZING,SPIDER-MAN,POWER`), copy it into your project folder, double-click.

### Malayalam quick guide (മലയാളം)
1. `raw\` ഫോൾഡറിൽ ക്ലിപ്പുകൾ, `song\`-ൽ പാട്ട് ഇടുക.
2. `PREP.bat` റൺ ചെയ്യുക → `song_report.txt`, `video_report.txt`, `sheets\` ചിത്രങ്ങൾ ഉണ്ടാകും.
3. മുകളിലെ ടെംപ്ലേറ്റ് പൂരിപ്പിച്ച്, ആ ഫയലുകൾ കൂടെ Claude-ന് അയക്കുക.
4. Claude തരുന്ന `project.json`, `picks.json` ഫോൾഡറിൽ സേവ് ചെയ്യുക.
5. `RUN_EDIT.bat` റൺ ചെയ്യുക → ഫൈനൽ വീഡിയോ.

Claude Code / desktop app-ൽ ഫോൾഡർ കണക്റ്റ് ചെയ്താൽ: ഫോൾഡറും ചെറിയ prompt-ഉം കൊടുത്താൽ മതി, Claude തന്നെ എല്ലാം ചെയ്ത് വീഡിയോ ഉണ്ടാക്കും.
Claude ഇല്ലാതെ: `AUTO_EDIT.bat`-ൽ PRESET, ASPECT, WORDS മാറ്റി double-click ചെയ്യുക.
