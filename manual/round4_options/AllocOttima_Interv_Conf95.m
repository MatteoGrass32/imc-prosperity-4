clc; clear all; close all;

% =========================================================
%   ALLOCAZIONE OTTIMA + DELTA HEDGE
%   Basato sui risultati MC (50 run x 500k paths)
% =========================================================

% --- DATI DAL PRICER (IC al 95%) ---
names   = {'AC_50_P';'AC_50_C';'AC_35_P';'AC_40_P';'AC_45_P';'AC_60_C'; ...
           'AC_50_P_2';'AC_50_C_2';'AC_50_CO';'AC_40_BP';'AC_45_KO'};

theos   = [12.0268; 12.0272; 4.3361; 6.5097; 9.0890; 8.7920;
            9.8718;  9.8738; 21.9014; 4.7680; 0.2060];
ci_low  = [12.0249; 12.0176; 4.3340; 6.5074; 9.0867; 8.7829;
            9.8696;  9.8670; 21.8934; 4.7674; 0.2055];
ci_high = [12.0288; 12.0367; 4.3382; 6.5120; 9.0913; 8.8011;
            9.8739;  9.8805; 21.9094; 4.7686; 0.2064];

bids  = [12.00; 12.00; 4.33; 6.50; 9.05; 8.80; 9.70; 9.70; 22.20; 5.00; 0.150];
asks  = [12.05; 12.05; 4.35; 6.55; 9.10; 8.85; 9.75; 9.75; 22.30; 5.10; 0.175];
sizes = [50; 50; 50; 50; 50; 50; 50; 50; 50; 50; 500];

% --- CRITERI DI TRADING CON FILTRO IC ---
actions = strings(length(names), 1);
volumes = zeros(length(names), 1);
edges   = theos - (bids + asks) / 2;

for i = 1:length(names)
    if ci_low(i) > asks(i)
        actions(i) = "Buy";
        volumes(i) = sizes(i);
    elseif ci_high(i) < bids(i)
        actions(i) = "Sell";
        volumes(i) = sizes(i);
    else
        actions(i) = "Skip";
        volumes(i) = 0;
    end
end

% --- CALCOLO DELTA ---
S0 = 50; sigma = 2.51; r = 0;
days_per_year = 252; steps_per_day = 4;
dt = 1 / (days_per_year * steps_per_day);

bs_delta = @(S,K,T,sig,type) ...
    (strcmp(type,'call') *  normcdf((log(S/K)+(r+0.5*sig^2)*T)/(sig*sqrt(T))) + ...
     strcmp(type,'put')  * (normcdf((log(S/K)+(r+0.5*sig^2)*T)/(sig*sqrt(T))) - 1));

T3w = 3*5/days_per_year;
T2w = 2*5/days_per_year;
T1w = 1*5/days_per_year;

deltas = zeros(length(names), 1);
deltas(1)  = bs_delta(S0, 50, T3w, sigma, 'put');
deltas(2)  = bs_delta(S0, 50, T3w, sigma, 'call');
deltas(3)  = bs_delta(S0, 35, T3w, sigma, 'put');
deltas(4)  = bs_delta(S0, 40, T3w, sigma, 'put');
deltas(5)  = bs_delta(S0, 45, T3w, sigma, 'put');
deltas(6)  = bs_delta(S0, 60, T3w, sigma, 'call');
deltas(7)  = bs_delta(S0, 50, T2w, sigma, 'put');
deltas(8)  = bs_delta(S0, 50, T2w, sigma, 'call');

% Chooser: pesato per probabilità di scelta call/put a T2w
d1_chooser = (log(S0/50) + 0.5*sigma^2*T2w) / (sigma*sqrt(T2w));
p_call = normcdf(d1_chooser);
p_put  = 1 - p_call;
deltas(9) = p_call * bs_delta(S0,50,T1w,sigma,'call') + ...
            p_put  * bs_delta(S0,50,T1w,sigma,'put');

% Binary Put: formula analitica
d2_bp = (log(S0/40) + (r-0.5*sigma^2)*T3w) / (sigma*sqrt(T3w));
deltas(10) = -normpdf(d2_bp) / (S0 * sigma * sqrt(T3w)) * 10;

% KO Put: MC veloce con differenze finite
paths_delta = 50000;
dS = 0.1;
Z_d   = randn(60, paths_delta);
ret_d = exp((r-0.5*sigma^2)*dt + sigma*sqrt(dt)*Z_d);
Su = [(S0+dS)*ones(1,paths_delta); (S0+dS)*cumprod(ret_d,1)];
Sd = [(S0-dS)*ones(1,paths_delta); (S0-dS)*cumprod(ret_d,1)];
surv_u = min(Su,[],1) > 35;
surv_d = min(Sd,[],1) > 35;
deltas(11) = mean(surv_u.*max(45-Su(end,:),0) - surv_d.*max(45-Sd(end,:),0)) / (2*dS);

% --- AGGREGAZIONE DELTA PORTAFOGLIO ---
portfolio_delta = 0;
for i = 1:length(names)
    if actions(i) == "Buy"
        portfolio_delta = portfolio_delta + deltas(i) * volumes(i);
    elseif actions(i) == "Sell"
        portfolio_delta = portfolio_delta - deltas(i) * volumes(i);
    end
end

% --- HEDGE SUL SOTTOSTANTE AC ---
ac_bid = 49.975; ac_ask = 50.025;
ac_max_size   = 200;
contract_size = 3000;

if portfolio_delta > 0.5
    ac_action = "Sell";
    ac_volume = min(round(portfolio_delta), ac_max_size);
elseif portfolio_delta < -0.5
    ac_action = "Buy";
    ac_volume = min(round(abs(portfolio_delta)), ac_max_size);
else
    ac_action = "Skip";
    ac_volume = 0;
end

% --- STIMA PNL ---
expected_pnl = 0;
for i = 1:length(names)
    if actions(i) == "Buy"
        expected_pnl = expected_pnl + (theos(i) - asks(i)) * volumes(i) * contract_size;
    elseif actions(i) == "Sell"
        expected_pnl = expected_pnl + (bids(i) - theos(i)) * volumes(i) * contract_size;
    end
end

ac_spread_cost      = (ac_ask - ac_bid) / 2 * ac_volume * contract_size;
expected_pnl_hedged = expected_pnl - ac_spread_cost;

% --- STAMPA ---
sep  = repmat('=',1,88);
sep2 = repmat('-',1,88);

fprintf('\n%s\n', sep);
fprintf('  ALLOCAZIONE OTTIMA  |  Filtro: CI 95%%  |  Contract size: %d\n', contract_size);
fprintf('%s\n', sep);
fprintf('%-12s | %-6s | %-6s | %-5s | %7s | %7s | %8s | %s\n', ...
        'ASSET','BID','ASK','ACTION','VOLUME','DELTA','EDGE','SIG?');
fprintf('%s\n', sep2);

for i = 1:length(names)
    mid_i = (bids(i) + asks(i)) / 2;
    sig   = '    ';
    if mid_i < ci_low(i) || mid_i > ci_high(i)
        sig = '***';
    end
    fprintf('%-12s | %6.4f | %6.4f | %-5s | %7d | %7.4f | %+8.4f | %s\n', ...
            names{i}, bids(i), asks(i), actions(i), volumes(i), deltas(i), edges(i), sig);
end

fprintf('%s\n', sep2);
fprintf('%-12s | %6s | %6s | %-5s | %7d |   (delta hedge)\n', ...
        'AC', num2str(ac_bid), num2str(ac_ask), ac_action, ac_volume);
fprintf('%s\n', sep);
fprintf('  Portfolio delta (pre-hedge)  : %+.4f\n', portfolio_delta);
fprintf('  Hedge AC                     : %s %d contracts\n', ac_action, ac_volume);
fprintf('%s\n', sep2);
fprintf('  Expected PnL (pre-hedge)     : %+.2f XIRECs\n', expected_pnl);
fprintf('  Spread cost hedge AC         : -%.2f XIRECs\n', ac_spread_cost);
fprintf('  Expected PnL (post-hedge)    : %+.2f XIRECs\n', expected_pnl_hedged);
fprintf('%s\n', sep);