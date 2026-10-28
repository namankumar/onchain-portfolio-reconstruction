# Synthetic worked examples

These examples describe the package's technical approach. They are fictional and do not describe a real account, portfolio or investigation.

## 1. Find sender transactions from nonce boundaries

Given a public EVM address and a fixed block interval, first read the account nonce immediately before and at the end of the interval. When the nonce changes, binary-search only the changing subranges, then fetch full blocks at the leaves. The result is complete only when the sender nonces in those blocks exactly match the expected sequence.

The portable command requires an address, chain ID, block boundaries, explicit request budget and a provider with historical state. It does not infer incoming transfers, internal activity or smart-account operations.

## 2. Reconcile a supplied movement set exactly

Consider a fictional ledger with an opening native balance, a successful deposit, a protocol call, a returned transfer, and gas from both successful and reverted transactions. The accounting invariant is:

`opening + settled inflows − settled outflows − actual gas = observed ending balance`

A reverted transfer principal is not settled, while its gas is still an expense. The included fixture reconciles to a zero raw-unit difference using integer arithmetic. If an event is unknown or an ending balance is absent, the result remains incomplete.

## 3. Treat provider failure as unresolved evidence

A provider can throttle, omit historical state or return inconsistent blocks. The RPC layer applies a small retry policy, charges each attempt against an explicit budget, caches only validated successful responses and rejects redirect or write methods. A failed request is not cached as a zero result.

For a fixed interval, fresh boundary-hash reads detect a changing chain boundary during the scan. The command returns failure rather than presenting a partial response as complete evidence.

## 4. Build one stateful unsigned preview

A multi-step route cannot safely be evaluated as unrelated snapshots because earlier steps can change the state assumed by later calls. The EVM preview builder emits temporary code that performs a supplied sequence of calls in one discarded evaluation context.

The builder separates large input calldata from previous-call output memory; the test suite includes a synthetic payload larger than 4 KB to protect that layout. It produces bytecode only—no deployment, signing, submission or proof that the route will succeed on a live network.

## 5. Keep evidence states separate

A valid address, a decoded receipt, an observed balance, a complete supplied ledger and an unsigned preview each answer different questions. The package labels these boundaries instead of collapsing them into a single assertion. This is the core design rule: valid retrieval or valid formatting never substitutes for independently verified state.
