PYTHON ?= python3
VENV   := .venv
BIN    := $(VENV)/bin

TRADER ?= traders/round5_final.py
DAY    ?= 5-2
LOG    := run_$(DAY).log

.PHONY: setup backtest backtest-all plot visualize clean

setup: $(VENV)/.installed

$(VENV)/.installed: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt
	touch $@

# make backtest                                   -> round 5 day 2, final trader
# make backtest DAY=5-4                           -> another day
# make backtest TRADER=traders/round4_trader.py DAY=4-3
backtest: setup
	$(BIN)/python -m prosperity4bt $(TRADER) $(DAY) --data ./data --out ./$(LOG)
	$(BIN)/python plot_run.py $(LOG)

# Every round, every day it shipped, with a chart each and a summary table.
# About two minutes and 350 MB. Add ARGS="--rounds 4 5" or ARGS=--no-plots.
backtest-all: setup
	$(BIN)/python run_all.py $(ARGS)

# Chart the newest log without re-running anything.
plot: setup
	$(BIN)/python plot_run.py --open

visualize: setup
	$(BIN)/streamlit run visualizer.py

clean:
	rm -f *.log
	rm -rf runs plots
