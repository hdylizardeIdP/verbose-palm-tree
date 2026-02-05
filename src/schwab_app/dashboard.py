"""
Web-based Dashboard for Schwab Investment App
Provides a GUI for monitoring and managing investment strategies.
"""
import logging
import json
import os
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    flash,
    redirect,
    url_for,
    send_from_directory,
)

from schwab_app.config import Config
from schwab_app.client import SchwabClient
from schwab_app.strategies import (
    DCAStrategy,
    DRIPStrategy,
    RebalanceStrategy,
    OpportunisticStrategy,
    OptionsStrategy,
)
from schwab_app.utils import (
    ValidationError,
    validate_amount,
    validate_symbols,
    validate_threshold,
    validate_allocation,
    setup_logging,
)

logger = logging.getLogger(__name__)

# In-memory activity log for the session
activity_log = []


def log_activity(action: str, details: str, status: str = "info"):
    """Record an activity entry."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "details": details,
        "status": status,
    }
    activity_log.insert(0, entry)
    # Keep last 200 entries
    if len(activity_log) > 200:
        activity_log.pop()


def create_app(env_file=None, log_level="INFO"):
    """
    Application factory for the Flask dashboard.

    Args:
        env_file: Path to .env file (optional)
        log_level: Logging level string

    Returns:
        Configured Flask application
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )
    app.secret_key = os.urandom(32)

    # Load configuration
    config = Config(env_file)
    setup_logging(log_level, config.log_file)

    # Store config on app
    app.config["SCHWAB_CONFIG"] = config

    # Initialize client lazily
    _client_instance = {}

    def get_client():
        if "client" not in _client_instance:
            try:
                c = SchwabClient(
                    config.api_key,
                    config.app_secret,
                    config.callback_url,
                    config.token_path,
                )
                _client_instance["client"] = c
                log_activity("System", "Schwab client initialized", "success")
            except Exception as e:
                log_activity("System", f"Client init failed: {e}", "error")
                raise
        return _client_instance["client"]

    def get_account():
        return config.account_number

    # ── Page Routes ──────────────────────────────────────────────────

    @app.route("/")
    def index():
        """Dashboard overview page."""
        return render_template("dashboard.html", config=config)

    @app.route("/positions")
    def positions_page():
        """Positions detail page."""
        return render_template("positions.html", config=config)

    @app.route("/strategies")
    def strategies_page():
        """Strategy execution page."""
        return render_template("strategies.html", config=config)

    @app.route("/activity")
    def activity_page():
        """Activity log page."""
        return render_template("activity.html", config=config)

    @app.route("/settings")
    def settings_page():
        """Settings & configuration page."""
        return render_template("settings.html", config=config)

    # ── API Routes ───────────────────────────────────────────────────

    @app.route("/api/balances")
    def api_balances():
        """Get account balances."""
        try:
            client = get_client()
            balances = client.get_account_balances(get_account())
            log_activity("Data", "Fetched account balances", "success")
            return jsonify({"status": "ok", "data": balances})
        except Exception as e:
            log_activity("Data", f"Failed to fetch balances: {e}", "error")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/positions")
    def api_positions():
        """Get current positions with calculated P/L."""
        try:
            client = get_client()
            raw_positions = client.get_positions(get_account())
            positions = []
            total_value = 0
            total_cost = 0

            for pos in raw_positions:
                instrument = pos.get("instrument", {})
                symbol = instrument.get("symbol", "")
                asset_type = instrument.get("assetType", "EQUITY")
                quantity = pos.get("longQuantity", 0)
                avg_price = pos.get("averagePrice", 0)
                market_value = pos.get("marketValue", 0)
                cost_basis = quantity * avg_price
                pnl = market_value - cost_basis
                pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0

                positions.append({
                    "symbol": symbol,
                    "assetType": asset_type,
                    "quantity": quantity,
                    "avgPrice": avg_price,
                    "marketValue": market_value,
                    "costBasis": cost_basis,
                    "pnl": pnl,
                    "pnlPct": pnl_pct,
                })
                total_value += market_value
                total_cost += cost_basis

            log_activity("Data", f"Fetched {len(positions)} positions", "success")
            return jsonify({
                "status": "ok",
                "data": positions,
                "summary": {
                    "totalValue": total_value,
                    "totalCost": total_cost,
                    "totalPnl": total_value - total_cost,
                    "totalPnlPct": ((total_value - total_cost) / total_cost * 100)
                    if total_cost > 0
                    else 0,
                },
            })
        except Exception as e:
            log_activity("Data", f"Failed to fetch positions: {e}", "error")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/account-info")
    def api_account_info():
        """Get full account info (balances + positions summary)."""
        try:
            client = get_client()
            balances = client.get_account_balances(get_account())
            raw_positions = client.get_positions(get_account())

            # Build allocation data
            allocation = {}
            total_value = 0
            for pos in raw_positions:
                instrument = pos.get("instrument", {})
                symbol = instrument.get("symbol", "")
                market_value = pos.get("marketValue", 0)
                allocation[symbol] = market_value
                total_value += market_value

            log_activity("Data", "Fetched account overview", "success")
            return jsonify({
                "status": "ok",
                "balances": balances,
                "allocation": allocation,
                "totalValue": total_value,
                "positionCount": len(raw_positions),
            })
        except Exception as e:
            log_activity("Data", f"Failed to fetch account info: {e}", "error")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/activity")
    def api_activity():
        """Get activity log."""
        limit = request.args.get("limit", 50, type=int)
        return jsonify({"status": "ok", "data": activity_log[:limit]})

    # ── Strategy Execution API ───────────────────────────────────────

    @app.route("/api/strategies/dca", methods=["POST"])
    def api_dca():
        """Execute Dollar Cost Averaging strategy."""
        try:
            data = request.get_json(force=True)
            amount = float(data.get("amount", 0))
            symbols_raw = data.get("symbols", "")
            dry_run = data.get("dryRun", True)

            symbol_list = [s.strip() for s in symbols_raw.split(",") if s.strip()]
            amount = validate_amount(amount, field_name="Investment amount")
            symbol_list = validate_symbols(symbol_list)

            client = get_client()
            strategy = DCAStrategy(client, get_account())
            results = strategy.execute(symbol_list, amount, dry_run)

            mode = "DRY RUN" if dry_run else "LIVE"
            log_activity(
                "DCA",
                f"[{mode}] ${amount:,.2f} across {', '.join(symbol_list)}",
                "success",
            )
            return jsonify({"status": "ok", "dryRun": dry_run, "results": results})

        except ValidationError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            log_activity("DCA", f"Strategy failed: {e}", "error")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/strategies/drip", methods=["POST"])
    def api_drip():
        """Execute DRIP strategy."""
        try:
            data = request.get_json(force=True)
            dry_run = data.get("dryRun", True)

            client = get_client()
            strategy = DRIPStrategy(client, get_account())
            results = strategy.execute(dry_run)

            mode = "DRY RUN" if dry_run else "LIVE"
            log_activity("DRIP", f"[{mode}] Dividend reinvestment executed", "success")
            return jsonify({"status": "ok", "dryRun": dry_run, "results": results or []})

        except Exception as e:
            log_activity("DRIP", f"Strategy failed: {e}", "error")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/strategies/rebalance", methods=["POST"])
    def api_rebalance():
        """Execute rebalancing strategy."""
        try:
            data = request.get_json(force=True)
            threshold = float(data.get("threshold", config.rebalance_threshold))
            dry_run = data.get("dryRun", True)

            threshold = validate_threshold(
                threshold, min_threshold=0.001, max_threshold=0.5,
                field_name="Rebalancing threshold",
            )

            client = get_client()
            strategy = RebalanceStrategy(client, get_account())
            results = strategy.execute(config.target_allocation, threshold, dry_run)

            mode = "DRY RUN" if dry_run else "LIVE"
            log_activity(
                "Rebalance",
                f"[{mode}] Threshold {threshold*100:.1f}%",
                "success",
            )
            return jsonify({"status": "ok", "dryRun": dry_run, "results": results or []})

        except ValidationError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            log_activity("Rebalance", f"Strategy failed: {e}", "error")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/strategies/opportunistic", methods=["POST"])
    def api_opportunistic():
        """Execute opportunistic buying strategy."""
        try:
            data = request.get_json(force=True)
            symbols_raw = data.get("symbols", "")
            threshold = float(data.get("threshold", config.opportunistic_dip_threshold))
            amount = float(data.get("amount", 100.0))
            dry_run = data.get("dryRun", True)

            symbol_list = [s.strip() for s in symbols_raw.split(",") if s.strip()]
            symbol_list = validate_symbols(symbol_list)
            threshold = validate_threshold(
                threshold, min_threshold=0.001, max_threshold=0.5,
                field_name="Dip threshold",
            )
            amount = validate_amount(amount, field_name="Buy amount")

            client = get_client()
            strategy = OpportunisticStrategy(client, get_account())
            results = strategy.execute(symbol_list, threshold, amount, dry_run)

            mode = "DRY RUN" if dry_run else "LIVE"
            log_activity(
                "Opportunistic",
                f"[{mode}] Scanning {', '.join(symbol_list)} at {threshold*100:.1f}% threshold",
                "success",
            )
            return jsonify({"status": "ok", "dryRun": dry_run, "results": results or []})

        except ValidationError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            log_activity("Opportunistic", f"Strategy failed: {e}", "error")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/strategies/covered-calls", methods=["POST"])
    def api_covered_calls():
        """Execute covered call strategy."""
        try:
            data = request.get_json(force=True)
            symbols_raw = data.get("symbols", "")
            dry_run = data.get("dryRun", True)

            symbol_list = None
            if symbols_raw:
                symbol_list = [s.strip() for s in symbols_raw.split(",") if s.strip()]
                symbol_list = validate_symbols(symbol_list)

            client = get_client()
            strategy = OptionsStrategy(client, get_account())
            results = strategy.sell_covered_calls(symbol_list, dry_run=dry_run)

            mode = "DRY RUN" if dry_run else "LIVE"
            targets = ", ".join(symbol_list) if symbol_list else "all positions"
            log_activity("Covered Calls", f"[{mode}] {targets}", "success")
            return jsonify({"status": "ok", "dryRun": dry_run, "results": results or []})

        except ValidationError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            log_activity("Covered Calls", f"Strategy failed: {e}", "error")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/strategies/protective-puts", methods=["POST"])
    def api_protective_puts():
        """Execute protective put strategy."""
        try:
            data = request.get_json(force=True)
            symbols_raw = data.get("symbols", "")
            dry_run = data.get("dryRun", True)

            symbol_list = None
            if symbols_raw:
                symbol_list = [s.strip() for s in symbols_raw.split(",") if s.strip()]
                symbol_list = validate_symbols(symbol_list)

            client = get_client()
            strategy = OptionsStrategy(client, get_account())
            results = strategy.buy_protective_puts(symbol_list, dry_run=dry_run)

            mode = "DRY RUN" if dry_run else "LIVE"
            targets = ", ".join(symbol_list) if symbol_list else "all positions"
            log_activity("Protective Puts", f"[{mode}] {targets}", "success")
            return jsonify({"status": "ok", "dryRun": dry_run, "results": results or []})

        except ValidationError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            log_activity("Protective Puts", f"Strategy failed: {e}", "error")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/config")
    def api_config():
        """Get current configuration (sensitive values redacted)."""
        return jsonify({
            "status": "ok",
            "data": {
                "dca": {
                    "enabled": config.dca_enabled,
                    "amount": config.dca_amount,
                    "frequency": config.dca_frequency,
                    "symbols": config.dca_symbols,
                },
                "drip": {"enabled": config.drip_enabled},
                "rebalance": {
                    "enabled": config.rebalance_enabled,
                    "threshold": config.rebalance_threshold,
                    "targetAllocation": config.target_allocation,
                },
                "opportunistic": {
                    "enabled": config.opportunistic_enabled,
                    "dipThreshold": config.opportunistic_dip_threshold,
                },
                "options": {"enabled": config.options_enabled},
                "logging": {
                    "level": config.log_level,
                    "file": config.log_file,
                },
            },
        })

    # Log app start
    log_activity("System", "Dashboard started", "success")

    return app


def run_dashboard(host="127.0.0.1", port=5000, env_file=None, log_level="INFO", debug=False):
    """
    Launch the web dashboard.

    Args:
        host: Bind address
        port: Port number
        env_file: Path to .env file
        log_level: Logging level
        debug: Enable Flask debug mode
    """
    app = create_app(env_file=env_file, log_level=log_level)
    print(f"\n  Schwab Investment Dashboard")
    print(f"  Running at: http://{host}:{port}")
    print(f"  Press Ctrl+C to stop\n")
    app.run(host=host, port=port, debug=debug)
