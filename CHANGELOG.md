# Changelog

All notable changes to Project Echo will be documented in this file.

## [v0.1.0] - 2026-01-12

### Added
- **Cosmic Ethics 39 Evaluator**: 39-dimensional ethical evaluation framework
  - BaseScorer wrapping existing CosmicEthicsFramework
  - Philosopher weight aggregation and tension calculation
  - Blocked options generation based on risk thresholds
- **5 Philosopher Presets**: Switchable philosopher sets for different ethical perspectives
  - `cosmic13`: Long-term and cosmological thinkers (13 philosophers)
  - `east_asia`: East Asian philosophy tradition (7 philosophers)
  - `kantian`: Deontological and duty-based ethics (6 philosophers)
  - `existentialist`: Freedom and individual responsibility (5 philosophers)
  - `classical`: Ancient Greek philosophy (5 philosophers)
- **CLI Tool**: `po-cosmic` command-line interface
  - `cosmic-39` subcommand for ethical evaluation
  - `--scenario` option: agi, mars, digital, seti
  - `--preset` option: philosopher set selection
  - `--save` / `--out` options: JSON output
- **JSON Logging**: Timestamped evaluation results in `runs/` directory
- **Report Generation**: Markdown reports with run comparison
  - `reports/latest.md`: Latest run with diff vs previous
  - `--archive` option: Timestamped reports (e.g., `20260112_042613_Mars_Terraforming.md`)
- **CI/CD Pipeline**: GitHub Actions with ruff + pytest
  - Automatic linting and formatting
  - Smoke tests for core functionality
- **Explicit cosmic_weights**: 3 philosophers with precise dimensional weights
  - Kant: universal_rights, direct_responsibility, rational_deliberation
  - Watsuji: systemic_responsibility, collective_good, local context
  - Jonas: future_generation, deep_time, irreversible_risk

### Documentation
- README with philosopher preset comparison demos
- Demonstration of ethical pluralism through Mars Terraforming scenario
- Quick start guide with CLI usage examples

### Infrastructure
- MIT License
- pyproject.toml with ruff and pytest configuration
- Makefile with development tasks (run/test/lint/format/ci)
- .gitignore for runs/, reports/, and Python artifacts

[v0.1.0]: https://github.com/hiroshitanaka-creator/project-echo/releases/tag/v0.1.0
