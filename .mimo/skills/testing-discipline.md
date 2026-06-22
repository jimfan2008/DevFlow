---
name: testing-discipline
description: Reminds the agent to run the test suite after every change.
triggers: [test, vitest, jest, pytest]
always: false
---

When the user changes source code, always:

1. Run the relevant test suite.
2. Surface the actual command and its output (truncated if long).
3. If tests fail, *do not* mark the task complete — fix or report the failure.
