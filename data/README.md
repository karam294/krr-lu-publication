# data/

`example.sql` is a tiny real sample of the course's Brunel case: 60 orders
(20 of them late, all from customer V555_15), 22 plant ports, 57 products per
plant, 30 freight rates. The pipeline loads it into `build/example.sqlite`
when `DB_URL` is not set.

YOUR TEAM: either replace `example.sql` with a small sample of your own
tables (then CI can map and validate it on every push), or set `DB_URL` in
`.env` to your database and keep a sample here for CI.
