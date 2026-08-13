from app.core.logger import logger
from app.services.demo_readiness_service import DemoReadinessService


def main():
    report = DemoReadinessService().report()
    performance = report["performance"]
    logger.info("")
    logger.info("=" * 55)
    logger.info("OKX DEMO READINESS STATUS")
    logger.info("=" * 55)
    logger.info(f"Closed Trades:     {performance['closed_trades']}")
    logger.info(f"Wins / Losses:     {performance['wins']} / {performance['losses']}")
    logger.info(f"Net Profit:        {performance['net_profit']:.2f} USDC")
    logger.info(f"Profit Factor:     {performance['profit_factor']:.2f}")
    logger.info(f"Max Drawdown:      {performance['max_drawdown_pct']:.2f}%")
    logger.info(f"Observation Days:  {report['observed_days']}")
    logger.info(f"Open Positions:    {performance['open_positions']}")
    logger.info(f"Pending Positions: {performance['pending_positions']}")
    logger.info(f"Unprotected:       {performance['unprotected_positions']}")
    logger.info(f"Pending Orders:    {len(report['pending_order_ids'])}")
    if performance["monthly_pnl"]:
        logger.info("Monthly Realized P&L:")
        for month, pnl in performance["monthly_pnl"].items():
            logger.info(f"  {month}: {pnl:.2f} USDC")
    for name, passed in report["checks"].items():
        logger.info(f"  {name}: {'PASS' if passed else 'FAIL'}")
    logger.info(
        "Live Readiness:    " + ("READY FOR REVIEW" if report["ready"] else "NOT READY")
    )
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
