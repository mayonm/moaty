# R package installation script for Moaty
# Run with: Rscript R/install.R

required_packages <- c("DBI", "RSQLite", "dplyr", "jsonlite", "boot")

install_if_missing <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cloud.r-project.org")
  }
}

for (pkg in required_packages) {
  install_if_missing(pkg)
}

cat("All R packages installed successfully.\n")
