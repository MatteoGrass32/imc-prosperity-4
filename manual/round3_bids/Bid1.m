clc
clear 
close all


% Round 3 manual. Counterparty reserve prices are uniform on 670..920 in steps of 5,
% the product resells at 920, and you submit two bids. The first trades against any
% reserve below it. The second trades against the reserves between the two bids, but
% is penalised by ((920-avgB2)/(920-B2))^3 if it falls under the field's average
% second bid. Below: B1 solved analytically, then the same thing by simulation.


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
