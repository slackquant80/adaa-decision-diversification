# ADAA v0.29
# Independent base-R EAA target-weight validation + exact missing Strategy-Zoo ETF input freeze.
#
# IMPORTANT
# - This script computes no strategy performance.
# - It validates only EAA target weights and downloads exact adjusted-price inputs for
#   VEU, RWX and IYR so DM / AAA / PAA / KDA can be reconstructed later.
# - Run with working directory set to the 05_ADAA project root.

options(stringsAsFactors = FALSE)

root <- normalizePath('.', winslash='/', mustWork=TRUE)
out_dir <- file.path(root, '03_Data_and_Code', '04_Outputs')
data_dir <- file.path(root, '03_Data_and_Code', '01_Data', 'raw_freeze_strategy_zoo_v0_29')
val_dir <- file.path(root, '03_Data_and_Code', '03_Validation', 'User_Runtime_Evidence')
dir.create(data_dir, recursive=TRUE, showWarnings=FALSE)
dir.create(val_dir, recursive=TRUE, showWarnings=FALSE)

monthly_file <- file.path(out_dir, 'G5_FROZEN_MONTH_END_ADJUSTED_R_v0_15.csv')
py_file <- file.path(out_dir, 'G4_ZOO_EAA_TARGET_WEIGHTS_IKTRADING_V1_SOURCEFAITHFUL_v0_29.csv')
if (!file.exists(monthly_file)) stop('Missing frozen monthly price input: ', monthly_file)
if (!file.exists(py_file)) stop('Missing Python EAA reconstruction: ', py_file)

# ---------------- Independent base-R EAA reconstruction ----------------
px <- read.csv(monthly_file, check.names=FALSE)
assets <- c('VTI','VEA','VWO','QQQ','EWJ','HYG','IEF')
need <- c('signal_month', assets)
if (!all(need %in% names(px))) stop('Frozen monthly input missing required EAA columns.')
px <- px[complete.cases(px[, assets]), need]
rownames(px) <- px$signal_month
P <- as.matrix(px[, assets])
mode(P) <- 'numeric'

# Discrete monthly returns, matching PerformanceAnalytics::Return.calculate default behavior.
R <- P[-1,,drop=FALSE] / P[-nrow(P),,drop=FALSE] - 1
rownames(R) <- rownames(P)[-1]

cumret <- function(x) apply(1 + x, 2, prod) - 1
bestN <- 1 + ceiling(sqrt(ncol(P)))  # 4
jitter <- 1e-6
current_wS <- 2
wlist <- vector('list', nrow(R)-11)

for (i in seq_len(nrow(R)-11)) {
  rd <- R[i:(i+11),,drop=FALSE]
  pr <- (rd[12,] + cumret(rd[10:12,,drop=FALSE]) + cumret(rd[7:12,,drop=FALSE]) + cumret(rd)) / 22
  vols <- apply(rd, 2, sd) * sqrt(12)
  mkt <- rowMeans(rd, na.rm=TRUE)
  cors <- sapply(seq_len(ncol(rd)), function(j) cor(rd[,j], mkt))
  names(cors) <- colnames(rd)

  weighted_rets <- pr
  weighted_cors <- (1 - cors)^0.5
  weighted_vols <- (vols + jitter)^0
  current_wS <- current_wS + jitter  # preserve public IKTrading v1.0 loop-level behavior
  base <- weighted_rets * weighted_cors / weighted_vols
  z <- suppressWarnings(base^current_wS)
  z[pr < 0] <- 0

  crash <- sum(z == 0, na.rm=TRUE) / sum(!is.na(z))
  ordered <- sort(z, decreasing=TRUE, na.last=NA)
  threshold <- ordered[bestN]
  selected <- z >= threshold
  pre <- z * as.numeric(selected)
  denom <- sum(pre, na.rm=TRUE)
  if (!is.finite(denom) || denom == 0) {
    w <- rep(0, length(z)); names(w) <- names(z)
  } else {
    w <- pre / denom
  }
  w <- w * (1 - crash)
  w[is.na(w)] <- 0
  w['IEF'] <- w['IEF'] + 1 - sum(w)
  wlist[[i]] <- w
  names(wlist)[i] <- rownames(rd)[12]
}

WR <- do.call(rbind, wlist)
rownames(WR) <- names(wlist)
WR <- WR[rownames(WR) >= '2008-07' & rownames(WR) <= '2026-06',,drop=FALSE]

py <- read.csv(py_file, check.names=FALSE)
rownames(py) <- as.character(py$signal_month)
py <- as.matrix(py[, assets])
mode(py) <- 'numeric'

common <- intersect(rownames(WR), rownames(py))
if (length(common) != 216) stop('Unexpected EAA validation window length: ', length(common))
WR <- WR[common, assets, drop=FALSE]
py <- py[common, assets, drop=FALSE]
max_diff <- max(abs(WR-py), na.rm=TRUE)
if (!is.finite(max_diff) || max_diff > 1e-10) stop(sprintf('EAA R/Python mismatch: %.12g', max_diff))

val_csv <- file.path(out_dir, 'G4_ZOO_EAA_R_PYTHON_TARGET_WEIGHT_VALIDATION_v0_29.csv')
write.csv(data.frame(signal_month=rownames(WR), WR, check.names=FALSE), val_csv, row.names=FALSE)

# ---------------- Exact missing ETF adjusted-price freeze ----------------
if (!requireNamespace('quantmod', quietly=TRUE)) {
  stop('Package quantmod is required for the exact VEU/RWX/IYR Yahoo input freeze.')
}

symbols <- c('VEU','RWX','IYR')
parts <- list()
audit <- list()
for (sym in symbols) {
  x <- quantmod::getSymbols(sym, src='yahoo', from='2006-01-01', to='2026-07-01', auto.assign=FALSE)
  a <- quantmod::Ad(x)
  d <- data.frame(date=as.Date(zoo::index(a)), symbol=sym, adjusted=as.numeric(a[,1]))
  d <- d[is.finite(d$adjusted),]
  if (nrow(d) < 1000) stop('Too few valid adjusted observations for ', sym)
  if (max(d$date) < as.Date('2026-06-20')) stop('Latest ', sym, ' observation is too old: ', max(d$date))
  parts[[sym]] <- d
  audit[[sym]] <- data.frame(symbol=sym, n_rows=nrow(d), first_date=min(d$date), last_date=max(d$date),
                             n_missing_adjusted=sum(!is.finite(d$adjusted)))
}
raw <- do.call(rbind, parts)
raw <- raw[order(raw$symbol, raw$date),]
raw_file <- file.path(data_dir, 'STRATEGY_ZOO_MISSING_ETF_ADJUSTED_DAILY_v0_29.csv')
write.csv(raw, raw_file, row.names=FALSE)

aud <- do.call(rbind, audit)
aud$source <- 'Yahoo Finance via quantmod::getSymbols'
aud$download_from <- '2006-01-01'
aud$download_to_exclusive <- '2026-07-01'
aud$performance_used <- FALSE
if (requireNamespace('digest', quietly=TRUE)) {
  aud$sha256_file <- digest::digest(file=raw_file, algo='sha256')
} else {
  aud$sha256_file <- NA_character_
}
audit_file <- file.path(data_dir, 'STRATEGY_ZOO_MISSING_ETF_INPUT_AUDIT_v0_29.csv')
write.csv(aud, audit_file, row.names=FALSE)

runtime <- data.frame(
  version='v0.29',
  eaa_validation='PASS',
  eaa_r_python_max_abs_diff=max_diff,
  exact_input_freeze='PASS',
  symbols='VEU|RWX|IYR',
  performance_computed=FALSE,
  performance_used_for_selection=FALSE
)
write.csv(runtime, file.path(val_dir, 'STRATEGY_ZOO_EAA_AND_INPUT_FREEZE_RUNTIME_v0_29.csv'), row.names=FALSE)

cat('PASS: v0.29 independent base-R EAA target-weight validation.\n')
cat(sprintf('R/Python EAA maximum absolute target-weight difference: %.3e\n', max_diff))
cat('PASS: exact Strategy-Zoo adjusted-price inputs VEU, RWX and IYR frozen from Yahoo Finance.\n')
cat('No strategy performance was calculated or used for selection.\n')
