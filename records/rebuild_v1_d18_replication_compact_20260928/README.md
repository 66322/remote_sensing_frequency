# D18 seed17 matched replication: compact cross-computer evidence

Status: **COMPLETE**. Executed commit: `b66a9017129b0d6adc45c71cc6e9ca042548fc0b`.
Training seed17 uses the original frozen DINO P0/P1/P2 protocol. Seed42 summaries are preserved unchanged.
The evaluator uses seed42 corruption keys for both training seeds. Historical R01 fallback stays separate from same-seed P0 fallback.

## Archived files

- `status.tsv`: b04856cf5c24b937d96a041ee11e3404be839c2322af372c1d8acc4f5d109e5e
- `planned_jobs.json`: a831d3fefed79ca5c7758f02c1cbd29a28e51361665298bc801490f61a88ad92
- `decision.json`: e0ceefc5d171453467dd0caff4addf8dd950fde8ddb6951f7b41c7031783a6a7
- `server_P0_seed42_summary.json`: 9918c7a8b662ab2959461d7a200706edd91053e0abbb10f33bc8ca4917c1e115
- `server_P1_seed42_summary.json`: b930d9b5292a6af72bc7df08a1f296bb09c8d284b8966392931e1fd3a5ccbd09
- `server_P2_seed42_summary.json`: 931a438da5c9b9d544d536f7077a2b92601331c073ed70611416ca533e0c0bf2
- `server_P0_seed17_summary.json`: 4d88a830c6cada43232ef4c408cf5bcd0d82944ff70e02f5ccfabd1abef58430
- `server_P1_seed17_summary.json`: 30649efc635efcd025e80ab0aa41b5bd0cb139730a79312ce0d61395b50cc9d1
- `server_P2_seed17_summary.json`: 53fbc29db5bc034a30e84e9d35eb6edc3a1279245b03ecfb3f0483c436d26d2d

## Missing files

- None

Large predictions, data, checkpoints and full logs remain on the server. Their locations and hashes are in `manifest.json`.
Use `decision.json` plus all six arm summaries to inspect gates, paired errors, class/tile counts and absence cost.
