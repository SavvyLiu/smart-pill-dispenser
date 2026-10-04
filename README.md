# Smart Pill Dispenser

Code and engineering change tracking for our smart pill dispenser project.

## Working pattern

1. Open an issue describing the problem or proposed change, why it matters, who owns it, affected artifacts, and acceptance checks.
2. Record the decision in issue comments: accepted, deferred, or rejected, with a short reason.
3. Link the implementation and evidence: a pull request, design revision, or physical build-log entry.
4. Review the result, run the relevant checks, and record the outcome before closing the issue.

Use `software`, `electronics`, or `mechanical` to identify the area. Use `bug`, `change`, or `experiment` to identify the work. Add `safety` or `interface` when relevant.

Issues marked `example` show the pattern. They are placeholders, not assigned work or evidence of completed tests.

- [Software change: add schedule tests](https://github.com/SavvyLiu/smart-pill-dispenser/issues/1)
- [Physical change: record a chute adjustment](https://github.com/SavvyLiu/smart-pill-dispenser/issues/2)
- [Experiment: compare chute configurations](https://github.com/SavvyLiu/smart-pill-dispenser/issues/3)

## Software

Work on a branch and open a pull request linked to the issue. Explain what changed and include relevant test results. Pass applicable CI checks and obtain approval from at least one member other than the author who can assess the work. CI and branch protection are not configured yet.

## Physical work and CAD

Use a dated build-log entry linked from the issue. Record the author, starting configuration, modification, useful photos or measurements, and observed results. Group small adjustments from one exploratory session.

If CAD is used, link the exact design version used for the build. Record direct physical modifications even without CAD, including any differences from existing drawings. Test evidence should identify the physical configuration and software commit tested.

## Experiments

Use `experiment` and record the question, starting configuration, method, and outcome. A useful experiment result still needs review and verification before it becomes an adopted change. Close trials that produce no retained change as **not planned**, keeping their results available.

## Suggested issue body

```text
Problem / proposed change:
Reason:
Owner: unassigned until agreed
Affected artifacts / starting configuration:
Acceptance checks:
Evidence: PR, design version, build-log entry, or test results
Decision / review: recorded in comments
```

## Suggested build-log entry

```text
Date / author / issue:
Starting configuration:
Modification or experiment:
Photos / measurements / design-version links:
Checks and observed results:
Disposition: retained, revised, or abandoned
```

## Repository scope

Keep code and engineering records here. Keep course materials, assignment reports, and submission files outside this repository. Use a separate code checkout; the local `C:\Code\Capstone` folder contains course documents and should not be pushed here.
