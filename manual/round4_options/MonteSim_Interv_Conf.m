clc
clear all
close all

clc; clear all; close all;

% --- PARAMETRI ---
S0 = 50; sigma = 2.51; r = 0;

% --- MONTE CARLO ---
num_runs      = 50;          % ridotto: 50 run da 500k paths sono sufficienti
paths_per_run = 500000;
half_paths    = paths_per_run / 2;
conf_level    = 0.90;
z_crit        = norminv(1 - (1 - conf_level)/2);  % 1.96

% --- TEMPO DISCRETO ---
days_per_year = 252; steps_per_day = 4;
dt            = 1 / (days_per_year * steps_per_day);
steps_T14     = 2 * 5 * steps_per_day;   % 40
steps_T21     = 3 * 5 * steps_per_day;   % 60
T_remain      = 1 * 5 / days_per_year;   % 1 settimana rimasta dopo la scelta (chooser)

% --- PREZZI DI MERCATO (MID) ---
mid_50_P   = (12    + 12.05) / 2;
mid_50_C   = (12    + 12.05) / 2;
mid_35_P   = (4.33  + 4.35)  / 2;
mid_40_P   = (6.5   + 6.55)  / 2;
mid_45_P   = (9.05  + 9.1)   / 2;
mid_60_C   = (8.8   + 8.85)  / 2;
mid_50_P_2 = (9.7   + 9.75)  / 2;
mid_50_C_2 = (9.7   + 9.75)  / 2;
mid_50_CO  = (22.2  + 22.3)  / 2;
mid_40_BP  = (5     + 5.1)   / 2;
mid_45_KO  = (0.15  + 0.175) / 2;

% --- INIZIALIZZAZIONE ---
res_50_P   = zeros(num_runs,1); res_50_C   = zeros(num_runs,1);
res_35_P   = zeros(num_runs,1); res_40_P   = zeros(num_runs,1);
res_45_P   = zeros(num_runs,1); res_60_C   = zeros(num_runs,1);
res_50_P_2 = zeros(num_runs,1); res_50_C_2 = zeros(num_runs,1);
res_50_CO  = zeros(num_runs,1); res_40_BP  = zeros(num_runs,1);
res_45_KO  = zeros(num_runs,1);

fprintf('Avvio MC: %d run x %dk paths...\n', num_runs, paths_per_run/1000);

% --- LOOP ---
for i = 1:num_runs
    % Variabili antitetiche
    Z_half = randn(steps_T21, half_paths);
    Z      = [Z_half, -Z_half];

    returns = exp((r - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z);

    S      = [S0 * ones(1, paths_per_run); S0 * cumprod(returns, 1)];
    S_T14  = S(steps_T14 + 1, :);
    S_T21  = S(steps_T21 + 1, :);

    % --- Vanilla ---
    res_50_P(i)   = mean(max(50 - S_T21, 0));
    res_50_C(i)   = mean(max(S_T21 - 50, 0));
    res_35_P(i)   = mean(max(35 - S_T21, 0));
    res_40_P(i)   = mean(max(40 - S_T21, 0));
    res_45_P(i)   = mean(max(45 - S_T21, 0));
    res_60_C(i)   = mean(max(S_T21 - 60, 0));
    res_50_P_2(i) = mean(max(50 - S_T14, 0));
    res_50_C_2(i) = mean(max(S_T14 - 50, 0));

    % --- Chooser (FIX) ---
    % A T14 il holder sceglie max(valore_call_residua, valore_put_residua)
    % entrambe con 1 settimana rimasta → usiamo BS vettorializzato
    d1 = (log(S_T14/50) + 0.5*sigma^2 * T_remain) / (sigma * sqrt(T_remain));
    d2 = d1 - sigma * sqrt(T_remain);
    call_val = S_T14 .* normcdf(d1) - 50 * normcdf(d2);
    put_val  = 50 * normcdf(-d2) - S_T14 .* normcdf(-d1);
    res_50_CO(i) = mean(max(call_val, put_val));

    % --- Binary Put ---
    res_40_BP(i) = mean((S_T21 < 40) * 10);

    % --- Knock-Out Put (monitoring su tutti gli step) ---
    min_S        = min(S, [], 1);
    survived     = min_S > 35;
    res_45_KO(i) = mean(survived .* max(45 - S_T21, 0));
end

% --- MEDIA E INTERVALLI DI CONFIDENZA ---
function [mu, lo, hi] = ci(data, z)
    mu = mean(data);
    se = std(data) / sqrt(length(data));
    lo = mu - z * se;
    hi = mu + z * se;
end

names    = {'AC_50_P','AC_50_C','AC_35_P','AC_40_P','AC_45_P','AC_60_C', ...
            'AC_50_P_2','AC_50_C_2','AC_50_CO','AC_40_BP','AC_45_KO'};
all_res  = {res_50_P, res_50_C, res_35_P, res_40_P, res_45_P, res_60_C, ...
            res_50_P_2, res_50_C_2, res_50_CO, res_40_BP, res_45_KO};
mids     = [mid_50_P, mid_50_C, mid_35_P, mid_40_P, mid_45_P, mid_60_C, ...
            mid_50_P_2, mid_50_C_2, mid_50_CO, mid_40_BP, mid_45_KO];

% sostituisci l'header e il fprintf con questi:

fprintf('\n%-12s | %8s | %8s | %8s | %8s | %20s | %8s\n', ...
        'ASSET', 'THEO', 'MKT MID', 'CI LOW', 'CI HIGH', '95% CI', 'EDGE');
disp(repmat('-', 1, 90));

for k = 1:numel(names)
    [mu, lo, hi] = ci(all_res{k}, z_crit);
    edge = mu - mids(k);
    if     edge >  0.03, action = 'BUY  ↑';
    elseif edge < -0.03, action = 'SELL ↓';
    else,                action = 'SKIP ~'; end

    fprintf('%-12s | %8.4f | %8.4f | %8.4f | %8.4f | [%7.4f, %7.4f] | %+7.4f  %s\n', ...
            names{k}, mu, mids(k), lo, hi, lo, hi, edge, action);
end