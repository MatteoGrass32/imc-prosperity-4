clc
clear

%variabili di base
sellPrice = 920;
reserveRange = 670:5:920;  
Nsimulation = 500; %è il numero di tentativi su cui faccio la media              
nGardeners = 1000; % è il numero di acquirenti stimato         
mySearchRangeFull = 700:1:900; %riduco l'intervallo per aumentare la velocità
pnlMatrix = zeros(length(mySearchRangeFull), length(mySearchRangeFull));

% ipotizziamo una normale
sigma_others = 0;  
base_pop = 859 * ones(Nsimulation, 1);
aggressors = 859 + abs(sigma_others * randn(Nsimulation, 1)); % Coda verso l'alto (es. +20 sigma)
mu_others = (0.5 * base_pop) + (0.5 * aggressors);% La media del mercato in ogni simulazione è la media pesata dei due gruppi   
avgB2_samples = mu_others + sigma_others * randn(Nsimulation, 1);
avgB2_samples = max(670, min(919, avgB2_samples)); % tronchiamo i valori assurdi 


% Pre-calcoliamo le riserve (Nsimulation x nGardeners)
allReserves = reserveRange(randi(length(reserveRange), Nsimulation, nGardeners));

% Pre-calcoliamo i vincitori per B1 per ogni possibile prezzo (Velocizza il loop)
vintiB1_all = zeros(Nsimulation, length(mySearchRangeFull));
for i = 1:length(mySearchRangeFull)
    vintiB1_all(:,i) = sum(mySearchRangeFull(i) > allReserves, 2);
end

for i = 1:length(mySearchRangeFull)
    b1 = mySearchRangeFull(i);
    v1 = vintiB1_all(:,i); % Unità vinte da B1 in ogni sim
    
    for j = i:length(mySearchRangeFull) % b2 può essere uguale a b1
        b2 = mySearchRangeFull(j);
        
        % 1. Calcolo Penalità VETTORIALE (per ogni simulazione)
        % In ogni universo (simulazione) la media degli altri è diversa
        penalties = ones(Nsimulation, 1);
        under_mean = (b2 <= avgB2_samples);
        
        % Applichiamo la formula solo dove siamo sotto la media di quella sim
        penalties(under_mean) = ((sellPrice - avgB2_samples(under_mean)) ./ (sellPrice - b2)).^3;
        penalties = max(0, penalties);
        
        % 2. Calcolo Unità B2
        v2 = sum(allReserves > b1 & allReserves < b2, 2);
        
        % 3. Calcolo PnL Medio
        % Moltiplichiamo punto a punto le unità B2 per le loro penalità specifiche
        pnls = v1 * (sellPrice - b1) + (v2 .* (sellPrice - b2) .* penalties);
        pnlMatrix(i,j) = mean(pnls);
    end
end

% Trova il Massimo 
[maxPnl, linearIdx] = max(pnlMatrix(:));
[bestIdx1, bestIdx2] = ind2sub(size(pnlMatrix), linearIdx);

bestB1 = mySearchRangeFull(bestIdx1);
bestB2 = mySearchRangeFull(bestIdx2);

fprintf('--- RISULTATI CON INCERTEZZA ---\n');
fprintf('Miglior Bid 1: %d\n', bestB1);
fprintf('Miglior Bid 2: %d\n', bestB2);
fprintf('PnL Totale: %.2f\n', maxPnl);


%nash eq: 751 836