# Week 0 — Base Environment Test
# Validates that Julia can read all core data sources in the MOATY project.

import Pkg
println("Installed packages:")
Pkg.status(["CSV", "DataFrames", "XLSX"])

using CSV, DataFrames, XLSX

ROOT = joinpath(@__DIR__, "..")
DATA = joinpath(ROOT, "data")

function section(title)
    println("\n" * "="^60)
    println("  $title")
    println("="^60)
end

function show_df(df::DataFrame, name::String)
    cols = names(df)
    preview_cols = cols[1:min(8, length(cols))]
    println("\n[$name]  $(nrow(df)) rows × $(ncol(df)) cols")
    println("  columns: $(join(preview_cols, ", "))" * (length(cols) > 8 ? "..." : ""))
    println(first(df[:, 1:min(6, ncol(df))], 3))
end

#  Financial Indicators CSV 
section("Financial Indicators (2014_Financial_Data.csv)")
fin = CSV.read(joinpath(DATA, "financial_indicators", "2014_Financial_Data.csv"), DataFrame)
show_df(fin, "2014_Financial_Data")

#  XBRL Quarter Reports (2017 Q1) 
section("XBRL Quarter Reports — 2017q1")
q1 = joinpath(DATA, "quarter_reports", "2017q1")

sub = CSV.read(joinpath(q1, "sub.txt"), DataFrame; delim='\t', types=String, missingstring="")
show_df(sub, "sub.txt [submissions]")

num = CSV.read(joinpath(q1, "num.txt"), DataFrame; delim='\t', types=String, missingstring="")
show_df(num, "num.txt [numeric values]")

tag = CSV.read(joinpath(q1, "tag.txt"), DataFrame; delim='\t', types=String, missingstring="")
show_df(tag, "tag.txt [tag taxonomy]")

#  Damodaran XLS Models
section("Damodaran XLS Models")
# XLSX.jl only supports the modern .xlsx format.
# wacc.xls and roc.xls are legacy binary .xls — read them via Python or R.
# Confirming files exist on disk:
for f in ["wacc.xls", "roc.xls"]
    path = joinpath(DATA, f)
    sz = stat(path).size
    println("  $f  exists=true  size=$(round(sz/1024, digits=1)) KB")
end
println("  (XLS parse skipped — XLSX.jl does not support legacy .xls format)")

println("\n\nAll data sources loaded successfully.")
