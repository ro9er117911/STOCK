# Source Registry

This file is the operator-facing view of the event whitelist. Runtime polling is driven by `source_registry.json`.

## PLTR

- `sec` (`sec`, `active`) priority 10: https://data.sec.gov/submissions/CIK0001321655.json
- `price` (`price`, `active`) priority 20: https://query1.finance.yahoo.com/v8/finance/chart/PLTR?range=1mo&interval=1d
- `investor_news` (`html`, `active`) priority 30: https://investors.palantir.com/news-events/news-releases/

## MSFT

- `sec` (`sec`, `active`) priority 10: https://data.sec.gov/submissions/CIK0000789019.json
- `price` (`price`, `active`) priority 20: https://query1.finance.yahoo.com/v8/finance/chart/MSFT?range=1mo&interval=1d
- `investor_news` (`rss`, `active`) priority 30: https://news.microsoft.com/feed/

## MAR

- `sec` (`sec`, `active`) priority 10: https://data.sec.gov/submissions/CIK0001048286.json
- `price` (`price`, `active`) priority 20: https://query1.finance.yahoo.com/v8/finance/chart/MAR?range=1mo&interval=1d
- `investor_news` (`html`, `active`) priority 30: https://news.marriott.com/news/
