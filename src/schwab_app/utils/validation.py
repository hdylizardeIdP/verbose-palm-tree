"""
Input validation utilities for Schwab Investment App

Provides comprehensive validation for all user inputs to prevent:
- Negative or invalid amounts
- Malformed stock symbols
- Invalid thresholds and percentages
- JSON injection attacks
- Overflow and precision errors
- Path traversal attacks
"""
import re
import math
import os
from pathlib import Path
from typing import List, Dict, Union, Optional


class ValidationError(ValueError):
    """Custom exception for validation errors"""
    pass


def validate_amount(
    amount: Union[int, float, None],
    min_amount: float = 0.01,
    max_amount: float = 1_000_000.00,
    field_name: str = "Amount"
) -> float:
    """
    Validate investment amount

    Args:
        amount: Amount to validate
        min_amount: Minimum allowed amount (default: $0.01)
        max_amount: Maximum allowed amount (default: $1,000,000)
        field_name: Name of field for error messages

    Returns:
        Validated amount rounded to 2 decimal places

    Raises:
        ValidationError: If amount is invalid

    Examples:
        >>> validate_amount(1000.00)
        1000.00
        >>> validate_amount(-100)
        ValidationError: Amount must be positive
        >>> validate_amount(2000000)
        ValidationError: Amount exceeds maximum
    """
    # Check for None
    if amount is None:
        raise ValidationError(f"{field_name} is required")

    # Check type
    if not isinstance(amount, (int, float)):
        raise ValidationError(
            f"{field_name} must be a number, got {type(amount).__name__}"
        )

    # Check for NaN, Infinity
    if not math.isfinite(amount):
        raise ValidationError(f"{field_name} must be a finite number")

    # Check for positive
    if amount <= 0:
        raise ValidationError(
            f"{field_name} must be positive, got ${amount:,.2f}"
        )

    # Check minimum
    if amount < min_amount:
        raise ValidationError(
            f"{field_name} must be at least ${min_amount:,.2f}, got ${amount:,.2f}"
        )

    # Check maximum
    if amount > max_amount:
        raise ValidationError(
            f"{field_name} exceeds maximum of ${max_amount:,.2f}, got ${amount:,.2f}"
        )

    # Round to cents (2 decimal places)
    return round(amount, 2)


def validate_symbol(symbol: Union[str, None]) -> str:
    """
    Validate stock symbol format

    Args:
        symbol: Stock symbol to validate

    Returns:
        Validated symbol in uppercase

    Raises:
        ValidationError: If symbol is invalid

    Examples:
        >>> validate_symbol("SPY")
        'SPY'
        >>> validate_symbol("spy")
        'SPY'
        >>> validate_symbol("INVALID123")
        ValidationError: Invalid symbol format
        >>> validate_symbol("")
        ValidationError: Symbol cannot be empty
    """
    # Check for None
    if symbol is None:
        raise ValidationError("Symbol is required")

    # Check type
    if not isinstance(symbol, str):
        raise ValidationError(
            f"Symbol must be a string, got {type(symbol).__name__}"
        )

    # Clean and uppercase
    symbol = symbol.strip().upper()

    # Check for empty
    if not symbol:
        raise ValidationError("Symbol cannot be empty or whitespace")

    # Check length (1-5 characters for standard symbols)
    # Note: Some symbols can be up to 5 chars (e.g., AAPL, GOOGL)
    if len(symbol) < 1 or len(symbol) > 5:
        raise ValidationError(
            f"Symbol must be 1-5 characters, got {len(symbol)}: '{symbol}'"
        )

    # Check format: Only uppercase letters A-Z
    # This prevents injection attacks and invalid symbols
    if not re.match(r'^[A-Z]{1,5}$', symbol):
        raise ValidationError(
            f"Invalid symbol format: '{symbol}'. "
            "Symbols must contain only letters A-Z (1-5 characters)"
        )

    return symbol


def validate_symbols(
    symbols: Union[str, List[str], None],
    min_count: int = 1,
    max_count: int = 50
) -> List[str]:
    """
    Validate and parse list of stock symbols

    Args:
        symbols: Comma-separated string or list of symbols
        min_count: Minimum number of symbols required
        max_count: Maximum number of symbols allowed

    Returns:
        List of validated symbols

    Raises:
        ValidationError: If symbols are invalid

    Examples:
        >>> validate_symbols("SPY,QQQ,IWM")
        ['SPY', 'QQQ', 'IWM']
        >>> validate_symbols(["spy", "qqq"])
        ['SPY', 'QQQ']
        >>> validate_symbols("")
        ValidationError: At least 1 symbol required
    """
    # Check for None
    if symbols is None:
        raise ValidationError("Symbols are required")

    # Parse string to list
    if isinstance(symbols, str):
        # Split by comma
        symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
    elif isinstance(symbols, list):
        symbol_list = [s for s in symbols if s]
    else:
        raise ValidationError(
            f"Symbols must be a string or list, got {type(symbols).__name__}"
        )

    # Check count
    if len(symbol_list) < min_count:
        raise ValidationError(
            f"At least {min_count} symbol(s) required, got {len(symbol_list)}"
        )

    if len(symbol_list) > max_count:
        raise ValidationError(
            f"Too many symbols: maximum {max_count}, got {len(symbol_list)}"
        )

    # Validate each symbol
    validated_symbols = []
    for symbol in symbol_list:
        try:
            validated_symbols.append(validate_symbol(symbol))
        except ValidationError as e:
            raise ValidationError(f"Invalid symbol in list: {e}")

    # Check for duplicates
    if len(validated_symbols) != len(set(validated_symbols)):
        duplicates = [s for s in validated_symbols if validated_symbols.count(s) > 1]
        raise ValidationError(
            f"Duplicate symbols not allowed: {', '.join(set(duplicates))}"
        )

    return validated_symbols


def validate_threshold(
    threshold: Union[int, float, None],
    min_threshold: float = 0.0,
    max_threshold: float = 1.0,
    field_name: str = "Threshold"
) -> float:
    """
    Validate threshold/percentage value

    Args:
        threshold: Threshold to validate (as decimal, e.g., 0.05 for 5%)
        min_threshold: Minimum allowed (default: 0.0)
        max_threshold: Maximum allowed (default: 1.0)
        field_name: Name of field for error messages

    Returns:
        Validated threshold

    Raises:
        ValidationError: If threshold is invalid

    Examples:
        >>> validate_threshold(0.05)
        0.05
        >>> validate_threshold(-0.1)
        ValidationError: Threshold must be positive
        >>> validate_threshold(1.5)
        ValidationError: Threshold cannot exceed 1.0
    """
    # Check for None
    if threshold is None:
        raise ValidationError(f"{field_name} is required")

    # Check type
    if not isinstance(threshold, (int, float)):
        raise ValidationError(
            f"{field_name} must be a number, got {type(threshold).__name__}"
        )

    # Check for NaN, Infinity
    if not math.isfinite(threshold):
        raise ValidationError(f"{field_name} must be a finite number")

    # Check range
    if threshold < min_threshold:
        raise ValidationError(
            f"{field_name} must be at least {min_threshold}, got {threshold}"
        )

    if threshold > max_threshold:
        raise ValidationError(
            f"{field_name} cannot exceed {max_threshold}, got {threshold}"
        )

    # Round to 6 decimal places for precision
    return round(threshold, 6)


def validate_allocation(
    allocation: Union[Dict[str, float], None],
    require_sum_to_one: bool = True,
    tolerance: float = 0.001
) -> Dict[str, float]:
    """
    Validate portfolio allocation dictionary

    Args:
        allocation: Dictionary of {symbol: percentage} (as decimals)
        require_sum_to_one: Whether percentages must sum to 1.0
        tolerance: Tolerance for sum check (default: 0.001)

    Returns:
        Validated allocation dictionary

    Raises:
        ValidationError: If allocation is invalid

    Examples:
        >>> validate_allocation({"SPY": 0.6, "AGG": 0.4})
        {'SPY': 0.6, 'AGG': 0.4}
        >>> validate_allocation({"SPY": 0.5})
        ValidationError: Allocation must sum to 1.0
        >>> validate_allocation({"SPY": -0.5, "AGG": 1.5})
        ValidationError: Percentage must be between 0 and 1
    """
    # Check for None
    if allocation is None:
        raise ValidationError("Allocation is required")

    # Check type
    if not isinstance(allocation, dict):
        raise ValidationError(
            f"Allocation must be a dictionary, got {type(allocation).__name__}"
        )

    # Check not empty
    if not allocation:
        raise ValidationError("Allocation cannot be empty")

    # Check size limit
    if len(allocation) > 100:
        raise ValidationError(
            f"Too many symbols in allocation: maximum 100, got {len(allocation)}"
        )

    # Validate each entry
    validated_allocation = {}
    total = 0.0

    for symbol, percentage in allocation.items():
        # Validate symbol
        validated_symbol = validate_symbol(symbol)

        # Validate percentage
        if not isinstance(percentage, (int, float)):
            raise ValidationError(
                f"Percentage for {symbol} must be a number, "
                f"got {type(percentage).__name__}"
            )

        if not math.isfinite(percentage):
            raise ValidationError(
                f"Percentage for {symbol} must be finite"
            )

        if percentage <= 0 or percentage > 1:
            raise ValidationError(
                f"Percentage for {symbol} must be greater than 0 and less than or equal to 1, "
                f"got {percentage}"
            )

        # Round to 6 decimal places
        validated_percentage = round(percentage, 6)
        validated_allocation[validated_symbol] = validated_percentage
        total += validated_percentage

    # Check sum if required
    if require_sum_to_one:
        if not (1.0 - tolerance <= total <= 1.0 + tolerance):
            raise ValidationError(
                f"Allocation percentages must sum to 1.0 (±{tolerance}), "
                f"got {total:.6f}"
            )

    return validated_allocation


def sanitize_for_log(value: str, max_length: int = 100) -> str:
    """
    Sanitize string for logging to prevent log injection

    Args:
        value: String to sanitize
        max_length: Maximum length to allow

    Returns:
        Sanitized string safe for logging

    Examples:
        >>> sanitize_for_log("Normal string")
        'Normal string'
        >>> sanitize_for_log("Line 1\\nLine 2")
        'Line 1 Line 2'
        >>> sanitize_for_log("A" * 200, max_length=50)
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA...'
    """
    if not isinstance(value, str):
        value = str(value)

    # Remove control characters and newlines to prevent log injection
    value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)

    # Replace newlines with spaces
    value = value.replace('\n', ' ').replace('\r', ' ')

    # Trim whitespace
    value = ' '.join(value.split())

    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length] + '...'

    return value


def validate_path(
    path: Union[str, Path, None],
    allowed_dir: Optional[Union[str, Path]] = None,
    must_exist: bool = False,
    allow_absolute: bool = True,
    field_name: str = "Path"
) -> Path:
    """
    Validate file path to prevent path traversal attacks.

    Args:
        path: Path to validate
        allowed_dir: If specified, path must be within this directory
        must_exist: If True, path must exist
        allow_absolute: If False, only relative paths allowed
        field_name: Name of field for error messages

    Returns:
        Validated Path object

    Raises:
        ValidationError: If path is invalid or traversal detected

    Examples:
        >>> validate_path(".tokens.json")
        PosixPath('.tokens.json')
        >>> validate_path("../../../etc/passwd")
        ValidationError: Path traversal detected
        >>> validate_path("/etc/passwd", allowed_dir="/home/user")
        ValidationError: Path outside allowed directory
    """
    # Check for None
    if path is None:
        raise ValidationError(f"{field_name} is required")

    # Convert to string first for validation
    if isinstance(path, Path):
        path_str = str(path)
    elif isinstance(path, str):
        path_str = path
    else:
        raise ValidationError(
            f"{field_name} must be a string or Path, got {type(path).__name__}"
        )

    # Check for empty
    if not path_str.strip():
        raise ValidationError(f"{field_name} cannot be empty")

    # Check for null bytes (security risk)
    if '\x00' in path_str:
        raise ValidationError(f"{field_name} contains invalid characters")

    # Check length
    if len(path_str) > 4096:
        raise ValidationError(f"{field_name} too long (max 4096 characters)")

    # Convert to Path object
    path_obj = Path(path_str)

    # Check for absolute paths if not allowed
    if not allow_absolute and path_obj.is_absolute():
        raise ValidationError(
            f"{field_name} must be a relative path, got absolute: {path_str}"
        )

    # Check for path traversal patterns
    # Resolve to absolute to detect traversal
    try:
        if allowed_dir:
            allowed_dir = Path(allowed_dir).resolve()
            resolved = (allowed_dir / path_obj).resolve()

            # Check if resolved path is within allowed directory
            try:
                resolved.relative_to(allowed_dir)
            except ValueError:
                raise ValidationError(
                    f"{field_name} must be within {allowed_dir}, "
                    f"path traversal detected"
                )
        else:
            # Just resolve to check for obvious traversal
            resolved = path_obj.resolve()

            # Check for suspicious patterns even without allowed_dir
            suspicious_patterns = ['..', '/etc/', '/var/', '/usr/', '/root/']
            for pattern in suspicious_patterns:
                if pattern in path_str:
                    raise ValidationError(
                        f"{field_name} contains suspicious pattern: {pattern}"
                    )
    except OSError as e:
        raise ValidationError(f"{field_name} is invalid: {e}")

    # Check existence if required
    if must_exist and not path_obj.exists():
        raise ValidationError(f"{field_name} does not exist: {path_str}")

    return path_obj


def redact_sensitive(
    value: str,
    visible_chars: int = 4,
    redact_char: str = "*"
) -> str:
    """
    Redact sensitive data for logging, keeping only last few characters visible.

    Args:
        value: Sensitive value to redact
        visible_chars: Number of characters to keep visible at the end
        redact_char: Character to use for redaction

    Returns:
        Redacted string

    Examples:
        >>> redact_sensitive("1234567890")
        '******7890'
        >>> redact_sensitive("ABC")
        '***'
        >>> redact_sensitive("secret_key_12345", visible_chars=5)
        '***********12345'
    """
    if not value:
        return ""

    value_str = str(value)
    length = len(value_str)

    if length <= visible_chars:
        # If value is shorter than visible chars, redact everything
        return redact_char * length

    # Keep last N characters visible
    redacted_part = redact_char * (length - visible_chars)
    visible_part = value_str[-visible_chars:]
    return redacted_part + visible_part


def redact_account_number(account_number: str) -> str:
    """
    Redact account number for logging (show only last 4 digits).

    Args:
        account_number: Account number to redact

    Returns:
        Redacted account number

    Examples:
        >>> redact_account_number("123456789012")
        '********9012'
    """
    return redact_sensitive(account_number, visible_chars=4)


def redact_amount(amount: float) -> str:
    """
    Redact amount for logging (show magnitude only).

    Args:
        amount: Dollar amount to redact

    Returns:
        Redacted amount string showing magnitude

    Examples:
        >>> redact_amount(12345.67)
        '$*****.**'
        >>> redact_amount(100.00)
        '$***.**'
    """
    if amount is None:
        return "$*.**"

    # Show only the magnitude (number of digits)
    magnitude = len(str(int(abs(amount))))
    return f"${'*' * magnitude}.**"
