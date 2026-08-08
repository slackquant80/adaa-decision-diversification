# ADAA v0.17.1 independent local-R validation of the opened performance/accounting engine.
# Patch: strip inherited date names from scalar metrics before row-binding validation outputs.
# Uses only frozen CSV inputs already produced before performance opening.
# No optimization or strategy selection is performed.

out_dir <- file.path('03_Data_and_Code','04_Outputs')
price_file <- file.path(out_dir,'G5_FROZEN_MONTH_END_ADJUSTED_R_v0_15.csv')
stopifnot(file.exists(price_file))

read_w <- function(fname) {
  x <- read.csv(file.path(out_dir,fname), check.names=FALSE, stringsAsFactors=FALSE)
  stopifnot('signal_month' %in% names(x))
  rownames(x) <- as.character(x$signal_month)
  x$signal_month <- NULL
  x[] <- lapply(x, as.numeric)
  rs <- rowSums(x)
  if (any(abs(rs-1)>1e-10)) stop(paste('Weight sum failure:',fname))
  x
}

px <- read.csv(price_file, check.names=FALSE, stringsAsFactors=FALSE)
rownames(px) <- as.character(px$signal_month); px$signal_month <- NULL
px[] <- lapply(px, as.numeric)
# Monthly simple total returns labeled by the ending month.
rmat <- as.matrix(px[-1,,drop=FALSE]) / as.matrix(px[-nrow(px),,drop=FALSE]) - 1
rownames(rmat) <- rownames(px)[-1]
colnames(rmat) <- colnames(px)

W <- list(
  HAA=read_w('G2_HAA_TARGET_WEIGHTS_R_v0_11_1.csv'),
  BAA=read_w('G2_BAA_AGGRESSIVE_TARGET_WEIGHTS_R_v0_11_1.csv'),
  ADM=read_w('G2_ADM_TARGET_WEIGHTS_R_v0_11_1.csv'),
  FAA=read_w('G3_FAA_CANONICAL_PEER_ONLY_EXACTN_TARGET_WEIGHTS_R_v0_16.csv'),
  LAA=read_w('G2_LAA_CARRY_CALENDAR_TARGET_WEIGHTS_v0_11.csv')
)
months <- Reduce(intersect,lapply(W,rownames))
months <- sort(months)
if (length(months)!=218 || months[1]!='2008-05' || months[length(months)]!='2026-06') stop('Unexpected primary signal window')
next_month <- function(x) format(seq(as.Date(paste0(x,'-01')), by='1 month', length.out=2)[2],'%Y-%m')
holding <- vapply(months,next_month,character(1))
if (holding[1]!='2008-06' || holding[length(holding)]!='2026-07') stop('Unexpected holding window')

agg_weights <- function(alphas) {
  if (abs(sum(unlist(alphas))-1)>1e-12) stop('alphas do not sum to 1')
  assets <- sort(unique(unlist(lapply(names(alphas), function(k) colnames(W[[k]])))))
  z <- matrix(0,nrow=length(months),ncol=length(assets),dimnames=list(months,assets))
  for (k in names(alphas)) {
    wk <- W[[k]][months,,drop=FALSE]
    add <- matrix(0,nrow=length(months),ncol=length(assets),dimnames=list(months,assets))
    add[,colnames(wk)] <- as.matrix(wk)
    z <- z + as.numeric(alphas[[k]])*add
  }
  if (any(abs(rowSums(z)-1)>1e-10)) stop('aggregate weight sum failure')
  as.data.frame(z,check.names=FALSE)
}

portfolio_path <- function(T) {
  assets <- colnames(T); prev_eop <- NULL
  gross <- turnover <- numeric(nrow(T)); hm <- character(nrow(T))
  for (i in seq_len(nrow(T))) {
    sm <- rownames(T)[i]; hm[i] <- next_month(sm)
    if (!(hm[i] %in% rownames(rmat))) stop(paste('missing return month',hm[i]))
    ar <- rmat[hm[i],assets,drop=TRUE]; t <- as.numeric(T[i,,drop=TRUE]); names(t)<-assets
    used <- abs(t)>1e-15
    if (any(is.na(ar[used]))) stop(paste('missing used return',hm[i],paste(names(ar)[used & is.na(ar)],collapse=',')))
    ar[is.na(ar)] <- 0
    gross[i] <- sum(t*ar)
    turnover[i] <- if (is.null(prev_eop)) 0 else sum(abs(t-prev_eop))
    prev_eop <- t*(1+ar)/(1+gross[i])
  }
  data.frame(signal_month=rownames(T),holding_month=hm,gross_return=gross,gross_L1_turnover=turnover,stringsAsFactors=FALSE)
}

max_uw <- function(x) {
  w <- cumprod(1+x); p <- cummax(w); u <- w < p*(1-1e-14); cur<-0; mx<-0
  for (v in u) { if (v) cur<-cur+1 else cur<-0; if (cur>mx) mx<-cur }
  mx
}
worst_roll <- function(x,h) {
  if (length(x)<h) return(c(NA_real_,NA_character_))
  vals <- rep(NA_real_,length(x))
  for (i in h:length(x)) vals[i] <- prod(1+x[(i-h+1):i])-1
  j <- which.min(vals)
  c(vals[j],names(x)[j])
}
metrics <- function(x, rf) {
  names(x) <- names(rf) <- holding
  n <- length(x); wealth <- cumprod(1+x); cagr <- unname(wealth[n]^(12/n)-1)
  annmean <- mean(x)*12; vol <- sd(x)*sqrt(12); ex <- x-rf; sh <- mean(ex)/sd(ex)*sqrt(12)
  dd <- wealth/cummax(wealth)-1; j <- which.min(dd); mdd <- unname(dd[j]); cal <- unname(cagr/abs(mdd))
  down <- sqrt(mean(pmin(x,0)^2))*sqrt(12)
  w1<-worst_roll(x,1); w3<-worst_roll(x,3); w12<-worst_roll(x,12); w36<-worst_roll(x,36)
  c(months=n,CAGR=cagr,annualized_arithmetic_mean=annmean,annualized_volatility=vol,BIL_excess_Sharpe=sh,
    max_drawdown=mdd,Calmar=cal,downside_deviation=down,max_time_under_water_months=max_uw(x),
    worst_1m_return=as.numeric(w1[1]),worst_3m_return=as.numeric(w3[1]),worst_12m_return=as.numeric(w12[1]),worst_36m_return=as.numeric(w36[1]),ending_growth_of_1=unname(wealth[n]))
}

T_equal <- agg_weights(list(HAA=.2,BAA=.2,ADM=.2,FAA=.2,LAA=.2))
T_hist <- agg_weights(list(HAA=.25,BAA=.15,ADM=.175,FAA=.175,LAA=.25))
T_6040 <- as.data.frame(matrix(rep(c(.6,.4),each=length(months)),nrow=length(months),ncol=2),check.names=FALSE)
rownames(T_6040)<-months; colnames(T_6040)<-c('SPY','IEF')
P <- list(ADAA_equal20_canonical=portfolio_path(T_equal),ADAA_historical_weights_canonical=portfolio_path(T_hist),Benchmark_60_40_SPY_IEF=portfolio_path(T_6040))
# Add standalone sleeves using the same engine.
for (k in names(W)) P[[paste0('Sleeve_',k)]] <- portfolio_path(W[[k]][months,,drop=FALSE])

rf <- as.numeric(rmat[holding,'BIL']); names(rf)<-holding
cost_grid <- c(0,5,10,25,50); rows <- list(); z<-1
expected_metric_names <- c('months','CAGR','annualized_arithmetic_mean','annualized_volatility','BIL_excess_Sharpe',
                           'max_drawdown','Calmar','downside_deviation','max_time_under_water_months',
                           'worst_1m_return','worst_3m_return','worst_12m_return','worst_36m_return','ending_growth_of_1')
for (nm in names(P)) {
  p <- P[[nm]]
  for (bps in cost_grid) {
    x <- p$gross_return - p$gross_L1_turnover*(bps/10000)
    names(x)<-p$holding_month
    mm <- metrics(x,rf)
    if (!identical(names(mm), expected_metric_names)) stop(paste('Metric schema drift:', nm, bps, paste(names(mm), collapse=',')))
    metric_df <- as.data.frame(as.list(unname(mm)), check.names=FALSE)
    names(metric_df) <- expected_metric_names
    rows[[z]] <- cbind(data.frame(portfolio=nm,cost_bps=bps,stringsAsFactors=FALSE),
                       metric_df,
                       data.frame(total_gross_L1_turnover=unname(sum(p$gross_L1_turnover)),
                                  annualized_mean_gross_L1_turnover=unname(mean(p$gross_L1_turnover)*12),
                                  check.names=FALSE))
    z<-z+1
  }
}
out <- do.call(rbind,rows)
write.csv(out,file.path(out_dir,'G6_PRIMARY_PERFORMANCE_R_VALIDATION_v0_17_1.csv'),row.names=FALSE)
monthly <- do.call(rbind,lapply(names(P)[1:3],function(nm){x<-P[[nm]];x$portfolio<-nm;x[,c('portfolio','signal_month','holding_month','gross_return','gross_L1_turnover')]}))
write.csv(monthly,file.path(out_dir,'G6_PRIMARY_MONTHLY_RETURN_TURNOVER_R_VALIDATION_v0_17_1.csv'),row.names=FALSE)
cat('PASS: v0.17.1 independent base-R performance/accounting validation exports written.\n')
cat('Validated: canonical equal-sleeve ADAA, historical-weight ADAA, 60/40, and five standalone sleeves.\n')
cat('No optimization or reselection was performed.\n')
