# ADAA v0.30
# Independent R validation of the four newly reconstructed full-2023 Strategy-Zoo rules.
#
# IMPORTANT RESEARCH BOUNDARY
# - This script computes NO strategy performance.
# - It validates target weights only: DM, AAA, PAA, KDA.
# - It reads only the frozen adjusted-price inputs and Python target weights.
# - The Decision-Space selector remains performance-blind and is NOT re-tuned here.
# - Run with working directory set to the 05_ADAA project root.

options(stringsAsFactors = FALSE)
root <- normalizePath('.', winslash='/', mustWork=TRUE)
out_dir <- file.path(root, '03_Data_and_Code', '04_Outputs')
base_file <- file.path(out_dir, 'G5_FROZEN_ADJUSTED_DAILY_LONG_R_v0_15.csv')
exact_file <- file.path(root, '03_Data_and_Code', '01_Data', 'raw_freeze_strategy_zoo_v0_29',
                       'STRATEGY_ZOO_MISSING_ETF_ADJUSTED_DAILY_v0_29.csv')
val_dir <- file.path(root, '03_Data_and_Code', '03_Validation', 'User_Runtime_Evidence')
dir.create(val_dir, recursive=TRUE, showWarnings=FALSE)

if (!file.exists(base_file)) stop('Missing frozen base daily prices: ', base_file)
if (!file.exists(exact_file)) stop('Missing exact Strategy-Zoo daily-price freeze: ', exact_file)
if (!requireNamespace('quadprog', quietly=TRUE)) stop('Package quadprog is required for independent minimum-variance validation.')

# ---------------- Data assembly ----------------
base <- read.csv(base_file, check.names=FALSE)
exact <- read.csv(exact_file, check.names=FALSE)
for (z in list(base, exact)) {
  if (!all(c('date','symbol','adjusted') %in% names(z))) stop('Frozen daily file has unexpected schema.')
}
base$date <- as.Date(base$date); exact$date <- as.Date(exact$date)
raw <- rbind(base[,c('date','symbol','adjusted')], exact[,c('date','symbol','adjusted')])
raw <- raw[order(raw$date, raw$symbol),]
# New exact symbols do not overlap the original v0.15 panel; if duplicates exist, require exact equality.
dupkey <- duplicated(raw[,c('date','symbol')]) | duplicated(raw[,c('date','symbol')], fromLast=TRUE)
if (any(dupkey)) {
  spl <- split(raw[dupkey,], interaction(raw$date[dupkey], raw$symbol[dupkey], drop=TRUE))
  bad <- vapply(spl, function(x) diff(range(x$adjusted, na.rm=TRUE)) > 1e-12, logical(1))
  if (any(bad)) stop('Conflicting duplicate frozen adjusted-price observations.')
  raw <- raw[!duplicated(raw[,c('date','symbol')]),]
}

all_dates <- sort(unique(raw$date))
all_syms <- sort(unique(raw$symbol))
P <- matrix(NA_real_, nrow=length(all_dates), ncol=length(all_syms),
            dimnames=list(as.character(all_dates), all_syms))
ii <- match(raw$date, all_dates); jj <- match(raw$symbol, all_syms)
P[cbind(ii,jj)] <- raw$adjusted
D <- all_dates

month_end_idx <- function(dates) {
  ym <- format(dates, '%Y-%m')
  as.integer(tapply(seq_along(dates), ym, max))
}

minvar_longonly <- function(S) {
  S <- as.matrix(S)
  S <- (S + t(S))/2
  n <- ncol(S)
  if (n == 1L) return(1)
  A <- cbind(rep(1,n), diag(n))
  b <- c(1, rep(0,n))
  # solve.QP requires positive definite Dmat. The 60-day and KDA covariance matrices
  # in the frozen sample are expected to be full rank. Do not add a discretionary ridge.
  ans <- quadprog::solve.QP(Dmat=S, dvec=rep(0,n), Amat=A, bvec=b, meq=1)$solution
  ans[abs(ans) < 1e-12] <- 0
  ans <- ans / sum(ans)
  ans
}

subset_complete <- function(symbols) {
  if (!all(symbols %in% colnames(P))) stop('Missing required symbol(s): ', paste(setdiff(symbols,colnames(P)), collapse=', '))
  X <- P[,symbols,drop=FALSE]
  keep <- complete.cases(X)
  list(date=D[keep], px=X[keep,,drop=FALSE])
}

slice_common <- function(w) {
  w <- w[rownames(w) >= '2008-07' & rownames(w) <= '2026-06',,drop=FALSE]
  if (nrow(w) != 216L) stop('Unexpected target-weight validation length: ', nrow(w))
  w
}

# ---------------- DM ----------------
validate_dm <- function() {
  assets <- c('SPY','VEU','BIL','AGG')
  z <- subset_complete(assets); X <- z$px; dates <- z$date
  ep <- month_end_idx(dates)
  out <- matrix(NA_real_, nrow=length(ep), ncol=length(assets), dimnames=list(format(dates[ep],'%Y-%m'),assets))
  for (k in seq_along(ep)) {
    i <- ep[k]
    if (i <= 240) next
    score <- X[i,c('SPY','VEU','BIL')] / X[i-240,c('SPY','VEU','BIL')] - 1
    win <- names(sort(score, decreasing=TRUE, method='radix'))[1]
    w <- setNames(rep(0,4),assets)
    if (win == 'BIL') w['AGG'] <- 1 else w[win] <- 1
    out[k,] <- w
  }
  slice_common(out)
}

# ---------------- AAA ----------------
validate_aaa <- function() {
  assets <- c('SPY','VGK','EWJ','VWO','VNQ','RWX','IEF','TLT','DBC','GLD')
  z <- subset_complete(assets); X <- z$px; dates <- z$date
  LR <- X * NA_real_
  LR[2:nrow(X),] <- log(X[2:nrow(X),,drop=FALSE] / X[1:(nrow(X)-1),,drop=FALSE])
  ep <- month_end_idx(dates)
  out <- matrix(NA_real_, nrow=length(ep), ncol=length(assets), dimnames=list(format(dates[ep],'%Y-%m'),assets))
  for (k in seq_along(ep)) {
    i <- ep[k]
    if (i <= 120 || i < 60) next
    mom <- X[i,] / X[i-120,]
    ord <- names(sort(mom, decreasing=TRUE, method='radix'))
    chosen <- ord[1:5]
    hist <- LR[(i-59):i, chosen, drop=FALSE]
    full <- chosen[colSums(is.finite(hist)) == 60]
    w <- setNames(rep(0,length(assets)),assets)
    if (length(full) == 1L) {
      w[full] <- 1
    } else if (length(full) > 1L) {
      S <- stats::cov(hist[,full,drop=FALSE])
      w[full] <- minvar_longonly(S)
    } else next
    out[k,] <- w
  }
  slice_common(out)
}

# ---------------- PAA ----------------
validate_paa <- function() {
  risk <- c('SPY','QQQ','IWM','VGK','EWJ','EEM','IYR','GSG','GLD','HYG','LQD','TLT')
  safe <- 'IEF'; assets <- c(risk,safe)
  z <- subset_complete(assets); X <- z$px; dates <- z$date
  ep <- month_end_idx(dates)
  out <- matrix(NA_real_, nrow=length(ep), ncol=length(assets), dimnames=list(format(dates[ep],'%Y-%m'),assets))
  denom <- 12 - 2*12/4  # a=2 => 6
  for (k in seq_along(ep)) {
    i <- ep[k]
    if (i < 240) next
    sma <- colMeans(X[(i-239):i,risk,drop=FALSE])
    score <- X[i,risk] / sma - 1
    chosen <- names(sort(score, decreasing=TRUE, method='radix'))[1:6]
    npos <- sum(score > 0)
    bf <- min(1,max(0,(12-npos)/denom))
    w <- setNames(rep(0,length(assets)),assets)
    w[safe] <- bf
    if (bf < 1) w[chosen] <- (1-bf)/6
    out[k,] <- w
  }
  slice_common(out)
}

# ---------------- KDA ----------------
cumret <- function(x) apply(1+x,2,prod)-1
validate_kda <- function() {
  invest <- c('SPY','VGK','EWJ','EEM','VNQ','RWX','TLT','DBC','GLD','IEF')
  canary <- c('VWO','BND'); assets <- c(invest,canary)
  z <- subset_complete(assets); X <- z$px; dates <- z$date
  R <- X * NA_real_
  R[2:nrow(X),] <- X[2:nrow(X),,drop=FALSE] / X[1:(nrow(X)-1),,drop=FALSE] - 1
  ep <- month_end_idx(dates)
  outcols <- c(invest,'CASH')
  out <- matrix(NA_real_, nrow=length(ep), ncol=length(outcols), dimnames=list(format(dates[ep],'%Y-%m'),outcols))
  for (k in seq_along(ep)) {
    if (k <= 12) next
    start <- ep[k-12] + 1
    finish <- ep[k]
    rd <- R[start:finish, assets, drop=FALSE]
    if (any(!is.finite(rd))) next
    ym <- format(dates[start:finish],'%Y-%m')
    u <- unique(ym)
    if (length(u) != 12L) stop('KDA did not contain 12 monthly blocks at ', rownames(out)[k])
    lastmonths <- function(n) rd[ym %in% tail(u,n),,drop=FALSE]
    one <- lastmonths(1); three <- lastmonths(3); six <- lastmonths(6); twelve <- rd
    moms <- cumret(one)*12 + cumret(three)*4 + cumret(six)*2 + cumret(twelve)
    am <- moms[invest]; cp <- moms[canary]
    sel <- names(am)[rank(am, ties.method='average') >= 6 & am > 0]
    rw <- setNames(rep(0,length(invest)),invest)
    if (length(sel) == 1L) {
      rw[sel] <- 1
    } else if (length(sel) > 1L) {
      C <- (stats::cor(one[,sel,drop=FALSE])*12 + stats::cor(three[,sel,drop=FALSE])*4 +
            stats::cor(six[,sel,drop=FALSE])*2 + stats::cor(twelve[,sel,drop=FALSE]))/19
      v <- apply(one[,sel,drop=FALSE],2,stats::sd)
      S <- outer(v,v)*C
      rw[sel] <- minvar_longonly(S)
    }
    pa <- mean(cp > 0)
    rw <- rw * pa
    w <- setNames(rep(0,length(outcols)),outcols)
    w[invest] <- rw
    protection <- 1-pa
    if (am['IEF'] > 0) w['IEF'] <- w['IEF'] + protection else w['CASH'] <- w['CASH'] + protection
    w['CASH'] <- w['CASH'] + 1-sum(w)
    w[abs(w)<1e-12] <- 0
    out[k,] <- w
  }
  slice_common(out)
}

# ---------------- Comparison with frozen Python candidates ----------------
validators <- list(DM=validate_dm, AAA=validate_aaa, PAA=validate_paa, KDA=validate_kda)
pyfiles <- c(
  DM='G4_ZOO_DM_TARGET_WEIGHTS_DB2022_FROZEN_v0_30.csv',
  AAA='G4_ZOO_AAA_TARGET_WEIGHTS_DB2022_FROZEN_v0_30.csv',
  PAA='G4_ZOO_PAA_TARGET_WEIGHTS_DB2022_FROZEN_v0_30.csv',
  KDA='G4_ZOO_KDA_TARGET_WEIGHTS_DB2022_FROZEN_v0_30.csv'
)
summary_rows <- list(); r_exports <- list()
for (nm in names(validators)) {
  wr <- validators[[nm]]()
  pf <- file.path(out_dir, pyfiles[[nm]])
  if (!file.exists(pf)) stop('Missing Python target-weight candidate: ', pf)
  py <- read.csv(pf, check.names=FALSE)
  rownames(py) <- as.character(py$signal_month); py$signal_month <- NULL
  cols <- union(colnames(wr), colnames(py))
  WR <- matrix(0,nrow=nrow(wr),ncol=length(cols),dimnames=list(rownames(wr),cols)); WR[,colnames(wr)] <- wr
  PY <- matrix(0,nrow=nrow(py),ncol=length(cols),dimnames=list(rownames(py),cols)); PY[,colnames(py)] <- as.matrix(py)
  common <- intersect(rownames(WR),rownames(PY))
  if (length(common)!=216L) stop(nm, ': unexpected common validation months: ',length(common))
  diff <- abs(WR[common,,drop=FALSE]-PY[common,,drop=FALSE])
  md <- max(diff,na.rm=TRUE)
  l1 <- max(rowSums(diff),na.rm=TRUE)
  # QP implementations can differ at machine epsilon and at zero-bound active-set tolerances.
  tol <- if (nm %in% c('AAA','KDA')) 5e-7 else 1e-10
  if (!is.finite(md) || md > tol) stop(sprintf('%s R/Python mismatch: max cell %.12g > tolerance %.3g',nm,md,tol))
  summary_rows[[nm]] <- data.frame(strategy=nm,n_months=length(common),max_abs_cell_diff=md,
                                    max_monthly_L1_diff=l1,tolerance=tol,verdict='PASS')
  r_exports[[nm]] <- data.frame(strategy=nm,signal_month=common,WR[common,,drop=FALSE],check.names=FALSE)
}
summary <- do.call(rbind,summary_rows)
write.csv(summary,file.path(out_dir,'G4_ZOO_FULL_2023_R_PYTHON_TARGET_WEIGHT_VALIDATION_SUMMARY_v0_30.csv'),row.names=FALSE)
# Keep a single detailed R export for auditability; strategy-specific columns are union-aligned by rbind(fill) below.
allcols <- unique(unlist(lapply(r_exports,names)))
allcols <- c('strategy','signal_month',setdiff(allcols,c('strategy','signal_month')))
details <- do.call(rbind,lapply(r_exports,function(d){
  miss <- setdiff(allcols,names(d)); for (m in miss) d[[m]] <- NA_real_; d[,allcols,drop=FALSE]
}))
write.csv(details,file.path(out_dir,'G4_ZOO_FULL_2023_R_TARGET_WEIGHTS_DETAIL_v0_30.csv'),row.names=FALSE)

runtime <- data.frame(
  version='v0.30',
  full_2023_strategy_zoo_target_weight_validation='PASS',
  strategies='DM|AAA|PAA|KDA',
  max_abs_cell_diff=max(summary$max_abs_cell_diff),
  performance_computed=FALSE,
  performance_used_for_selection=FALSE,
  selector_changed=FALSE
)
write.csv(runtime,file.path(val_dir,'FULL_2023_STRATEGY_ZOO_TARGET_WEIGHT_RUNTIME_v0_30.csv'),row.names=FALSE)

cat('PASS: v0.30 independent R target-weight validation for DM / AAA / PAA / KDA.\n')
for (i in seq_len(nrow(summary))) cat(sprintf('%s max absolute cell difference: %.3e\n',summary$strategy[i],summary$max_abs_cell_diff[i]))
cat('No strategy performance was calculated or used for selection.\n')
cat('The frozen v0.29 Decision-Space selector definition was not changed.\n')
