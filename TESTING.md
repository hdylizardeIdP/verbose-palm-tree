# Testing Guide for Schwab Investment App

This guide explains how to test the Schwab Investment App safely before using it with real money.

## Prerequisites

Before testing:
1. Have a Charles Schwab account (preferably a paper trading account for testing)
2. Register for API access at [Charles Schwab Developer Portal](https://developer.schwab.com/)
3. Python 3.8+ installed
4. All dependencies installed (`pip install -r requirements.txt`)

## Setup for Testing

### 1. Create Test Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your test credentials
# Use paper trading account credentials if available
nano .env
```

### 2. Required Configuration

Minimum required settings in `.env`:
```
SCHWAB_API_KEY=your_test_api_key
SCHWAB_APP_SECRET=your_test_app_secret
SCHWAB_CALLBACK_URL=https://localhost:8182
SCHWAB_ACCOUNT_NUMBER=your_test_account_hash
```

### 3. First Authentication

Test authentication first:
```bash
schwab-invest --log-level DEBUG balance
```

This will:
1. Prompt you to authorize via OAuth
2. Save tokens to `.schwab_tokens.json`
3. Display your account balance if successful

## Testing Each Strategy

### Safety First: Always Use Dry-Run

**IMPORTANT**: Always test with `--dry-run` flag first!

### 1. Test Account Access

```bash
# Check balance
schwab-invest balance

# View positions
schwab-invest positions
```

### 2. Test Dollar Cost Averaging (DCA)

```bash
# Preview what would happen
schwab-invest dca --amount 10 --symbols "SPY" --dry-run

# If preview looks good, execute (start with small amounts!)
schwab-invest dca --amount 10 --symbols "SPY"
```

**Testing checklist:**
- [ ] Dry run shows expected number of shares
- [ ] Price looks reasonable
- [ ] Amount is correct
- [ ] Symbol is correct

### 3. Test Dividend Reinvestment (DRIP)

```bash
# Preview dividend reinvestment
schwab-invest drip --dry-run

# Execute if preview is good
schwab-invest drip
```

**Testing checklist:**
- [ ] Identifies dividend-paying positions correctly
- [ ] Calculates proportional reinvestment correctly
- [ ] Skips positions with insufficient cash

### 4. Test Portfolio Rebalancing

```bash
# Preview rebalancing with high threshold (to avoid frequent trades)
schwab-invest rebalance --threshold 0.10 --dry-run

# Execute if preview is good
schwab-invest rebalance --threshold 0.10
```

**Testing checklist:**
- [ ] Calculates current allocation correctly
- [ ] Identifies which positions need rebalancing
- [ ] Buy/sell decisions make sense
- [ ] Threshold is respected

### 5. Test Opportunistic Buying

```bash
# Preview opportunistic buying
schwab-invest opportunistic --symbols "AAPL,MSFT" --threshold 0.05 --amount 50 --dry-run

# Execute if opportunities found
schwab-invest opportunistic --symbols "AAPL,MSFT" --threshold 0.05 --amount 50
```

**Testing checklist:**
- [ ] Correctly identifies price dips
- [ ] Calculates dip percentage accurately
- [ ] Buy amount is as expected
- [ ] Only triggers on actual dips

### 6. Test Options Strategies

**WARNING**: Options trading is complex and risky. Test very carefully!

```bash
# Preview covered calls (requires you to own 100+ shares)
schwab-invest covered-calls --symbols "SPY" --dry-run

# Preview protective puts
schwab-invest protective-puts --symbols "SPY" --dry-run
```

**Testing checklist:**
- [ ] Only attempts covered calls on owned positions
- [ ] Strike prices are reasonable (5% OTM by default)
- [ ] Expiration dates are appropriate
- [ ] Premium amounts look correct
- [ ] Contract quantities match position sizes

## Automated Testing with Scheduler

### Test the Scheduler

1. Edit `.env` to enable only one strategy for testing:
```bash
DCA_ENABLED=true
DCA_AMOUNT=10  # Small amount for testing
DRIP_ENABLED=false
REBALANCE_ENABLED=false
OPPORTUNISTIC_ENABLED=false
OPTIONS_ENABLED=false
```

2. Run scheduler in foreground for testing:
```bash
python examples/scheduler.py
```

3. Monitor the logs to ensure:
   - Scheduler starts correctly
   - Scheduled times are appropriate
   - Strategies run at expected intervals

4. Stop with Ctrl+C when done testing

## Monitoring and Logs

### View Logs

```bash
# Watch log file in real-time
tail -f schwab_app.log

# View recent errors
grep ERROR schwab_app.log

# View all trades executed
grep "Order placed successfully" schwab_app.log
```

### Check Order Status

After executing a strategy, verify in your Schwab account:
1. Log into Charles Schwab website/app
2. Check "Order Status" 
3. Verify orders match what was logged

## Common Issues and Solutions

### Issue: Authentication fails

**Solution:**
```bash
# Remove old tokens and re-authenticate
rm .schwab_tokens.json
schwab-invest balance
```

### Issue: "Account not found"

**Solution:**
- Verify `SCHWAB_ACCOUNT_NUMBER` is the account hash (not the readable account number)
- Get the hash from the first successful API call or Schwab's API documentation

### Issue: Orders rejected

**Possible causes:**
- Market is closed
- Insufficient buying power
- Symbol is invalid
- Order size too small

**Solution:**
- Check market hours (9:30 AM - 4:00 PM ET)
- Verify account balance
- Test with valid symbols (SPY, QQQ, etc.)
- Increase order amounts

### Issue: Dry run works but real execution fails

**Solution:**
- Check if account has required permissions
- Verify account type allows the order type
- Ensure real-time market data is available

## Best Practices

1. **Start Small**: Test with minimal amounts ($10-50)
2. **Use Dry-Run**: Always preview before executing
3. **Check Logs**: Review logs after each test
4. **Verify in Schwab**: Always verify orders in your Schwab account
5. **Test Incrementally**: Test one strategy at a time
6. **Monitor Actively**: Don't run automated strategies unattended until fully tested
7. **Paper Trading**: Use a paper trading account if available
8. **Keep Records**: Save log files for review

## Gradual Rollout

Once basic testing is complete:

1. **Week 1**: Run manual commands with `--dry-run` daily
2. **Week 2**: Execute small real trades manually
3. **Week 3**: Enable one automated strategy with minimal amounts
4. **Week 4**: Gradually increase amounts if everything works correctly
5. **Month 2+**: Consider enabling additional strategies

## Security Testing

Before full deployment:

1. Verify `.env` is in `.gitignore`
2. Verify `.schwab_tokens.json` is in `.gitignore`
3. Never commit credentials to version control
4. Use environment-specific configurations
5. Regularly rotate API credentials

## Performance Testing

Track these metrics:
- Order execution time
- API response time
- Strategy execution success rate
- Actual returns vs. expected
- Error rate

## When to Stop Testing

You're ready to use in production when:
- [ ] All strategies tested with dry-run successfully
- [ ] Small real trades executed correctly
- [ ] Logs show no errors for 1 week
- [ ] Orders appear correctly in Schwab account
- [ ] Strategy logic makes sense for market conditions
- [ ] You understand all configuration options
- [ ] Error handling works as expected
- [ ] You're comfortable with the risk

## Need Help?

If you encounter issues:
1. Check logs first (`schwab_app.log`)
2. Increase log level to DEBUG for more details
3. Review Schwab API documentation
4. Open an issue on GitHub with:
   - Error messages (remove any sensitive info!)
   - Steps to reproduce
   - Log excerpts
   - Configuration (without credentials!)

## Final Reminder

**This is real money and real risk!**
- Never test with amounts you can't afford to lose
- Understand each strategy before using it
- Markets are unpredictable
- No strategy guarantees profits
- You are solely responsible for your trades

Good luck and trade safely!
