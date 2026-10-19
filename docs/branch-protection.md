# Protecting master

**Status checked October 19, 2026:** GitHub reports `master` as unprotected and
the repository ruleset collection is empty. The ruleset in this checkout is
prepared for import; committing this file does not activate protection.

The connected GitHub tools support repository changes and ruleset reads, but
do not expose ruleset administration writes. The cloud CLI's request to
`api.github.com` is denied by the environment's network policy. No repository
settings were changed during this session.

## Activate the prepared ruleset

1. Open [Mimi's ruleset settings](https://github.com/zalkabsi/Mimi/settings/rules).
2. Choose **New ruleset → Import a ruleset** and select
   [`.github/rulesets/master.json`](../.github/rulesets/master.json). The submission
   bundle also includes a top-level `master-ruleset.json` copy.
3. Review the rules, keep enforcement **Active**, then click **Create**.
   If `Protect master` already exists, inspect and update it instead of importing
   a duplicate.
4. Open [the active repository rules](https://github.com/zalkabsi/Mimi/rules)
   and confirm the ruleset targets `master` and is active. PR #6's merge box
   should list the required checks. No destructive push is needed to verify it.

The ruleset blocks branch deletion and force pushes, requires a pull request,
requires resolved review conversations, and requires the branch to be current
with `master` and pass these GitHub Actions checks:

- `Backend tests (Python 3.12)`
- `Backend tests (Python 3.13)`
- `Frontend production build` (includes live/replay builds and browser checks)

All three check names and the GitHub Actions app ID (`15368`) were verified
against successful check runs for readiness PR #6. Keep the names in sync if
the CI job names or Python matrix change. There are no bypass actors. Required
approvals are zero so the solo owner can merge a passing PR without a second
reviewer. This still requires the pull request and passing checks.

An administrator can alternatively apply the JSON from an authenticated machine
with GitHub API access:

```sh
gh api --method POST repos/zalkabsi/Mimi/rulesets \
  --input .github/rulesets/master.json
gh api repos/zalkabsi/Mimi/rulesets \
  --jq '.[] | {name, enforcement, id}'
```

The API requires repository **Administration: write** permission. Run the POST
only once; it creates a ruleset. See GitHub's official
[import instructions](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/managing-rulesets-for-a-repository#importing-a-ruleset)
and [rules API reference](https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset).
