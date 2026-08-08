PYTHON ?= python3
VENV   := .venv
BIN    := $(VENV)/bin

TRADER ?= traders/round5_final.py
DAY    ?= 5-2

.PHONY: setup backtest visualize clean

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
	$(BIN)/python -m prosperity4bt $(TRADER) $(DAY) --data ./data --out ./run_$(DAY).log

visualize: setup
	$(BIN)/streamlit run visualizer.py

clean:
	rm -f *.log
