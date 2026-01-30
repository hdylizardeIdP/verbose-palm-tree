"""
Audit logging for trade operations.

Provides immutable, structured audit logs for all trading operations to support:
- Compliance requirements (SEC, FINRA)
- Transaction accountability
- Forensic analysis
- Dispute resolution

Logs are written in JSON format for easy parsing and analysis.
"""
import json
import logging
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum

from schwab_app.utils.validation import redact_account_number, redact_amount


class AuditEventType(str, Enum):
    """Types of auditable events."""
    # Trade events
    TRADE_INITIATED = "trade_initiated"
    TRADE_CONFIRMED = "trade_confirmed"
    TRADE_CANCELLED = "trade_cancelled"
    TRADE_EXECUTED = "trade_executed"
    TRADE_FAILED = "trade_failed"

    # Authentication events
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"
    TOKEN_REFRESHED = "token_refreshed"  # nosec B105 - not a password, audit event type

    # Configuration events
    CONFIG_LOADED = "config_loaded"
    CONFIG_CHANGED = "config_changed"

    # Strategy events
    STRATEGY_STARTED = "strategy_started"
    STRATEGY_COMPLETED = "strategy_completed"
    STRATEGY_FAILED = "strategy_failed"


class AuditLogger:
    """
    Structured audit logger for trade operations.

    Features:
    - JSON-formatted log entries
    - Automatic sensitive data redaction
    - Hash chain for tamper detection
    - Separate audit log file
    """

    def __init__(
        self,
        log_file: str = "audit.log",
        redact_sensitive: bool = True,
        include_hash_chain: bool = True,
    ):
        """
        Initialize audit logger.

        Args:
            log_file: Path to audit log file
            redact_sensitive: Whether to redact sensitive data (default: True)
            include_hash_chain: Whether to include hash chain for integrity (default: True)
        """
        self.log_file = Path(log_file)
        self.redact_sensitive = redact_sensitive
        self.include_hash_chain = include_hash_chain
        self._last_hash: Optional[str] = None
        self._logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up dedicated audit logger."""
        logger = logging.getLogger("schwab_audit")
        logger.setLevel(logging.INFO)
        logger.propagate = False  # Don't propagate to root logger

        # Remove existing handlers
        logger.handlers.clear()

        # Create file handler
        handler = logging.FileHandler(self.log_file, mode='a')
        handler.setLevel(logging.INFO)

        # Use simple formatter (we format as JSON ourselves)
        handler.setFormatter(logging.Formatter('%(message)s'))

        logger.addHandler(handler)
        return logger

    def _compute_hash(self, entry: Dict[str, Any]) -> str:
        """Compute SHA-256 hash of entry for hash chain."""
        # Include previous hash in computation
        entry_copy = entry.copy()
        if self._last_hash:
            entry_copy['_prev_hash'] = self._last_hash

        # Serialize deterministically
        serialized = json.dumps(entry_copy, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def _redact_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive data in audit entry."""
        redacted = entry.copy()

        # Redact known sensitive fields
        if 'account_number' in redacted:
            redacted['account_number'] = redact_account_number(
                str(redacted['account_number'])
            )

        if 'amount' in redacted and isinstance(redacted['amount'], (int, float)):
            redacted['amount_display'] = redact_amount(redacted['amount'])
            # Keep actual amount but mark as redacted in display
            redacted['amount'] = redacted['amount']  # Keep for internal use

        # Redact nested details
        if 'details' in redacted and isinstance(redacted['details'], dict):
            redacted['details'] = self._redact_entry(redacted['details'])

        return redacted

    def log(
        self,
        event_type: AuditEventType,
        account_number: Optional[str] = None,
        symbol: Optional[str] = None,
        amount: Optional[float] = None,
        quantity: Optional[int] = None,
        strategy: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            account_number: Account number involved
            symbol: Stock symbol involved
            amount: Dollar amount involved
            quantity: Share quantity involved
            strategy: Strategy name (dca, drip, etc.)
            success: Whether operation succeeded
            details: Additional details
            error: Error message if failed

        Returns:
            The audit entry that was logged
        """
        # Build entry
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type.value,
            "success": success,
        }

        # Add optional fields
        if account_number:
            entry["account_number"] = account_number
        if symbol:
            entry["symbol"] = symbol
        if amount is not None:
            entry["amount"] = amount
        if quantity is not None:
            entry["quantity"] = quantity
        if strategy:
            entry["strategy"] = strategy
        if details:
            entry["details"] = details
        if error:
            entry["error"] = error

        # Add process info
        entry["pid"] = os.getpid()

        # Compute hash chain
        if self.include_hash_chain:
            entry["_hash"] = self._compute_hash(entry)
            self._last_hash = entry["_hash"]

        # Redact for logging if enabled
        log_entry = self._redact_entry(entry) if self.redact_sensitive else entry

        # Write to audit log
        self._logger.info(json.dumps(log_entry, default=str))

        return entry

    def log_trade(
        self,
        event_type: AuditEventType,
        account_number: str,
        symbol: str,
        amount: Optional[float] = None,
        quantity: Optional[int] = None,
        order_type: str = "market",
        dry_run: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Convenience method for logging trade events.

        Args:
            event_type: Type of trade event
            account_number: Account number
            symbol: Stock symbol
            amount: Dollar amount
            quantity: Share quantity
            order_type: Order type (market, limit, etc.)
            dry_run: Whether this is a dry run
            **kwargs: Additional details

        Returns:
            The audit entry that was logged
        """
        details = {
            "order_type": order_type,
            "dry_run": dry_run,
            **kwargs
        }

        return self.log(
            event_type=event_type,
            account_number=account_number,
            symbol=symbol,
            amount=amount,
            quantity=quantity,
            details=details,
        )

    def log_strategy(
        self,
        event_type: AuditEventType,
        strategy: str,
        account_number: str,
        symbols: Optional[List[str]] = None,
        total_amount: Optional[float] = None,
        dry_run: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Convenience method for logging strategy events.

        Args:
            event_type: Type of strategy event
            strategy: Strategy name
            account_number: Account number
            symbols: List of symbols involved
            total_amount: Total amount for strategy
            dry_run: Whether this is a dry run
            **kwargs: Additional details

        Returns:
            The audit entry that was logged
        """
        details = {
            "symbols": symbols or [],
            "dry_run": dry_run,
            **kwargs
        }

        return self.log(
            event_type=event_type,
            strategy=strategy,
            account_number=account_number,
            amount=total_amount,
            details=details,
        )


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(log_file: str = "audit.log") -> AuditLogger:
    """Get or create the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(log_file=log_file)
    return _audit_logger


def audit_trade(
    event_type: AuditEventType,
    account_number: str,
    symbol: str,
    **kwargs
) -> Dict[str, Any]:
    """Convenience function to log a trade event using the global logger."""
    return get_audit_logger().log_trade(
        event_type=event_type,
        account_number=account_number,
        symbol=symbol,
        **kwargs
    )


def audit_strategy(
    event_type: AuditEventType,
    strategy: str,
    account_number: str,
    **kwargs
) -> Dict[str, Any]:
    """Convenience function to log a strategy event using the global logger."""
    return get_audit_logger().log_strategy(
        event_type=event_type,
        strategy=strategy,
        account_number=account_number,
        **kwargs
    )
