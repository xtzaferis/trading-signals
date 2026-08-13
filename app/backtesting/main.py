from app.backtesting.multi_symbol_backtest_engine import (
    MultiSymbolBacktestEngine,
)


def main():

    engine = MultiSymbolBacktestEngine()

    engine.run()


if __name__ == "__main__":

    main()
