# ADAA G2 v0.11 — frozen-input target-weight export only
# PURPOSE: independently reproduce dashboard-successor sleeve target weights in R.
# IMPORTANT: this script DOES NOT compute strategy or portfolio returns, CAGR, Sharpe, MDD, or headline performance.

suppressPackageStartupMessages({
  library(xts)
  library(zoo)
})

root <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
raw_dir <- file.path(root, "03_Data_and_Code", "01_Data", "raw_freeze_v0_8")
out_dir <- file.path(root, "03_Data_and_Code", "04_Outputs")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

primary <- readRDS(file.path(raw_dir, "yahoo_primary_raw.rds"))
unrate_xts <- readRDS(file.path(raw_dir, "fred_UNRATE_current_vintage_raw.rds"))

get_adj <- function(x) {
  j <- grep("Adjusted", colnames(x), fixed = TRUE)
  if (length(j) != 1) stop("Adjusted column not unique")
  x[, j]
}

px_list <- lapply(primary, get_adj)
prices_daily <- do.call(merge, c(px_list, all = TRUE))
colnames(prices_daily) <- names(primary)
prices_m <- to.monthly(prices_daily, indexAt = "lastof", OHLC = FALSE)
month_key <- format(index(prices_m), "%Y-%m")

signal_start <- "2008-05"
signal_end <- "2026-06"
keep_signal <- month_key >= signal_start & month_key <= signal_end

r_rank <- function(x) rank(as.numeric(x), ties.method = "average", na.last = "keep")
ratio_avg <- function(v, i, lags) mean(v[i] / v[i-lags])
sma_ratio <- function(v, i, k=13) v[i] / mean(v[(i-k+1):i])

empty_w <- function(cols) {
  out <- matrix(0, nrow(prices_m), length(cols), dimnames=list(NULL, cols))
  xts(out, order.by=index(prices_m))
}

# ---- HAA successor ----
haa_trace <- data.frame(signal_month=character(), tip_score=double(), regime=integer())
build_haa <- function() {
  trace_rows <- list()
  risk <- c("SPY","QQQ","IWM","EFA","EEM","VNQ","DBC","IEF","TLT","EWY","GLD")
  safe <- c("IEF","BIL")
  w <- empty_w(unique(c(risk,safe)))
  for (i in 13:nrow(prices_m)) {
    req <- unique(c(risk,safe,"TIP")); if (any(is.na(prices_m[i-c(0,1,3,6,12), req]))) next
    # IMPORTANT: coerce the current and lagged TIP observations to plain numeric
    # BEFORE division. Dividing two xts objects with different timestamps aligns
    # on the time index and can yield an empty intersection, which previously
    # collapsed sum(numeric(0)) to zero and forced every HAA month defensive.
    tip_now <- as.numeric(prices_m[i,"TIP"])
    tip_lag <- as.numeric(prices_m[i-c(1,3,6,12),"TIP"])
    tp <- sum(tip_now / tip_lag - 1)
    regime <- ifelse(tp > 0, 1, 0)
    trace_rows[[length(trace_rows)+1]] <- data.frame(signal_month=month_key[i], tip_score=tp, regime=regime)
    rs <- sapply(risk, function(a) ratio_avg(as.numeric(prices_m[,a]), i, c(1,3,6,12)))
    ss <- sapply(safe, function(a) ratio_avg(as.numeric(prices_m[,a]), i, c(1,3,6,12)))
    if (regime == 1) {
      rr <- r_rank(rs); sel <- risk[rr >= 6]
      w[i, sel] <- 1/6
    } else {
      rr <- r_rank(ss); sel <- safe[rr >= 2]
      w[i, sel] <- 1
    }
  }
  assign("haa_trace", do.call(rbind, trace_rows), envir=.GlobalEnv)
  w
}

# ---- BAA Aggressive successor ----
build_baa <- function() {
  risk <- c("QQQ","EEM","EFA","AGG")
  safe <- c("TIP","DBC","IEF","TLT","LQD","AGG","BIL")
  cana <- c("SPY","EEM","EFA","AGG")
  w <- empty_w(unique(c(risk,safe)))
  for (i in 13:nrow(prices_m)) {
    req <- unique(c(risk,safe,cana)); if (any(is.na(prices_m[i-c(0,1,3,6,12), req]))) next
    can <- sapply(cana, function(a) {
      p <- as.numeric(prices_m[,a]); 12*(p[i]/p[i-1]-1)+4*(p[i]/p[i-3]-1)+2*(p[i]/p[i-6]-1)+(p[i]/p[i-12]-1)
    })
    regime <- ifelse(all(can >= 0),1,0)
    rs <- sapply(risk, function(a) sma_ratio(as.numeric(prices_m[,a]),i,13))
    ss <- sapply(safe, function(a) sma_ratio(as.numeric(prices_m[,a]),i,13))
    if (regime == 1) {
      rr <- r_rank(rs); sel <- risk[rr == 4]; if (length(sel)) w[i,sel] <- 1
    } else {
      rr <- r_rank(ss); sel <- safe[rr >= 5]; if (length(sel)) w[i,sel] <- 1/3
      bil <- ss["BIL"]
      for (a in setdiff(safe,"BIL")) if (ss[a] <= bil) w[i,a] <- 0
      w[i,"BIL"] <- as.numeric(w[i,"BIL"]) + (1 - sum(w[i,]))
    }
  }
  w
}

# ---- ADM successor ----
build_adm <- function() {
  risk <- c("SPY","QQQ","VGK","EWY","EEM","VNQ","DBC","GLD","TLT","HYG","LQD","TIP")
  safe <- c("SHY","BIL")
  w <- empty_w(c(risk,safe))
  for (i in 13:nrow(prices_m)) {
    req <- c(risk,safe); if (any(is.na(prices_m[i-c(0,1,3,6,12), req]))) next
    sc <- sapply(risk, function(a) ratio_avg(as.numeric(prices_m[,a]),i,c(1,3,6)))
    rr <- r_rank(sc); sel <- risk[rr >= 7]
    for (a in sel) if (sc[a] >= 1) w[i,a] <- 1/6
    res <- 1 - sum(w[i,risk])
    sh <- sma_ratio(as.numeric(prices_m[,"SHY"]),i,13); bi <- sma_ratio(as.numeric(prices_m[,"BIL"]),i,13)
    w[i, ifelse(sh > bi,"SHY","BIL")] <- res
  }
  w
}

# ---- FAA successor: exact legacy correlation and rank-tie semantics ----
build_faa <- function() {
  risk <- c("SPY","QQQ","VGK","EWY","EEM","VNQ","DBC","GLD","TLT","HYG","LQD","TIP")
  safe <- c("SHY","BIL")
  w <- empty_w(c(risk,safe))
  # monthly returns, corresponding to dashboard rtn_FAA_m after first-row NA removal
  ret <- prices_m[,risk] / lag(prices_m[,risk],1) - 1
  for (i in 13:nrow(prices_m)) {
    if (i < 7) next
    req <- c(risk,safe); if (any(is.na(prices_m[i-c(0,3,6,12), req]))) next
    rwin <- ret[(i-5):i, risk]
    if (any(is.na(rwin))) next
    mom <- sapply(risk, function(a) ratio_avg(as.numeric(prices_m[,a]),i,c(3,6,12)))
    vol <- sapply(risk, function(a) sd(as.numeric(rwin[,a])))
    ew <- rowMeans(as.matrix(rwin))
    corv <- sapply(risk, function(a) cor(as.numeric(rwin[,a]), ew))
    M <- r_rank(-mom); V <- r_rank(vol); C <- r_rank(corv)
    agg <- M + 0.5*V + 0.5*C
    R <- r_rank(agg); sel <- risk[R <= 6]
    denom <- length(sel); if (denom == 0) next
    for (a in sel) if (mom[a] >= 1) w[i,a] <- 1/denom
    res <- 1 - sum(w[i,risk])
    sh <- sma_ratio(as.numeric(prices_m[,"SHY"]),i,13); bi <- sma_ratio(as.numeric(prices_m[,"BIL"]),i,13)
    w[i, ifelse(sh > bi,"SHY","BIL")] <- res
  }
  w
}

# ---- LAA successor: explicit proven chronology, observation t -> signal t+1 ----
build_laa <- function() {
  assets <- c("SPY","QQQ","EEM","EWY","IEF","GLD","SHY")
  w <- empty_w(assets)
  u <- as.numeric(unrate_xts[,1]); names(u) <- format(index(unrate_xts), "%Y-%m")
  for (i in 13:nrow(prices_m)) {
    sm <- month_key[i]
    obs_month <- format(as.Date(as.yearmon(sm) - 1/12, frac=0), "%Y-%m")
    # Need current plus previous 12 observation months; preserve NA if a structurally missing observation exists.
    obs_end <- match(obs_month, names(u)); if (is.na(obs_end) || obs_end < 13) next
    uh <- u[(obs_end-12):obs_end]; if (any(is.na(uh))) next
    if (any(is.na(prices_m[(i-10):i,"SPY"])) || any(is.na(prices_m[i,assets]))) next
    sp_score <- as.numeric(prices_m[i,"SPY"]) / mean(as.numeric(prices_m[(i-10):i,"SPY"]))
    un_score <- tail(uh,1) / mean(uh)
    w[i,c("SPY","EEM","EWY","IEF","GLD")] <- c(0.175,0.05,0.025,0.25,0.25)
    if (sp_score > 1 || un_score < 1) w[i,"QQQ"] <- 0.25 else w[i,"SHY"] <- 0.25
  }
  w
}

write_w <- function(w, tag) {
  sel <- keep_signal & rowSums(abs(w)) > 0
  x <- data.frame(signal_month=month_key[sel], coredata(w[sel,]), check.names=FALSE)
  write.csv(x, file.path(out_dir, paste0("G2_", tag, "_TARGET_WEIGHTS_R_v0_11_1.csv")), row.names=FALSE)
}

haa_w <- build_haa()
write_w(haa_w, "HAA")
haa_trace_sub <- haa_trace[haa_trace$signal_month >= signal_start & haa_trace$signal_month <= signal_end, ]
if (nrow(haa_trace_sub) == 0 || length(unique(haa_trace_sub$regime)) < 2) {
  stop("HAA canary sanity check failed: frozen signal window must contain both risk and defensive regimes.")
}
write.csv(haa_trace_sub, file.path(out_dir, "G2_HAA_CANARY_TRACE_R_v0_11_1.csv"), row.names=FALSE)
write_w(build_baa(), "BAA_AGGRESSIVE")
write_w(build_adm(), "ADM")
write_w(build_faa(), "FAA_LEGACY")
write_w(build_laa(), "LAA")

cat("PASS: v0.11.1 performance-blind R target-weight exports written. HAA canary scalar/index fix active. No portfolio performance was calculated.\n")
