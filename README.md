# MOATY - Multi-Language Data Analysis Environment

A multi-language data analysis project with Python, Julia, and R support for financial data analysis.

## Overview

This project provides environment validation tests for working with financial datasets including:
- Financial indicators data (CSV)
- SEC XBRL quarterly reports (TSV)
- Damodaran valuation models (XLS)

## Setup

### Python

```bash
pip install -r requirements.txt
```

### Julia

Install the required packages:

```julia
using Pkg
Pkg.add(["CSV", "DataFrames", "XLSX"])
```

### R

Install the required packages:

```r
install.packages(c("readr", "readxl", "dplyr", "knitr", "rmarkdown"))
```

## Data Structure

The project expects data files in the following structure (not included in repo):

```
data/
├── financial_indicators/
│   └── 2014_Financial_Data.csv
├── quarter_reports/
│   └── 2017q1/
│       ├── sub.txt
│       ├── num.txt
│       └── tag.txt
├── wacc.xls
└── roc.xls
```

## Running Tests

### Python
```bash
python test/test_environment.py
```

### Julia
```bash
julia test/test_environment.jl
```

### R
```bash
Rscript -e "rmarkdown::render('test/test_environment.Rmd')"
```

## License

See LICENSE file for details.
