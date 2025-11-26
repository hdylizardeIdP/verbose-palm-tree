"""
Command Line Interface for Schwab Investment App
"""
import click
import logging
from rich.console import Console
from rich.table import Table
from rich import box
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
    setup_logging,
    ValidationError,
    validate_amount,
    validate_symbols,
    validate_threshold,
)

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.option('--env-file', type=click.Path(exists=True), help='Path to .env file')
@click.option('--log-level', default='INFO', help='Logging level')
@click.pass_context
def main(ctx, env_file, log_level):
    """Schwab Investment App - Automated trading strategies"""
    ctx.ensure_object(dict)
    
    # Load configuration
    config = Config(env_file)
    ctx.obj['config'] = config
    
    # Setup logging
    setup_logging(log_level, config.log_file)
    
    # Initialize client
    try:
        client = SchwabClient(
            config.api_key,
            config.app_secret,
            config.callback_url,
            config.token_path,
            encryption_key=config.token_encryption_key,
        )
        ctx.obj['client'] = client
        ctx.obj['account_number'] = config.account_number
    except Exception as e:
        console.print(f"[red]Failed to initialize client: {e}[/red]")
        raise click.Abort()


@main.command()
@click.pass_context
def balance(ctx):
    """Check account balances"""
    client = ctx.obj['client']
    account_number = ctx.obj['account_number']
    
    try:
        console.print("[cyan]Fetching account balances...[/cyan]")
        balances = client.get_account_balances(account_number)
        
        # Create table
        table = Table(title="Account Balances", box=box.ROUNDED)
        table.add_column("Item", style="cyan")
        table.add_column("Amount", style="green", justify="right")
        
        # Add balance items
        items = [
            ("Liquid Value", balances.get("liquidationValue", 0)),
            ("Cash Available", balances.get("cashAvailableForTrading", 0)),
            ("Buying Power", balances.get("buyingPower", 0)),
            ("Market Value", balances.get("marketValue", 0)),
        ]
        
        for item, value in items:
            table.add_row(item, f"${value:,.2f}")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Failed to get balances: {e}")


@main.command()
@click.pass_context
def positions(ctx):
    """Show current positions"""
    client = ctx.obj['client']
    account_number = ctx.obj['account_number']
    
    try:
        console.print("[cyan]Fetching positions...[/cyan]")
        positions = client.get_positions(account_number)
        
        if not positions:
            console.print("[yellow]No positions found[/yellow]")
            return
        
        # Create table
        table = Table(title="Current Positions", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan")
        table.add_column("Quantity", justify="right")
        table.add_column("Avg Cost", justify="right")
        table.add_column("Market Value", style="green", justify="right")
        table.add_column("P/L", justify="right")
        
        for position in positions:
            instrument = position.get("instrument", {})
            symbol = instrument.get("symbol", "")
            quantity = position.get("longQuantity", 0)
            avg_price = position.get("averagePrice", 0)
            market_value = position.get("marketValue", 0)
            
            # Calculate P/L
            cost_basis = quantity * avg_price
            pnl = market_value - cost_basis
            pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
            
            pnl_color = "green" if pnl >= 0 else "red"
            pnl_str = f"[{pnl_color}]${pnl:,.2f} ({pnl_pct:+.2f}%)[/{pnl_color}]"
            
            table.add_row(
                symbol,
                f"{quantity:.0f}",
                f"${avg_price:.2f}",
                f"${market_value:,.2f}",
                pnl_str
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Failed to get positions: {e}")


@main.command()
@click.option('--amount', type=float, help='Amount to invest (overrides config)')
@click.option('--symbols', help='Comma-separated symbols (overrides config)')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def dca(ctx, amount, symbols, dry_run, yes):
    """Execute Dollar Cost Averaging strategy"""
    config = ctx.obj['config']
    client = ctx.obj['client']
    account_number = ctx.obj['account_number']

    try:
        # Use provided values or fall back to config
        invest_amount = amount or config.dca_amount
        symbol_list = symbols.split(',') if symbols is not None else config.dca_symbols

        # Validate inputs
        invest_amount = validate_amount(invest_amount, field_name="Investment amount")
        symbol_list = validate_symbols(symbol_list)

    except ValidationError as e:
        console.print(f"[red]✗ Validation Error: {e}[/red]")
        logger.error(f"Input validation failed for DCA: {e}")
        raise click.Abort()

    console.print(f"[cyan]Executing DCA: ${invest_amount} across {symbol_list}[/cyan]")
    if dry_run:
        console.print("[yellow]DRY RUN - No orders will be placed[/yellow]")

    # Require confirmation for real trades
    if not dry_run and not yes:
        console.print(f"\n[yellow]⚠️  You are about to execute a REAL trade:[/yellow]")
        console.print(f"   Amount: [bold]${invest_amount:,.2f}[/bold]")
        console.print(f"   Symbols: [bold]{', '.join(symbol_list)}[/bold]")
        console.print(f"   Strategy: [bold]Dollar Cost Averaging[/bold]\n")
        if not click.confirm("Do you want to proceed with this trade?", default=False):
            console.print("[red]✗ Trade cancelled by user[/red]")
            return
    
    try:
        strategy = DCAStrategy(client, account_number)
        results = strategy.execute(symbol_list, invest_amount, dry_run)
        
        # Display results
        table = Table(title="DCA Results", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan")
        table.add_column("Status")
        table.add_column("Shares", justify="right")
        table.add_column("Price", justify="right")
        table.add_column("Amount", style="green", justify="right")
        
        for result in results:
            status = result.get("status", "unknown")
            status_color = "green" if status == "success" else "yellow"
            
            table.add_row(
                result.get("symbol", ""),
                f"[{status_color}]{status}[/{status_color}]",
                str(result.get("shares", 0)),
                f"${result.get('price', 0):.2f}",
                f"${result.get('amount', 0):.2f}"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"DCA strategy failed: {e}")


@main.command()
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def drip(ctx, dry_run, yes):
    """Execute Dividend Reinvestment strategy"""
    client = ctx.obj['client']
    account_number = ctx.obj['account_number']

    console.print("[cyan]Executing DRIP strategy...[/cyan]")
    if dry_run:
        console.print("[yellow]DRY RUN - No orders will be placed[/yellow]")

    # Require confirmation for real trades
    if not dry_run and not yes:
        console.print(f"\n[yellow]⚠️  You are about to execute REAL dividend reinvestment trades[/yellow]")
        console.print(f"   Strategy: [bold]Dividend Reinvestment (DRIP)[/bold]\n")
        if not click.confirm("Do you want to proceed with this strategy?", default=False):
            console.print("[red]✗ Trade cancelled by user[/red]")
            return
    
    try:
        strategy = DRIPStrategy(client, account_number)
        results = strategy.execute(dry_run)
        
        if not results:
            console.print("[yellow]No dividend reinvestment needed[/yellow]")
            return
        
        # Display results
        table = Table(title="DRIP Results", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan")
        table.add_column("Status")
        table.add_column("Shares", justify="right")
        table.add_column("Amount", style="green", justify="right")
        
        for result in results:
            status = result.get("status", "unknown")
            status_color = "green" if status == "success" else "yellow"
            
            table.add_row(
                result.get("symbol", ""),
                f"[{status_color}]{status}[/{status_color}]",
                str(result.get("shares", 0)),
                f"${result.get('amount', 0):.2f}"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"DRIP strategy failed: {e}")


@main.command()
@click.option('--threshold', type=float, help='Rebalancing threshold (e.g., 0.05 for 5%)')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def rebalance(ctx, threshold, dry_run, yes):
    """Execute portfolio rebalancing strategy"""
    config = ctx.obj['config']
    client = ctx.obj['client']
    account_number = ctx.obj['account_number']

    try:
        rebal_threshold = threshold or config.rebalance_threshold

        # Validate threshold
        rebal_threshold = validate_threshold(
            rebal_threshold,
            min_threshold=0.001,  # 0.1% minimum
            max_threshold=0.5,    # 50% maximum
            field_name="Rebalancing threshold"
        )

    except ValidationError as e:
        console.print(f"[red]✗ Validation Error: {e}[/red]")
        logger.error(f"Input validation failed for rebalance: {e}")
        raise click.Abort()

    console.print(f"[cyan]Executing rebalancing (threshold: {rebal_threshold*100}%)...[/cyan]")
    if dry_run:
        console.print("[yellow]DRY RUN - No orders will be placed[/yellow]")

    # Require confirmation for real trades
    if not dry_run and not yes:
        console.print(f"\n[yellow]⚠️  You are about to execute REAL rebalancing trades[/yellow]")
        console.print(f"   Threshold: [bold]{rebal_threshold*100}%[/bold]")
        console.print(f"   Strategy: [bold]Portfolio Rebalancing[/bold]")
        console.print(f"   Target Allocation: [bold]{config.target_allocation}[/bold]\n")
        if not click.confirm("Do you want to proceed with rebalancing?", default=False):
            console.print("[red]✗ Rebalancing cancelled by user[/red]")
            return
    
    try:
        strategy = RebalanceStrategy(client, account_number)
        results = strategy.execute(config.target_allocation, rebal_threshold, dry_run)
        
        if not results:
            console.print("[green]Portfolio is balanced![/green]")
            return
        
        # Display results
        table = Table(title="Rebalancing Results", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan")
        table.add_column("Action")
        table.add_column("Status")
        table.add_column("Shares", justify="right")
        table.add_column("Value", style="green", justify="right")
        
        for result in results:
            action = result.get("action", "").upper()
            action_color = "green" if action == "BUY" else "red"
            status = result.get("status", "unknown")
            status_color = "green" if status == "success" else "yellow"
            
            table.add_row(
                result.get("symbol", ""),
                f"[{action_color}]{action}[/{action_color}]",
                f"[{status_color}]{status}[/{status_color}]",
                str(result.get("shares", 0)),
                f"${result.get('value', 0):.2f}"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Rebalancing strategy failed: {e}")


@main.command()
@click.option('--symbols', help='Comma-separated watchlist symbols')
@click.option('--threshold', type=float, help='Dip threshold (e.g., 0.03 for 3%)')
@click.option('--amount', type=float, help='Amount to invest per dip')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def opportunistic(ctx, symbols, threshold, amount, dry_run, yes):
    """Execute opportunistic buying on market dips"""
    config = ctx.obj['config']
    client = ctx.obj['client']
    account_number = ctx.obj['account_number']

    try:
        watchlist = symbols.split(',') if symbols is not None else config.dca_symbols
        dip_threshold = threshold or config.opportunistic_dip_threshold
        buy_amount = amount or 100.0

        # Validate inputs
        watchlist = validate_symbols(watchlist)
        dip_threshold = validate_threshold(
            dip_threshold,
            min_threshold=0.001,  # 0.1% minimum
            max_threshold=0.5,    # 50% maximum
            field_name="Dip threshold"
        )
        buy_amount = validate_amount(buy_amount, field_name="Buy amount")

    except ValidationError as e:
        console.print(f"[red]✗ Validation Error: {e}[/red]")
        logger.error(f"Input validation failed for opportunistic: {e}")
        raise click.Abort()

    console.print(f"[cyan]Scanning for dips (threshold: {dip_threshold*100}%)...[/cyan]")
    if dry_run:
        console.print("[yellow]DRY RUN - No orders will be placed[/yellow]")

    # Require confirmation for real trades
    if not dry_run and not yes:
        console.print(f"\n[yellow]⚠️  You are about to execute REAL opportunistic trades[/yellow]")
        console.print(f"   Dip Threshold: [bold]{dip_threshold*100}%[/bold]")
        console.print(f"   Buy Amount per Dip: [bold]${buy_amount:,.2f}[/bold]")
        console.print(f"   Watchlist: [bold]{', '.join(watchlist)}[/bold]\n")
        if not click.confirm("Do you want to proceed with opportunistic buying?", default=False):
            console.print("[red]✗ Trade cancelled by user[/red]")
            return
    
    try:
        strategy = OpportunisticStrategy(client, account_number)
        results = strategy.execute(watchlist, dip_threshold, buy_amount, dry_run)
        
        if not results:
            console.print("[yellow]No buying opportunities found[/yellow]")
            return
        
        # Display results
        table = Table(title="Opportunistic Buying Results", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan")
        table.add_column("Status")
        table.add_column("Dip", justify="right")
        table.add_column("Shares", justify="right")
        table.add_column("Amount", style="green", justify="right")
        
        for result in results:
            status = result.get("status", "unknown")
            status_color = "green" if status == "success" else "yellow"
            dip = result.get("dip", 0)
            
            table.add_row(
                result.get("symbol", ""),
                f"[{status_color}]{status}[/{status_color}]",
                f"{dip*100:.2f}%",
                str(result.get("shares", 0)),
                f"${result.get('amount', 0):.2f}"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Opportunistic strategy failed: {e}")


@main.command()
@click.option('--symbols', help='Comma-separated symbols for covered calls')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def covered_calls(ctx, symbols, dry_run, yes):
    """Sell covered calls on existing positions"""
    client = ctx.obj['client']
    account_number = ctx.obj['account_number']

    try:
        symbol_list = symbols.split(',') if symbols is not None else None

        # Validate symbols if provided
        if symbol_list:
            symbol_list = validate_symbols(symbol_list)

    except ValidationError as e:
        console.print(f"[red]✗ Validation Error: {e}[/red]")
        logger.error(f"Input validation failed for covered_calls: {e}")
        raise click.Abort()

    console.print("[cyan]Executing covered call strategy...[/cyan]")
    if dry_run:
        console.print("[yellow]DRY RUN - No orders will be placed[/yellow]")

    # Require confirmation for real trades
    if not dry_run and not yes:
        console.print(f"\n[yellow]⚠️  You are about to sell REAL covered call options[/yellow]")
        console.print(f"   Symbols: [bold]{', '.join(symbol_list) if symbol_list else 'All positions'}[/bold]")
        console.print(f"   Strategy: [bold]Covered Calls[/bold]\n")
        console.print("[yellow]Note: Selling covered calls may limit upside potential[/yellow]\n")
        if not click.confirm("Do you want to proceed with selling covered calls?", default=False):
            console.print("[red]✗ Trade cancelled by user[/red]")
            return
    
    try:
        strategy = OptionsStrategy(client, account_number)
        results = strategy.sell_covered_calls(symbol_list, dry_run=dry_run)
        
        if not results:
            console.print("[yellow]No covered call opportunities[/yellow]")
            return
        
        # Display results
        table = Table(title="Covered Call Results", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan")
        table.add_column("Status")
        table.add_column("Contracts", justify="right")
        table.add_column("Strike", justify="right")
        table.add_column("Premium", style="green", justify="right")
        
        for result in results:
            status = result.get("status", "unknown")
            status_color = "green" if status == "success" else "yellow"
            
            table.add_row(
                result.get("symbol", ""),
                f"[{status_color}]{status}[/{status_color}]",
                str(result.get("contracts", 0)),
                f"${result.get('strike', 0):.2f}",
                f"${result.get('premium', 0):.2f}"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Covered call strategy failed: {e}")


@main.command()
@click.option('--symbols', help='Comma-separated symbols for protective puts')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def protective_puts(ctx, symbols, dry_run, yes):
    """Buy protective puts on existing positions"""
    client = ctx.obj['client']
    account_number = ctx.obj['account_number']

    try:
        symbol_list = symbols.split(',') if symbols is not None else None

        # Validate symbols if provided
        if symbol_list:
            symbol_list = validate_symbols(symbol_list)

    except ValidationError as e:
        console.print(f"[red]✗ Validation Error: {e}[/red]")
        logger.error(f"Input validation failed for protective_puts: {e}")
        raise click.Abort()

    console.print("[cyan]Executing protective put strategy...[/cyan]")
    if dry_run:
        console.print("[yellow]DRY RUN - No orders will be placed[/yellow]")

    # Require confirmation for real trades
    if not dry_run and not yes:
        console.print(f"\n[yellow]⚠️  You are about to buy REAL protective put options[/yellow]")
        console.print(f"   Symbols: [bold]{', '.join(symbol_list) if symbol_list else 'All positions'}[/bold]")
        console.print(f"   Strategy: [bold]Protective Puts (Insurance)[/bold]\n")
        console.print("[yellow]Note: Protective puts cost premium but provide downside protection[/yellow]\n")
        if not click.confirm("Do you want to proceed with buying protective puts?", default=False):
            console.print("[red]✗ Trade cancelled by user[/red]")
            return
    
    try:
        strategy = OptionsStrategy(client, account_number)
        results = strategy.buy_protective_puts(symbol_list, dry_run=dry_run)
        
        if not results:
            console.print("[yellow]No protective put opportunities[/yellow]")
            return
        
        # Display results
        table = Table(title="Protective Put Results", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan")
        table.add_column("Status")
        table.add_column("Contracts", justify="right")
        table.add_column("Strike", justify="right")
        table.add_column("Cost", style="red", justify="right")
        
        for result in results:
            status = result.get("status", "unknown")
            status_color = "green" if status == "success" else "yellow"
            
            table.add_row(
                result.get("symbol", ""),
                f"[{status_color}]{status}[/{status_color}]",
                str(result.get("contracts", 0)),
                f"${result.get('strike', 0):.2f}",
                f"${result.get('cost', 0):.2f}"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Protective put strategy failed: {e}")


if __name__ == '__main__':
    main()
