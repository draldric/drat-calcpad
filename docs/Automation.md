# Repository automation

## Hosted verification

The `Repository verification` GitHub Actions workflow runs on pull requests targeting `develop` or `main`, pushes to those branches, and manual dispatches.
Its stable required-check job is `Windows static and distribution verification`.

The hosted Windows job checks out the complete history, verifies changed-file whitespace, and runs:

```powershell
pwsh -NoProfile -File Tools/VerifyRepository.ps1 -SkipCalcPad
```

This covers:

- generated-Core freshness;
- Core and component API declarations;
- direct, relative, exact-case include paths;
- example, test, and template conventions;
- unresolved template placeholders outside `Templates/`;
- public API, orphan-helper, documentation, and macro-namespace audits;
- Core API documentation values;
- distribution build, installation, update, integrity, and portable-project checks; and
- the workflow's own hosted-verification contract.

Repository branch protection can require `Repository verification / Windows static and distribution verification` before merging into `develop` or `main`.
The job rejects a checkout that is dirty before verification or becomes dirty during verification, so its distribution result is tied to the exact clean commit under review.

## CalcPad qualification boundary

GitHub-hosted verification does not install or execute CalcPad CE.
The `-SkipCalcPad` switch is intentional and must remain visible in the workflow and its job summary.

Before merging calculation, rendering, stylesheet, plotting, template, or release changes, run the full verifier on a Windows machine with CalcPad CE installed:

```powershell
pwsh -NoProfile -File Tools/VerifyRepository.ps1
```

The full verifier generates the maintained tests, examples, and general template and checks rendered `all_tests` results.
Manual CalcPad CE GUI review remains required where screen layout, print preview, PDF pagination, browser JavaScript, or Plotly rendering is affected.

A future self-hosted Windows runner may execute the full verifier only after its CalcPad CE installation, version, network requirements, security controls, and maintenance ownership are documented and verified.
Until then, pull requests and release records must state who performed the CalcPad qualification and which version was used.

## Updating workflow dependencies

Third-party actions are pinned to immutable commit SHAs.
When updating an action, confirm the release in its official repository, replace the SHA and adjacent version comment together, and rerun the hosted workflow.
