# ADAA v0.16 — performance-blind canonical FAA candidate export
# Candidate policy: current ADAA FAA parameters/universe + source-faithful peer-only
# correlation + deterministic exact-N stable tie handling.
# This script DOES NOT calculate strategy or portfolio performance.

suppressPackageStartupMessages({
  library(xts)
  library(zoo)
})

root <- normalizePath(getwd(), winslash="/", mustWork=TRUE)
raw_dir <- file.path(root,"03_Data_and_Code","01_Data","raw_freeze_v0_8")
out_dir <- file.path(root,"03_Data_and_Code","04_Outputs")
dir.create(out_dir,recursive=TRUE,showWarnings=FALSE)

primary <- readRDS(file.path(raw_dir,"yahoo_primary_raw.rds"))
get_adj <- function(x) {
  j <- grep("Adjusted",colnames(x),fixed=TRUE)
  if (length(j)!=1) stop("Adjusted column not unique")
  x[,j]
}
px <- lapply(primary,get_adj)
prices_daily <- do.call(merge,c(px,all=TRUE)); colnames(prices_daily) <- names(primary)
prices_m <- xts::to.monthly(prices_daily,indexAt="lastof",OHLC=FALSE)
month_key <- format(zoo::index(prices_m),"%Y-%m")

risk <- c("SPY","QQQ","VGK","EWY","EEM","VNQ","DBC","GLD","TLT","HYG","LQD","TIP")
safe <- c("SHY","BIL")
req_all <- c(risk,safe)
if (!all(req_all %in% colnames(prices_m))) stop("Required FAA symbols missing")

ratio_avg <- function(v,i,lags) mean(v[i]/v[i-lags])
sma_ratio <- function(v,i,k=13) v[i]/mean(v[(i-k+1):i])
r_rank <- function(x) rank(as.numeric(x),ties.method="average",na.last="keep")

# Stable exact-N selector: aggregate score ascending, asset ticker alphabetical only for exact ties.
exact_n_stable <- function(score,n) {
  z <- data.frame(asset=names(score),score=as.numeric(score),stringsAsFactors=FALSE)
  z <- z[is.finite(z$score),,drop=FALSE]
  z <- z[order(z$score,z$asset),,drop=FALSE]
  head(z$asset,n)
}

w <- xts::xts(matrix(0,nrow(prices_m),length(req_all),dimnames=list(NULL,req_all)),order.by=zoo::index(prices_m))
ret <- prices_m[,risk]/xts::lag.xts(prices_m[,risk],1)-1
trace <- list()

for (i in 13:nrow(prices_m)) {
  sm <- month_key[i]
  if (sm < "2008-05" || sm > "2026-06") next
  if (any(is.na(prices_m[i-c(0,3,6,12),req_all]))) next
  rwin <- ret[(i-5):i,risk]
  if (nrow(rwin)!=6 || any(is.na(rwin))) next

  mom <- sapply(risk,function(a) ratio_avg(as.numeric(prices_m[,a]),i,c(3,6,12)))
  vol <- sapply(risk,function(a) stats::sd(as.numeric(rwin[,a])))
  corv <- sapply(risk,function(a) {
    others <- setdiff(risk,a)
    peer <- rowMeans(as.matrix(rwin[,others,drop=FALSE]))
    stats::cor(as.numeric(rwin[,a]),peer)
  })
  if (any(!is.finite(c(mom,vol,corv)))) next

  M <- r_rank(-mom); names(M) <- risk
  V <- r_rank(vol); names(V) <- risk
  C <- r_rank(corv); names(C) <- risk
  agg <- M + 0.5*V + 0.5*C; names(agg) <- risk
  sel <- exact_n_stable(agg,6)
  if (length(sel)!=6) stop("Exact-N selector failed")

  for (a in sel) if (mom[a] >= 1) w[i,a] <- 1/6
  residual <- 1-sum(as.numeric(w[i,risk]))
  sh <- sma_ratio(as.numeric(prices_m[,"SHY"]),i,13)
  bi <- sma_ratio(as.numeric(prices_m[,"BIL"]),i,13)
  safe_sel <- ifelse(sh>bi,"SHY","BIL")
  w[i,safe_sel] <- residual

  trace[[length(trace)+1]] <- data.frame(
    signal_month=sm,
    selected=paste(sel,collapse="|"),
    n_selected=length(sel),
    negative_or_below_one_selected=sum(mom[sel] < 1),
    residual_safe_weight=residual,
    safe_asset=safe_sel,
    stringsAsFactors=FALSE
  )
}

keep <- month_key >= "2008-05" & month_key <= "2026-06" & rowSums(abs(w))>0
out <- data.frame(signal_month=month_key[keep],zoo::coredata(w[keep,]),check.names=FALSE)
if (nrow(out)!=218) stop(paste("Expected 218 FAA signal months, got",nrow(out)))
if (max(abs(rowSums(out[,-1])-1))>1e-10) stop("FAA weights do not sum to one")
write.csv(out,file.path(out_dir,"G3_FAA_CANONICAL_PEER_ONLY_EXACTN_TARGET_WEIGHTS_R_v0_16.csv"),row.names=FALSE)
write.csv(do.call(rbind,trace),file.path(out_dir,"G3_FAA_CANONICAL_PEER_ONLY_EXACTN_TRACE_R_v0_16.csv"),row.names=FALSE)
cat("PASS: v0.16 canonical FAA candidate target weights exported. Peer-only correlation and exact-N stable tie handling active. No portfolio performance was calculated.\n")
