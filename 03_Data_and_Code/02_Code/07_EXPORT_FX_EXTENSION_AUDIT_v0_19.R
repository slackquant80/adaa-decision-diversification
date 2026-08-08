# ADAA v0.19 — KRW/USD extension audit export
# PURPOSE: reproduce the legacy FX signal mechanics from the frozen KRW=X series,
#          expose warm-up/missing-data behavior, and export predeclared sensitivity paths.
# This script does NOT calculate ADAA portfolio performance and does NOT select an FX rule.

options(stringsAsFactors=FALSE)
required <- c('xts','zoo','digest')
missing <- required[!vapply(required, requireNamespace, logical(1), quietly=TRUE)]
if (length(missing)) stop('Install required packages first: ', paste(missing, collapse=', '))

root <- normalizePath(getwd(), winslash='/', mustWork=TRUE)
if (!grepl('05_ADAA$', root)) stop('Set working directory to the 05_ADAA project root.')
raw_dir <- file.path(root,'03_Data_and_Code','01_Data','raw_freeze_v0_8')
out_dir <- file.path(root,'03_Data_and_Code','04_Outputs')
dir.create(out_dir, recursive=TRUE, showWarnings=FALSE)

manifest <- read.csv(file.path(raw_dir,'RAW_MANIFEST_SHA256.csv'), stringsAsFactors=FALSE)
r <- manifest[manifest$file=='yahoo_KRWUSD_raw.rds',,drop=FALSE]
if (nrow(r)!=1) stop('KRW/USD manifest row missing or duplicated.')
fx_file <- file.path(raw_dir,'yahoo_KRWUSD_raw.rds')
got <- digest::digest(file=fx_file, algo='sha256')
if (!identical(tolower(got),tolower(r$sha256[1]))) stop('KRW/USD frozen-file SHA-256 mismatch.')
cat('PASS: frozen KRW/USD SHA-256 verified.\n')

fx <- readRDS(fx_file)
close_col <- grep('\\.Close$', colnames(fx), value=TRUE)
adj_col <- grep('\\.Adjusted$', colnames(fx), value=TRUE)
if (length(close_col)!=1) stop('Expected exactly one KRW=X Close column.')
close_raw <- fx[,close_col]
adj_raw <- if (length(adj_col)==1) fx[,adj_col] else close_raw
idx <- zoo::index(close_raw)

# Legacy dashboard behavior: last-observation-carried-forward before signal construction.
close_locf <- zoo::na.locf(close_raw, na.rm=FALSE)

rolling_z <- function(x, window) {
  zoo::rollapply(x, width=window,
    FUN=function(v) {
      z <- (tail(v,1)-mean(v,na.rm=TRUE))/stats::sd(v,na.rm=TRUE)
      as.numeric(z)
    }, align='right', fill=NA)
}
month_end <- function(x) {
  ep <- xts::endpoints(x, on='months')
  ep <- ep[ep>0]
  x[ep]
}

# Exact legacy window and warm-up policy.
z1306_strict <- rolling_z(close_locf,1306)
z1306_fill1 <- z1306_strict
z1306_fill1[is.na(z1306_fill1)] <- 1
zm_strict <- month_end(z1306_strict)
zm_fill1 <- month_end(z1306_fill1)
cm <- month_end(close_locf)
fxret_m <- cm/stats::lag(cm)-1

legacy_unhedged_weight <- function(z, lo=-0.5, hi=2.0) {
  w <- rep(NA_real_,length(z))
  ok <- is.finite(z)
  w[ok & z>hi] <- 0.10
  w[ok & z<lo] <- 0.90
  w[ok & z>=lo & z<=hi] <- 0.50
  w
}

base <- data.frame(
  month=format(zoo::index(cm),'%Y-%m'),
  fx_close=as.numeric(cm),
  fx_return=as.numeric(fxret_m),
  z1306_strict=as.numeric(zm_strict),
  z1306_legacy_fill1=as.numeric(zm_fill1),
  legacy_unhedged_weight=legacy_unhedged_weight(as.numeric(zm_fill1)),
  strict_unhedged_weight=legacy_unhedged_weight(as.numeric(zm_strict)),
  stringsAsFactors=FALSE
)
write.csv(base,file.path(out_dir,'G3_FX_MONTHLY_SIGNAL_AND_RETURNS_R_v0_19.csv'),row.names=FALSE)

# Missing-data audit with exact legacy LOCF impact.
raw_na <- is.na(as.numeric(close_raw))
locf_changed <- raw_na & is.finite(as.numeric(close_locf))
daily <- data.frame(
  date=as.character(idx), raw_close=as.numeric(close_raw), adjusted=as.numeric(adj_raw),
  locf_close=as.numeric(close_locf), raw_close_missing=raw_na, locf_imputed=locf_changed,
  stringsAsFactors=FALSE
)
write.csv(daily,file.path(out_dir,'G3_FX_DAILY_MISSING_AND_LOCF_AUDIT_R_v0_19.csv'),row.names=FALSE)

# Window-length sensitivity. These are diagnostics only; no rule is promoted from results.
win_rows <- list(); zc <- 1L
for (ww in c(756L,1306L,1827L)) {
  z <- rolling_z(close_locf,ww); zm <- month_end(z)
  win_rows[[zc]] <- data.frame(month=format(zoo::index(zm),'%Y-%m'), window_days=ww,
                               z_score=as.numeric(zm),
                               unhedged_weight=legacy_unhedged_weight(as.numeric(zm)),
                               stringsAsFactors=FALSE); zc<-zc+1L
}
write.csv(do.call(rbind,win_rows),file.path(out_dir,'G3_FX_WINDOW_SENSITIVITY_R_v0_19.csv'),row.names=FALSE)

# Threshold grid is predeclared as a robustness surface, never a selection search.
# Low threshold controls when USD is considered cheap (more unhedged exposure);
# high threshold controls when USD is considered expensive (less unhedged exposure).
lo_grid <- c(-1.5,-1.0,-0.5,0.0)
hi_grid <- c(1.0,1.5,2.0,2.5)
zv <- as.numeric(zm_fill1); mon <- format(zoo::index(zm_fill1),'%Y-%m')
thr <- list(); tc<-1L
for (lo in lo_grid) for (hi in hi_grid) {
  if (lo>=hi) next
  thr[[tc]] <- data.frame(month=mon, low_threshold=lo, high_threshold=hi,
                          unhedged_weight=legacy_unhedged_weight(zv,lo,hi),
                          is_legacy_rule=(abs(lo+0.5)<1e-12 & abs(hi-2.0)<1e-12),
                          stringsAsFactors=FALSE); tc<-tc+1L
}
write.csv(do.call(rbind,thr),file.path(out_dir,'G3_FX_THRESHOLD_GRID_WEIGHTS_R_v0_19.csv'),row.names=FALSE)

# Alternative handling of missing daily observations: roll over valid observations only.
valid <- close_raw[!is.na(close_raw)]
z_valid <- rolling_z(valid,1306)
z_valid_m <- month_end(z_valid)
valid_df <- data.frame(month=format(zoo::index(z_valid_m),'%Y-%m'), z1306_valid_observations_only=as.numeric(z_valid_m),
                       unhedged_weight_valid_observations_only=legacy_unhedged_weight(as.numeric(z_valid_m)), stringsAsFactors=FALSE)
write.csv(valid_df,file.path(out_dir,'G3_FX_VALID_OBSERVATION_CONTROL_R_v0_19.csv'),row.names=FALSE)

first_strict <- if (any(is.finite(as.numeric(zm_strict)))) format(zoo::index(zm_strict)[which(is.finite(as.numeric(zm_strict)))[1]],'%Y-%m') else NA_character_
meta <- data.frame(
  freeze_sha256=got,
  rows=NROW(fx), first_date=as.character(min(idx)), last_date=as.character(max(idx)),
  raw_close_missing=sum(raw_na), locf_imputed_rows=sum(locf_changed),
  legacy_window_days=1306, legacy_low_threshold=-0.5, legacy_high_threshold=2.0,
  legacy_low_state_unhedged_weight=0.90, legacy_mid_state_unhedged_weight=0.50, legacy_high_state_unhedged_weight=0.10,
  first_month_with_strict_1306day_z=first_strict,
  warmup_policy_legacy='fill missing z-score with 1, implying 50% unhedged exposure',
  performance_calculated=FALSE, rule_selected=FALSE,
  stringsAsFactors=FALSE
)
write.csv(meta,file.path(out_dir,'G3_FX_AUDIT_METADATA_R_v0_19.csv'),row.names=FALSE)

cat('PASS: v0.19 KRW/USD signal/missingness/sensitivity audit exports written.\n')
cat('Legacy 1306-day z-score, warm-up fill=1, thresholds -0.5/+2, and 90/50/10 unhedged weights were replicated.\n')
cat('No ADAA portfolio performance was calculated and no FX rule was selected.\n')
