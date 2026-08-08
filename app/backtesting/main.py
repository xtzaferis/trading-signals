from app.backtesting.backtest_engine import (
    BacktestEngine,
)


def main():

    engine = BacktestEngine()

    engine.run()


if __name__ == "__main__":

    main()