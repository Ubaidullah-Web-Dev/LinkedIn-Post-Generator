# Changelog

## [2.5.0] – 06-30-2026
### Added
- **Deterministic Infographic Engine**: Uses PIL + NumPy to render 7 beautiful templates (Quote Card, Tips List, Comparison, Step Flow, Stat Highlight, Code Snippet, and Minimal Card) with auto-scaling, text-wrapping, and overflow fallback.
- **Dynamic Themes**: Added 5 premium themes (Cyberpunk Neon, Minimal Monochrome, Soft Pastel, Glassmorphism, Bold High-Contrast) with built-in contrast validation.
- **Config Hardening**: Integrated `python-dotenv` for secure, environment-variable based secrets handling (`LI_AT`, `JSESSIONID`, API keys).
- **pyfiglet**: Added pyfiglet support for rendering compact terminal banners.

### Changed
- **TUI Redesign**: Fully overhauled GUI using Textual with a space-saving sidebar (width 28), compact ASCII monogram, and real-time generation previews.
- **SQLite Engine**: Hardened WAL configuration and set `check_same_thread=False` to prevent thread conflicts during background jobs.

### Fixed
- Fixed button height layout squishing issues on terminal rendering.
- Fixed SQLite database thread exception when generating content.

## [1.1.0] – 04-13-2025
### Added
- **Updated RSS handling**  
  - First try to parse any URL with *feedparser*; fall back to HTML scraping only if it isn’t a feed.
  - `timeout` on `requests.get` to avoid hangs.
- Guards for malformed or empty feeds (`bozo`, empty `entries`).

### Changed
- `rss_parse()` now
  - chooses an entry with `random.choice()`,  
  - falls back to `description`, `content:encoded`, or `title` when `summary` is missing,  
  - strips HTML with *BeautifulSoup*
- Updated `example_config.json` with larger `scrape_char_limit` value.
- Clean up

### Fixed
- Crash when a feed had zero entries.  
- Crash when `summary` field was absent.

## [1.0.0] – 04-13-2025
### Added
- Inject current datetime into the pre‑amble of every ChatGPT request.
- Added CHANGELOG.md

### Changed
- Default model switched from **`gpt‑4`** to **`gpt‑4o‑mini`**.
- Added `.idea/` to `.gitignore`.

### Compatibility
- Codebase migrated to **openai‑python 1.73.0** (SDK ≥ 1.0).
