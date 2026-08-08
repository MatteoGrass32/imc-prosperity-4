clc
clear all
close all
% --- PARAMETRI INIZIALI ---
S0 = 50;            
sigma = 2.51;       
r = 0;              

% --- IMPOSTAZIONI MONTE CARLO ---
num_runs = 1000;                % Numero di iterazioni su cui fare la media
paths_per_run = 1000000;      % Path per singola iterazione
half_paths = paths_per_run / 2; % Per le variabili antitetiche

% --- GESTIONE DEL TEMPO DISCRETO ---
days_per_year = 252;
steps_per_day = 4;
dt = 1 / (days_per_year * steps_per_day); 

steps_T14 = 2 * 5 * steps_per_day; % 40 step totali
steps_T21 = 3 * 5 * steps_per_day; % 60 step totali

% Inizializzazione vettori per salvare i risultati intermedi
res_50_P = zeros(num_runs, 1);  res_50_C = zeros(num_runs, 1);
res_35_P = zeros(num_runs, 1);  res_40_P = zeros(num_runs, 1);
res_45_P = zeros(num_runs, 1);  res_60_C = zeros(num_runs, 1);
res_50_P_2 = zeros(num_runs, 1); res_50_C_2 = zeros(num_runs, 1);
res_50_CO = zeros(num_runs, 1);  res_40_BP = zeros(num_runs, 1);
res_45_KO = zeros(num_runs, 1);

disp(['Avvio Monte Carlo: ' num2str(num_runs) ' iterazioni da ' num2str(paths_per_run/1000000) 'M di paths...']);

% --- CICLO DI SIMULAZIONI ---
for i = 1:num_runs
    fprintf('Calcolo iterazione %d di %d...\n', i, num_runs);
    
    % Generazione Variabili Antitetiche: metà normali, metà speculari
    Z_half = randn(steps_T21, half_paths);
    Z = [Z_half, -Z_half]; 
    
    returns = exp(-0.5 * sigma^2 * dt + sigma * sqrt(dt) * Z);
    
    S = zeros(steps_T21 + 1, paths_per_run);
    S(1, :) = S0;
    S(2:end, :) = S0 * cumprod(returns, 1);
    
    S_T14 = S(steps_T14 + 1, :);
    S_T21 = S(steps_T21 + 1, :);
    
    % Pricing
    res_50_P(i)   = mean(max(50 - S_T21, 0));
    res_50_C(i)   = mean(max(S_T21 - 50, 0));
    res_35_P(i)   = mean(max(35 - S_T21, 0));
    res_40_P(i)   = mean(max(40 - S_T21, 0));
    res_45_P(i)   = mean(max(45 - S_T21, 0));
    res_60_C(i)   = mean(max(S_T21 - 60, 0));
    res_50_P_2(i) = mean(max(50 - S_T14, 0));
    res_50_C_2(i) = mean(max(S_T14 - 50, 0));
    
    % Esotiche
    is_call = S_T14 > 50;
    is_put = S_T14 <= 50;
    payoff_chooser = is_call .* max(S_T21 - 50, 0) + is_put .* max(50 - S_T21, 0);
    res_50_CO(i) = mean(payoff_chooser);
    
    res_40_BP(i) = mean((S_T21 < 40) * 10);
    
    min_S = min(S, [], 1); 
    survived = min_S > 35; 
    res_45_KO(i) = mean(survived .* max(45 - S_T21, 0));
end

% --- MEDIA FINALE SULLE ITERAZIONI ---
AC_50_P   = mean(res_50_P);
AC_50_C   = mean(res_50_C);
AC_35_P   = mean(res_35_P);
AC_40_P   = mean(res_40_P);
AC_45_P   = mean(res_45_P);
AC_60_C   = mean(res_60_C);
AC_50_P_2 = mean(res_50_P_2);
AC_50_C_2 = mean(res_50_C_2);
AC_50_CO  = mean(res_50_CO);
AC_40_BP  = mean(res_40_BP);
AC_45_KO  = mean(res_45_KO);

% --- DATI DI MERCATO (DAGLI SCREENSHOT) ---
mid_50_P   = (12 + 12.05) / 2;
mid_50_C   = (12 + 12.05) / 2;
mid_35_P   = (4.33 + 4.35) / 2;
mid_40_P   = (6.5 + 6.55) / 2;
mid_45_P   = (9.05 + 9.1) / 2;
mid_60_C   = (8.8 + 8.85) / 2;
mid_50_P_2 = (9.7 + 9.75) / 2;
mid_50_C_2 = (9.7 + 9.75) / 2;
mid_50_CO  = (22.2 + 22.3) / 2;
mid_40_BP  = (5 + 5.1) / 2;
mid_45_KO  = (0.15 + 0.175) / 2;

% --- STAMPA RISULTATI ---
disp(' ');
fprintf('%-10s | %-8s | %-8s | %-8s\n', 'ASSET', 'THEO', 'MKT MID', 'EDGE');
disp('---------------------------------------------');
fprintf('%-10s | %8.4f | %8.4f | %8.4f\n', 'AC_50_P', AC_50_P, mid_50_P, AC_50_P - mid_50_P);
fprintf('%-10s | %8.4f | %8.4f | %8.4f\n', 'AC_50_C', AC_50_C, mid_50_C, AC_50_C - mid_50_C);
fprintf('%-10s | %8.4f | %8.4f | %8.4f\n', 'AC_35_P', AC_35_P, mid_35_P, AC_35_P - mid_35_P);
fprintf('%-10s | %8.4f | %8.4f | %8.4f\n', 'AC_40_P', AC_40_P, mid_40_P, AC_40_P - mid_40_P);
fprintf('%-10s | %8.4f | %8.4f | %8.4f\n', 'AC_45_P', AC_45_P, mid_45_P, AC_45_P - mid_45_P);
fprintf('%-10s | %8.4f | %8.4f | %8.4f\n', 'AC_60_C', AC_60_C, mid_60_C, AC_60_C - mid_60_C);
disp('---------------------------------------------');
fprintf('%-10s | %8.4f | %8.4f | %8.4f\n', 'AC_50_P_2', AC_50_P_2, mid_50_P_2, AC_50_P_2 - mid_50_P_2);
fprintf('%-10s | %8.4f | %8.4f | %8.4f\n', 'AC_50_C_2', AC_50_C_2, mid_50_C_2, AC_50_C_2 - mid_50_C_2);
disp('---------------------------------------------');
fprintf('%-10s | %8.4f | %8.4f | %8.4f\n', 'AC_50_CO', AC_50_CO, mid_50_CO, AC_50_CO - mid_50_CO);
fprintf('%-10s | %8.4f | %8.4f | %8.4f\n', 'AC_40_BP', AC_40_BP, mid_40_BP, AC_40_BP - mid_40_BP);
fprintf('%-10s | %8.4f | %8.4f | %8.4f\n', 'AC_45_KO', AC_45_KO, mid_45_KO, AC_45_KO - mid_45_KO);
disp(' ');