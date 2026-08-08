clc
clear 
close all


% **Manual trading challenge: “The Celestial Gardeners’ Guild”**
% You trade against a number of counterparties that all have a **reserve price** ranging between **670** and **920**. On the next trading day, you’re able to sell all the product for a fair price, **920**.
%The distribution of the bids is **uniformly distributed** at **increments of 5** between **670** and **920**. 
%Example**: counterparties may have reserve prices at 675 and 680, but not at 676, 677, 678, 679, etc..

%You may submit **two bids**. If the first bid is **higher** than the
%reserve price, they trade with you at your first bid. If your second bid is **higher** than the reserve price of a counterparty and **higher** than the mean of second bids of all players you trade at your second bid. If your second bid is **higher** than the reserve price, but **lower** than the mean of second bids of all players, the chance of a trade rapidly decreases: you will trade at your second bid **but** your PNL is penalised by:
%Penalty = ((920-avgB2) / (920-B2) )^3

%Q:is the "increments of 5 between 670 and 920" inclusive or naw
%Ans:It's inclusive

%Q:how do the two bids work, are you basically doing the same trade twice as
%in youll bid once and then their "stock refreshes" ?
%Ans: Each counterparty is willing to trade with you at most once

%Q:If the first bid is higher than some reserve price and second bid is also higher than some reserve price, do we trade 2 units one at the price of first bid and another at the price of second bid?
%Ans: If you first bid is already higher than a certain counterparties reserve price, you just trade it at that level (first bid), and then sell it at fair price later. 2nd bid is not even considered in that case.

%Info: Counterparties are not other players, but predefined bots, with their reserve prices distributed according to distribution on Wiki
%Info: Other player's 2nd bids do impact average of 2nd bids, and then the scaling formula applies (if you're below it)
%Info:With a particular counterparty you can only trade maximally of 1 time. It's also possible to not trade with some at all of course (if both of your bids are <= to their reserve price)
%Info:The number of counterparties is not given
%Info: Penality is only applied to B2, not B1
%(Info not verified but almost sure: B2 execute all the possibile trades
%between B1 and B2, either with penalty or not
%Info: B1 and B2 can be every integer number beteween 670 and 920 (B2 has
%to be bigger than B1)
%Info: B1 and B2 have to be strictly greater than the offers

%LOW BID (p uniforme tra 670 e 920 con 51 masse di probabilità, uno ogni 5)
n = 1; %n non è rilevante
pSingolaMassa = 1/51;
PnlMax=0;
p_cumulata=0;
i=670;
counter=1;

while i<=920
    p_cumulata=p_cumulata+pSingolaMassa;
    Pnl(counter,1) = n*p_cumulata * (920-i);
    if(Pnl(counter,1)>PnlMax)
        PnlMax=Pnl(counter,1);
        indice=i;
    end
    i=i+5;
    counter=counter+1;
end

%SIMULATION (p not fixed)
% Parametri base
sellPrice = 920;
reserveRange = 670:5:920; % I 51 possibili prezzi di riserva
Ncounterparties = 10000;            % Numero di simulazioni (più sono, più è preciso)
nGardeners = 51;         % Numero di venditori
pnlMedioPerBid = zeros(length(reserveRange), 1);
% Testiamo ogni possibile Bid 1
for i = 1:length(reserveRange)
    currentBid = reserveRange(i);
    pnlSimulati = zeros(Ncounterparties, 1);
    
    for s = 1:Ncounterparties
        % GENERATORE CASUALE: 
        % Estraiamo i prezzi di riserva per 51 venditori in questa simulazione
        reserves = reserveRange(randi(length(reserveRange), 1, nGardeners));
        
        % Quanti Gardeners accettano il mio bid?
        venditoriVinti = sum(currentBid >= reserves);
        
        % Calcolo PnL di questa simulazione
        pnlSimulati(s) = venditoriVinti * (sellPrice - currentBid);
    end
    
    % Facciamo la media di tutti i risultati per questo specifico Bid
    pnlMedioPerBid(i) = mean(pnlSimulati);
end
% Trova il massimo
[maxPnl, idx] = max(pnlMedioPerBid);
bestBid1 = reserveRange(idx);
fprintf('Miglior Bid 1 calcolato: %d\n', bestBid1);
fprintf('PnL Medio atteso: %.2f\n', maxPnl);
% Grafico della parabola
plot(reserveRange, pnlMedioPerBid, 'LineWidth', 2);
grid on; xlabel('Tuo Bid 1'); ylabel('PnL Medio');
title('Ottimizzazione Stocastica Bid 1');
