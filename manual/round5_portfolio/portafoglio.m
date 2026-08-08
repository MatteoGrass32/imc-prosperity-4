clear all
close all

budget = 1e6;

% fee su percentuale (es. 25 per 25%), non su XIRECs assoluti
fee = @(pct) (pct / 100).^2 * budget;

% [Lava cake, Pyroflex, Volcanic, Ashes, Scoria, Magma, Obsidian, Sulfur, Thermalite]
pct       = [20;  9;   7;   2;  13;  17;   5;  19;   8];  % % budget
buy_sell  = [-1; -1;  +1;  +1;  +1;  -1;  -1;  +1;  +1];  % +1=BUY, -1=SELL
gainings  = [-0.6335; -0.1953; -0.1457; -0.035; 0.0133; 0.0223; 0.0992; 0.1742; 0.2216];

investment = pct / 100 * budget;
FEE        = fee(pct);
GROSS      = investment .* gainings .* buy_sell;
PNL_net    = GROSS - FEE;

% Output tabellare
names = ["Lava cake"; "Pyroflex cells"; "Volcanic incense"; "Ashes of Phoenix"; ...
         "Scoria paste"; "Magma ink"; "Obsidian cutlery"; "Sulfur reactor"; "Thermalite core"];

fprintf('\n%-20s  %5s  %10s  %10s  %12s\n', 'Asset','Pct%','Investment','Fee','Net PnL');
fprintf('%s\n', repmat('-',1,65));
for i = 1:length(pct)
    fprintf('%-20s  %4d%%  %10.0f  %10.0f  %+12.0f\n', ...
        names(i), pct(i), investment(i), FEE(i), PNL_net(i));
end
fprintf('%s\n', repmat('-',1,65));
fprintf('%-20s  %4d%%  %10.0f  %10.0f  %+12.0f\n', ...
    'TOTAL', sum(pct), sum(investment), sum(FEE), sum(PNL_net));