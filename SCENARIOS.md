# Scenarios

Every public feature of JP Core has Given/When/Then scenarios here. Each scenario is one end-to-end test named
exactly after its title (test-core's testing protocol, vendored in `tools/test-core/`). For a library, end to end
means through the public API, as an application calls it, with real files in a scratch folder:

- Python features: `tests/test_scenarios.py` (`def test_<title in snake case>`), run by pytest;
- the browser distribution: `browser/test/scenarios.test.js` (`test('<title>', …)`), run by `node --test`;
- the furigana page in a real browser: `tests/e2e/furigana.e2e.mjs`, Playwright with headless Chromium.

Check: `python3 tools/test-core/scenarios.py check SCENARIOS.md --tests tests/test_scenarios.py browser/test/scenarios.test.js tests/e2e/furigana.e2e.mjs`
(add `--junit` with the three JUnit reports to require that each one ran and passed; see tools/test-core/README.md).
Renaming a scenario renames its test; removing a feature removes its scenario and its test in the same commit.

## Anki decks

### Scenario: Build an Anki deck file from notes
Given a deck registered in an ids.toml and a note type with two fields
When I build the deck with two notes and write the package to a scratch folder
Then the .apkg holds a collection with both notes under the registered deck ID and name

### Scenario: Correcting a gloss keeps the note's identity
Given a deck built once with a note keyed by its row ID
When I correct the note's English gloss and build again
Then both packages give the note the same GUID, so Anki updates it in place

### Scenario: Two files claiming one media name are refused
Given a package that already has the clip a.mp3 from one folder
When I add a different file also named a.mp3
Then the package refuses it and names both paths

### Scenario: Two decks sharing an ID range are refused
Given an ids.toml where a second deck's base ID falls inside the first deck's range
When the build checks the registry
Then it fails naming both decks

## Furigana and text

### Scenario: Generate furigana for a sentence
Given a sentence with one hand-written reading and kanji without readings
When I annotate it with the installed analyser
Then the new readings are added and the hand-written one is kept

### Scenario: Render one annotation for a card, a docs site and plain text
Given the annotated word 日本語【にほんご】
When I render it as ruby, as MkDocs ruby and as plain text
Then I get ruby HTML, the MkDocs braces form and 日本語

### Scenario: Ruby HTML shows readings and escapes markup
Given annotated text that also contains an HTML tag
When I render it with the web module
Then the reading is a ruby element and the tag is shown as text

### Scenario: Turn kana into romaji for a filename
Given the annotated words 人【ひと】 and 東京【とうきょう】駅【えき】
When I ask for filenames
Then I get w_hito with the prefix and toukyoueki

### Scenario: Split Japanese text into sentences
Given a paragraph with three sentences and a full-width space
When I split it and count its scripts
Then I get the three sentences and the kanji, hiragana and katakana counts

## Corpus, guardrails and pipelines

### Scenario: A collection resolves its sentences from a saved corpus
Given a corpus of two sentences saved to a JSON file
When I load it back and resolve a lesson that lists them in teaching order
Then the lesson returns the sentences in that order with their provenance

### Scenario: A beginner policy refuses kanji without furigana
Given a beginner policy that requires Japanese, a length limit and furigana for kanji
When a sentence has one kanji without a reading
Then the policy names the missing reading and require() fails

### Scenario: A pipeline records what each step did
Given a pipeline of two named steps
When I run it on a sentence
Then the result has both steps applied and a manifest of input and output digests per step

## Speech

### Scenario: A registered TTS provider writes the clip
Given an application TTS provider registered by name
When I send it a request with a pronunciation override
Then the clip file exists and the provider received the spoken text with the override applied

### Scenario: Synthesize repeated text once
Given an Edge TTS stand-in that counts requests, and three jobs where two have the same text
When the synthesizer runs the jobs
Then three clip files exist and the stand-in received two requests

### Scenario: Compare a spoken transcript with the expected sentence
Given an expected sentence with furigana and punctuation
When a transcript has the same words without punctuation, or different words
Then the first matches and the second does not

## Validation and release

### Scenario: A CSV with a missing column is refused
Given a CSV file without the translation column
When I load and check its columns
Then the report fails and names the missing column

### Scenario: An edited input makes the released deck stale
Given a manifest written for a CSV at release time
When the CSV is edited afterwards
Then the freshness check fails naming that file

### Scenario: Publish a deck as a new GitHub release
Given a built deck and a gh stand-in on PATH that has no such release
When I publish the release
Then gh is asked to create the tag with the deck as an asset and the title

### Scenario: A release that renames a published deck is refused
Given a published package and a new build that renames its deck
When I check the two packages for upgrade compatibility
Then the release is refused naming the renamed deck ID

## Discovery and styling

### Scenario: Find the projects that use a capability
Given the implementation registry shipped with JP Core
When I ask for the capabilities and for examples of the first one
Then every example found lists that capability

### Scenario: Compose the card stylesheet from layers
Given the base, ruby and night layers and my own extra rule
When I compose them
Then the stylesheet holds every layer and ends with my rule

## Browser distribution (node)

### Scenario: The browser module renders the same ruby as Python
Given annotated text with an HTML tag
When the browser module renders it
Then the HTML is exactly what the Python web module renders

### Scenario: A backup round-trips without losing review history
Given a reviewed sentence on this device
When a JSON backup holding an unreviewed copy of the same sentence is parsed and merged in
Then one sentence remains with its reviews and scheduling, and the backup carried no API key

### Scenario: Rewriting a sentence keeps its reviews
Given a reviewed sentence record
When I replace its source, casual and polite text
Then the text and plain readings change and the identity and reviews stay

### Scenario: Look up dictionary words in a sentence
Given a small dictionary with a verb and a loanword
When I match the sentence パンを食べます。
Then the loanword and the polite verb are spans with their dictionary IDs

### Scenario: Correct a wrong reading from the dictionary
Given a dictionary that knows 重複 is ちょうふく
When I resolve 重複【じゅうふく】
Then the text becomes 重複【ちょうふく】 and its speech reading is ちょうふく

### Scenario: A grammar analysis that misquotes the sentence is dropped
Given known grammar points を and ます
When an analysis quotes text that is not in the sentence or an unknown point
Then only the matches quoted from the sentence remain, with their positions

## In a browser (Playwright)

### Scenario: Hide and show furigana with the toggle button
Given the page jp_core.web builds with ruby text and the furigana toggle
When I press the toggle, reload, and press it again
Then the readings hide and the button says not pressed, the choice survives the reload, and they come back

### Scenario: The browser module renders ruby in Chromium
Given a page that imports browser/jp-core.js
When it renders annotated text into the page
Then Chromium shows a ruby element with its reading and no injected element
