# Experimental file-owner teams

`--team` asks a coordinator to define a shared interface and assign disjoint files to one or two workers. Workers run concurrently on the selected hosted route. For a single-file assignment the harness supplies the destination; the worker returns only content. A single trusted writer materializes the assembled files. The existing frozen checks govern acceptance and a single integrated repair. This is bounded delegation, not a persistent background team. Worker calls are not individually checkpointed.

## Development calibration

Two data tasks with frozen checks were repeated with the same ChatGPT model, alternating arm order. No candidate files were manually edited. Both arms could use one repair, but the team could make more model calls. Elapsed time includes orchestration and verification. Cost and token counts were not measured.

| Iteration | Single | Team | Main observation |
| --- | --- | --- | --- |
| Initial | 2/2 | 0/2 | Out-of-assignment files; SQL seed data collided with the evaluator. |
| Clarify worker role | 2/2 | 0/2 | Prompt alone did not enforce scope. |
| Harness owns single-file destination | 2/2 | 1/2 | Schema and summary passed; inventory still hit an ownership violation. |
| Separate coordinator brief and split two-file requests | 1/2 | 2/2 | Team times: inventory 10.4 s, SQL 11.1 s. Single: 6.5 s and 19.6 s. |

**Transfer:** after the last change, both arms built an offline podcast timecode converter from the same prompt. Chromium tested `2:10:11 → 7811` and `2:61:10 → Invalid timecode` plus four viewport widths. Team passed with its first candidate in 23.8 s; single needed a layout repair and passed in 55.3 s. One paired observation cannot establish a latency advantage.

The development tasks are not held out. Earlier single-arm runs passed both; the SQL check can also reject legitimate seeded tables. Keep team mode opt-in. Before promotion, use unseen repositories, the same model and aggregate compute limits in each arm, record blocked runs and actual usage, and report per-task differences. None of the twenty external harnesses has been beaten in a matched trial here.
