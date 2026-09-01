#!/usr/bin/env julia
"""
Moaty Decay Fitting Engine

Fits exponential decay model to ROIC time series:
ROIC(t) = ROIC_terminal + (ROIC_0 - ROIC_terminal) × e^(-λt)

Uses LsqFit.jl for nonlinear least squares fitting.
"""

using CSV
using DataFrames
using LsqFit
using Statistics
using Dates

# Model: ROIC(t) = p[3] + (p[1] - p[3]) * exp(-p[2] * t)
# p[1] = ROIC_0 (initial ROIC)
# p[2] = λ (decay rate)
# p[3] = ROIC_terminal (long-run equilibrium ROIC)
decay_model(t, p) = p[3] .+ (p[1] .- p[3]) .* exp.(-p[2] .* t)

"""
Fit decay model to a single company's ROIC time series.
Returns Dict with fit results or nothing if fitting fails.
"""
function fit_company(df::DataFrame; min_points::Int=5)
    # Need at least min_points data points
    if nrow(df) < min_points
        return nothing
    end
    
    # Sort by fiscal year
    df = sort(df, :fiscal_year)
    
    # Create time variable (years from start)
    years = df.fiscal_year .- minimum(df.fiscal_year)
    roic = df.roic
    
    # Filter out NaN/missing values
    valid_idx = .!isnan.(roic) .& .!ismissing.(roic)
    years = Float64.(years[valid_idx])
    roic = Float64.(roic[valid_idx])
    
    if length(roic) < min_points
        return nothing
    end
    
    # Initial parameter guesses
    roic_0_guess = roic[1]
    roic_terminal_guess = mean(roic[end-min(2, length(roic)-1):end])
    lambda_guess = 0.1  # Moderate decay
    
    # Bounds: [ROIC_0, λ, ROIC_terminal]
    # λ should be positive but not too large
    # ROIC values should be in reasonable range
    lower = [-1.0, 0.001, -1.0]
    upper = [1.0, 2.0, 1.0]
    
    p0 = [roic_0_guess, lambda_guess, roic_terminal_guess]
    
    # Clamp initial guess to bounds
    p0 = max.(p0, lower)
    p0 = min.(p0, upper)
    
    try
        fit = curve_fit(decay_model, years, roic, p0, lower=lower, upper=upper)
        
        # Extract parameters
        params = coef(fit)
        roic_0 = params[1]
        lambda = params[2]
        roic_terminal = params[3]
        
        # Calculate R²
        y_pred = decay_model(years, params)
        ss_res = sum((roic .- y_pred).^2)
        ss_tot = sum((roic .- mean(roic)).^2)
        r_squared = 1.0 - ss_res / (ss_tot + 1e-10)
        
        # Check convergence
        converged = fit.converged
        
        return Dict(
            "lambda" => lambda,
            "roic_0" => roic_0,
            "roic_terminal" => roic_terminal,
            "r_squared" => r_squared,
            "converged" => converged,
            "n_periods" => length(roic)
        )
        
    catch e
        @warn "Fitting failed for company" exception=e
        return nothing
    end
end

"""
Fit decay model for all companies in the training data.
"""
function fit_all_companies(training_path::String, db_path::String)
    println("Loading training data from $training_path")
    
    # Read training data
    df = CSV.read(training_path, DataFrame)
    
    # Get unique companies
    companies = unique(df[:, [:cik, :ticker, :company_name]])
    n_companies = nrow(companies)
    
    println("Fitting decay model for $n_companies companies...")
    
    results = DataFrame(
        cik = String[],
        ticker = Union{String, Missing}[],
        company_name = Union{String, Missing}[],
        lambda = Float64[],
        roic_0 = Float64[],
        roic_terminal = Float64[],
        r_squared = Float64[],
        converged = Bool[],
        n_periods = Int[],
        fit_date = String[]
    )
    
    fit_date = Dates.format(now(), "yyyy-mm-dd")
    
    successful = 0
    failed = 0
    skipped = 0
    
    for i in 1:n_companies
        cik = companies.cik[i]
        ticker = get(companies, i, :ticker, missing)
        company_name = get(companies, i, :company_name, missing)
        
        # Get company data
        company_df = filter(row -> row.cik == cik, df)
        
        # Fit model
        result = fit_company(company_df)
        
        if result === nothing
            if nrow(company_df) < 5
                skipped += 1
            else
                failed += 1
            end
            continue
        end
        
        # Add to results
        push!(results, (
            cik = string(cik),
            ticker = ismissing(ticker) ? missing : string(ticker),
            company_name = ismissing(company_name) ? missing : string(company_name),
            lambda = result["lambda"],
            roic_0 = result["roic_0"],
            roic_terminal = result["roic_terminal"],
            r_squared = result["r_squared"],
            converged = result["converged"],
            n_periods = result["n_periods"],
            fit_date = fit_date
        ))
        
        successful += 1
        
        # Progress update
        if i % 500 == 0
            println("  Processed $i/$n_companies companies...")
        end
    end
    
    println("\nFitting complete:")
    println("  Successful: $successful")
    println("  Failed: $failed")
    println("  Skipped (insufficient data): $skipped")
    
    # Write results to CSV for Python to load into SQLite
    # (SQLite.jl has compatibility issues with existing schema)
    results_path = joinpath(dirname(dirname(training_path)), "data", "decay_fits.csv")
    CSV.write(results_path, results)
    println("\nResults written to $results_path")

    # Print leaderboard (top 10 most durable moats = lowest λ)
    println("\n=== Top 10 Most Durable Moats (lowest λ) ===")
    sorted_results = sort(filter(row -> row.converged, results), :lambda)
    for i in 1:min(10, nrow(sorted_results))
        row = sorted_results[i, :]
        ticker_str = ismissing(row.ticker) ? "N/A" : row.ticker
        println("  $i. $ticker_str (λ=$(round(row.lambda, digits=4)), R²=$(round(row.r_squared, digits=3)))")
    end
    
    println("\n=== Top 10 Fastest Decaying Moats (highest λ) ===")
    sorted_desc = sort(filter(row -> row.converged, results), :lambda, rev=true)
    for i in 1:min(10, nrow(sorted_desc))
        row = sorted_desc[i, :]
        ticker_str = ismissing(row.ticker) ? "N/A" : row.ticker
        println("  $i. $ticker_str (λ=$(round(row.lambda, digits=4)), R²=$(round(row.r_squared, digits=3)))")
    end
    
    return results
end

# Helper function for safe column access
function Base.get(df::DataFrame, row::Int, col::Symbol, default)
    if hasproperty(df, col) && !ismissing(df[row, col])
        return df[row, col]
    end
    return default
end

# Main execution
if abspath(PROGRAM_FILE) == @__FILE__
    # Default paths
    workspace = dirname(dirname(@__FILE__))
    training_path = joinpath(workspace, "data", "training_data.csv")
    db_path = joinpath(workspace, "moaty.db")
    
    # Allow command-line override
    if length(ARGS) >= 1
        training_path = ARGS[1]
    end
    if length(ARGS) >= 2
        db_path = ARGS[2]
    end
    
    results = fit_all_companies(training_path, db_path)
    
    println("\nDone! Results written to $db_path")
end
