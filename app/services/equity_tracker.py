class EquityTracker:

    def __init__(
        self,
        initial_equity: float,
    ):

        self.initial_equity = (
            initial_equity
        )

        self.current_equity = (
            initial_equity
        )

        self.peak_equity = (
            initial_equity
        )

        self.max_drawdown = 0.0

        self.current_drawdown = 0.0

        self.history = [
            initial_equity
        ]

    def update(
        self,
        pnl: float,
    ):

        self.current_equity += pnl

        self.history.append(
            self.current_equity
        )

        self.peak_equity = max(self.peak_equity, self.current_equity)

        self.current_drawdown = 0.0

        if self.peak_equity:

            self.current_drawdown = (
                (
                    self.peak_equity
                    -
                    self.current_equity
                )
                /
                self.peak_equity
            ) * 100

        self.max_drawdown = max(self.max_drawdown, self.current_drawdown)

    def total_return(self):

        if self.initial_equity == 0:

            return 0.0

        return (
            (
                self.current_equity
                -
                self.initial_equity
            )
            /
            self.initial_equity
        ) * 100