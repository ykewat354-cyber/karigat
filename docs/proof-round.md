# Local release-candidate proof: 0.2.1rc3

All new candidates in this round used the explicitly selected ChatGPT subscription route through OpenCode. No hand edits to candidate files. Local checks ran on Termux; these results apply to the tested artifacts, not all future generations.

| Exercise | Independent observation |
| --- | --- |
| Fresh bookmarks service | Started a clean copy with the README command and an available loopback port. Empty list on startup, saved an HTTPS URL, received 400 for a file URL, restarted the server, and read back exactly the saved URL. Chromium submitted and displayed a link, then reloaded and displayed it again (5 steps). No horizontal overflow at 320, 360, 390 or 768 px. |
| SQLite returns ledger | First candidate passed the existing ledger grader: partial and full refund amounts, unchanged zero-refund sale, replay after completion and rejection of unknown receipts, excessive and nonpositive quantities. |
| Offline 3D exhibit | First candidate failed the heading check. One generated repair passed mesh grading and the painted-view check. A separate browser replay observed motion, stable pixels after Pause, a changed view on drag and a repeatable change on Reset. This does not measure the exact camera angle. |
| Data pilot | Stock JSON, sorted CSV and compass SVG passed all three existing checks. The SVG check validates the root, not the compass design. The earlier OpenRouter pilots scored 2/3 each; a different route prevents attributing the difference to calibration. |
| Saved habit tracker | Replayed the existing candidate, targeting the newly created habit. All eight steps passed, including checked state after reload. Not a new generation. |
| Harness regressions | 20 offline tests passed. |

Generation, syntax and file-existence checks alone did not establish the service result. The API, restart, visual and interaction checks above were run separately. This is evidence for local pilot use. There was no public deployment, load test, free-route reliability measurement or matched Claude benchmark in this round.
