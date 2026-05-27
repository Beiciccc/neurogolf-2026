# submit30_20260527 Results

- UTC recorded: `2026-05-27T00:24:30Z`
- Submitted: `30`
- Status: `30 COMPLETE / 0 ERROR / 0 PENDING`
- Previous best public score: `6101.34`
- New best public score: `6101.39`
- Improvement: `+0.05`
- Best experiment: `iter5221-task376-submit30-20260527-01-over-iter5157`
- Best task: `task376.onnx`
- Best artifact: `runs/iter5221-task376-submit30-20260527-01-over-iter5157/submission.zip`

## Top Results

- `6101.39` `iter5221-task376-submit30-20260527-01-over-iter5157` `task376.onnx`
- `6101.34` `iter5225-task244-submit30-20260527-05-over-iter5157` `task244.onnx`
- `6101.34` `iter5226-task079-submit30-20260527-06-over-iter5157` `task079.onnx`
- `6101.34` `iter5227-task183-submit30-20260527-07-over-iter5157` `task183.onnx`
- `6101.34` `iter5228-task268-submit30-20260527-08-over-iter5157` `task268.onnx`
- `6101.34` `iter5229-task237-submit30-20260527-09-over-iter5157` `task237.onnx`
- `6101.34` `iter5230-task084-submit30-20260527-10-over-iter5157` `task084.onnx`
- `6101.34` `iter5231-task003-submit30-20260527-11-over-iter5157` `task003.onnx`
- `6101.34` `iter5234-task061-submit30-20260527-14-over-iter5157` `task061.onnx`
- `6101.33` `iter5233-task081-submit30-20260527-13-over-iter5157` `task081.onnx`

## Notes

- The winning move was adding the `task376` FP16/static candidate on top of the prior `task012` best.
- Several neutral candidates stayed at `6101.34`, which is useful evidence that they do not materially interact with the current best.
- `task190` regressed strongly to `6092.91`; keep it out of the next automatic queue unless a new clean-room version is built.
