"""In Case of — deterministic domain core.

This package owns safety state. It has no AWS imports, no model imports, and no I/O:
everything here is a pure function of its inputs plus an injected clock. That is what
makes the safety properties testable, and what keeps them true when the model is down
and when the phone is off.

`docs/PRODUCT-STATES.md` is normative for the Alert lifecycle. `test_doc_parity.py`
asserts this package agrees with it.
"""
