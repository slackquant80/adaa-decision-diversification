# ADAA v0.15.1 — parent / counterfactual decision-panel export (namespace patch)
# PURPOSE:
#   1) verify frozen parent-source inputs;
#   2) export frozen adjusted-price inputs to plain CSV for independent audit;
#   3) construct source-faithful parent and pre-registered counterfactual target weights only.
# FORBIDDEN HERE: strategy returns, portfolio returns, CAGR, Sharpe, Sortino, MDD, Calmar,
#                 optimization, parameter search, or performance-based model selection.

options(stringsAsFactors = FALSE)

required_pkgs <- c("xts", "zoo", "digest")
missing_pkgs <- required_pkgs[!vapply(required_pkgs, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_pkgs)) stop("Install required packages first: ", paste(missing_pkgs, collapse=", "))

root <- normalizePath(getwd(), winslash="/", mustWork=TRUE)
if (!grepl("05_ADAA$", root)) stop("Set the R working directory to the 05_ADAA project root before running.")

raw0 <- file.path(root, "03_Data_and_Code", "01_Data", "raw_freeze_v0_8")
rawp <- file.path(root, "03_Data_and_Code", "01_Data", "raw_freeze_parent_v0_14")
out_dir <- file.path(root, "03_Data_and_Code", "04_Outputs")
dir.create(out_dir, recursive=TRUE, showWarnings=FALSE)

required_files <- c(
  file.path(raw0, "yahoo_primary_raw.rds"),
  file.path(raw0, "yahoo_proxy_raw.rds"),
  file.path(raw0, "fred_UNRATE_current_vintage_raw.rds"),
  file.path(rawp, "yahoo_parent_source_raw.rds"),
  file.path(rawp, "RAW_MANIFEST_SHA256_v0_14.csv")
)
if (!all(file.exists(required_files))) stop("Required frozen inputs are missing. Do not redownload silently; restore the v0.14 project first.")

cat("ADAA v0.15.1 parent / counterfactual decision export\n")
cat("No portfolio performance will be calculated.\n")

# -----------------------------------------------------------------------------
# 0. Frozen parent-manifest recheck
# -----------------------------------------------------------------------------
man <- read.csv(file.path(rawp, "RAW_MANIFEST_SHA256_v0_14.csv"), check.names=FALSE)
man$exists <- file.exists(file.path(rawp, man$file))
man$bytes_actual <- vapply(file.path(rawp, man$file), function(f) if (file.exists(f)) file.info(f)$size else NA_real_, numeric(1))
man$sha256_actual <- vapply(file.path(rawp, man$file), function(f) if (file.exists(f)) digest::digest(f, file=TRUE, algo="sha256") else NA_character_, character(1))
man$sha_match <- man$exists & man$sha256 == man$sha256_actual
man$bytes_match <- man$exists & as.numeric(man$bytes) == man$bytes_actual
write.csv(man, file.path(out_dir, "G5_PARENT_RAW_MANIFEST_RECHECK_R_v0_15.csv"), row.names=FALSE)
if (!all(man$sha_match & man$bytes_match)) stop("Parent raw manifest recheck failed. Stop before decision reconstruction.")

# -----------------------------------------------------------------------------
# 1. Load frozen objects and create a single immutable lookup
# -----------------------------------------------------------------------------
primary <- readRDS(file.path(raw0, "yahoo_primary_raw.rds"))
proxy   <- readRDS(file.path(raw0, "yahoo_proxy_raw.rds"))
parent  <- readRDS(file.path(rawp, "yahoo_parent_source_raw.rds"))
unrate_xts <- readRDS(file.path(raw0, "fred_UNRATE_current_vintage_raw.rds"))

get_adj <- function(x) {
  j <- grep("Adjusted", colnames(x), fixed=TRUE)
  if (length(j) != 1) stop("Adjusted column not unique for a frozen Yahoo object")
  ans <- x[, j]
  colnames(ans) <- sub("\\.Adjusted$", "", colnames(ans))
  ans
}

# Explicit precedence: primary ETF -> parent-source newly frozen -> legacy proxy.
# Duplicate symbols must be byte/logically identical in role before use; none are expected here.
all_names <- unique(c(names(primary), names(parent), names(proxy)))
lookup <- list()
source_class <- character(0)
for (sym in all_names) {
  if (sym %in% names(primary)) {
    lookup[[sym]] <- get_adj(primary[[sym]]); source_class[sym] <- "primary_v0_8"
  } else if (sym %in% names(parent)) {
    lookup[[sym]] <- get_adj(parent[[sym]]); source_class[sym] <- "parent_v0_14"
  } else {
    lookup[[sym]] <- get_adj(proxy[[sym]]); source_class[sym] <- "legacy_proxy_v0_8"
  }
}

need <- function(sym) {
  if (!sym %in% names(lookup)) stop("Frozen symbol unavailable: ", sym)
  lookup[[sym]]
}

# Export daily adjusted data in long form: easy to audit independently, no performance calculations.
daily_long <- do.call(rbind, lapply(names(lookup), function(sym) {
  x <- need(sym)
  data.frame(
    date=as.character(zoo::index(x)),
    symbol=sym,
    adjusted=as.numeric(x[,1]),
    source_class=unname(source_class[sym]),
    stringsAsFactors=FALSE
  )
}))
write.csv(daily_long, file.path(out_dir, "G5_FROZEN_ADJUSTED_DAILY_LONG_R_v0_15.csv"), row.names=FALSE)

# Monthly end prices per asset, then merge. Doing the endpoint asset-by-asset prevents union-calendar
# last-day alignment from manufacturing end-of-month NAs.
monthly_list <- lapply(names(lookup), function(sym) {
  x <- need(sym)
  m <- xts::to.monthly(x, indexAt="lastof", OHLC=FALSE)
  colnames(m) <- sym
  m
})
names(monthly_list) <- names(lookup)
prices_m <- do.call(merge, c(monthly_list, all=TRUE))
month_key <- format(zoo::index(prices_m), "%Y-%m")
monthly_wide <- data.frame(signal_month=month_key, zoo::coredata(prices_m), check.names=FALSE)
write.csv(monthly_wide, file.path(out_dir, "G5_FROZEN_MONTH_END_ADJUSTED_R_v0_15.csv"), row.names=FALSE)

# Restrict decision comparison to the pre-registered common ETF-era signal window.
signal_start <- "2008-05"
signal_end <- "2026-06"

# -----------------------------------------------------------------------------
# 2. Utilities: deterministic ties, information-state UNRATE, safe output
# -----------------------------------------------------------------------------
num_px <- function(sym) as.numeric(prices_m[, sym])

mom_ret <- function(sym, i, lags) {
  p <- num_px(sym)
  mean(p[i] / p[i-lags] - 1)
}

mom_sum <- function(sym, i, lags) {
  p <- num_px(sym)
  sum(p[i] / p[i-lags] - 1)
}

baa_fast <- function(sym, i) {
  p <- num_px(sym)
  12*(p[i]/p[i-1]-1) + 4*(p[i]/p[i-3]-1) + 2*(p[i]/p[i-6]-1) + (p[i]/p[i-12]-1)
}

sma_ratio13 <- function(sym, i) {
  p <- num_px(sym)
  p[i] / mean(p[(i-12):i])
}

pick_best <- function(scores, n=1, decreasing=TRUE) {
  scores <- scores[is.finite(scores)]
  if (!length(scores)) return(character(0))
  # deterministic symbol tie-break is a reconstruction convention only; tie binding is logged later.
  ord <- if (decreasing) order(-scores, names(scores)) else order(scores, names(scores))
  names(scores)[ord][seq_len(min(n, length(ord)))]
}

empty_w <- function(cols) {
  xts::xts(matrix(0, nrow=nrow(prices_m), ncol=length(cols), dimnames=list(NULL, cols)), order.by=zoo::index(prices_m))
}

valid_req <- function(i, syms, lags) {
  rows <- i - unique(c(0, lags))
  if (min(rows) < 1) return(FALSE)
  all(is.finite(as.matrix(prices_m[rows, syms, drop=FALSE])))
}

# Build monthly decision-time unemployment information state.
u_raw <- as.numeric(unrate_xts[,1])
u_month <- format(zoo::index(unrate_xts), "%Y-%m")
u_df <- data.frame(obs_month=u_month, value=u_raw, stringsAsFactors=FALSE)
# Calendar grid exactly over frozen UNRATE history.
ugrid <- seq(as.Date(paste0(min(u_month), "-01")), as.Date(paste0(max(u_month), "-01")), by="month")
uis <- data.frame(calendar_month=format(ugrid, "%Y-%m"), value=NA_real_, source_obs_month=NA_character_, stringsAsFactors=FALSE)
for (k in seq_len(nrow(uis))) {
  j <- match(uis$calendar_month[k], u_df$obs_month)
  if (!is.na(j) && is.finite(u_df$value[j])) {
    uis$value[k] <- u_df$value[j]
    uis$source_obs_month[k] <- u_df$obs_month[j]
  } else if (k > 1) {
    # Frozen G3 policy: latest actually released state persists; do not fabricate a new observation.
    uis$value[k] <- uis$value[k-1]
    uis$source_obs_month[k] <- uis$source_obs_month[k-1]
  }
}
write.csv(uis, file.path(out_dir, "G5_UNRATE_INFORMATION_STATE_R_v0_15.csv"), row.names=FALSE)

get_uis <- function(calendar_month) {
  j <- match(calendar_month, uis$calendar_month)
  if (is.na(j)) return(c(value=NA_real_, row=NA_real_))
  c(value=uis$value[j], row=j)
}

prev_month <- function(ym, k=1) {
  format(zoo::as.yearmon(ym) - k/12, "%Y-%m")
}

# signal month s uses the latest observation-month state from s-1; weights become effective next month.
laa_ue_sma12 <- function(signal_month) {
  om <- prev_month(signal_month, 1)
  x <- get_uis(om); j <- as.integer(x["row"])
  if (!is.finite(j) || j < 12) return(NA_real_)
  vals <- uis$value[(j-11):j]
  if (any(!is.finite(vals))) return(NA_real_)
  vals[12] / mean(vals)
}

laa_spy_sma10 <- function(i) {
  p <- num_px("SPY")
  if (i < 10 || any(!is.finite(p[(i-9):i]))) return(NA_real_)
  p[i] / mean(p[(i-9):i])
}

adaa_laa_ue_ratio13 <- function(signal_month) {
  om <- prev_month(signal_month, 1)
  x <- get_uis(om); j <- as.integer(x["row"])
  if (!is.finite(j) || j < 13) return(NA_real_)
  vals <- uis$value[(j-12):j]
  if (any(!is.finite(vals))) return(NA_real_)
  vals[13] / mean(vals)
}

adaa_laa_spy_ratio11 <- function(i) {
  p <- num_px("SPY")
  if (i < 11 || any(!is.finite(p[(i-10):i]))) return(NA_real_)
  p[i] / mean(p[(i-10):i])
}

write_weights <- function(w, tag, trace=NULL) {
  keep <- month_key >= signal_start & month_key <= signal_end & rowSums(abs(w)) > 0
  x <- data.frame(signal_month=month_key[keep], zoo::coredata(w[keep,]), check.names=FALSE)
  sums <- rowSums(x[,-1,drop=FALSE])
  if (any(!is.finite(sums)) || any(abs(sums - 1) > 1e-10)) stop(tag, ": invalid target-weight row sums")
  if (any(as.matrix(x[,-1,drop=FALSE]) < -1e-12)) stop(tag, ": negative target weight")
  write.csv(x, file.path(out_dir, paste0("G5_", tag, "_TARGET_WEIGHTS_R_v0_15.csv")), row.names=FALSE)
  if (!is.null(trace)) write.csv(trace, file.path(out_dir, paste0("G5_", tag, "_TRACE_R_v0_15.csv")), row.names=FALSE)
  invisible(x)
}

# -----------------------------------------------------------------------------
# 3. HAA parent and interpretable parent/universe counterfactuals
# -----------------------------------------------------------------------------
build_haa_rule <- function(risk, topn=4, replace_bad=TRUE, tag="HAA") {
  safe <- c("IEF","BIL")
  w <- empty_w(unique(c(risk,safe)))
  tr <- list()
  for (i in 13:nrow(prices_m)) {
    req <- unique(c(risk,safe,"TIP"))
    if (!valid_req(i, req, c(1,3,6,12))) next
    tip <- mom_ret("TIP", i, c(1,3,6,12))
    safe_sc <- setNames(vapply(safe, mom_ret, numeric(1), i=i, lags=c(1,3,6,12)), safe)
    best_safe <- pick_best(safe_sc, 1, TRUE)
    risk_sc <- setNames(vapply(risk, mom_ret, numeric(1), i=i, lags=c(1,3,6,12)), risk)
    regime <- ifelse(tip > 0, 1L, 0L)
    if (regime == 0) {
      w[i,best_safe] <- 1
    } else {
      sel <- pick_best(risk_sc, topn, TRUE)
      unit <- 1/topn
      for (a in sel) {
        if (replace_bad && risk_sc[a] <= 0) w[i,best_safe] <- w[i,best_safe] + unit else w[i,a] <- w[i,a] + unit
      }
    }
    tr[[length(tr)+1]] <- data.frame(signal_month=month_key[i], tip_score=tip, regime=regime,
                                      best_safe=best_safe, selected=paste(pick_best(risk_sc, topn, TRUE), collapse="|"), stringsAsFactors=FALSE)
  }
  list(w=w, trace=do.call(rbind,tr))
}

haa_parent_risk <- c("SPY","IWM","VEA","VWO","VNQ","DBC","IEF","TLT")
haa_adaa_risk <- c("SPY","QQQ","IWM","EFA","EEM","VNQ","DBC","IEF","TLT","EWY","GLD")
haa_pp <- build_haa_rule(haa_parent_risk, topn=4, replace_bad=TRUE)
write_weights(haa_pp$w, "HAA_PARENT_PP", haa_pp$trace[haa_pp$trace$signal_month >= signal_start & haa_pp$trace$signal_month <= signal_end,])
haa_pa <- build_haa_rule(haa_adaa_risk, topn=4, replace_bad=TRUE)
write_weights(haa_pa$w, "HAA_PARENT_RULE_ADAA_UNIVERSE", haa_pa$trace[haa_pa$trace$signal_month >= signal_start & haa_pa$trace$signal_month <= signal_end,])
# ADAA rule on parent assets: same canary, Top6, no individual bad-asset replacement.
haa_ap <- build_haa_rule(haa_parent_risk, topn=6, replace_bad=FALSE)
write_weights(haa_ap$w, "HAA_ADAA_RULE_PARENT_UNIVERSE", haa_ap$trace[haa_ap$trace$signal_month >= signal_start & haa_ap$trace$signal_month <= signal_end,])

# -----------------------------------------------------------------------------
# 4. BAA Aggressive parent, proxy-expression control, and historical Balanced parent/proxy
# -----------------------------------------------------------------------------
build_baa <- function(offensive, top_off, canary, defensive, tag="BAA") {
  w <- empty_w(unique(c(offensive, defensive)))
  tr <- list()
  for (i in 13:nrow(prices_m)) {
    req <- unique(c(offensive, canary, defensive))
    if (!valid_req(i, req, c(1,3,6,12))) next
    can_sc <- setNames(vapply(canary, baa_fast, numeric(1), i=i), canary)
    regime <- ifelse(all(can_sc >= 0), 1L, 0L)
    off_sc <- setNames(vapply(offensive, sma_ratio13, numeric(1), i=i), offensive)
    def_sc <- setNames(vapply(defensive, sma_ratio13, numeric(1), i=i), defensive)
    if (regime == 1) {
      sel <- pick_best(off_sc, top_off, TRUE)
      for (a in sel) w[i,a] <- w[i,a] + 1/top_off
    } else {
      sel <- pick_best(def_sc, 3, TRUE)
      bil_sc <- unname(def_sc["BIL"])
      for (a in sel) {
        if (a != "BIL" && def_sc[a] <= bil_sc) w[i,"BIL"] <- w[i,"BIL"] + 1/3 else w[i,a] <- w[i,a] + 1/3
      }
    }
    tr[[length(tr)+1]] <- data.frame(signal_month=month_key[i], regime=regime,
                                      min_canary=min(can_sc), selected=paste(if(regime==1) pick_best(off_sc,top_off,TRUE) else pick_best(def_sc,3,TRUE), collapse="|"), stringsAsFactors=FALSE)
  }
  list(w=w, trace=do.call(rbind,tr))
}

baa_can_parent <- c("SPY","VWO","VEA","BND")
baa_def_parent <- c("TIP","DBC","BIL","IEF","TLT","LQD","BND")
baa_off_aggr_parent <- c("QQQ","VWO","VEA","BND")
baa_ag_pp <- build_baa(baa_off_aggr_parent,1,baa_can_parent,baa_def_parent)
write_weights(baa_ag_pp$w,"BAA_AGGRESSIVE_PARENT_PP",baa_ag_pp$trace[baa_ag_pp$trace$signal_month>=signal_start & baa_ag_pp$trace$signal_month<=signal_end,])

baa_can_proxy <- c("SPY","EEM","EFA","AGG")
baa_def_proxy <- c("TIP","DBC","BIL","IEF","TLT","LQD","AGG")
baa_off_aggr_proxy <- c("QQQ","EEM","EFA","AGG")
baa_ag_pa <- build_baa(baa_off_aggr_proxy,1,baa_can_proxy,baa_def_proxy)
write_weights(baa_ag_pa$w,"BAA_AGGRESSIVE_PARENT_RULE_ADAA_PROXY",baa_ag_pa$trace[baa_ag_pa$trace$signal_month>=signal_start & baa_ag_pa$trace$signal_month<=signal_end,])

# Source BAA-G12/T6 Balanced. Source-author paper/excerpt freezes these 12 offensive assets.
baa_bal_parent <- c("SPY","QQQ","IWM","VGK","EWJ","VWO","VNQ","DBC","GLD","TLT","HYG","LQD")
baa_b_pp <- build_baa(baa_bal_parent,6,baa_can_parent,baa_def_parent)
write_weights(baa_b_pp$w,"BAA_BALANCED_PARENT_PP",baa_b_pp$trace[baa_b_pp$trace$signal_month>=signal_start & baa_b_pp$trace$signal_month<=signal_end,])
# Historical ADAA expression swaps parent VWO/VEA/BND roles to EEM/EFA/AGG while preserving G12/T6 architecture.
baa_bal_proxy <- c("SPY","QQQ","IWM","VGK","EWJ","EEM","VNQ","DBC","GLD","TLT","HYG","LQD")
baa_b_pa <- build_baa(baa_bal_proxy,6,baa_can_proxy,baa_def_proxy)
write_weights(baa_b_pa$w,"BAA_BALANCED_ADAA_PROXY_EXPRESSION",baa_b_pa$trace[baa_b_pa$trace$signal_month>=signal_start & baa_b_pa$trace$signal_month<=signal_end,])

# -----------------------------------------------------------------------------
# 5. ADM parent and source-author VSS expression control
# -----------------------------------------------------------------------------
build_adm_parent <- function(exus_sym) {
  risk <- c("VFINX", exus_sym); safe <- "VUSTX"
  w <- empty_w(c(risk,safe)); tr <- list()
  for (i in 7:nrow(prices_m)) {
    req <- c(risk,safe)
    if (!valid_req(i, req, c(1,3,6))) next
    sc <- setNames(vapply(risk, mom_sum, numeric(1), i=i, lags=c(1,3,6)), risk)
    best <- pick_best(sc,1,TRUE)
    if (max(sc) > 0) w[i,best] <- 1 else w[i,safe] <- 1
    tr[[length(tr)+1]] <- data.frame(signal_month=month_key[i], exus_vehicle=exus_sym,
                                      us_score=sc["VFINX"], exus_score=sc[exus_sym], selected=ifelse(max(sc)>0,best,safe), stringsAsFactors=FALSE)
  }
  list(w=w, trace=do.call(rbind,tr))
}
adm_pp <- build_adm_parent("VINEX")
write_weights(adm_pp$w,"ADM_PARENT_VINEX",adm_pp$trace[adm_pp$trace$signal_month>=signal_start & adm_pp$trace$signal_month<=signal_end,])
adm_vss <- build_adm_parent("VSS")
write_weights(adm_vss$w,"ADM_PARENT_VSS_CONTROL",adm_vss$trace[adm_vss$trace$signal_month>=signal_start & adm_vss$trace$signal_month<=signal_end,])

# Optional OSMAX control, frozen because the source author discussed active-fund vehicle sensitivity.
if ("OSMAX" %in% colnames(prices_m)) {
  adm_osmax <- build_adm_parent("OSMAX")
  write_weights(adm_osmax$w,"ADM_PARENT_OSMAX_CONTROL",adm_osmax$trace[adm_osmax$trace$signal_month>=signal_start & adm_osmax$trace$signal_month<=signal_end,])
}

# -----------------------------------------------------------------------------
# 6. FAA source-faithful parent and parent-rule / ADAA-universe counterfactual
# -----------------------------------------------------------------------------
# Source reconstruction convention: 84 most recent complete daily return observations ending at
# the signal month-end for V and C, consistent with the author's/coauthor's 4-month ≈84-day exposition.
# C is correlation with an equal-weight portfolio of the OTHER assets (target excluded).

daily_px_wide <- do.call(merge, c(lapply(names(lookup), need), all=TRUE))
colnames(daily_px_wide) <- names(lookup)
daily_ret_wide <- daily_px_wide / xts::lag.xts(daily_px_wide,1) - 1

build_faa_parent <- function(universe, cash="SHY", topn=3) {
  w <- empty_w(universe); tr <- list()
  for (i in 5:nrow(prices_m)) {
    if (!all(universe %in% colnames(prices_m))) next
    # 4-month total return from monthly endpoints
    if (!valid_req(i, universe, c(4))) next
    mom <- setNames(vapply(universe, function(a) {
      p <- num_px(a); p[i]/p[i-4]-1
    }, numeric(1)), universe)

    end_date <- zoo::index(prices_m)[i]
    dr <- daily_ret_wide[zoo::index(daily_ret_wide) <= end_date, universe, drop=FALSE]
    dr <- dr[stats::complete.cases(dr),,drop=FALSE]
    if (nrow(dr) < 84) next
    dr <- tail(dr,84)
    vol <- setNames(vapply(universe, function(a) stats::sd(as.numeric(dr[,a])), numeric(1)), universe)
    corv <- setNames(vapply(universe, function(a) {
      others <- setdiff(universe,a)
      if (!length(others)) return(0)
      peer <- rowMeans(as.matrix(dr[,others,drop=FALSE]))
      stats::cor(as.numeric(dr[,a]), peer)
    }, numeric(1)), universe)
    if (any(!is.finite(c(mom,vol,corv)))) next

    # lower composite rank is better: high return, low vol, low correlation
    rR <- rank(-mom, ties.method="average")
    rV <- rank(vol, ties.method="average")
    rC <- rank(corv, ties.method="average")
    L <- rR + 0.5*rV + 0.5*rC
    names(L) <- universe
    sel <- pick_best(L,topn,FALSE)
    for (a in sel) {
      if (mom[a] > 0) w[i,a] <- w[i,a] + 1/topn else w[i,cash] <- w[i,cash] + 1/topn
    }
    tr[[length(tr)+1]] <- data.frame(signal_month=month_key[i], selected=paste(sel,collapse="|"),
                                      negative_selected=sum(mom[sel] <= 0), stringsAsFactors=FALSE)
  }
  list(w=w,trace=do.call(rbind,tr))
}

faa_parent_u <- c("VTI","VEA","VWO","SHY","BND","GSG","VNQ")
faa_pp <- build_faa_parent(faa_parent_u,"SHY",3)
write_weights(faa_pp$w,"FAA_PARENT_PP",faa_pp$trace[faa_pp$trace$signal_month>=signal_start & faa_pp$trace$signal_month<=signal_end,])
# Parent rule on the current ADAA investable risky universe + SHY as the source-rule cash asset.
faa_adaa_u <- c("SPY","QQQ","VGK","EWY","EEM","VNQ","DBC","GLD","TLT","HYG","LQD","TIP","SHY")
faa_pa <- build_faa_parent(faa_adaa_u,"SHY",3)
write_weights(faa_pa$w,"FAA_PARENT_RULE_ADAA_UNIVERSE",faa_pa$trace[faa_pa$trace$signal_month>=signal_start & faa_pa$trace$signal_month<=signal_end,])

# -----------------------------------------------------------------------------
# 7. LAA parent, parent rule with ADAA equity expression, and ADAA timing on parent universe
# -----------------------------------------------------------------------------
build_laa <- function(equity_weights, spy_window=c("parent","adaa"), ue_window=c("parent","adaa")) {
  spy_window <- match.arg(spy_window); ue_window <- match.arg(ue_window)
  assets <- unique(c(names(equity_weights),"GLD","IEF","QQQ","SHY"))
  w <- empty_w(assets); tr <- list()
  for (i in seq_len(nrow(prices_m))) {
    sm <- month_key[i]
    if (sm < signal_start || sm > signal_end) next
    req <- c(names(equity_weights),"GLD","IEF","QQQ","SHY","SPY")
    if (!all(req %in% colnames(prices_m)) || any(!is.finite(prices_m[i,req]))) next
    sp <- if (spy_window=="parent") laa_spy_sma10(i) else adaa_laa_spy_ratio11(i)
    ue <- if (ue_window=="parent") laa_ue_sma12(sm) else adaa_laa_ue_ratio13(sm)
    if (!is.finite(sp) || !is.finite(ue)) next
    for (a in names(equity_weights)) w[i,a] <- equity_weights[a]
    w[i,"GLD"] <- 0.25; w[i,"IEF"] <- 0.25
    riskoff <- (sp <= 1 && ue >= 1)
    if (riskoff) w[i,"SHY"] <- 0.25 else w[i,"QQQ"] <- 0.25
    tr[[length(tr)+1]] <- data.frame(signal_month=sm, spy_ratio=sp, ue_ratio=ue, riskoff=as.integer(riskoff),
                                      ue_calendar_obs_month=prev_month(sm,1), stringsAsFactors=FALSE)
  }
  list(w=w,trace=do.call(rbind,tr))
}

laa_parent_eq <- c(IWD=0.25)
laa_adaa_eq <- c(SPY=0.175,EEM=0.05,EWY=0.025)
laa_pp <- build_laa(laa_parent_eq,"parent","parent")
write_weights(laa_pp$w,"LAA_PARENT_PP",laa_pp$trace)
laa_pa <- build_laa(laa_adaa_eq,"parent","parent")
write_weights(laa_pa$w,"LAA_PARENT_RULE_ADAA_EQUITY_EXPRESSION",laa_pa$trace)
laa_ap <- build_laa(laa_parent_eq,"adaa","adaa")
write_weights(laa_ap$w,"LAA_ADAA_TIMING_PARENT_UNIVERSE",laa_ap$trace)

# Static mechanism controls: persistence without GT timing.
build_static <- function(weights_named) {
  w <- empty_w(names(weights_named))
  for (i in seq_len(nrow(prices_m))) {
    sm <- month_key[i]
    if (sm < signal_start || sm > signal_end) next
    if (any(!is.finite(prices_m[i,names(weights_named)]))) next
    w[i,names(weights_named)] <- weights_named
  }
  w
}
write_weights(build_static(c(IWD=.25,GLD=.25,IEF=.25,QQQ=.25)),"STATIC_LAA_PARENT_RISKY_CORE")
write_weights(build_static(c(SPY=.175,EEM=.05,EWY=.025,GLD=.25,IEF=.25,QQQ=.25)),"STATIC_ADAA_LAA_RISKY_CORE")

# -----------------------------------------------------------------------------
# 8. RAA P3 quasi-static comparator
# -----------------------------------------------------------------------------
build_raa <- function() {
  risky <- c("QQQ","IWN","IEF","TLT","GLD")
  safe <- c("IEF","TLT")
  cana <- c("VWO","BND")
  w <- empty_w(unique(c(risky,safe))); tr <- list()
  for (i in 13:nrow(prices_m)) {
    sm <- month_key[i]
    if (sm < signal_start || sm > signal_end) next
    req <- unique(c(risky,safe,cana))
    if (!valid_req(i, req, c(1,3,6,12))) next
    can_sc <- setNames(vapply(cana, baa_fast, numeric(1), i=i), cana)
    market_bear <- any(can_sc < 0)
    om <- prev_month(sm,1)
    x <- get_uis(om); j <- as.integer(x["row"])
    if (!is.finite(j) || j < 13) next
    ue_now <- uis$value[j]; ue_12 <- uis$value[j-12]
    if (!is.finite(ue_now) || !is.finite(ue_12)) next
    ue_bear <- ue_now > ue_12
    riskoff <- market_bear && ue_bear
    if (riskoff) w[i,safe] <- 0.5 else w[i,risky] <- 0.2
    tr[[length(tr)+1]] <- data.frame(signal_month=sm, min_canary=min(can_sc), market_bear=as.integer(market_bear),
                                      ue_now=ue_now, ue_12m_ago=ue_12, ue_bear=as.integer(ue_bear), riskoff=as.integer(riskoff), stringsAsFactors=FALSE)
  }
  list(w=w,trace=do.call(rbind,tr))
}
raa <- build_raa()
write_weights(raa$w,"RAA_PARENT_COMPARATOR",raa$trace)

# -----------------------------------------------------------------------------
# 9. Output inventory / sanity contract
# -----------------------------------------------------------------------------
out_files <- list.files(out_dir, pattern="^G5_.*v0_15\\.csv$", full.names=TRUE)
out_inv <- data.frame(
  file=basename(out_files),
  bytes=file.info(out_files)$size,
  sha256=vapply(out_files,digest::digest,character(1),file=TRUE,algo="sha256"),
  performance_calculated=FALSE,
  stringsAsFactors=FALSE
)
write.csv(out_inv,file.path(out_dir,"G5_PARENT_DECISION_EXPORT_MANIFEST_v0_15.csv"),row.names=FALSE)

meta <- data.frame(
  export_version="v0.15",
  signal_start=signal_start,
  signal_end=signal_end,
  parent_manifest_pass=TRUE,
  daily_long_rows=nrow(daily_long),
  monthly_rows=nrow(monthly_wide),
  R_version=R.version.string,
  xts=as.character(utils::packageVersion("xts")),
  zoo=as.character(utils::packageVersion("zoo")),
  performance_calculated=FALSE,
  stringsAsFactors=FALSE
)
write.csv(meta,file.path(out_dir,"G5_PARENT_DECISION_EXPORT_METADATA_v0_15.csv"),row.names=FALSE)

cat("\nPASS: v0.15 parent and counterfactual target-weight exports written.\n")
cat("PASS: parent raw manifest SHA-256 rechecked before reconstruction.\n")
cat("PASS: frozen daily/month-end adjusted inputs exported for independent Python audit.\n")
cat("No strategy or portfolio performance was calculated.\n")
