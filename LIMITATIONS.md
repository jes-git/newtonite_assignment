# Known limitations

This solution is intentionally scoped to the challenge and is not a full production enterprise platform.

- Team-based authorization is used rather than a deeper multi-role enterprise permission system.
- The app is built around SQLite for simplicity and fast local execution.
- Search and filtering are basic and suitable for a reviewable operational queue.
- Background/secondary processing is simplified and not designed as a full distributed job runner.
- The browser UI is functional and minimal rather than a polished enterprise dashboard.

These trade-offs keep the project simple, testable, and easy to evaluate while still demonstrating the important engineering decisions around reliability and correctness.
