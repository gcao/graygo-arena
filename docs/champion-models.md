# Historical and loop champions

The arena at http://10.0.4.130:5174/ exposes three separate local model choices:

- graygo_nfsp_experimental / avg-9x9-diagnostic-32k: the existing short-trained average policy.
- graygo_old_champion / v6-0081-raw-policy: a frozen strict-loading copy of the old 12-block/128-filter checkpoint. It samples its raw six-plane policy including PASS; MCTS is disabled.
- graygo_loop_champion / latest: the atomic champion release produced by the new persistent learner controller. A revision is frozen on the first request for a game, so new releases affect new games only.

The loop slot is currently bootstrapped to the old 0081 checkpoint. It does not imply a newly trained or promoted model. Checkpoint SHA-256 is recorded in model responses. Both seats retain private sampling and transcripts; sharing immutable model weights does not share private state.

Runtime configuration uses GRAYGO_OLD_MODEL_REPO, GRAYGO_OLD_MODEL_PATH and GRAYGO_LOOP_MANIFEST. The existing NFSP source/interpreter configuration remains independent. Models, database, logs and pointers are stored under .runtime/ and ignored by git.

The loop manifest uses body.version graygo/champion-release/1 and a canonical SHA-256. Payload checksums are verified before use. Loop candidates use the complete 30+14 input representation; historical checkpoints use their original six-plane representation. They are separate policies, not partially loaded versions of one another.

Use a 9x9 board and 200-turn limit, Black human, White the desired provider, Create Game, Start, and click a legal empty point. Arena rules remain its existing variant; these informal games do not constitute training-engine validation or protected-promotion evidence.
