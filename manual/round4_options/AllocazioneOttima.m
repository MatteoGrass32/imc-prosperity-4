clc
clear all
close all
% --- SCRIPT DI ALLOCAZIONE, DELTA HEDGING E PNL ATTESO ---
disp('--- AVVIO OTTIMIZZATORE DI PORTAFOGLIO ---');

% 1. Input Dati (Opzioni)
names = {'AC_50_P'; 'AC_50_C'; 'AC_35_P'; 'AC_40_P'; 'AC_45_P'; 'AC_60_C'; 'AC_50_P_2'; 'AC_50_C_2'; 'AC_50_CO'; 'AC_40_BP'; 'AC_45_KO'};
theos = [12.0268; 12.0260; 4.3360; 6.5094; 9.0888; 8.7908; 9.8707; 9.8703; 21.8968; 4.7679; 0.2062];
bids  = [12.00;   12.00;   4.33;   6.50;   9.05;   8.80;   9.70;   9.70;   22.20;   5.00;   0.15];
asks  = [12.05;   12.05;   4.35;   6.55;   9.10;   8.85;   9.75;   9.75;   22.30;   5.10;   0.175];
sizes = [50;      50;      50;     50;     50;     50;     50;     50;     50;      50;     500];

num_options = length(names);
contract_size = 3000; % Moltiplicatore per ogni lotto
min_edge = 0.005;      % Margine di sicurezza (si considera anche lo spread)

% Array per le decisioni
actions = strings(num_options, 1);
volumes = zeros(num_options, 1);
expected_pnl = zeros(num_options, 1);

% --- CALCOLO DEI DELTA TRAMITE DIFFERENZE FINITE ---
disp('Calcolo della matrice dei rischi (Delta)...');
S_up = 50.1; S_down = 49.9; dS = S_up - S_down;
sigma = 2.51; dt = 1/1008; paths = 100000;
Z = randn(60, paths);
ret = exp(-0.5 * sigma^2 * dt + sigma * sqrt(dt) * Z);

S_u = zeros(61, paths); S_u(1,:) = S_up; S_u(2:end,:) = S_up * cumprod(ret,1);
S_d = zeros(61, paths); S_d(1,:) = S_down; S_d(2:end,:) = S_down * cumprod(ret,1);

calc_delta = @(V_up, V_down) mean(V_up - V_down) / dS;

deltas = zeros(num_options, 1);
deltas(1) = calc_delta(max(50 - S_u(61,:), 0), max(50 - S_d(61,:), 0)); 
deltas(2) = calc_delta(max(S_u(61,:) - 50, 0), max(S_d(61,:) - 50, 0)); 
deltas(3) = calc_delta(max(35 - S_u(61,:), 0), max(35 - S_d(61,:), 0)); 
deltas(4) = calc_delta(max(40 - S_u(61,:), 0), max(40 - S_d(61,:), 0)); 
deltas(5) = calc_delta(max(45 - S_u(61,:), 0), max(45 - S_d(61,:), 0)); 
deltas(6) = calc_delta(max(S_u(61,:) - 60, 0), max(S_d(61,:) - 60, 0)); 
deltas(7) = calc_delta(max(50 - S_u(41,:), 0), max(50 - S_d(41,:), 0)); 
deltas(8) = calc_delta(max(S_u(41,:) - 50, 0), max(S_d(41,:) - 50, 0)); 

pay_u = (S_u(41,:) > 50) .* max(S_u(61,:) - 50, 0) + (S_u(41,:) <= 50) .* max(50 - S_u(61,:), 0);
pay_d = (S_d(41,:) > 50) .* max(S_d(61,:) - 50, 0) + (S_d(41,:) <= 50) .* max(50 - S_d(61,:), 0);
deltas(9) = calc_delta(pay_u, pay_d);

deltas(10) = calc_delta((S_u(61,:) < 40)*10, (S_d(61,:) < 40)*10);

surv_u = min(S_u, [], 1) > 35; surv_d = min(S_d, [], 1) > 35;
deltas(11) = calc_delta(surv_u .* max(45 - S_u(61,:), 0), surv_d .* max(45 - S_d(61,:), 0));

% --- LOGICA DI TRADING SULLE 11 OPZIONI ---
portfolio_delta = 0;
total_options_pnl = 0;

for i = 1:num_options
    if theos(i) > asks(i) + min_edge
        actions(i) = "Buy";
        volumes(i) = sizes(i);
        portfolio_delta = portfolio_delta + (deltas(i) * sizes(i));
        edge_unit = theos(i) - asks(i);
        expected_pnl(i) = edge_unit * sizes(i) * contract_size;
        
    elseif theos(i) < bids(i) - min_edge
        actions(i) = "Sell";
        volumes(i) = sizes(i);
        portfolio_delta = portfolio_delta - (deltas(i) * sizes(i));
        edge_unit = bids(i) - theos(i);
        expected_pnl(i) = edge_unit * sizes(i) * contract_size;
        
    else
        actions(i) = "Ignore";
        volumes(i) = 0;
        expected_pnl(i) = 0;
    end
    total_options_pnl = total_options_pnl + expected_pnl(i);
end

% --- LOGICA DI HEDGING SUL SOTTOSTANTE (LA RIGA 1: AC) ---
ac_max_size = 200;
ac_action = "Ignore";
ac_volume = 0;
ac_edge_unit = -0.025; % Si perde sempre lo spread (Bid 49.975 o Ask 50.025 contro FV 50)
ac_expected_pnl = 0;

if portfolio_delta > 0
    ac_action = "Sell";
    ac_volume = min(round(portfolio_delta), ac_max_size);
    ac_expected_pnl = ac_edge_unit * ac_volume * contract_size;
elseif portfolio_delta < 0
    ac_action = "Buy";
    ac_volume = min(round(abs(portfolio_delta)), ac_max_size);
    ac_expected_pnl = ac_edge_unit * ac_volume * contract_size;
end

total_net_pnl = total_options_pnl + ac_expected_pnl;


% --- STAMPA DELLA TABELLA FINALE ---
disp(' ');
disp('========================================================================');
disp('                    BOOK DI TRADING (Compila la UI)                     ');
disp('========================================================================');
fprintf('%-10s | %-6s | %-6s | %-15s\n', 'ASSET', 'AZIONE', 'VOLUME', 'PnL ATTESO (x3k)');
disp('------------------------------------------------------------------------');

% Stampa la primissima riga (Il sottostante AC)
fprintf('%-10s | %-6s | %-6d | %-15.2f  <-- Hedging\n', 'AC', ac_action, ac_volume, ac_expected_pnl);
disp('------------------------------------------------------------------------');

% Stampa le 11 righe delle opzioni
for i = 1:num_options
    fprintf('%-10s | %-6s | %-6d | %-15.2f\n', names{i}, actions(i), volumes(i), expected_pnl(i));
end

disp('========================================================================');
disp('                         RIEPILOGO PORTAFOGLIO                          ');
disp('========================================================================');
fprintf('Delta Netto (prima dell''hedging) : %+.2f contratti\n', portfolio_delta);
fprintf('Guadagno Atteso (Opzioni)        : %.2f\n', total_options_pnl);
fprintf('Costo stimato per l''Hedging      : %.2f\n', ac_expected_pnl);
disp('------------------------------------------------------------------------');
fprintf('PROFITTO NETTO ATTESO (PnL Tot)  : %.2f\n', total_net_pnl);
disp('========================================================================');