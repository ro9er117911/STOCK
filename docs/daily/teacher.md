這個程式我想要改成用html來撰寫  
並且用html呈現結果  
遇到用到r套件的時候，盡量不要引用，自己撰寫函數
我希望程式可以自己去抓取yahoo finance 的資料
我需要幾個輸入的參數 (1) 股票代碼 (2) 資料擷取期間 (3) 初始金額 (IA) (4) 定期定額年金額 (CFA) (5) 投資頻率 (Freq) 
我知道 CORS Proxy 常常會被擋，需要利用Cloudflare Worker 完美繞過 Yahoo Finance 的跨域限制，這個部分請你指導如何設定，並把虛擬的網域植入


packages=c("xts","quantmod","lubridate","PerformanceAnalytics",

           "googledrive","tidyverse", "quadprog","HierPortfolios","epo",

           "ggplot2","ggrepel","Rcpp")

for(i in packages){

  if(!require(i,character.only = TRUE)) install.packages(i)

  library(i,character.only = TRUE)

}



Ticker <- "SPY"         # NVDA, SPY, 3324.TWO

SD <- "2002-07-01"

ED <- "2025-10-30"

IA <- 10000             # Initial Amount

CF <- 10000             # Contribute Fixed Amount every Month

Freq <- "months"

adjF <- 12



CFA <- CF*adjF           # Contribute Fixed Amount every year

SD <- as.Date(SD)

ED <- as.Date(ED)





tem = loadSymbols(Ticker, from =  SD, to =ED,

                  auto.assign = FALSE, return.class = 'xts')



tem <-  adjustOHLC(tem,use.Adjusted=TRUE)

colnames(tem) <- c("PO","PH","PL","P","VO","adjP")

Prices <- na.locf(tem$P)

Loc <- endpoints(Prices,Freq)

Price <- Prices[Loc,]

RETs <- Price/lag.xts(Price,1) - 1

colnames(RETs) <- "R"

RET <- na.omit(RETs)





CF <- c(IA,rep(CFA*(1/adjF),(length(RET)-1)))

FVMat <- matrix(0,

                nrow=length(RET),

                ncol=length(RET))



for (i in seq(1,length(RET))) {

  

  temR <- as.matrix(RET)

  temR <- temR[i:length(temR)]

  temGR <- cumprod(1+temR)

  temFV <- temGR*CF[i]

  FVMat[(i:length(RET)),i] <- temFV

}

Wealth <- apply(FVMat,1,sum)

Wealth <- xts(c(IA,Wealth),order.by = index(Price))



#print(FVMat[1:10,1:10])





Wealth.RET <- ((Wealth / lag.xts(Wealth,1)) - 1)



stat = matrix(0, ncol(Wealth.RET), 8)



rx <- na.omit(Wealth.RET )



stat[ , 1 ]  <-  ((tail(Wealth,1) / sum(CF))^(1/length(rx)))^adjF - 1

stat[ , 2 ] = sqrt(adjF)*apply(rx, 2, sd)

stat[ , 3 ] = stat[ , 1 ]/stat[ , 2 ]

stat[ , 4 ] = sqrt(adjF)*DownsideDeviation(rx)

stat[ , 5 ] = sqrt(adjF)*SortinoRatio(rx)

stat[ , 6 ] = maxDrawdown(rx)

stat[ , 7 ] = as.numeric(Wealth[length(Wealth)])/as.numeric(Wealth[1])

stat[ , 8 ] = as.numeric(Wealth[length(Wealth)])/as.numeric(sum(CF))

stat = round(as.table(stat),2)



colnames(stat) = c('mean', 'vol', 'sharpe', 'downsideRisk', 'Sortino', 'maxDrawdown',

                   'Wealth(T)/IA','Wealth(T)/Invest')

rownames(stat) = Ticker



Wealth.df <- data.frame((index(Wealth)),round(Wealth,2))

colnames(Wealth.df) <- c("Date","Wealth")

data_end <- data.frame(Wealth.df[nrow(Wealth.df),c(1,2)])

data_first <- data.frame(Wealth.df[1,c(1,2)])

stat.sum <- data.frame(CAGR = stat[1],Stdev = stat[2],MaxDown = stat[6])



lab  <- paste('Ticker=',Ticker,

              '\nFreq=',Freq, ";",

              "IA=", format(IA,big.mark=",",scientific=FALSE), "; ",

              "CFA=", format(CFA,big.mark=",",scientific=FALSE), "; ",

              "CFA/Freq=", format(round(CFA*(1/adjF),0),big.mark=",",scientific=FALSE),

              "\nInvest=", format(round(sum(CF),0),big.mark=",",scientific=FALSE), "; ",

              "Wealth(T)=", format(round(Wealth[length(Wealth)],0),big.mark=",",scientific=FALSE),

              "\nCAGR = ", stat[1],"; ","DownStdev = ", stat[4], "; ","MaxDown = ", stat[6],

              '\nWealth(T)/IA=',stat[7], "; ",'Wealth(T)/Invest=',stat[8])



p <- ggplot(data = Wealth.df ,

            aes(x = Date,

                y = Wealth))

p <- p + geom_line()

p <- p + labs(x = 'Date', y = 'Wealth')

p <- p + scale_colour_grey(start = 0.0, end = 0.6)  # remove the color of lines

p <- p + theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank(),

               panel.background = element_blank(), axis.line = element_line(colour = "black"),

               text = element_text(size=15)) # remove vertical and horizontal lines with light gray

p <- p + geom_text_repel(aes(label = scales::comma(Wealth)), data = data_end, size = 5)

p <- p + geom_text_repel(aes(label = scales::comma(Wealth)), data = data_first, size = 5)

p <- p + ggtitle(lab) + theme(plot.title = element_text(size = 10, face = 'bold'))

p <- p + scale_y_continuous(breaks=seq(round(min(Wealth.df[,2]),0),

                                       round(max(Wealth.df[,2]),0),length.out=5))

p <- p + scale_x_continuous(breaks=seq(ymd(Wealth.df[,1])[1],

                                       ymd(Wealth.df[,1])[nrow(Wealth.df)],length.out=5))

print(p)   

