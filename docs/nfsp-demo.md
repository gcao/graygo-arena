# Experimental NFSP play demo

URL on the ai host's LAN: http://10.0.4.130:5174/

Choose a 9x9 board and 200-turn limit. Set Black to human and White to
graygo_nfsp_experimental, model avg-9x9-diagnostic-32k. Click Create Game, then
Start. Clicking an empty intersection seals the human move immediately; the
board updates when both moves are ready. Pass Black submits a pass.

The checkpoint is an actual 9x9, 64-channel/eight-block NFSP average policy from
32,768 aggregate self-play records (228 Q updates, 58 supervised updates).
It is a short early-open hardware diagnostic, with unvalidated playing strength.
It is not a promoted champion or a completed development/confirmation run.

Source checkpoint:
 /home/gcao/proj/graygo/runs/nfsp-graph-cost-bbfd5e4/core/pipeline/early_open_diagnostic/checkpoints/resume/000000032768

Inference bundle:
 /home/gcao/proj/graygo-arena/.runtime/models/nfsp-average-9x9-32k-diagnostic.pt

Bundle SHA-256:
 cccf038dee07e6f235bfb5267c25782fee20a4e3ec3ee93f25e834f02f53fe45

The worker uses the training Python environment and its original compatible
source at .worktrees/frozen-cuda-c3b8b5f. It receives only complete public rule
state: board, player perspective, both restriction sets, the last two completed
pre-boards/moves, pass count and round limit. Backend legal moves remain
authoritative. Sampling includes PASS and does not override the opening.

The arena now shares the training engine's two-mutual-pass ending and
capture-before-suicide order. Its capture-derived restrictions and lack of
training-engine two-round ko still make it a variant demo rather than a strength
evaluation under the full training rules.

Validation: 105 backend tests pass, changed-interface strict typing passes, the
frontend builds, and an actual provider health request plus four human/model
turns complete with valid model responses and no fallback errors.

Runtime process metadata, logs, model and the separate demo SQLite database
are under .runtime/ and ignored by git. Backend listens on loopback port 8000;
frontend listens on port 5174 and proxies /api. This local-model demo starts
without paid-provider credentials. Existing training artifacts are untouched.
