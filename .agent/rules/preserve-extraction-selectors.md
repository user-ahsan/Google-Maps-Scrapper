---
trigger: always_on
glob: perserv
description: preserver
**DO NOT check or modify XPath or CSS selectors** (e.g., `h1.DUwDvf`, `span[role="img"]`, `div[role="feed"]`) unless you have explicit confirmation that Google's DOM has changed.

- **Why**: These selectors are fragile and specific to the current DOM layout. "Cleaning" them often breaks extraction.
- **Action**: If you suspect a selector is broken, verify it with a dry-run test before committing changes.
---
