# Protecting master

**Verified October 19, 2026:** GitHub reports `master` as protected. The owner
activated [Protect master, ruleset 25390422](https://github.com/zalkabsi/Mimi/rules/25390422).
The GitHub API confirms active enforcement, the exact target
`refs/heads/master`, all four rule types below, and an empty bypass list.
This connection's `current_user_can_bypass` value is `never`.

The prepared JSON matches the active rules. Committing the JSON alone does
not activate protection; activation was independently verified through GitHub's
branch and ruleset responses. No destructive push was used to verify it.

## Maintain or recreate the ruleset

1. Open [Mimi's ruleset settings](https://github.com/zalkabsi/Mimi/settings/rules)
   and inspect the existing **Protect master** ruleset. Update it there if needed.
2. Only if the ruleset is missing, choose **New ruleset → Import a ruleset** and select
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
against the active ruleset and successful check runs for readiness PR #6. Keep the names in sync if
the CI job names or Python matrix change. There are no bypass actors. Required
approvals are zero so the solo owner can merge a passing PR without a second
reviewer. This still requires the pull request and passing checks.

If recreating a missing ruleset, an administrator can alternatively apply the
JSON from an authenticated machine with GitHub API access:

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
