# Sample report (bundled demo case)

**This is an already-public vulnerability** (CVE-2021-44906), used only as a
bundled demo input. It is not a private or unpatched report.

Package: minimist 1.2.5

## Report

There is a prototype pollution vulnerability in minimist 1.2.5. A crafted
argument whose key path walks through the parsed `_` array and the
`constructor` chain makes `parse()` assign onto a built-in prototype.

PoC:

```js
const minimist = require('minimist');
minimist(['--_.constructor.constructor.prototype.polluted', 'yes']);
console.log((function () {}).polluted);
```

Expected effect: `Function.prototype` gains `polluted === "yes"` after parsing
the crafted argv, so every function inherits it. Affects versions before the
fix published in 1.2.6.
