.PHONY: run report report-archive audit test lint format ci demo-shopping help

help:
	@echo "Project Echo - Makefile targets:"
	@echo "  run             - Run po-cosmic with default scenario (mars + cosmic13)"
	@echo "  demo-shopping   - Run Shopping Bias Defense demo (Demo B)"
	@echo "  report          - Generate latest.md from most recent run"
	@echo "  report-archive  - Generate latest.md + timestamped archive"
	@echo "  audit           - Run threshold audit on all runs/*.json"
	@echo "  test            - Run pytest"
	@echo "  lint            - Run ruff check"
	@echo "  format          - Run ruff format"
	@echo "  ci              - Run full CI pipeline (format + lint + test)"

run:
	bin/po-cosmic cosmic-39 --scenario mars --preset cosmic13 --save

demo-shopping:
	@echo "========================================"
	@echo "Demo B: Shopping Bias Defense"
	@echo "========================================"
	@echo ""
	@python tools/demo_shopping.py
	@echo ""
	@echo "✅ Demo completed. Check runs/ for outputs."
	@echo "📖 See docs/DEMO_SHOPPING.md for details."

report:
	python tools/report_latest.py

report-archive:
	python tools/report_latest.py --archive

audit:
	python tools/threshold_audit.py

test:
	pytest -q

lint:
	ruff check .

format:
	ruff format .

ci: format lint test
	@echo "✅ CI pipeline completed successfully"
