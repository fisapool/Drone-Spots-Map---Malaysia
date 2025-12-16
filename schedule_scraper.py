#!/usr/bin/env python3
"""
Scheduler for periodic web scraping of drone spots.
Can run on a schedule (weekly/monthly) or as a one-time task.
"""

import argparse
import logging
import sys
from pathlib import Path
import schedule
import time
from datetime import datetime
from scrape_drone_spots import WebScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_scraper(config_path: str = "scraper_config.json", output_file: str = None):
    """
    Run the scraper and log results.
    
    Args:
        config_path: Path to configuration file
        output_file: Optional output file path
    """
    logger.info("=" * 60)
    logger.info(f"Scheduled scrape started at {datetime.now().isoformat()}")
    logger.info("=" * 60)
    
    try:
        scraper = WebScraper(config_path=config_path)
        scraper.run(output_file=output_file)
        logger.info("Scheduled scrape completed successfully")
    except Exception as e:
        logger.error(f"Error during scheduled scrape: {e}", exc_info=True)
    
    logger.info("=" * 60)


def main():
    """Main entry point for scheduler."""
    parser = argparse.ArgumentParser(
        description="Schedule periodic web scraping of drone spots",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once immediately
  python schedule_scraper.py --once
  
  # Schedule weekly (every Monday at 2 AM)
  python schedule_scraper.py --weekly --time "02:00"
  
  # Schedule monthly (1st of month at 3 AM)
  python schedule_scraper.py --monthly --time "03:00"
  
  # Run continuously, checking schedule every minute
  python schedule_scraper.py --weekly --time "02:00" --run
  
  # Custom config and output
  python schedule_scraper.py --once --config custom_config.json --output custom_output.json
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        default="scraper_config.json",
        help="Path to configuration file (default: scraper_config.json)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path (default: from config)"
    )
    
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once immediately and exit"
    )
    
    parser.add_argument(
        "--weekly",
        action="store_true",
        help="Schedule to run weekly"
    )
    
    parser.add_argument(
        "--monthly",
        action="store_true",
        help="Schedule to run monthly (1st of month)"
    )
    
    parser.add_argument(
        "--time",
        default="02:00",
        help="Time to run scheduled task (HH:MM format, default: 02:00)"
    )
    
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run continuously, checking schedule (use with --weekly or --monthly)"
    )
    
    args = parser.parse_args()
    
    # Check if config file exists
    if not Path(args.config).exists():
        logger.error(f"Configuration file not found: {args.config}")
        return 1
    
    # Validate time format
    try:
        time.strptime(args.time, "%H:%M")
    except ValueError:
        logger.error(f"Invalid time format: {args.time}. Use HH:MM format (e.g., 02:00)")
        return 1
    
    # Run once
    if args.once:
        logger.info("Running scraper once...")
        run_scraper(config_path=args.config, output_file=args.output)
        return 0
    
    # Schedule weekly
    if args.weekly:
        schedule.every().monday.at(args.time).do(
            run_scraper,
            config_path=args.config,
            output_file=args.output
        )
        logger.info(f"Scheduled weekly scrape for every Monday at {args.time}")
    
    # Schedule monthly
    if args.monthly:
        def monthly_job():
            if datetime.now().day == 1:
                run_scraper(config_path=args.config, output_file=args.output)
        
        schedule.every().day.at(args.time).do(monthly_job)
        logger.info(f"Scheduled monthly scrape for 1st of month at {args.time}")
    
    # If no schedule specified, show help
    if not args.weekly and not args.monthly:
        logger.error("Please specify --once, --weekly, or --monthly")
        parser.print_help()
        return 1
    
    # Run continuously if requested
    if args.run:
        logger.info("Running scheduler continuously. Press Ctrl+C to stop.")
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("\nScheduler stopped by user")
            return 0
    else:
        # Just show the schedule
        logger.info("Schedule configured. Use --run to start the scheduler.")
        logger.info("Or use a system cron job to run: python schedule_scraper.py --once")
        return 0


if __name__ == "__main__":
    exit(main())

