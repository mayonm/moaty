#!/usr/bin/env Rscript
# Moaty Statistical Validation
#
# Performs statistical validation of decay fits:
# 1. P-values and confidence intervals on λ
# 2. Holdout RMSE comparison (model vs naive baseline)
# 3. Price-performance correlation analysis

.libPaths(c("~/R/library", .libPaths()))

library(DBI)
library(RSQLite)
library(dplyr)
library(boot)

# Configuration
WORKSPACE <- Sys.getenv("WORKSPACE")
if (WORKSPACE == "" || is.na(WORKSPACE)) {
  WORKSPACE <- "/workspace"
}
DB_PATH <- file.path(WORKSPACE, "moaty.db")
HOLDOUT_YEARS <- c(2025, 2026)
N_BOOTSTRAP <- 100  # Bootstrap samples for CI

# Decay model function
decay_model <- function(t, roic_0, lambda, roic_terminal) {
  roic_terminal + (roic_0 - roic_terminal) * exp(-lambda * t)
}

# Bootstrap function for lambda CI
bootstrap_lambda <- function(data, indices) {
  d <- data[indices, ]
  if (nrow(d) < 4) return(NA)
  
  tryCatch({
    # Simple linear regression on log-transformed decay
    # ln(ROIC - ROIC_terminal) = ln(ROIC_0 - ROIC_terminal) - λt
    roic_terminal <- mean(tail(d$roic, 2))
    y <- log(pmax(d$roic - roic_terminal + 0.001, 0.001))
    t <- d$t
    
    fit <- lm(y ~ t)
    return(-coef(fit)[2])  # lambda = -slope
  }, error = function(e) {
    return(NA)
  })
}

# Compute validation metrics for a single company
validate_company <- function(cik, conn) {
  # Get fit parameters
  fit <- dbGetQuery(conn, sprintf(
    "SELECT * FROM decay_fits WHERE cik = '%s' LIMIT 1", cik
  ))
  
  if (nrow(fit) == 0 || !fit$converged) {
    return(NULL)
  }
  
  # Get training data
  train_data <- dbGetQuery(conn, sprintf(
    "SELECT fiscal_year, roic FROM fundamentals 
     WHERE cik = '%s' AND is_holdout = 0 AND roic IS NOT NULL
     ORDER BY fiscal_year", cik
  ))
  
  # Get holdout data
  holdout_data <- dbGetQuery(conn, sprintf(
    "SELECT fiscal_year, roic FROM fundamentals 
     WHERE cik = '%s' AND is_holdout = 1 AND roic IS NOT NULL
     ORDER BY fiscal_year", cik
  ))
  
  if (nrow(train_data) < 4) {
    return(NULL)
  }
  
  # Create time variable
  min_year <- min(train_data$fiscal_year)
  train_data$t <- train_data$fiscal_year - min_year
  
  # Bootstrap for CI on lambda
  tryCatch({
    boot_result <- boot(train_data, bootstrap_lambda, R = N_BOOTSTRAP)
    ci <- boot.ci(boot_result, type = "perc", conf = 0.95)
    
    if (!is.null(ci$percent)) {
      ci_low <- ci$percent[4]
      ci_high <- ci$percent[5]
    } else {
      ci_low <- NA
      ci_high <- NA
    }
    
    # P-value: test if lambda significantly different from 0
    # Using bootstrap standard error
    se <- sd(boot_result$t, na.rm = TRUE)
    if (!is.na(se) && se > 0) {
      z <- fit$lambda / se
      p_value <- 2 * (1 - pnorm(abs(z)))
    } else {
      p_value <- NA
    }
  }, error = function(e) {
    ci_low <<- NA
    ci_high <<- NA
    p_value <<- NA
  })
  
  # Holdout RMSE
  if (nrow(holdout_data) > 0) {
    holdout_data$t <- holdout_data$fiscal_year - min_year
    
    # Model predictions
    model_pred <- decay_model(
      holdout_data$t, 
      fit$roic_0, 
      fit$lambda, 
      fit$roic_terminal
    )
    
    # Naive baseline: last training ROIC
    naive_pred <- rep(tail(train_data$roic, 1), nrow(holdout_data))
    
    # RMSE
    holdout_rmse_model <- sqrt(mean((holdout_data$roic - model_pred)^2))
    holdout_rmse_naive <- sqrt(mean((holdout_data$roic - naive_pred)^2))
  } else {
    holdout_rmse_model <- NA
    holdout_rmse_naive <- NA
  }
  
  return(data.frame(
    cik = cik,
    ticker = fit$ticker,
    p_value = p_value,
    ci_low = ci_low,
    ci_high = ci_high,
    holdout_rmse_model = holdout_rmse_model,
    holdout_rmse_naive = holdout_rmse_naive,
    stringsAsFactors = FALSE
  ))
}

# Compute price-performance correlation
compute_price_correlation <- function(conn) {
  cat("Computing price-performance correlation...\n")
  
  # Get decay fits with lambda
  fits <- dbGetQuery(conn, 
    "SELECT cik, ticker, lambda FROM decay_fits WHERE converged = 1 AND ticker IS NOT NULL"
  )
  
  # Get price returns for holdout period
  # Using first and last price in holdout period
  price_returns <- dbGetQuery(conn, sprintf(
    "SELECT ticker,
            MIN(CASE WHEN date >= '%s' THEN close_price END) as start_price,
            MAX(CASE WHEN date <= '%s' THEN close_price END) as end_price
     FROM prices
     WHERE date >= '%s' AND date <= '%s'
     GROUP BY ticker
     HAVING start_price IS NOT NULL AND end_price IS NOT NULL",
    "2025-01-01", "2026-12-31", "2025-01-01", "2026-12-31"
  ))
  
  if (nrow(price_returns) == 0) {
    cat("No price data available for holdout period\n")
    return(list(correlation = NA, n = 0))
  }
  
  price_returns$return <- (price_returns$end_price - price_returns$start_price) / price_returns$start_price
  
  # Merge with fits
  merged <- merge(fits, price_returns, by = "ticker")
  
  if (nrow(merged) < 10) {
    cat(sprintf("Insufficient data for correlation: %d companies\n", nrow(merged)))
    return(list(correlation = NA, n = nrow(merged)))
  }
  
  # Compute correlation
  corr <- cor(merged$lambda, merged$return, use = "complete.obs")
  
  cat(sprintf("Price correlation computed: r = %.4f (n = %d)\n", corr, nrow(merged)))
  
  return(list(correlation = corr, n = nrow(merged)))
}

# Main validation function
run_validation <- function() {
  cat("Starting validation...\n")
  cat(sprintf("Database: %s\n", DB_PATH))
  
  # Connect to database
  conn <- dbConnect(RSQLite::SQLite(), DB_PATH)
  on.exit(dbDisconnect(conn))
  
  # Get list of companies with fits
  companies <- dbGetQuery(conn, 
    "SELECT DISTINCT cik FROM decay_fits WHERE converged = 1"
  )
  
  n_companies <- nrow(companies)
  cat(sprintf("Validating %d companies...\n", n_companies))
  
  # Validate each company
  results <- list()
  for (i in seq_len(n_companies)) {
    cik <- companies$cik[i]
    result <- validate_company(cik, conn)
    if (!is.null(result)) {
      results[[length(results) + 1]] <- result
    }
    
    if (i %% 500 == 0) {
      cat(sprintf("  Processed %d/%d companies...\n", i, n_companies))
    }
  }
  
  validation_df <- bind_rows(results)
  cat(sprintf("Validated %d companies successfully\n", nrow(validation_df)))
  
  # Compute price correlation
  price_corr <- compute_price_correlation(conn)
  validation_df$lambda_price_corr <- price_corr$correlation
  validation_df$price_return_holdout <- NA  # Would need individual returns
  
  # Clear and insert validation results
  dbExecute(conn, "DELETE FROM validation")
  
  dbWriteTable(conn, "validation", validation_df, append = TRUE, row.names = FALSE)
  
  # Print summary
  cat("\n=== Validation Summary ===\n")
  cat(sprintf("Companies validated: %d\n", nrow(validation_df)))
  
  sig_lambda <- sum(validation_df$p_value < 0.05, na.rm = TRUE)
  cat(sprintf("Significant λ (p < 0.05): %d (%.1f%%)\n", 
              sig_lambda, 100 * sig_lambda / nrow(validation_df)))
  
  # Model vs Naive comparison
  model_better <- sum(validation_df$holdout_rmse_model < validation_df$holdout_rmse_naive, na.rm = TRUE)
  has_holdout <- sum(!is.na(validation_df$holdout_rmse_model))
  cat(sprintf("Model beats naive (holdout): %d / %d (%.1f%%)\n",
              model_better, has_holdout, 100 * model_better / max(1, has_holdout)))
  
  cat(sprintf("Lambda-Price correlation: %.4f\n", price_corr$correlation))
  
  # Save summary stats
  summary_df <- data.frame(
    metric = c("companies_validated", "significant_lambda", "model_beats_naive", 
               "lambda_price_corr", "mean_holdout_rmse_model", "mean_holdout_rmse_naive"),
    value = c(nrow(validation_df), sig_lambda, model_better,
              price_corr$correlation, 
              mean(validation_df$holdout_rmse_model, na.rm = TRUE),
              mean(validation_df$holdout_rmse_naive, na.rm = TRUE))
  )
  
  summary_path <- file.path(WORKSPACE, "data", "validation_summary.csv")
  write.csv(summary_df, summary_path, row.names = FALSE)
  cat(sprintf("\nSummary saved to %s\n", summary_path))
  
  return(validation_df)
}

# Run validation
if (!interactive()) {
  results <- run_validation()
  cat("\nValidation complete!\n")
}
