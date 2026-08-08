# ADAA v0.26 — independent base-R validation of corrected drawdown/compounding metrics.
# Purpose: validate the risk-metric layer from already frozen monthly return paths.
# IMPORTANT: standard drawdown includes initial invested wealth W0=1 as a valid running peak.
# No strategy rule, return path, weight, cost, sample, optimizer, or selector is changed.

options(stringsAsFactors=FALSE)
root <- normalizePath(getwd(), winslash='/', mustWork=TRUE)
if (!grepl('05_ADAA$', root)) stop('Set working directory to the 05_ADAA project root.')
out_dir <- file.path(root,'03_Data_and_Code','04_Outputs')
path_file <- file.path(out_dir,'G6_ALL_MONTHLY_PATHS_FOR_INFERENCE_v0_19.csv')
py_file <- file.path(out_dir,'G6_DRAWDOWN_COMPOUNDING_DIAGNOSTICS_v0_26.csv')
stopifnot(file.exists(path_file), file.exists(py_file))

d <- read.csv(path_file, check.names=FALSE, stringsAsFactors=FALSE)
py <- read.csv(py_file, check.names=FALSE, stringsAsFactors=FALSE)

standard_dd <- function(x) {
  w <- cumprod(1 + as.numeric(x))
  peak <- cummax(c(1, w))[-1]
  dd <- w / peak - 1
  list(wealth=w, dd=dd)
}

max_uw <- function(dd, tol=1e-14) {
  u <- dd < -tol
  cur <- 0L; mx <- 0L
  for (v in u) {
    if (v) cur <- cur + 1L else cur <- 0L
    if (cur > mx) mx <- cur
  }
  mx
}

metrics <- function(x, months) {
  z <- standard_dd(x); w <- z$wealth; dd <- z$dd
  n <- length(x)
  j <- which.min(dd)
  mdd <- unname(dd[j])
  rec_req <- if (mdd < 0) 1/(1+mdd)-1 else 0
  underwater <- dd < -1e-14
  cagr <- unname(w[n]^(12/n)-1)
  c(
    months=n,
    CAGR_unchanged=cagr,
    standard_max_drawdown=mdd,
    recovery_return_required_from_MDD=rec_req,
    fraction_months_underwater=mean(underwater),
    max_underwater_spell_months=max_uw(dd),
    mean_drawdown_all_months=mean(-pmin(dd,0)),
    mean_drawdown_conditional_underwater=if (any(underwater)) mean(-dd[underwater]) else 0,
    ulcer_index=sqrt(mean(pmin(dd,0)^2)),
    drawdown_area_decimal_months=sum(-pmin(dd,0)),
    ending_growth_of_1_unchanged=unname(w[n])
  )
}

portfolio_map <- c(
  ADAA_historical='ADAA_historical',
  ADAA_equal20='ADAA_equal20',
  Sleeve_HAA='Sleeve_HAA',
  Benchmark_60_40_SPY_IEF='Benchmark_60_40_SPY_IEF',
  Benchmark_SPY='Benchmark_SPY'
)

rows <- list(); k <- 1L
for (nm in names(portfolio_map)) {
  g <- d[d$portfolio == portfolio_map[[nm]],,drop=FALSE]
  g <- g[order(g$holding_month),,drop=FALSE]
  if (nrow(g) != 218L) stop('Unexpected monthly row count for ', nm)
  for (basis in c('gross','net25')) {
    col <- if (basis=='gross') 'gross_return' else 'net_return_25bps'
    mm <- metrics(g[[col]], g$holding_month)
    one <- data.frame(portfolio=nm,basis=basis,stringsAsFactors=FALSE)
    for (j in seq_along(mm)) one[[names(mm)[j]]] <- unname(mm[j])
    rows[[k]] <- one; k <- k + 1L
  }
}
out <- do.call(rbind, rows)

# Compare every numeric field computed here with the independent Python diagnostic.
numcols <- c('months','CAGR_unchanged','standard_max_drawdown','recovery_return_required_from_MDD',
             'fraction_months_underwater','max_underwater_spell_months','mean_drawdown_all_months',
             'mean_drawdown_conditional_underwater','ulcer_index','drawdown_area_decimal_months',
             'ending_growth_of_1_unchanged')
comp <- merge(out, py[,c('portfolio','basis',numcols)], by=c('portfolio','basis'), suffixes=c('_R','_PY'))
if (nrow(comp) != nrow(out)) stop('Python comparison rows missing.')
maxdiff <- 0
for (cc in numcols) {
  dd <- max(abs(comp[[paste0(cc,'_R')]] - comp[[paste0(cc,'_PY')]]), na.rm=TRUE)
  if (is.finite(dd)) maxdiff <- max(maxdiff, dd)
}
if (!is.finite(maxdiff) || maxdiff > 1e-10) stop(sprintf('R/Python drawdown validation failed: max diff %.3e', maxdiff))

write.csv(out,file.path(out_dir,'G6_DRAWDOWN_R_VALIDATION_v0_26.csv'),row.names=FALSE)
meta <- data.frame(
  validation='PASS',
  rows=nrow(out),
  max_abs_numeric_diff_vs_python=maxdiff,
  definition='W0=1 included as valid running peak',
  return_path_changed=FALSE,
  strategy_changed=FALSE,
  weights_changed=FALSE,
  costs_changed=FALSE,
  stringsAsFactors=FALSE
)
write.csv(meta,file.path(out_dir,'G6_DRAWDOWN_R_VALIDATION_METADATA_v0_26.csv'),row.names=FALSE)

cat('PASS: v0.26 independent base-R drawdown/compounding validation export written.\n')
cat('Validated: standard MDD includes initial wealth W0=1 as a valid running peak.\n')
cat(sprintf('R/Python maximum absolute numeric difference: %.3e\n', maxdiff))
cat('No strategy rule, return path, weight, cost or sample was changed.\n')
