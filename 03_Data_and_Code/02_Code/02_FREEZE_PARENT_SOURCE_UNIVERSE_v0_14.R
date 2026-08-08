# ADAA v0.14 — Parent-source universe raw-data freeze
# PURPOSE: download missing source-faithful parent instruments and pre-registered controls only.
# FORBIDDEN HERE: portfolio returns, CAGR, Sharpe, drawdown, Calmar, optimization, strategy ranking.
# Expected runtime: usually 1–5 minutes. Yahoo may be silent briefly.

options(stringsAsFactors = FALSE)

required_pkgs <- c("quantmod", "xts", "zoo", "digest")
missing_pkgs <- required_pkgs[!vapply(required_pkgs, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_pkgs)) stop("Install required packages first: ", paste(missing_pkgs, collapse=", "))

root <- normalizePath(getwd(), winslash="/", mustWork=TRUE)
if (!grepl("05_ADAA$", root)) stop("Set the R working directory to the 05_ADAA project root before running.")

out_dir <- file.path(root, "03_Data_and_Code", "01_Data", "raw_freeze_parent_v0_14")
dir.create(out_dir, recursive=TRUE, showWarnings=FALSE)

# Exact/near-exact parent instruments absent from the v0.8 primary freeze.
# VSS is a source-author-motivated modern ETF expression/control for ADM's ex-US small-cap role.
required_symbols <- c("VEA", "VWO", "BND", "VTI", "GSG", "VINEX", "VSS", "IWD", "IWN")
# Optional source robustness control discussed by the ADM author. Failure does not invalidate the freeze.
optional_symbols <- c("OSMAX")
all_symbols <- c(required_symbols, optional_symbols)

from_date <- as.Date("1990-01-01")
retrieval_started <- Sys.time()

cat("ADAA v0.14 parent-source raw freeze\n")
cat("No portfolio performance will be calculated.\n")
cat("Output:", out_dir, "\n\n")

raw <- list()
errors <- list()

for (sym in all_symbols) {
  cat("Downloading", sym, "... ")
  obj <- tryCatch(
    quantmod::getSymbols(sym, src="yahoo", from=from_date, auto.assign=FALSE, warnings=TRUE),
    error=function(e) e
  )
  if (inherits(obj, "error")) {
    errors[[sym]] <- conditionMessage(obj)
    cat("FAILED\n")
  } else {
    raw[[sym]] <- obj
    cat("OK (", NROW(obj), " rows)\n", sep="")
  }
}

missing_required <- setdiff(required_symbols, names(raw))
if (length(missing_required)) {
  stop("Required parent-source symbols failed: ", paste(missing_required, collapse=", "),
       ". Existing raw_freeze_v0_8 was not changed. Inspect network/Yahoo availability before retrying.")
}

saveRDS(raw, file.path(out_dir, "yahoo_parent_source_raw.rds"), compress="xz")

inventory <- do.call(rbind, lapply(names(raw), function(sym) {
  x <- raw[[sym]]
  idx <- zoo::index(x)
  data.frame(
    symbol=sym,
    role=ifelse(sym %in% required_symbols, "required", "optional_control"),
    first_date=as.character(min(idx)),
    last_date=as.character(max(idx)),
    rows=NROW(x),
    columns=NCOL(x),
    total_na=sum(is.na(x)),
    adjusted_na=if (paste0(sym,".Adjusted") %in% colnames(x)) sum(is.na(x[,paste0(sym,".Adjusted")])) else NA_integer_,
    stringsAsFactors=FALSE
  )
}))
write.csv(inventory, file.path(out_dir, "PARENT_SOURCE_INVENTORY_v0_14.csv"), row.names=FALSE)

err_df <- if (length(errors)) {
  data.frame(symbol=names(errors), error=unlist(errors, use.names=FALSE), stringsAsFactors=FALSE)
} else data.frame(symbol=character(0), error=character(0))
write.csv(err_df, file.path(out_dir, "OPTIONAL_OR_FAILED_DOWNLOADS_v0_14.csv"), row.names=FALSE)

meta <- data.frame(
  freeze_version="v0.14",
  purpose="parent-source universe / P3 decision-only preparation",
  retrieval_started=as.character(retrieval_started),
  retrieval_completed=as.character(Sys.time()),
  timezone=Sys.timezone(),
  R_version=R.version.string,
  quantmod=as.character(utils::packageVersion("quantmod")),
  xts=as.character(utils::packageVersion("xts")),
  zoo=as.character(utils::packageVersion("zoo")),
  performance_calculated=FALSE,
  stringsAsFactors=FALSE
)
write.csv(meta, file.path(out_dir, "environment_metadata_v0_14.csv"), row.names=FALSE)

# Build manifest last; exclude the manifest file itself.
manifest_targets <- list.files(out_dir, full.names=TRUE)
manifest_targets <- manifest_targets[basename(manifest_targets) != "RAW_MANIFEST_SHA256_v0_14.csv"]
manifest <- data.frame(
  file=basename(manifest_targets),
  bytes=file.info(manifest_targets)$size,
  sha256=vapply(manifest_targets, digest::digest, character(1), file=TRUE, algo="sha256"),
  stringsAsFactors=FALSE
)
write.csv(manifest, file.path(out_dir, "RAW_MANIFEST_SHA256_v0_14.csv"), row.names=FALSE)

# Recheck manifest immediately.
manifest_check <- vapply(seq_len(nrow(manifest)), function(i) {
  f <- file.path(out_dir, manifest$file[i])
  identical(digest::digest(f, file=TRUE, algo="sha256"), manifest$sha256[i])
}, logical(1))
if (!all(manifest_check)) stop("Manifest self-check failed.")

cat("\nPASS: v0.14 parent-source raw freeze completed.\n")
cat("Required symbols:", length(required_symbols), "/", length(required_symbols), "available.\n")
if (length(errors)) cat("Optional/failed downloads recorded:", paste(names(errors), collapse=", "), "\n")
cat("No portfolio performance was calculated.\n")
