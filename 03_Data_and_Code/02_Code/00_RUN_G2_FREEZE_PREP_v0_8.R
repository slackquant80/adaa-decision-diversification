# ADAA G2 local input-freeze preparation — v0.8
# Purpose: acquire and freeze raw inputs only. Do NOT calculate headline performance.
# Expected runtime: usually 3–10 minutes depending on network and package state.
# Long silent periods: Yahoo downloads can pause for 1–2 minutes. If there is no output
# for >10 minutes, stop and inspect network/API errors before retrying.

options(stringsAsFactors = FALSE)

required <- c("quantmod", "xts", "zoo", "digest")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) stop("Install required packages first: ", paste(missing, collapse=", "))

root <- normalizePath(getwd(), winslash="/", mustWork=TRUE)
if (!grepl("05_ADAA$", root)) stop("Run this script with working directory set to the 05_ADAA project root.")

raw_dir <- file.path(root, "03_Data_and_Code", "01_Data", "raw_freeze_v0_8")
dir.create(raw_dir, recursive=TRUE, showWarnings=FALSE)

symbols_primary <- c("SPY","EEM","EFA","AGG","QQQ","IWM","VGK","EWJ","EWY",
                     "VNQ","DBC","GLD","TLT","HYG","LQD","TIP","BIL","IEF","SHY")
symbols_proxy <- c("VFINX","VEIEX","FDIVX","VBMFX","VIGRX","NAESX","VEURX",
                   "VGSIX","PCRAX","FKRCX","VUSTX","VWEHX","VWESX","VIPSX","VFISX","VFITX")

stamp <- format(Sys.time(), "%Y%m%dT%H%M%S%z")
cat("[1/4] Downloading primary market series...\n")
env1 <- new.env()
quantmod::getSymbols(symbols_primary, src="yahoo", from="2000-01-01", env=env1, auto.assign=TRUE)
cat("[2/4] Downloading historical proxy series...\n")
env2 <- new.env()
quantmod::getSymbols(symbols_proxy, src="yahoo", from="2000-01-01", env=env2, auto.assign=TRUE)
cat("[3/5] Downloading current-vintage UNRATE...\n")
env3 <- new.env()
quantmod::getSymbols("UNRATE", src="FRED", from="2000-01-01", env=env3, auto.assign=TRUE)
cat("[4/5] Downloading KRW/USD overlay input...\n")
fx <- quantmod::getSymbols("KRW=X", src="yahoo", from="2003-01-01", auto.assign=FALSE)

saveRDS(as.list(env1), file.path(raw_dir, "yahoo_primary_raw.rds"), compress="xz")
saveRDS(as.list(env2), file.path(raw_dir, "yahoo_proxy_raw.rds"), compress="xz")
saveRDS(env3$UNRATE, file.path(raw_dir, "fred_UNRATE_current_vintage_raw.rds"), compress="xz")
saveRDS(fx, file.path(raw_dir, "yahoo_KRWUSD_raw.rds"), compress="xz")

meta <- data.frame(
  freeze_version="v0.8",
  retrieval_timestamp=as.character(Sys.time()),
  timezone=Sys.timezone(),
  R_version=R.version.string,
  quantmod=as.character(utils::packageVersion("quantmod")),
  xts=as.character(utils::packageVersion("xts")),
  zoo=as.character(utils::packageVersion("zoo")),
  stringsAsFactors=FALSE
)
write.csv(meta, file.path(raw_dir,"environment_metadata.csv"), row.names=FALSE)

files <- list.files(raw_dir, full.names=TRUE)
manifest <- data.frame(
  file=basename(files),
  bytes=file.info(files)$size,
  sha256=vapply(files, digest::digest, character(1), file=TRUE, algo="sha256"),
  stringsAsFactors=FALSE
)
write.csv(manifest, file.path(raw_dir,"RAW_MANIFEST_SHA256.csv"), row.names=FALSE)

cat("[5/5] Raw freeze complete. No portfolio performance was calculated.\n")
cat("Output:", raw_dir, "\n")
