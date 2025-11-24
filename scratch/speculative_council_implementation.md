
SPECULATIVE COUNCIL OPTIMIZATION PATTERN
==========================================

Current (Sequential):
  Round 1 → Arbiter → Check convergence → Round 2 → Arbiter → Check...

Optimized (Speculative):
  Round 1 → (Arbiter + Round 2 in parallel) → Check → ...

Implementation Steps:

1. Modify run_deliberation() in council.py

   # Add futures-based execution
   from concurrent.futures import Future, ThreadPoolExecutor

   next_round_future = None  # Holds speculative Round N+1

2. In deliberation loop:

   for round_num in range(1, max_rounds + 1):
       # ... execute Round N personas ...

       # Speculative: Start Round N+1 WHILE Arbiter synthesizing
       if round_num < max_rounds:
           with ThreadPoolExecutor(max_workers=1) as executor:
               next_round_future = executor.submit(
                   prepare_next_round,
                   round_num + 1,
                   round_history,
                   personas
               )

       # Arbiter synthesis (while Round N+1 preparing)
       convergence = detector.check_convergence(output_list)

       if convergence["converged"]:
           # Cancel Round N+1
           if next_round_future:
               next_round_future.cancel()
           break

       # Not converged, wait for Round N+1 (it's already running!)
       if next_round_future:
           next_round_data = next_round_future.result()
           # Use next_round_data for Round N+1
           # (personas already consulted in background)

3. Helper function:

   def prepare_next_round(round_num, history, personas):
       """
       Speculatively prepare next round (runs in background).
       """
       # Build context
       context = build_round_context(proposal, history, ...)

       # Consult personas (in parallel)
       results = consult_personas_parallel(personas, context)

       return {
           "round": round_num,
           "outputs": results,
           "prepared_speculatively": True
       }

Performance Impact:
- Single-round: No change (0% improvement)
- Multi-round: 30-50% speedup (rounds overlap)
- 3-round council: ~40% faster (3 sequential → 2 overlapped)

Complexity: HIGH
Risk: MEDIUM (cancellation logic, context management)
ROI: HIGH (significant speedup for multi-round deliberations)

Status: IMPLEMENTATION PATTERN PROVIDED
Next: Apply to scripts/ops/council.py (requires careful testing)
