#!/usr/bin/env python3
"""
Automated scheduler for running investment strategies on a schedule
This script can be run as a background service or cron job
"""

import schedule
import time
import logging
from schwab_app.config import Config
from schwab_app.client import SchwabClient
from schwab_app.strategies import (
    DCAStrategy,
    DRIPStrategy,
    RebalanceStrategy,
    OpportunisticStrategy,
)
from schwab_app.utils import setup_logging

logger = logging.getLogger(__name__)


class StrategyScheduler:
    """Scheduler for automated investment strategies"""
    
    def __init__(self, config: Config):
        """
        Initialize scheduler
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.client = SchwabClient(
            config.api_key,
            config.app_secret,
            config.callback_url,
            config.token_path
        )
        
    def run_dca(self):
        """Run Dollar Cost Averaging strategy"""
        if not self.config.dca_enabled:
            logger.info("DCA strategy is disabled")
            return
        
        try:
            logger.info("Running DCA strategy")
            strategy = DCAStrategy(self.client, self.config.account_number)
            results = strategy.execute(
                self.config.dca_symbols,
                self.config.dca_amount,
                dry_run=False
            )
            logger.info(f"DCA completed: {len(results)} trades executed")
        except Exception as e:
            logger.error(f"DCA strategy failed: {e}")
    
    def run_drip(self):
        """Run Dividend Reinvestment strategy"""
        if not self.config.drip_enabled:
            logger.info("DRIP strategy is disabled")
            return
        
        try:
            logger.info("Running DRIP strategy")
            strategy = DRIPStrategy(self.client, self.config.account_number)
            results = strategy.execute(dry_run=False)
            logger.info(f"DRIP completed: {len(results)} reinvestments executed")
        except Exception as e:
            logger.error(f"DRIP strategy failed: {e}")
    
    def run_rebalance(self):
        """Run Portfolio Rebalancing strategy"""
        if not self.config.rebalance_enabled:
            logger.info("Rebalancing strategy is disabled")
            return
        
        try:
            logger.info("Running rebalancing strategy")
            strategy = RebalanceStrategy(self.client, self.config.account_number)
            results = strategy.execute(
                self.config.target_allocation,
                self.config.rebalance_threshold,
                dry_run=False
            )
            logger.info(f"Rebalancing completed: {len(results)} trades executed")
        except Exception as e:
            logger.error(f"Rebalancing strategy failed: {e}")
    
    def run_opportunistic(self):
        """Run Opportunistic Buying strategy"""
        if not self.config.opportunistic_enabled:
            logger.info("Opportunistic strategy is disabled")
            return
        
        try:
            logger.info("Running opportunistic buying strategy")
            strategy = OpportunisticStrategy(self.client, self.config.account_number)
            results = strategy.execute(
                self.config.dca_symbols,  # Use same watchlist as DCA
                self.config.opportunistic_dip_threshold,
                100.0,  # Default amount per opportunity
                dry_run=False
            )
            logger.info(f"Opportunistic buying completed: {len(results)} opportunities acted on")
        except Exception as e:
            logger.error(f"Opportunistic strategy failed: {e}")


def main():
    """Main scheduler function"""
    # Load configuration
    config = Config()
    
    # Setup logging
    setup_logging(config.log_level, config.log_file)
    
    logger.info("Starting investment strategy scheduler")
    
    # Initialize scheduler
    scheduler = StrategyScheduler(config)
    
    # Schedule DCA based on frequency
    if config.dca_enabled:
        if config.dca_frequency == "daily":
            schedule.every().day.at("09:35").do(scheduler.run_dca)  # 5 min after market open
            logger.info("Scheduled DCA: daily at 9:35 AM")
        elif config.dca_frequency == "weekly":
            schedule.every().monday.at("09:35").do(scheduler.run_dca)
            logger.info("Scheduled DCA: weekly on Monday at 9:35 AM")
        elif config.dca_frequency == "monthly":
            schedule.every().day.at("09:35").do(
                lambda: scheduler.run_dca() if time.localtime().tm_mday == 1 else None
            )
            logger.info("Scheduled DCA: monthly on 1st at 9:35 AM")
    
    # Schedule DRIP - run daily to check for dividends
    if config.drip_enabled:
        schedule.every().day.at("10:00").do(scheduler.run_drip)
        logger.info("Scheduled DRIP: daily at 10:00 AM")
    
    # Schedule rebalancing - run weekly
    if config.rebalance_enabled:
        schedule.every().friday.at("15:00").do(scheduler.run_rebalance)  # Before close
        logger.info("Scheduled rebalancing: weekly on Friday at 3:00 PM")
    
    # Schedule opportunistic buying - run multiple times per day
    if config.opportunistic_enabled:
        schedule.every().day.at("10:00").do(scheduler.run_opportunistic)
        schedule.every().day.at("12:00").do(scheduler.run_opportunistic)
        schedule.every().day.at("14:00").do(scheduler.run_opportunistic)
        logger.info("Scheduled opportunistic buying: 3x daily at 10:00, 12:00, 14:00")
    
    logger.info("Scheduler initialized, running...")
    
    # Run scheduler loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")


if __name__ == "__main__":
    main()
