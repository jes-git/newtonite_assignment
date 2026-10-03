# Engineering Decisions

## 1) SQLite for the first usable version

We chose SQLite instead of a larger relational database because the challenge focuses on correctness and architecture rather than infrastructure scale. SQLite is easy to run, easy to review, and good enough for a work-item system that is expected to serve thousands of users, not millions. It keeps local development and submission simple.

## 2) Team-based authorization enforced by the backend

Each work item belongs to a team. Users only access items after verifying membership in that team. The UI does not determine whether an action is allowed; the server checks it each time. This reduces the chance of unauthorized updates and matches the challenge requirement for meaningful authorization.

## 3) Version checks to protect against stale writes

Work items carry a version value. When a user attempts to update an item, the server compares the submitted version with the stored one. If they differ, the request is rejected with a stale-update error. This avoids silent overwrites when two people edit the same item at roughly the same time.

## 4) History as a first-class part of the data model

Important changes are stored in an item history table rather than only in the work item row. This keeps operational reasoning visible: who changed what, when, and why. It also makes the app much easier to debug and review when a decision needs to be explained.

## 5) Secondary processing is asynchronous by design

Notifications and follow-up actions are treated as secondary work rather than part of the main request flow. This keeps the user-facing transaction responsive while still allowing background processing. The core platform is therefore simpler and more reliable under load.

## 6) Functional simplicity over broad feature scope

The app intentionally focuses on correctness around ownership, team access, history, and stale updates instead of trying to build every possible enterprise feature. This matches the challenge's preference for a smaller but well-considered system.
