# Third-party code

## `prosperity4bt/`, `visualizer.py`, `quick_plot.py`

The backtesting engine and the Streamlit visualiser are **not my work**. They come from
[blackswan-quants/prosperity4_imc](https://github.com/blackswan-quants/prosperity4_imc),
the shared environment my team built for the competition, and are redistributed here
under their MIT licence (Copyright (c) 2026 BlackswanQuants). A copy of that licence is
in [`LICENSE-prosperity4bt`](LICENSE-prosperity4bt).

They are vendored rather than linked so that this repository stays runnable on its own.
I made three changes on top of the upstream code, all of them small:

1. `prosperity4bt/data.py`: added the round 5 position limits (10 for all 50 products,
   per the round 5 wiki). Upstream only carried the round 1 limits, so round 5 backtests
   silently ran against the default limit of 80.
2. `prosperity4bt/file_reader.py`: the reader now transparently decompresses `.gz`
   datasets, so the raw CSVs (156 MB) can be committed gzipped (40 MB).
3. `requirements.txt`: upstream was missing `orjson`, `ipython`, `tqdm` and `numpy`,
   which the engine imports; without them it does not start.

## Datasets under `data/`

Market data released by IMC during Prosperity 4. Reproduced here for reproducibility of
the backtests; all rights belong to IMC Trading.

## Everything else

`traders/`, `research/` and `results/` are mine.
