# Sample report (bundled demo case)

**This is an already-public vulnerability** (CVE-2021-44906), used only as a
bundled demo input. It is not a private or unpatched report.

Package: minimist 1.2.5

## Report

There is a prototype pollution vulnerability in minimist 1.2.5. Passing
crafted arguments through `parse()` allows an attacker to pollute
`Object.prototype` with attacker-controlled properties.

PoC:

```js
const minimist = require('minimist');
minimist(['--__proto__.polluted', 'yes']);
console.log({}.polluted);
```

Expected effect: `{}` inherits `polluted === "yes"` after parsing the crafted
argv. Affects versions before the fix published in 1.2.6.
