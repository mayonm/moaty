# Moaty Methodology

This document explains the analytical choices made in the Moaty economic moat decay prediction system.

## Overview

Moaty models how long a company's economic moat (competitive advantage) lasts by fitting an exponential decay curve to historical Return on Invested Capital (ROIC) data:

```
ROIC(t) = ROIC_terminal + (ROIC_0 - ROIC_terminal) × e^(-λt)
```

Where:
- **ROIC_0**: Initial ROIC at the start of the observation period
- **ROIC_terminal**: Long-run equilibrium ROIC (the "commodity" level)
- **λ (lambda)**: Decay rate — higher values indicate faster erosion of competitive advantage
- **t**: Time in years

## ROIC Calculation

### Formula

We use the classic ROIC definition:

```
ROIC = NOPAT / Invested Capital
```

Where:
- **NOPAT** (Net Operating Profit After Tax) = Operating Income × (1 - Effective Tax Rate)
- **Invested Capital** = Total Assets - Current Liabilities

### Data Sources

- **Operating Income**: SEC EDGAR XBRL tag `OperatingIncomeLoss`
- **Income Tax**: SEC EDGAR XBRL tag `IncomeTaxExpenseBenefit`
- **Total Assets**: SEC EDGAR XBRL tag `Assets`
- **Current Liabilities**: SEC EDGAR XBRL tag `LiabilitiesCurrent`

### Effective Tax Rate

Calculated as:
```
Effective Tax Rate = Income Tax Expense / Operating Income
```

Capped at range [0, 0.50] to handle outliers. Defaults to 21% (U.S. corporate rate) if calculation yields invalid result.

### Data Quality Filters

- Require 7+ annual ROIC observations per company
- Require 80%+ coverage within the company's observed year range
- ROIC values capped to [-1, 1] to handle extreme outliers

## Train/Holdout Split

- **Training period**: 2017-2024 (fiscal years)
- **Holdout period**: 2025-2026 (fiscal years)

This is a true predictive setup — the model is fit on training data only, and holdout data is used exclusively for validation.

## Decay Model Fitting

### Algorithm

We use non-linear least squares fitting via Julia's `LsqFit.jl` package.

### Parameter Bounds

| Parameter | Lower Bound | Upper Bound |
|-----------|-------------|-------------|
| ROIC_0 | -1.0 | 1.0 |
| λ | 0.001 | 2.0 |
| ROIC_terminal | -1.0 | 1.0 |

### Initial Guesses

- ROIC_0: First observed ROIC value
- λ: 0.1 (moderate decay)
- ROIC_terminal: Mean of last 2 observed ROIC values

### Convergence

Fits that don't converge within the solver's iteration limit are flagged (`converged = false`) but still recorded.

## Sector Mapping

Companies are mapped to sectors using SEC SIC (Standard Industrial Classification) codes:

| SIC Range | Sector |
|-----------|--------|
| 0100-0999 | Agriculture |
| 1000-1499 | Mining |
| 1500-1799 | Construction |
| 2000-3999 | Manufacturing |
| 4000-4999 | Transportation & Utilities |
| 5000-5199 | Wholesale Trade |
| 5200-5999 | Retail Trade |
| 6000-6799 | Finance & Insurance |
| 7000-8999 | Services |
| 9000-9999 | Public Administration |

## WACC Benchmarks

Industry WACC benchmarks are sourced from Professor Aswath Damodaran's datasets (NYU Stern). These provide cost of capital estimates by industry for comparison with company ROIC.

## Statistical Validation

### P-value on λ

Bootstrap resampling (100 iterations) is used to estimate the standard error of λ. The p-value tests whether λ is significantly different from zero (i.e., is there a real decay signal?).

### Confidence Intervals

95% confidence intervals on λ are computed using percentile bootstrap.

### Holdout RMSE

We compare two models on the holdout period:
1. **Decay model**: Predicted ROIC using fitted parameters
2. **Naive baseline**: Flat prediction using the last training ROIC value

A lower RMSE indicates better predictive accuracy.

### Price-Performance Correlation

We compute the correlation between:
- λ (decay rate) 
- Forward stock returns over the holdout period

Hypothesis: Companies with faster moat decay (higher λ) should underperform.

## Forecasts

### Base Case

Pure extrapolation of the fitted decay curve for 5 and 10 years beyond the last training period.

### Disruption Scenario

Applies a **1.5x multiplier** to λ to model faster erosion due to:
- Competitive disruption
- Technology shifts
- Regulatory changes
- Market structure changes

This is a stress test, not a prediction. The multiplier is intentionally aggressive.

## Limitations

1. **ROIC measurement noise**: Accounting choices affect reported values
2. **Sector assignment**: SIC codes are imperfect industry classifiers
3. **Survivorship bias**: Only companies with filings in both training and holdout periods are fully validated
4. **Model simplicity**: Exponential decay may not capture cyclical patterns or sudden regime changes
5. **Future data**: 2025-2026 data may be incomplete or preliminary

## Data Sources

| Data | Source | Period |
|------|--------|--------|
| Financial fundamentals | SEC EDGAR XBRL | 2017-2026 |
| Stock prices | Yahoo Finance (via yfinance) | 2017-2026 |
| WACC benchmarks | Damodaran datasets | Current |

## References

- Damodaran, A. "Return on Capital (ROC), Return on Invested Capital (ROIC) and Return on Equity (ROE): Measurement and Implications"
- SEC EDGAR Financial Statement Data Sets: https://www.sec.gov/dera/data/financial-statement-data-sets
